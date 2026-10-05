"""scene author brief

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("brief_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scenes", "brief_json")
