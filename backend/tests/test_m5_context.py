
from app.ai.context import ContextBuilder,ContextItem
def test_context_budget_and_manifest():
    text,m=ContextBuilder().build([ContextItem("author_brief","A",100,"user",1),ContextItem("history","B"*100,1,"summary",100)],10)
    assert text=="A" and m.omitted[0]["reason"]=="token_budget"
