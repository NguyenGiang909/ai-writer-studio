
from alembic import op
import sqlalchemy as sa
revision="0003"; down_revision="0002"
def pc(): return [sa.Column("id",sa.String(36),primary_key=True),sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id",ondelete="CASCADE"),nullable=False)]
def upgrade():
    op.create_table("canon_facts",*pc(),sa.Column("subject_type",sa.String(64),nullable=False),sa.Column("subject_id",sa.String(36)),sa.Column("predicate",sa.String(120),nullable=False),sa.Column("value_text",sa.Text(),nullable=False),sa.Column("truth_status",sa.String(24),nullable=False),sa.Column("locked",sa.Boolean(),nullable=False),sa.Column("valid_from",sa.Integer()),sa.Column("valid_to",sa.Integer()),sa.Column("source_scene_id",sa.String(36),sa.ForeignKey("scenes.id",ondelete="SET NULL")))
    op.create_table("author_decisions",*pc(),sa.Column("title",sa.String(240),nullable=False),sa.Column("decision_text",sa.Text(),nullable=False),sa.Column("status",sa.String(24),nullable=False))
    op.create_table("story_events",*pc(),sa.Column("scene_id",sa.String(36),sa.ForeignKey("scenes.id",ondelete="SET NULL")),sa.Column("event_type",sa.String(64),nullable=False),sa.Column("summary",sa.Text(),nullable=False),sa.Column("story_time",sa.Integer()),sa.Column("narrative_order",sa.Integer()),sa.Column("location_id",sa.String(36),sa.ForeignKey("locations.id",ondelete="SET NULL")))
    op.create_table("story_states",*pc(),sa.Column("entity_type",sa.String(64),nullable=False),sa.Column("entity_id",sa.String(36),nullable=False),sa.Column("key",sa.String(120),nullable=False),sa.Column("value_text",sa.Text(),nullable=False),sa.Column("story_time",sa.Integer()),sa.Column("narrative_order",sa.Integer()),sa.Column("source_event_id",sa.String(36),sa.ForeignKey("story_events.id",ondelete="SET NULL")))
    op.create_table("knowledge_states",*pc(),sa.Column("knower_type",sa.String(32),nullable=False),sa.Column("knower_id",sa.String(36)),sa.Column("fact_id",sa.String(36),sa.ForeignKey("canon_facts.id",ondelete="CASCADE"),nullable=False),sa.Column("state",sa.String(24),nullable=False),sa.Column("disclosure_level",sa.Integer(),nullable=False),sa.Column("known_aspects",sa.Text()),sa.Column("acquired_story_time",sa.Integer()),sa.Column("acquired_narrative_order",sa.Integer()))
    op.create_table("secrets",*pc(),sa.Column("fact_id",sa.String(36),sa.ForeignKey("canon_facts.id",ondelete="CASCADE"),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("status",sa.String(24),nullable=False))
def downgrade():
    for n in ["secrets","knowledge_states","story_states","story_events","author_decisions","canon_facts"]: op.drop_table(n)
