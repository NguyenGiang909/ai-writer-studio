
import hashlib
from dataclasses import dataclass
@dataclass
class AuthorPlan:
    beats:list[str]; constraints:list[str]; target_words:int; plan_hash:str
def parse_author_brief(text:str,target_words:int=2000):
    beats=[]; constraints=[]
    for raw in text.splitlines():
        line=raw.strip(" -\t")
        if not line: continue
        low=line.lower()
        (constraints if any(x in low for x in ["không ","đừng ","must not","do not"]) else beats).append(line)
    normalized="\n".join(beats+constraints)+f"|{target_words}"
    return AuthorPlan(beats,constraints,target_words,hashlib.sha256(normalized.encode()).hexdigest()[:16])
def allocate_word_budget(target:int,scene_count:int):
    if scene_count<1: raise ValueError("scene_count")
    q,r=divmod(target,scene_count)
    return [q+(1 if i<r else 0) for i in range(scene_count)]
def line_diff(original:str,replacement:str):
    import difflib
    return list(difflib.ndiff(original.splitlines(),replacement.splitlines()))
