"""Add user ownership to documents and chat_sessions.

Adds user_id column (Clerk user ID string) to documents and chat_sessions
tables for access control filtering.

Revision ID: 003
"""

import sqlalchemy as sa
from alembic import op


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id to documents (nullable initially for migration, then set NOT NULL)
    op.add_column("documents", sa.Column("user_id", sa.String(64), nullable=True))
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    # Add user_id to chat_sessions
    op.add_column("chat_sessions", sa.Column("user_id", sa.String(64), nullable=True))
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_user_id")
    op.drop_column("chat_sessions", "user_id")
    op.drop_index("ix_documents_user_id")
    op.drop_column("documents", "user_id")
