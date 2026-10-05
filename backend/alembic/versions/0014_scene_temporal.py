"""scene story_time + narrative_order (temporal axes)

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("story_time", sa.Integer(), nullable=True))
    op.add_column("scenes", sa.Column("narrative_order", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("scenes", "narrative_order")
    op.drop_column("scenes", "story_time")
