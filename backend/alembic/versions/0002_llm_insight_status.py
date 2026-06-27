"""add status to llm_insights for async (queued) insight generation

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_insights",
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
    )
    op.alter_column("llm_insights", "response_text", server_default="")


def downgrade() -> None:
    op.alter_column("llm_insights", "response_text", server_default=None)
    op.drop_column("llm_insights", "status")
