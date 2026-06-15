"""Research Agent — performs RAG retrieval and synthesizes answers.

This agent:
1. Retrieves relevant chunks using hybrid search
2. Builds an optimized context window within token budget
3. Generates a cited answer grounded in the retrieved sources
"""

from app.db.session import async_session_factory
from app.services.llm import llm_client
from app.services.retrieval import build_context_window, hybrid_search

RESEARCH_PROMPT = """Based on the following context from uploaded documents, answer the user's question.

Rules:
1. Only use information present in the context below
2. Cite sources using [Source N] notation corresponding to the numbered sources
3. If the context doesn't contain enough information, clearly state what's missing
4. Be thorough but concise
5. Structure your answer with clear sections if the question is complex

Context:
{context}

---

Question: {query}

Provide a well-structured answer with citations:"""


async def research_node(state: dict) -> dict:
    """Retrieve relevant documents and synthesize a cited answer.

    Uses hybrid search (semantic + keyword) to find the best chunks,
    then generates an answer grounded in the retrieved context.
    """
    query = state["query"]

    # Perform hybrid search
    async with async_session_factory() as db:
        results = await hybrid_search(db=db, query=query, top_k=10)

    # Build context window within token budget
    context, included_chunks = build_context_window(results, max_tokens=4096)

    if not included_chunks:
        return {
            "raw_answer": "I couldn't find any relevant information in the uploaded documents to answer this question.",
            "context_chunks": [],
            "sources": [],
            "confidence_score": 0.0,
            "agent_steps": state.get("agent_steps", [])
            + [{"node": "research", "action": "no_relevant_chunks_found"}],
        }

    # Generate answer
    response = await llm_client.complete(
        messages=[
            {"role": "user", "content": RESEARCH_PROMPT.format(context=context, query=query)}
        ],
        max_tokens=2048,
        temperature=0.3,  # Lower temperature for factual answers
    )

    # Package source references
    sources = [
        {
            "source_index": i + 1,
            "chunk_id": str(chunk.chunk_id),
            "document_id": str(chunk.document_id),
            "content_preview": chunk.content[:200],
            "relevance_score": chunk.fused_score,
        }
        for i, chunk in enumerate(included_chunks)
    ]

    return {
        "raw_answer": response.content,
        "context_chunks": [
            {"content": chunk.content, "chunk_id": str(chunk.chunk_id)}
            for chunk in included_chunks
        ],
        "sources": sources,
        "agent_steps": state.get("agent_steps", [])
        + [
            {
                "node": "research",
                "action": "retrieved_and_synthesized",
                "chunks_used": len(included_chunks),
                "tokens_used": response.input_tokens + response.output_tokens,
            }
        ],
        "total_tokens": state.get("total_tokens", 0)
        + response.input_tokens
        + response.output_tokens,
        "total_cost": state.get("total_cost", 0.0) + response.cost_usd,
    }
