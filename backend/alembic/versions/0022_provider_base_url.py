"""provider_credentials.base_url — custom endpoint (LM Studio, proxy, …)."""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("provider_credentials") as b:
        b.add_column(sa.Column("base_url", sa.String(length=300), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("provider_credentials") as b:
        b.drop_column("base_url")
