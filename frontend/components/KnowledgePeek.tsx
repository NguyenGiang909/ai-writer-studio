"use client";
import { useState } from "react";
import { getJSON } from "../lib/api";
import { knowledgeStateLabel } from "../lib/labels";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export default function KnowledgePeek({
  projectId,
  characters,
}: {
  projectId: string;
  characters: { id: string; name: string }[];
}) {
  const lang = useLang();
  const [knower, setKnower] = useState(characters[0]?.id ?? "");
  const [order, setOrder] = useState("");
  const [rows, setRows] = useState<any[] | null>(null);
  const [error, setError] = useState("");

  async function run() {
    setError(""); setRows(null);
    try {
      const q = `knower_id=${encodeURIComponent(knower)}${order ? `&narrative_order=${order}` : ""}`;
      setRows(await getJSON(`/api/v1/projects/${projectId}/knowledge-states/as-of?${q}`));
    } catch (e: any) {
      setError(e?.message ?? t(lang, "Lỗi"));
    }
  }

  return (
    <div className="card">
      <h3>{t(lang, "Kiến thức theo thời điểm")}</h3>
      <p>
        {t(lang, "Chọn một nhân vật và mốc truyện để xem họ thật sự biết gì. \"Sự thật toàn cục\" không được hiển thị như kiến thức POV.")}
      </p>
      <div className="field">
        <label>{t(lang, "Nhân vật")}</label>
        <select value={knower} onChange={(e) => setKnower(e.target.value)}>
          {characters.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>{t(lang, "Mốc thứ tự kể (để trống = mới nhất)")}</label>
        <input value={order} onChange={(e) => setOrder(e.target.value)} placeholder={t(lang, "VD: 42")} inputMode="numeric" />
      </div>
      <button className="btn wide" onClick={run}>{t(lang, "Xem kiến thức tại mốc")}</button>
      {error && <div className="notice" style={{ marginTop: 10 }}>{error}</div>}
      {rows && (
        <div style={{ marginTop: 10 }}>
          {rows.map((k: any) => (
            <div key={k.id} className="list-row">
              <b>{knowledgeStateLabel(k.state, lang)}</b> · {t(lang, "sự thật")} {k.fact_id?.slice(0, 8)}{" "}
              <small className="subtle">{t(lang, "lộ")} {k.disclosure_level}%</small>
            </div>
          ))}
          {!rows.length && <p className="subtle">{t(lang, "Nhân vật chưa biết sự thật nào tại mốc này.")}</p>}
        </div>
      )}
    </div>
  );
}
