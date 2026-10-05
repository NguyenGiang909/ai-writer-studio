"""scene_versions — prose history snapshots for scene editor

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", sa.String(36), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(240), nullable=True),
        sa.Column("prose", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_scene_versions_project_id", "scene_versions", ["project_id"])
    op.create_index("ix_scene_versions_scene_id", "scene_versions", ["scene_id"])


def downgrade() -> None:
    op.drop_table("scene_versions")
