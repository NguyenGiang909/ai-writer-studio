
from app.db.base import Base
import app.models
def test_thread_contract():
    assert {"threads","thread_beats","thread_dependencies"} <= set(Base.metadata.tables)
    assert "planned_payoff_order" in Base.metadata.tables["threads"].c
