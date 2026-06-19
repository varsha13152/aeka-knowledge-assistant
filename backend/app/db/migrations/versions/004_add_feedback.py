"""Add feedback tables for message ratings and general app feedback.

Revision ID: 004
"""

import sqlalchemy as sa
from alembic import op


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Message feedback (thumbs up/down per AI response)
    op.create_table(
        "message_feedback",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("rating", sa.String(16), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # One feedback per user per message
    op.create_index(
        "ix_message_feedback_unique",
        "message_feedback",
        ["message_id", "user_id"],
        unique=True,
    )

    # General app feedback
    op.create_table(
        "general_feedback",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_general_feedback_user_id", "general_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_table("general_feedback")
    op.drop_table("message_feedback")
