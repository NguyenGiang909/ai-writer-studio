
from alembic import op
import sqlalchemy as sa
revision="0008"; down_revision="0007"
def upgrade():
    op.create_table("suggested_changes",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("scene_id",sa.String(36),sa.ForeignKey("scenes.id",ondelete="SET NULL")),sa.Column("change_type",sa.String(40),nullable=False),sa.Column("payload_json",sa.Text(),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("auto_applied",sa.Boolean(),nullable=False))
def downgrade(): op.drop_table("suggested_changes")
