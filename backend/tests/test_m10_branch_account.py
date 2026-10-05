
from app.services.branch import merge_contract,validate_change
from app.services.credentials import public_credential_view,resolve_model
def test_branch_merge_never_mutates_truth():
    x=merge_contract({"merged_decision_id":None})
    assert x["artifact"]=="AuthorDecision" and x["mutates_canon"] is False and x["mutates_manuscript"] is False
def test_byok_never_returns_secret():
    x=public_credential_view("openai","••••1234"); assert x["secret"] is None
def test_model_precedence():
    assert resolve_model("writing",None,"project-model","account-model","fallback")=="project-model"
