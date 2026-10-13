import {t,Lang} from "../lib/i18n";
export default function StyleInstructions({text,lang}:{text?:string|null;lang:Lang}){
 let value:unknown;
 try{value=JSON.parse(text||"");}catch{}
 if(!value||typeof value!=="object"||Array.isArray(value))return <p className="style-free-text">{text}</p>;
 const labels:Record<string,string>={tone:"Giọng điệu",pov:"Góc nhìn",tense:"Thì kể",notes:"Chỉ dẫn",voice:"Giọng kể",style:"Phong cách"};
 const display=(v:unknown):string=>typeof v==="string"?v:Array.isArray(v)?v.map(display).join(" · "):v&&typeof v==="object"?Object.entries(v).map(([k,x])=>`${k}: ${display(x)}`).join("; "):String(v??"");
 return <dl className="style-instructions">{Object.entries(value).map(([key,v])=><div key={key}><dt>{t(lang,labels[key]||key)}</dt><dd>{display(v)}</dd></div>)}</dl>;
}
