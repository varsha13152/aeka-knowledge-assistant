"""Per-user LLM cost budget enforcement.

Tracks daily usage per user and rejects requests when budget is exceeded.
Budget limits are configured per role.
"""

from datetime import date

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

# Daily budget per role (USD)
DAILY_BUDGET_BY_ROLE: dict[str, float] = {
    "student": 0.50,
    "tutor": 5.00,
    "admin": 50.00,  # Effectively unlimited for reasonable usage
}


async def check_budget(db: AsyncSession, user_id: str, role: str) -> tuple[bool, float]:
    """Check if user has remaining budget for today.

    Returns:
        (is_allowed, remaining_budget_usd)
    """
    daily_limit = DAILY_BUDGET_BY_ROLE.get(role, 0.50)

    # Sum today's cost from chat_messages for this user's sessions
    result = await db.execute(
        text("""
            SELECT COALESCE(SUM(cm.cost_usd), 0) as total_cost
            FROM chat_messages cm
            JOIN chat_sessions cs ON cs.id = cm.session_id
            WHERE cs.user_id = :user_id
              AND cm.created_at::date = :today
              AND cm.cost_usd IS NOT NULL
        """),
        {"user_id": user_id, "today": date.today().isoformat()},
    )
    row = result.fetchone()
    spent_today = float(row.total_cost) if row else 0.0

    remaining = daily_limit - spent_today
    return remaining > 0, remaining


async def record_usage(db: AsyncSession, user_id: str, cost_usd: float) -> None:
    """Record usage (called after LLM response completes).

    Note: The actual cost is recorded on the ChatMessage row — this function
    is a no-op placeholder for future usage tracking table integration.
    """
    pass  # Cost is already stored on ChatMessage.cost_usd
