"use client";
import {useEffect,useState} from "react";
import {useRouter} from "next/navigation";
import {patchJSON} from "../lib/api";
import {t} from "../lib/i18n";
import {useLang} from "../lib/use-lang";
export default function ThreadPriorityControls({endpoint,mustResolve,important}:{endpoint:string;mustResolve:boolean;important:boolean}){
 const lang=useLang(),router=useRouter();
 const [values,setValues]=useState({must_resolve:mustResolve,important});
 const [busy,setBusy]=useState(false),[message,setMessage]=useState("");
 useEffect(()=>setValues({must_resolve:mustResolve,important}),[mustResolve,important]);
 async function toggle(key:"must_resolve"|"important"){
  if(busy)return;setBusy(true);setMessage("");const previous=values;setValues({...values,[key]:!values[key]});
  try{const saved=await patchJSON(endpoint,{[key]:!values[key]});setValues({must_resolve:saved.must_resolve,important:saved.important});setMessage(t(lang,"Đã lưu"));router.refresh();}
  catch(e){setValues(previous);setMessage(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 return <div className="thread-priorities">{([['must_resolve','Hố bắt buộc lấp'],['important','Hố quan trọng']] as const).map(([key,label])=><label key={key}><input type="checkbox" checked={!!values[key]} disabled={busy} onChange={()=>toggle(key)}/>{t(lang,label)}</label>)}<small role="status">{message}</small></div>;
}
