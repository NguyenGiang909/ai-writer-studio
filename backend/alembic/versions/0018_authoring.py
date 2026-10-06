"""authoring pipeline — runs, steps, entity provenance

Revision ID: 0018
Revises: 0017
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authoring_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("phase", sa.String(24), nullable=False, server_default="premise"),
        sa.Column("status", sa.String(24), nullable=False, server_default="running"),
        sa.Column("stage_payload_json", sa.Text(), nullable=True),
        sa.Column("cursor_json", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_authoring_runs_project_id", "authoring_runs", ["project_id"])

    op.create_table(
        "authoring_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("authoring_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_key", sa.String(120), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("input_json", sa.Text(), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_authoring_steps_run_id", "authoring_steps", ["run_id"])
    op.create_index("ix_authoring_steps_project_id", "authoring_steps", ["project_id"])
    op.create_index("ix_authoring_steps_step_key", "authoring_steps", ["step_key"])

    op.create_table(
        "entity_provenance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=True),
        sa.Column("origin", sa.String(16), nullable=False, server_default="ai"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_entity_provenance_project_id", "entity_provenance", ["project_id"])
    op.create_index("ix_entity_provenance_entity_type", "entity_provenance", ["entity_type"])
    op.create_index("ix_entity_provenance_entity_id", "entity_provenance", ["entity_id"])
    op.create_index("ix_entity_provenance_run_id", "entity_provenance", ["run_id"])


def downgrade() -> None:
    op.drop_table("entity_provenance")
    op.drop_table("authoring_steps")
    op.drop_table("authoring_runs")
