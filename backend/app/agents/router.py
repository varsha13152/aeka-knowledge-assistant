"""Router Agent — classifies query intent and routes to specialists.

Intent categories:
- question: Requires RAG retrieval and synthesis
- summary: Summarize a document or topic
- direct: Can be answered without retrieval (greetings, meta-questions)
- unsafe: Blocked by guardrails
"""

import json

from app.services.llm import llm_client

ROUTER_PROMPT = """You are a query router for an enterprise knowledge assistant.
Classify the user's query into one of these intents:

- "question": The user is asking a factual question that requires searching documents
- "summary": The user wants a summary of a topic or document
- "direct": The query can be answered without document search (greetings, system questions, simple math)

Respond with JSON only:
{{
    "intent": "question" | "summary" | "direct",
    "reasoning": "brief explanation of why",
    "keywords": ["key", "terms", "for", "search"]
}}

User query: {query}"""


async def router_node(state: dict) -> dict:
    """Classify query intent and extract search keywords.

    This node determines the execution path through the agent graph.
    """
    query = state["query"]

    response = await llm_client.complete(
        messages=[{"role": "user", "content": ROUTER_PROMPT.format(query=query)}],
        temperature=0.1,  # Low temperature for consistent classification
        max_tokens=256,
    )

    try:
        result = json.loads(response.content)
        intent = result.get("intent", "question")
        keywords = result.get("keywords", [])
    except (json.JSONDecodeError, KeyError):
        # Default to question if parsing fails
        intent = "question"
        keywords = query.split()[:5]

    # For direct intents, generate a quick response
    direct_answer = ""
    if intent == "direct":
        direct_response = await llm_client.complete(
            messages=[{"role": "user", "content": query}],
            system_prompt="You are a helpful assistant. Give a brief, friendly response.",
            max_tokens=512,
        )
        direct_answer = direct_response.content

    return {
        "intent": intent,
        "routed_to": "research" if intent in ("question", "summary") else "output",
        "final_answer": direct_answer if intent == "direct" else "",
        "agent_steps": state.get("agent_steps", [])
        + [
            {
                "node": "router",
                "action": f"classified_as_{intent}",
                "keywords": keywords,
                "tokens_used": response.input_tokens + response.output_tokens,
            }
        ],
        "total_tokens": state.get("total_tokens", 0)
        + response.input_tokens
        + response.output_tokens,
        "total_cost": state.get("total_cost", 0.0) + response.cost_usd,
    }
