"""authoring run flow — batch (khung trước) / rolling (sóng theo hồi) + pause_after_wave."""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.add_column(sa.Column("flow", sa.String(length=16), nullable=False,
                               server_default="batch"))
        b.add_column(sa.Column("pause_after_wave", sa.Boolean(), nullable=False,
                               server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("authoring_runs") as b:
        b.drop_column("pause_after_wave")
        b.drop_column("flow")
