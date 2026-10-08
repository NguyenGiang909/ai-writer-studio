
from app.db.base import Base
import app.models

EXPECTED={"projects","volumes","arcs","chapters","scenes","scene_versions",
 "characters","world_entities","locations","factions","items","abilities",
 "relationships","aliases","character_arcs","style_profiles","style_samples",
 "canon_facts","author_decisions","story_events","story_states","knowledge_states","secrets",
 "threads","thread_beats","thread_dependencies",
 "discussion_threads","discussion_messages","style_preferences",
 "suggested_changes","story_summaries","retcon_proposals","ai_turns","audit_findings",
 "provider_credentials","model_preferences","story_branches","branch_changes","usage_logs",
 "authoring_runs","authoring_steps","entity_provenance"}

# account-level tables belong to the user, not a project
USER_SCOPED={"provider_credentials","model_preferences","usage_logs"}

def test_all_expected_tables_present():
    assert set(Base.metadata.tables)==EXPECTED

def test_all_story_tables_are_project_scoped():
    for name in set(Base.metadata.tables)-{"projects"}-USER_SCOPED:
        assert "project_id" in Base.metadata.tables[name].c
