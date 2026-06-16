"""HITL Review Queue endpoints — list, approve, reject, edit."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import AdminUser
from app.core.dependencies import DBSession
from app.models.document import HITLReviewItem

router = APIRouter(prefix="/review", tags=["review"])


# ─── Schemas ────────────────────────────────────────────────────────────────


class ReviewItemResponse(BaseModel):
    id: str
    query: str
    generated_answer: str
    confidence_score: float
    reason: str
    status: str
    reviewer_notes: str | None
    created_at: str


class ReviewQueueResponse(BaseModel):
    items: list[ReviewItemResponse]
    total_pending: int


class UpdateReviewRequest(BaseModel):
    status: str  # approved | rejected | edited
    edited_answer: str | None = None
    reviewer_notes: str | None = None


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/queue", response_model=ReviewQueueResponse)
async def get_review_queue(db: DBSession):
    """Get all items in the review queue (pending first)."""
    result = await db.execute(
        select(HITLReviewItem).order_by(
            # Pending items first, then by creation date
            HITLReviewItem.status.desc(),
            HITLReviewItem.created_at.desc(),
        )
    )
    items = result.scalars().all()

    pending_count = sum(1 for i in items if i.status == "pending")

    return ReviewQueueResponse(
        items=[
            ReviewItemResponse(
                id=str(item.id),
                query=item.query,
                generated_answer=item.generated_answer,
                confidence_score=item.confidence_score,
                reason=item.reason,
                status=item.status,
                reviewer_notes=item.reviewer_notes,
                created_at=item.created_at.isoformat(),
            )
            for item in items
        ],
        total_pending=pending_count,
    )


@router.patch("/{item_id}")
async def update_review_item(item_id: uuid.UUID, request: UpdateReviewRequest, db: DBSession):
    """Approve, reject, or edit a review item."""
    result = await db.execute(select(HITLReviewItem).where(HITLReviewItem.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    if request.status not in ("approved", "rejected", "edited"):
        raise HTTPException(status_code=400, detail="Status must be: approved, rejected, or edited")

    item.status = request.status
    item.reviewed_at = datetime.now(timezone.utc)

    if request.reviewer_notes:
        item.reviewer_notes = request.reviewer_notes

    if request.status == "edited" and request.edited_answer:
        item.generated_answer = request.edited_answer

    return {
        "id": str(item.id),
        "status": item.status,
        "reviewed_at": item.reviewed_at.isoformat(),
    }
