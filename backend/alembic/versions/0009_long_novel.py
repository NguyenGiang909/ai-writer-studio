
from alembic import op
import sqlalchemy as sa
revision="0009"; down_revision="0008"
def upgrade():
    op.create_table("story_summaries",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("scope_type",sa.String(16),nullable=False),sa.Column("scope_id",sa.String(36),nullable=False),sa.Column("summary",sa.Text(),nullable=False),sa.Column("stale",sa.Boolean(),nullable=False),sa.Column("narrative_end",sa.Integer()))
    op.create_table("retcon_proposals",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("target_type",sa.String(24),nullable=False),sa.Column("target_id",sa.String(36),nullable=False),sa.Column("proposal",sa.Text(),nullable=False),sa.Column("impact_snapshot_json",sa.Text(),nullable=False))
def downgrade():
    op.drop_table("retcon_proposals"); op.drop_table("story_summaries")
