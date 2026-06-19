"""Add full-text search GIN index for keyword search performance.

The existing trigram index (gin_trgm_ops) does NOT support
to_tsvector/plainto_tsquery operations. This adds the correct index.

Revision ID: 002
"""

from alembic import op


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Full-text search index for keyword search (to_tsvector @@ plainto_tsquery)
    op.execute(
        "CREATE INDEX ix_chunks_content_fts ON document_chunks "
        "USING gin (to_tsvector('english', content))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_content_fts")
