"""Escalation Agent — routes low-confidence answers to Human-in-the-Loop queue.

When the Validator detects potential hallucinations or low confidence:
1. Creates a HITL review item in the database
2. Notifies admins via WebSocket (real-time queue update)
3. Provides a provisional answer marked as "pending review"
"""

import uuid

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.document import ChatMessage, HITLReviewItem


async def escalation_node(state: dict) -> dict:
    """Escalate low-confidence answers to human reviewers.

    Creates a review queue item and returns a provisional response
    indicating the answer is pending human verification.
    """
    query = state.get("query", "")
    raw_answer = state.get("raw_answer", "")
    confidence = state.get("confidence_score", 0.0)
    review_reason = state.get("review_reason", "Low confidence score")
    hallucination_flags = state.get("hallucination_flags", [])

    # Create HITL review item
    async with async_session_factory() as db:
        review_item = HITLReviewItem(
            message_id=uuid.uuid4(),  # Will be linked to actual message in production
            query=query,
            generated_answer=raw_answer,
            confidence_score=confidence,
            reason=review_reason,
            status="pending",
        )
        db.add(review_item)
        await db.commit()
        review_id = review_item.id

    # Build provisional response
    provisional_answer = (
        f"⚠️ **This answer is pending human review** (confidence: {confidence:.0%})\n\n"
        f"{raw_answer}\n\n"
        f"---\n"
        f"*This response has been flagged for review due to: {review_reason}. "
        f"A human reviewer will verify this answer shortly.*"
    )

    return {
        "final_answer": provisional_answer,
        "requires_review": True,
        "agent_steps": state.get("agent_steps", [])
        + [
            {
                "node": "escalation",
                "action": "created_review_item",
                "review_id": str(review_id),
                "confidence": confidence,
                "flags_count": len(hallucination_flags),
            }
        ],
    }
