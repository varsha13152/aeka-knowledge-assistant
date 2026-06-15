"""Hybrid retrieval: pgvector semantic search + BM25 keyword search.

Combines dense vector similarity (cosine) with sparse keyword matching
using PostgreSQL's full-text search, then fuses results via Reciprocal Rank Fusion.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding import embedding_service


@dataclass
class RetrievalResult:
    """A retrieved chunk with relevance scores."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    token_count: int
    semantic_score: float  # Cosine similarity (0-1)
    keyword_score: float  # BM25-style rank score
    fused_score: float  # RRF combined score
    metadata: dict | None = None


async def hybrid_search(
    db: AsyncSession,
    query: str,
    top_k: int = 10,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    rrf_k: int = 60,
) -> list[RetrievalResult]:
    """Perform hybrid search combining semantic and keyword retrieval.

    Strategy:
    1. Semantic: Embed the query, find nearest neighbors via pgvector
    2. Keyword: Full-text search using PostgreSQL ts_rank
    3. Fusion: Reciprocal Rank Fusion (RRF) to combine both rankings

    Args:
        db: Database session
        query: User's search query
        top_k: Number of results to return
        semantic_weight: Weight for semantic search in RRF
        keyword_weight: Weight for keyword search in RRF
        rrf_k: RRF constant (higher = less aggressive rank difference)
    """
    # Get query embedding
    query_embedding = await embedding_service.embed_single(query)

    # ─── Semantic Search (pgvector cosine distance) ─────────────────────
    semantic_sql = text("""
        SELECT
            id AS chunk_id,
            document_id,
            content,
            token_count,
            metadata_json,
            1 - (embedding <=> :embedding::vector) AS similarity
        FROM document_chunks
        ORDER BY embedding <=> :embedding::vector
        LIMIT :limit
    """)

    semantic_results = await db.execute(
        semantic_sql,
        {"embedding": str(query_embedding), "limit": top_k * 2},
    )
    semantic_rows = semantic_results.fetchall()

    # ─── Keyword Search (PostgreSQL full-text search) ───────────────────
    keyword_sql = text("""
        SELECT
            id AS chunk_id,
            document_id,
            content,
            token_count,
            metadata_json,
            ts_rank_cd(
                to_tsvector('english', content),
                plainto_tsquery('english', :query)
            ) AS rank
        FROM document_chunks
        WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :limit
    """)

    keyword_results = await db.execute(
        keyword_sql,
        {"query": query, "limit": top_k * 2},
    )
    keyword_rows = keyword_results.fetchall()

    # ─── Reciprocal Rank Fusion ─────────────────────────────────────────
    chunk_scores: dict[uuid.UUID, dict] = {}

    # Score semantic results
    for rank, row in enumerate(semantic_rows, start=1):
        chunk_id = row.chunk_id
        rrf_score = semantic_weight / (rrf_k + rank)
        chunk_scores[chunk_id] = {
            "chunk_id": chunk_id,
            "document_id": row.document_id,
            "content": row.content,
            "token_count": row.token_count,
            "metadata": row.metadata_json,
            "semantic_score": float(row.similarity),
            "keyword_score": 0.0,
            "rrf_semantic": rrf_score,
            "rrf_keyword": 0.0,
        }

    # Score keyword results
    for rank, row in enumerate(keyword_rows, start=1):
        chunk_id = row.chunk_id
        rrf_score = keyword_weight / (rrf_k + rank)

        if chunk_id in chunk_scores:
            chunk_scores[chunk_id]["keyword_score"] = float(row.rank)
            chunk_scores[chunk_id]["rrf_keyword"] = rrf_score
        else:
            chunk_scores[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": row.document_id,
                "content": row.content,
                "token_count": row.token_count,
                "metadata": row.metadata_json,
                "semantic_score": 0.0,
                "keyword_score": float(row.rank),
                "rrf_semantic": 0.0,
                "rrf_keyword": rrf_score,
            }

    # Compute fused scores and sort
    results = []
    for data in chunk_scores.values():
        fused = data["rrf_semantic"] + data["rrf_keyword"]
        results.append(
            RetrievalResult(
                chunk_id=data["chunk_id"],
                document_id=data["document_id"],
                content=data["content"],
                token_count=data["token_count"],
                semantic_score=data["semantic_score"],
                keyword_score=data["keyword_score"],
                fused_score=fused,
                metadata=data["metadata"],
            )
        )

    results.sort(key=lambda r: r.fused_score, reverse=True)
    return results[:top_k]


def build_context_window(
    results: list[RetrievalResult],
    max_tokens: int = 4096,
) -> tuple[str, list[RetrievalResult]]:
    """Build a context string from retrieval results, respecting token budget.

    Returns:
        Tuple of (context string, chunks that were included)
    """
    included: list[RetrievalResult] = []
    total_tokens = 0

    for result in results:
        if total_tokens + result.token_count > max_tokens:
            break
        included.append(result)
        total_tokens += result.token_count

    context_parts = []
    for i, chunk in enumerate(included, 1):
        context_parts.append(f"[Source {i}]\n{chunk.content}")

    return "\n\n---\n\n".join(context_parts), included
