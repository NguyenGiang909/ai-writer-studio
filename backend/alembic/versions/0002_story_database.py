
from alembic import op
import sqlalchemy as sa
revision="0002"; down_revision="0001"
def base_cols():
    return [sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False)]
def upgrade():
    op.create_table("characters",*base_cols(),sa.Column("name",sa.String(240),nullable=False),sa.Column("role",sa.String(64)),sa.Column("summary",sa.Text()),sa.Column("voice_notes",sa.Text()),sa.Column("status",sa.String(32),nullable=False),sa.UniqueConstraint("project_id","name"))
    op.create_table("world_entities",*base_cols(),sa.Column("name",sa.String(240),nullable=False),sa.Column("entity_type",sa.String(64),nullable=False),sa.Column("description",sa.Text()))
    op.create_table("locations",*base_cols(),sa.Column("parent_location_id",sa.String(36),sa.ForeignKey("locations.id",ondelete="SET NULL")),sa.Column("name",sa.String(240),nullable=False),sa.Column("description",sa.Text()))
    op.create_table("factions",*base_cols(),sa.Column("name",sa.String(240),nullable=False),sa.Column("description",sa.Text()))
    op.create_table("items",*base_cols(),sa.Column("name",sa.String(240),nullable=False),sa.Column("description",sa.Text()),sa.Column("unique_item",sa.Boolean(),nullable=False))
    op.create_table("abilities",*base_cols(),sa.Column("name",sa.String(240),nullable=False),sa.Column("ability_type",sa.String(64)),sa.Column("can_do",sa.Text()),sa.Column("cannot_do",sa.Text()),sa.Column("limits",sa.Text()),sa.Column("cost",sa.Text()),sa.Column("conditions",sa.Text()),sa.Column("counters",sa.Text()))
    op.create_table("relationships",*base_cols(),sa.Column("source_character_id",sa.String(36),sa.ForeignKey("characters.id",ondelete="CASCADE"),nullable=False),sa.Column("target_character_id",sa.String(36),sa.ForeignKey("characters.id",ondelete="CASCADE"),nullable=False),sa.Column("relationship_type",sa.String(64),nullable=False),sa.Column("notes",sa.Text()))
    op.create_table("aliases",*base_cols(),sa.Column("character_id",sa.String(36),sa.ForeignKey("characters.id",ondelete="CASCADE"),nullable=False),sa.Column("alias",sa.String(240),nullable=False),sa.Column("notes",sa.Text()))
    op.create_table("character_arcs",*base_cols(),sa.Column("character_id",sa.String(36),sa.ForeignKey("characters.id",ondelete="CASCADE"),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("opening_state",sa.Text()),sa.Column("target_state",sa.Text()))
    op.create_table("style_profiles",*base_cols(),sa.Column("name",sa.String(240),nullable=False),sa.Column("scope_type",sa.String(32),nullable=False),sa.Column("scope_id",sa.String(36)),sa.Column("priority",sa.Integer(),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.Column("instructions",sa.Text()))
    op.create_table("style_samples",*base_cols(),sa.Column("style_profile_id",sa.String(36),sa.ForeignKey("style_profiles.id",ondelete="CASCADE"),nullable=False),sa.Column("sample_type",sa.String(64),nullable=False),sa.Column("title",sa.String(240)),sa.Column("text",sa.Text(),nullable=False))
def downgrade():
    for n in ["style_samples","style_profiles","character_arcs","aliases","relationships","abilities","items","factions","locations","world_entities","characters"]: op.drop_table(n)
