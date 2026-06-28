"""cascade-delete forecast_runs/llm_insights when their parent is deleted

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-28
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("forecast_runs_dataset_id_fkey", "forecast_runs", type_="foreignkey")
    op.create_foreign_key(
        "forecast_runs_dataset_id_fkey",
        "forecast_runs",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("llm_insights_forecast_run_id_fkey", "llm_insights", type_="foreignkey")
    op.create_foreign_key(
        "llm_insights_forecast_run_id_fkey",
        "llm_insights",
        "forecast_runs",
        ["forecast_run_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("llm_insights_forecast_run_id_fkey", "llm_insights", type_="foreignkey")
    op.create_foreign_key(
        "llm_insights_forecast_run_id_fkey",
        "llm_insights",
        "forecast_runs",
        ["forecast_run_id"],
        ["id"],
    )

    op.drop_constraint("forecast_runs_dataset_id_fkey", "forecast_runs", type_="foreignkey")
    op.create_foreign_key(
        "forecast_runs_dataset_id_fkey",
        "forecast_runs",
        "datasets",
        ["dataset_id"],
        ["id"],
    )
