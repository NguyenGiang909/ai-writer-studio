
from dataclasses import dataclass,field
@dataclass
class ContextItem:
    bucket:str; text:str; priority:int; source:str; estimated_tokens:int=0
@dataclass
class ContextManifest:
    included:list[dict]=field(default_factory=list); omitted:list[dict]=field(default_factory=list); total_estimated_tokens:int=0
class ContextBuilder:
    PROTECTED={"author_brief","temporal_anchor","pov_knowledge","current_scene"}
    def build(self,items:list[ContextItem],budget:int=8000):
        ordered=sorted(items,key=lambda x:(x.bucket not in self.PROTECTED,-x.priority))
        used=0; chunks=[]; manifest=ContextManifest()
        for i in ordered:
            cost=i.estimated_tokens or max(1,len(i.text)//4)
            if used+cost<=budget:
                chunks.append(i.text); used+=cost; manifest.included.append({"bucket":i.bucket,"source":i.source,"tokens":cost})
            else: manifest.omitted.append({"bucket":i.bucket,"source":i.source,"reason":"token_budget"})
        manifest.total_estimated_tokens=used
        return "\n\n".join(chunks),manifest
