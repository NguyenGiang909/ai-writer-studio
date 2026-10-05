
from app.db.base import Base
import app.models
def test_truth_tables_and_dual_time():
    for n in ["canon_facts","author_decisions","story_events","story_states","knowledge_states","secrets"]: assert n in Base.metadata.tables
    e=Base.metadata.tables["story_events"]
    assert "story_time" in e.c and "narrative_order" in e.c
    k=Base.metadata.tables["knowledge_states"]
    assert "disclosure_level" in k.c and "known_aspects" in k.c
