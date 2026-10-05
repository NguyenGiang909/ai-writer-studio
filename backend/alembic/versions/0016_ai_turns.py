"""ai_turns — persisted AI call history for session memory

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_turns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column("task", sa.String(32), nullable=False),
        sa.Column("prompt_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("reply_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider", sa.String(32), nullable=False, server_default=""),
        sa.Column("model", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_ai_turns_project_id", "ai_turns", ["project_id"])
    op.create_index("ix_ai_turns_scope_id", "ai_turns", ["scope_id"])
    op.create_index("ix_ai_turns_task", "ai_turns", ["task"])
    op.create_index("ix_ai_turns_created_at", "ai_turns", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_turns")
