
from alembic import op
import sqlalchemy as sa
revision="0010"; down_revision="0009"
def upgrade():
    op.create_table("provider_credentials",sa.Column("id",sa.String(36),primary_key=True),sa.Column("user_id",sa.String(36),nullable=False),sa.Column("provider",sa.String(32),nullable=False),sa.Column("encrypted_secret",sa.Text(),nullable=False),sa.Column("key_hint",sa.String(16),nullable=False),sa.Column("status",sa.String(20),nullable=False))
    op.create_table("model_preferences",sa.Column("id",sa.String(36),primary_key=True),sa.Column("user_id",sa.String(36),nullable=False),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE")),sa.Column("task",sa.String(32),nullable=False),sa.Column("provider",sa.String(32),nullable=False),sa.Column("model",sa.String(120),nullable=False))
    op.create_table("story_branches",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("name",sa.String(240),nullable=False),sa.Column("status",sa.String(20),nullable=False))
    op.create_table("branch_changes",sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),sa.Column("branch_id",sa.String(36),sa.ForeignKey("story_branches.id",ondelete="CASCADE"),nullable=False),sa.Column("change_type",sa.String(32),nullable=False),sa.Column("payload_json",sa.Text(),nullable=False),sa.Column("merged_decision_id",sa.String(36),sa.ForeignKey("author_decisions.id",ondelete="SET NULL")))
def downgrade():
    for n in ["branch_changes","story_branches","model_preferences","provider_credentials"]: op.drop_table(n)
