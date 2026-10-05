
from app.db.base import Base
from app.services.continuity import knowledge_leak
import app.models
def test_suggestions_never_auto_apply_by_contract():
    assert "auto_applied" in Base.metadata.tables["suggested_changes"].c
    assert Base.metadata.tables["suggested_changes"].c.auto_applied.default.arg is False
def test_knowledge_leak_signal():
    assert knowledge_leak(20,10).code=="KNOWLEDGE_LEAK"
    assert knowledge_leak(5,10) is None
