import PostForm from "./PostForm";
import ActionButton from "./ActionButton";
import ThreadPriorityControls from "./ThreadPriorityControls";
import {t,Lang} from "../lib/i18n";
export default function ThreadPriorityBoard({threads,base,current,lang}:{threads:any[];base:string;current:number;lang:Lang}){
 const pending=threads.filter(x=>!['RESOLVED','ABANDONED'].includes(x.status));
 return <div className="priority-board">{([{key:'must_resolve',label:'Hố bắt buộc lấp'}, {key:'important',label:'Hố quan trọng'}] as const).map(group=>{
 const rows=pending.filter(x=>group.key==='must_resolve'?x.must_resolve:x.important&&!x.must_resolve);
 return <section key={group.key} className={'card priority-card '+group.key}><h3>{t(lang,group.label)} · {rows.length}</h3>
 <p className="subtle">{t(lang,group.key==='must_resolve'?'Cần có payoff trước khi kết truyện. Không bắt buộc lấp ngay ở cảnh hiện tại.':'Theo dõi xuyên suốt; nhắc lại hoặc phát triển khi phù hợp với cảnh.')}</p>
 {!rows.length&&<p className="subtle">{t(lang,'Chưa có hố ưu tiên trong nhóm này.')}</p>}
 {rows.map(th=><div className="priority-entry" key={th.id}><b>{th.title}</b><ThreadPriorityControls endpoint={`${base}/threads/${th.id}`} mustResolve={!!th.must_resolve} important={!!th.important}/>
 {th.description&&<p className="subtle">{th.description}</p>}
 {th.planned_payoff_order!=null&&<small>{t(lang,'Chương payoff dự kiến')}: {th.planned_payoff_order}</small>}
 <div className="priority-actions"><PostForm endpoint={`${base}/threads/${th.id}`} method="patch" triggerLabel={t(lang,"Sửa")} submitLabel={t(lang,"Lưu")} fields={[
 {name:"title",label:t(lang,"Tên hố"),required:true,defaultValue:th.title},
 {name:"description",label:t(lang,"Mô tả / ý đồ tác giả"),type:"textarea",defaultValue:th.description||""},
 {name:"planned_payoff_order",label:t(lang,"Chương payoff dự kiến"),type:"number",defaultValue:th.planned_payoff_order!=null?String(th.planned_payoff_order):undefined},
 ]}/>
<ActionButton endpoint={`${base}/threads/${th.id}/beats`} method="post" body={{beat_type:'considered',narrative_order:current,notes:'Đã cân nhắc, tạm để'}} label={t(lang,'Đã xem xét · để sau')}/><ActionButton endpoint={`${base}/threads/${th.id}`} method="patch" body={{status:'RESOLVED'}} label={t(lang,'Đánh dấu xong')}/></div>
 </div>)}</section>})}</div>;
}
