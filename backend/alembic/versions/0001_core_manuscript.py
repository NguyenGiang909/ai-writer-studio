from alembic import op
import sqlalchemy as sa
revision="0001"
down_revision=None

def upgrade():
    op.create_table("projects",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("name",sa.String(240),nullable=False),
        sa.Column("description",sa.Text()),
        sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_table("volumes",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),
        sa.Column("title",sa.String(240),nullable=False),
        sa.Column("order_index",sa.Integer(),nullable=False),
        sa.UniqueConstraint("project_id","order_index"))
    op.create_table("arcs",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),
        sa.Column("volume_id",sa.String(36),sa.ForeignKey("volumes.id",ondelete="SET NULL")),
        sa.Column("title",sa.String(240),nullable=False),
        sa.Column("order_index",sa.Integer(),nullable=False),
        sa.UniqueConstraint("project_id","order_index"))
    op.create_table("chapters",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),
        sa.Column("volume_id",sa.String(36),sa.ForeignKey("volumes.id",ondelete="SET NULL")),
        sa.Column("arc_id",sa.String(36),sa.ForeignKey("arcs.id",ondelete="SET NULL")),
        sa.Column("title",sa.String(240),nullable=False),
        sa.Column("order_index",sa.Integer(),nullable=False),
        sa.Column("status",sa.String(32),nullable=False),
        sa.UniqueConstraint("project_id","order_index"))
    op.create_table("scenes",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False),
        sa.Column("chapter_id",sa.String(36),sa.ForeignKey("chapters.id",ondelete="CASCADE"),nullable=False),
        sa.Column("title",sa.String(240)),
        sa.Column("order_index",sa.Integer(),nullable=False),
        sa.Column("prose",sa.Text(),nullable=False),
        sa.Column("pov_character_id",sa.String(36)),
        sa.Column("scene_type",sa.String(64)),
        sa.UniqueConstraint("chapter_id","order_index"))

def downgrade():
    for name in ["scenes","chapters","arcs","volumes","projects"]: op.drop_table(name)
