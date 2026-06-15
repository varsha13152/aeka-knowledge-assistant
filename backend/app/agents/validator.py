"""Validator Agent — detects hallucinations by cross-referencing against source chunks.

Validation strategy:
1. Extract claims from the generated answer
2. Check each claim against the source chunks
3. Flag unsupported or contradicted claims
4. Compute a confidence score

A low confidence score triggers escalation to HITL review.
"""

import json

from app.services.llm import llm_client

VALIDATION_PROMPT = """You are a hallucination detector. Analyze the generated answer against the source context.

For each factual claim in the answer:
1. Check if it is SUPPORTED by the source context
2. Check if it is CONTRADICTED by the source context
3. Check if it is UNSUPPORTED (not mentioned in sources)

Source context:
{context}

Generated answer:
{answer}

Respond with JSON:
{{
    "claims": [
        {{
            "claim": "the specific claim text",
            "status": "supported" | "contradicted" | "unsupported",
            "source_reference": "which source supports/contradicts it, or null",
            "explanation": "brief reasoning"
        }}
    ],
    "confidence_score": 0.0-1.0,
    "summary": "overall assessment",
    "has_hallucinations": true/false
}}"""

CONFIDENCE_THRESHOLD = 0.7  # Below this, escalate to HITL


async def validator_node(state: dict) -> dict:
    """Validate the generated answer against source chunks.

    Performs hallucination detection by having the LLM cross-reference
    each claim in the answer against the retrieved context.
    """
    raw_answer = state.get("raw_answer", "")
    context_chunks = state.get("context_chunks", [])

    if not raw_answer or not context_chunks:
        return {
            "confidence_score": 0.0,
            "is_valid": False,
            "hallucination_flags": [],
            "requires_review": True,
            "review_reason": "No answer or context available for validation",
            "agent_steps": state.get("agent_steps", [])
            + [{"node": "validator", "action": "skipped_no_content"}],
        }

    # Build context string for validation
    context_str = "\n\n---\n\n".join(
        f"[Source {i+1}]: {chunk['content']}" for i, chunk in enumerate(context_chunks)
    )

    # Run validation
    response = await llm_client.complete(
        messages=[
            {
                "role": "user",
                "content": VALIDATION_PROMPT.format(context=context_str, answer=raw_answer),
            }
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    try:
        validation = json.loads(response.content)
        confidence = float(validation.get("confidence_score", 0.5))
        has_hallucinations = validation.get("has_hallucinations", False)
        claims = validation.get("claims", [])
    except (json.JSONDecodeError, ValueError):
        confidence = 0.5
        has_hallucinations = False
        claims = []

    # Determine if review is needed
    requires_review = confidence < CONFIDENCE_THRESHOLD or has_hallucinations

    # Build hallucination flags
    hallucination_flags = [
        claim for claim in claims if claim.get("status") in ("contradicted", "unsupported")
    ]

    return {
        "confidence_score": confidence,
        "is_valid": not has_hallucinations,
        "hallucination_flags": hallucination_flags,
        "requires_review": requires_review,
        "review_reason": (
            f"Low confidence ({confidence:.2f}) with {len(hallucination_flags)} flagged claims"
            if requires_review
            else ""
        ),
        "final_answer": raw_answer if not requires_review else "",
        "agent_steps": state.get("agent_steps", [])
        + [
            {
                "node": "validator",
                "action": "validated",
                "confidence": confidence,
                "hallucinations_found": len(hallucination_flags),
                "requires_review": requires_review,
            }
        ],
        "total_tokens": state.get("total_tokens", 0)
        + response.input_tokens
        + response.output_tokens,
        "total_cost": state.get("total_cost", 0.0) + response.cost_usd,
    }
