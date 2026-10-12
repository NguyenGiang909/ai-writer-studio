"""Style rules: lifecycle + strength + scope + provenance (Novel Humanizer port)."""
from alembic import op
import sqlalchemy as sa
revision="0030"
down_revision="0029"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("style_preferences",sa.Column("strength",sa.String(16),nullable=False,server_default="PREFERRED"))
    op.add_column("style_preferences",sa.Column("status",sa.String(16),nullable=False,server_default="confirmed"))
    op.add_column("style_preferences",sa.Column("source",sa.String(24),nullable=False,server_default="explicit"))
    op.add_column("style_preferences",sa.Column("attribute",sa.String(80)))
    op.add_column("style_preferences",sa.Column("scope_type",sa.String(32)))
    op.add_column("style_preferences",sa.Column("scope_id",sa.String(36)))
    op.add_column("style_preferences",sa.Column("evidence",sa.Text))
    op.add_column("style_preferences",sa.Column("supersedes_id",sa.String(36)))
    op.add_column("style_preferences",sa.Column("updated_at",sa.String(40)))
def downgrade():
    with op.batch_alter_table("style_preferences") as b:
        for c in ("updated_at","supersedes_id","evidence","scope_id","scope_type","attribute","source","status","strength"):
            b.drop_column(c)
