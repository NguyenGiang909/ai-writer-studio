"""Author-controlled thread priorities."""
from alembic import op
import sqlalchemy as sa
revision="0029"
down_revision="0028"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("threads",sa.Column("must_resolve",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column("threads",sa.Column("important",sa.Boolean(),nullable=False,server_default=sa.false()))
def downgrade():
    with op.batch_alter_table("threads") as b:
        b.drop_column("important")
        b.drop_column("must_resolve")
