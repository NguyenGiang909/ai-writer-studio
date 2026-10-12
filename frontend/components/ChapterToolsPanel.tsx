"use client";
import {useEffect,useMemo,useState} from "react";
import {useRouter} from "next/navigation";
import PostForm from "./PostForm";
import {putJSON} from "../lib/api";
import {useLang} from "../lib/use-lang";
import {t} from "../lib/i18n";
type Item={id:string;name?:string;summary?:string;description?:string;instructions?:string;story_time?:number|null};
export type ToolData={world:Item[];locations:Item[];timeline:Item[];styles:Item[]};
export default function ChapterToolsPanel({projectId,chapter,data,inline=false}:{projectId:string;chapter:{id:string;cast_json?:string|null}|null|undefined;data:ToolData;inline?:boolean}){
 const lang=useLang(),router=useRouter();const [busy,setBusy]=useState(false),[message,setMessage]=useState("");
 const parsed=useMemo(()=>{try{const value=JSON.parse(chapter?.cast_json||"{}");return value&&typeof value==="object"&&!Array.isArray(value)?value:{}}catch{return {}}},[chapter?.cast_json]);
 const [cast,setCast]=useState(parsed);
 const [query,setQuery]=useState("");
 useEffect(()=>setCast(parsed),[parsed]);
 if(!chapter)return null;
 async function toggle(key:keyof ToolData,id:string){
  if(busy||!chapter)return;setBusy(true);setMessage("");
  const ids:string[]=Array.isArray(cast[key])?cast[key]:[];
  const previous=cast;const next=ids.includes(id)?ids.filter(x=>x!==id):[...ids,id];setCast({...cast,[key]:next});
  try{await putJSON(`/api/v1/projects/${projectId}/chapters/${chapter.id}/cast`,{[key]:next});setMessage(t(lang,"Đã lưu"));router.refresh();}
  catch(e){setCast(previous);setMessage(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 const body=<><p className="subtle">{t(lang,"Chọn dữ liệu tham chiếu cho chương. AI sẽ nhận nội dung đã chọn.")}</p>
 <input className="cast-filter" aria-label={t(lang,"Lọc tên…")} placeholder={t(lang,"Lọc tên…")} value={query} onChange={e=>setQuery(e.target.value)} />
 <small role="status">{busy?t(lang,"Đang lưu…"):message}</small>
 {([['world','Thế giới'],['locations','Địa điểm'],['timeline','Timeline'],['styles','Phong cách']] as const).map(([key,label])=>{
 const ids:string[]=Array.isArray(cast[key])?cast[key]:[];
 return <details className="cast-group" key={key} open><summary><span>{t(lang,label)}</span><b className="badge-sm">{ids.length}</b></summary>
 {!data[key].length&&<p className="subtle">{t(lang,"Chưa có dữ liệu")}</p>}
 <div className="tool-options">{data[key].filter(item=>ids.includes(item.id)||`${item.name||""} ${item.summary||""}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())).sort((a,b)=>Number(ids.includes(b.id))-Number(ids.includes(a.id))).map(item=><div key={item.id}><label className={'cast-row'+(ids.includes(item.id)?' on':'')}><input type="checkbox" checked={ids.includes(item.id)} disabled={busy} onChange={()=>toggle(key,item.id)}/><span className="cast-name">{item.name||item.summary}</span></label>
 {ids.includes(item.id)&&<div className="tool-selected">{item.story_time!=null&&<small>{t(lang,"Thời gian")}: {item.story_time}</small>}<p>{item.instructions||item.description||item.summary||t(lang,"Chưa có mô tả")}</p></div>}</div>)}</div>
 {key==="styles"&&<div className="tool-add-style"><PostForm
   endpoint={`/api/v1/projects/${projectId}/style-profiles`}
   triggerLabel={t(lang,"＋ Thêm phong cách")} triggerClass="btn sm"
   submitLabel={t(lang,"Lưu phong cách")} fields={[
     {name:"name",label:t(lang,"Tên phong cách"),required:true},
     {name:"instructions",label:t(lang,"Hướng dẫn viết"),type:"textarea",required:true},
   ]} /></div>}
 </details>})}</>;
 return inline?<details className="skeleton tools-inline"><summary>{t(lang,"Công cụ")}</summary><div className="cast-inline-body">{body}</div></details>:<aside className="tool-rail" aria-label={t(lang,"Công cụ")}><div className="cast-head">{t(lang,"Công cụ")}</div>{body}</aside>;
}
