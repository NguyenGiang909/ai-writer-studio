
from app.ai.writer import parse_author_brief,allocate_word_budget,line_diff
def test_writer_plan_and_budget():
    p=parse_author_brief("Đến khách điếm\nKhông đánh nhau",2001)
    assert p.beats==["Đến khách điếm"] and p.constraints==["Không đánh nhau"]
    assert sum(allocate_word_budget(2001,3))==2001
def test_rewrite_is_diff_not_auto_apply():
    d=line_diff("a","b"); assert any(x.startswith("- ") for x in d) and any(x.startswith("+ ") for x in d)
