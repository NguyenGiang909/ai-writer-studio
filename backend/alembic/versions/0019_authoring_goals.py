"""authoring run goals — target_chapters + words_per_scene."""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.add_column(sa.Column("target_chapters", sa.Integer(), nullable=True))
        b.add_column(sa.Column("words_per_scene", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.drop_column("words_per_scene")
        b.drop_column("target_chapters")
