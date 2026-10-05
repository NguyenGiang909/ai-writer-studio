
from alembic import op
import sqlalchemy as sa
revision="0011"; down_revision="0010"
def upgrade():
    op.add_column("scenes", sa.Column("skeleton", sa.Text(), nullable=True))
def downgrade():
    op.drop_column("scenes", "skeleton")
