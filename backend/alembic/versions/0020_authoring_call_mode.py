"""authoring run call_mode — safe (call nhỏ) / fast (call gộp, API mạnh)."""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.add_column(sa.Column("call_mode", sa.String(length=16), nullable=False,
                               server_default="safe"))


def downgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.drop_column("call_mode")
