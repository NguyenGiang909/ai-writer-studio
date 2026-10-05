"""scene location_id + author decision rationale/rejected

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("location_id", sa.String(36), nullable=True))
    op.add_column("author_decisions", sa.Column("rationale", sa.Text(), nullable=True))
    op.add_column("author_decisions", sa.Column("rejected_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("author_decisions", "rejected_json")
    op.drop_column("author_decisions", "rationale")
    op.drop_column("scenes", "location_id")
