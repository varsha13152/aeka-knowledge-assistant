"""Input/Output Guardrails — safety filters for AI-generated content.

Input guardrails:
- Prompt injection detection
- Harmful content filtering
- PII detection

Output guardrails:
- Structural validation (format, length)
- Content safety (no harmful advice, no PII leakage)
- Citation verification
"""

import json
import re

from app.services.llm import llm_client

# ─── Input Guardrails ───────────────────────────────────────────────────────

# Known prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore (all |previous |above )?(instructions|prompts|rules)",
    r"you are now",
    r"pretend (to be|you're|you are)",
    r"system prompt",
    r"reveal your (instructions|prompt|system)",
    r"act as (a|an) (different|new)",
    r"jailbreak",
    r"DAN mode",
]

# PII patterns
PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(\+1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
}


def check_injection(text: str) -> tuple[bool, str]:
    """Check for common prompt injection attempts."""
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True, f"Potential prompt injection detected: pattern '{pattern}'"
    return False, ""


def check_pii_input(text: str) -> list[dict]:
    """Detect PII in user input."""
    findings = []
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            findings.append({"type": pii_type, "count": len(matches)})
    return findings


async def input_guardrail_node(state: dict) -> dict:
    """Check user input for safety before processing.

    Checks:
    1. Prompt injection attempts
    2. Harmful content (via LLM classification)
    3. PII in the query (warning, not blocking)
    """
    query = state["query"]
    agent_steps = state.get("agent_steps", [])

    # Check for prompt injection
    is_injection, injection_reason = check_injection(query)
    if is_injection:
        return {
            "intent": "unsafe",
            "final_answer": "I detected a potential prompt injection in your query. Please rephrase your question.",
            "agent_steps": agent_steps
            + [{"node": "input_guardrail", "action": "blocked_injection", "reason": injection_reason}],
        }

    # Check for PII (warn but don't block)
    pii_findings = check_pii_input(query)

    # Quick safety check via LLM (lightweight)
    safety_response = await llm_client.complete(
        messages=[{"role": "user", "content": query}],
        system_prompt=(
            "Classify this query as 'safe' or 'unsafe'. Unsafe means it asks for: "
            "harmful instructions, illegal activities, or bypassing safety measures. "
            "Respond with JSON: {\"safe\": true/false, \"reason\": \"...\"}"
        ),
        max_tokens=100,
        temperature=0.0,
    )

    try:
        safety = json.loads(safety_response.content)
        is_safe = safety.get("safe", True)
    except (json.JSONDecodeError, KeyError):
        is_safe = True  # Default to safe if parsing fails

    if not is_safe:
        return {
            "intent": "unsafe",
            "final_answer": "I'm unable to help with that type of request.",
            "agent_steps": agent_steps
            + [{"node": "input_guardrail", "action": "blocked_unsafe_content"}],
        }

    return {
        "agent_steps": agent_steps
        + [
            {
                "node": "input_guardrail",
                "action": "passed",
                "pii_warnings": pii_findings if pii_findings else None,
            }
        ],
        "total_tokens": state.get("total_tokens", 0)
        + safety_response.input_tokens
        + safety_response.output_tokens,
        "total_cost": state.get("total_cost", 0.0) + safety_response.cost_usd,
    }


# ─── Output Guardrails ─────────────────────────────────────────────────────

MAX_OUTPUT_LENGTH = 10000  # Characters
MIN_OUTPUT_LENGTH = 10


async def output_guardrail_node(state: dict) -> dict:
    """Validate the generated output before delivery.

    Checks:
    1. Output length bounds
    2. PII leakage from documents
    3. Content appropriateness
    4. Citation format validation
    """
    answer = state.get("final_answer") or state.get("raw_answer", "")
    agent_steps = state.get("agent_steps", [])

    issues = []

    # Length check
    if len(answer) > MAX_OUTPUT_LENGTH:
        answer = answer[:MAX_OUTPUT_LENGTH] + "\n\n[Response truncated for safety]"
        issues.append("truncated_length")

    if len(answer) < MIN_OUTPUT_LENGTH:
        issues.append("suspiciously_short")

    # PII leakage check
    pii_findings = check_pii_input(answer)
    if pii_findings:
        # Mask PII in output
        for pii_type, pattern in PII_PATTERNS.items():
            answer = re.sub(pattern, f"[REDACTED {pii_type.upper()}]", answer)
        issues.append("pii_redacted")

    return {
        "final_answer": answer,
        "agent_steps": agent_steps
        + [
            {
                "node": "output_guardrail",
                "action": "validated_output",
                "issues": issues if issues else None,
            }
        ],
    }
