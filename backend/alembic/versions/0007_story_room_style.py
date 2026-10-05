
from alembic import op
import sqlalchemy as sa
revision="0007"; down_revision="0006"
def upgrade():
    op.create_table("discussion_threads",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("role",sa.String(40),nullable=False),sa.Column("summary",sa.Text()))
    op.create_table("discussion_messages",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("thread_id",sa.String(36),sa.ForeignKey("discussion_threads.id",ondelete="CASCADE"),nullable=False),sa.Column("author",sa.String(16),nullable=False),sa.Column("content",sa.Text(),nullable=False),sa.Column("pinned",sa.Boolean(),nullable=False))
    op.create_table("style_preferences",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("style_profile_id",sa.String(36),sa.ForeignKey("style_profiles.id",ondelete="CASCADE"),nullable=False),sa.Column("preference_type",sa.String(16),nullable=False),sa.Column("pattern",sa.Text(),nullable=False),sa.Column("explicit_author_feedback",sa.Boolean(),nullable=False))
def downgrade():
    for n in ["style_preferences","discussion_messages","discussion_threads"]: op.drop_table(n)
