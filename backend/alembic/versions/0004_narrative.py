
from alembic import op
import sqlalchemy as sa
revision="0004"; down_revision="0003"
def upgrade():
    op.create_table("threads",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("thread_type",sa.String(32),nullable=False),sa.Column("status",sa.String(24),nullable=False),sa.Column("description",sa.Text()),sa.Column("planned_payoff_order",sa.Integer()))
    op.create_table("thread_beats",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("thread_id",sa.String(36),sa.ForeignKey("threads.id",ondelete="CASCADE"),nullable=False),sa.Column("scene_id",sa.String(36),sa.ForeignKey("scenes.id",ondelete="SET NULL")),sa.Column("beat_type",sa.String(24),nullable=False),sa.Column("narrative_order",sa.Integer()),sa.Column("notes",sa.Text()))
    op.create_table("thread_dependencies",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("thread_id",sa.String(36),sa.ForeignKey("threads.id",ondelete="CASCADE"),nullable=False),sa.Column("depends_on_thread_id",sa.String(36),sa.ForeignKey("threads.id",ondelete="CASCADE"),nullable=False))
def downgrade():
    for n in ["thread_dependencies","thread_beats","threads"]: op.drop_table(n)
