"""authoring run goal_mode — end (viết hết) / waves (theo tiến độ, dừng mỗi hồi)."""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.add_column(sa.Column("goal_mode", sa.String(length=16), nullable=False,
                               server_default="end"))


def downgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.drop_column("goal_mode")
