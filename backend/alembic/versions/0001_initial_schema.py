"""initial schema: organizations, users, datasets, forecast_runs, llm_insights

Revision ID: 0001
Revises:
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("column_mapping", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_datasets_org_id", "datasets", ["org_id"])

    op.create_table(
        "forecast_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("forecast_params", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_forecast_runs_org_id", "forecast_runs", ["org_id"])
    op.create_index("ix_forecast_runs_dataset_id", "forecast_runs", ["dataset_id"])

    op.create_table(
        "llm_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "forecast_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("forecast_runs.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("response_text", sa.Text, nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_insights_forecast_run_id", "llm_insights", ["forecast_run_id"])


def downgrade() -> None:
    op.drop_table("llm_insights")
    op.drop_table("forecast_runs")
    op.drop_table("datasets")
    op.drop_table("users")
    op.drop_table("organizations")
