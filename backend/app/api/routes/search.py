"""Search endpoints for hybrid retrieval."""

import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser
from app.core.dependencies import DBSession
from app.core.rate_limit import limiter
from app.services.retrieval import hybrid_search

router = APIRouter(prefix="/search", tags=["search"])


# ─── Schemas ────────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    token_count: int
    semantic_score: float
    keyword_score: float
    fused_score: float


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    query: str
    total_results: int


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search_documents(request: SearchRequest, req: Request, db: DBSession, current_user: CurrentUser):
    """Perform hybrid search across all document chunks.

    Combines semantic (vector) search with keyword (BM25) search using
    Reciprocal Rank Fusion for optimal retrieval quality.
    """
    results = await hybrid_search(
        db=db,
        query=request.query,
        top_k=request.top_k,
        semantic_weight=request.semantic_weight,
        keyword_weight=request.keyword_weight,
    )

    return SearchResponse(
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                content=r.content,
                token_count=r.token_count,
                semantic_score=r.semantic_score,
                keyword_score=r.keyword_score,
                fused_score=r.fused_score,
            )
            for r in results
        ],
        query=request.query,
        total_results=len(results),
    )
