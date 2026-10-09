"""provider_credentials.tier — năng lực gateway (low/standard/strong, NULL=auto theo provider)."""
from alembic import op
import sqlalchemy as sa

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("provider_credentials") as b:
        b.add_column(sa.Column("tier", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("provider_credentials") as b:
        b.drop_column("tier")
