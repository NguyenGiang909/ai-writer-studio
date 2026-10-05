
from app.db.base import Base
import app.models
def test_story_room_and_explicit_style_memory():
    assert {"discussion_threads","discussion_messages","style_preferences"} <= set(Base.metadata.tables)
    assert "explicit_author_feedback" in Base.metadata.tables["style_preferences"].c
