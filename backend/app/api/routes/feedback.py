"""Feedback endpoints — message ratings and general app feedback."""

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.auth import AdminUser, CurrentUser
from app.core.dependencies import DBSession
from app.models.document import GeneralFeedback, MessageFeedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ─── Schemas ────────────────────────────────────────────────────────────────


class MessageFeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: Literal["thumbs_up", "thumbs_down"]
    comment: str | None = Field(None, max_length=1000)


class MessageFeedbackResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    rating: str
    comment: str | None
    created_at: str


class GeneralFeedbackRequest(BaseModel):
    category: Literal["bug", "feature", "ux", "other"]
    message: str = Field(..., min_length=1, max_length=5000)


class GeneralFeedbackResponse(BaseModel):
    id: uuid.UUID
    category: str
    message: str
    created_at: str


class FeedbackStatsResponse(BaseModel):
    total_thumbs_up: int
    total_thumbs_down: int
    recent_negative: list[dict]


# ─── Message Feedback Endpoints ─────────────────────────────────────────────


@router.post("/", response_model=MessageFeedbackResponse, status_code=201)
async def submit_message_feedback(
    request: MessageFeedbackRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Submit thumbs up/down feedback for an AI response.

    One rating per user per message — submitting again updates the existing rating.
    """
    # Check if user already rated this message
    existing = await db.execute(
        select(MessageFeedback).where(
            MessageFeedback.message_id == request.message_id,
            MessageFeedback.user_id == current_user.id,
        )
    )
    feedback = existing.scalar_one_or_none()

    if feedback:
        # Update existing rating
        feedback.rating = request.rating
        feedback.comment = request.comment
    else:
        # Create new feedback
        feedback = MessageFeedback(
            message_id=request.message_id,
            user_id=current_user.id,
            rating=request.rating,
            comment=request.comment,
        )
        db.add(feedback)

    await db.flush()

    return MessageFeedbackResponse(
        id=feedback.id,
        message_id=feedback.message_id,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at.isoformat(),
    )


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(db: DBSession, current_user: AdminUser):
    """Get aggregated feedback statistics. Requires admin/tutor role."""
    # Count totals
    up_result = await db.execute(
        select(func.count()).select_from(MessageFeedback).where(
            MessageFeedback.rating == "thumbs_up"
        )
    )
    total_up = up_result.scalar_one()

    down_result = await db.execute(
        select(func.count()).select_from(MessageFeedback).where(
            MessageFeedback.rating == "thumbs_down"
        )
    )
    total_down = down_result.scalar_one()

    # Recent negative feedback
    recent = await db.execute(
        select(MessageFeedback)
        .where(MessageFeedback.rating == "thumbs_down")
        .order_by(MessageFeedback.created_at.desc())
        .limit(20)
    )
    recent_items = recent.scalars().all()

    return FeedbackStatsResponse(
        total_thumbs_up=total_up,
        total_thumbs_down=total_down,
        recent_negative=[
            {
                "id": str(f.id),
                "message_id": str(f.message_id),
                "comment": f.comment,
                "created_at": f.created_at.isoformat(),
            }
            for f in recent_items
        ],
    )


# ─── General Feedback Endpoints ──────────────────────────────────────────────


@router.post("/general", response_model=GeneralFeedbackResponse, status_code=201)
async def submit_general_feedback(
    request: GeneralFeedbackRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """Submit general app feedback (bug reports, feature requests, etc.)."""
    feedback = GeneralFeedback(
        user_id=current_user.id,
        category=request.category,
        message=request.message,
    )
    db.add(feedback)
    await db.flush()

    return GeneralFeedbackResponse(
        id=feedback.id,
        category=feedback.category,
        message=feedback.message,
        created_at=feedback.created_at.isoformat(),
    )


@router.get("/general", response_model=list[GeneralFeedbackResponse])
async def list_general_feedback(db: DBSession, current_user: AdminUser, limit: int = 50):
    """List all general feedback. Requires admin/tutor role."""
    limit = min(limit, 100)
    result = await db.execute(
        select(GeneralFeedback).order_by(GeneralFeedback.created_at.desc()).limit(limit)
    )
    items = result.scalars().all()

    return [
        GeneralFeedbackResponse(
            id=f.id,
            category=f.category,
            message=f.message,
            created_at=f.created_at.isoformat(),
        )
        for f in items
    ]
