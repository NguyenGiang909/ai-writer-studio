import Link from "next/link";
import { getJSON } from "../../../../../lib/api";
import { branchStatusLabel, branchChangeLabel, payloadText } from "../../../../../lib/labels";
import { getLang } from "../../../../../lib/lang-server";
import { t } from "../../../../../lib/i18n";

export default async function ComparePage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ a?: string; b?: string }>;
}) {
  const { projectId } = await params;
  const { a = "", b = "" } = await searchParams;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const branches: any[] = await getJSON(`${base}/branches`).catch(() => []);
  const ba = branches.find((x) => x.id === a);
  const bb = branches.find((x) => x.id === b);
  const [ca, cb] = await Promise.all([
    a ? getJSON(`${base}/branches/${a}/changes`).catch(() => []) : [],
    b ? getJSON(`${base}/branches/${b}/changes`).catch(() => []) : [],
  ]);

  const types = [...new Set([...ca, ...cb].map((c: any) => c.change_type))];
  const countOf = (list: any[], ty: string) => list.filter((c) => c.change_type === ty).length;

  const col = (br: any, changes: any[]) => (
    <div className="card">
      <h3>
        {br ? br.name : "—"}{" "}
        {br && <small className="subtle">{branchStatusLabel(br.status, lang)}</small>}
      </h3>
      {br && !changes.length && <p className="subtle">{t(lang, "Chưa có thay đổi nào trong nhánh.")}</p>}
      {changes.map((c: any) => (
        <div key={c.id} className="list-row">
          <b>{branchChangeLabel(c.change_type, lang)}</b>
          {c.merged_decision_id && <span className="pill" style={{ color: "#559d78" }}>{t(lang, "Đã gộp")}</span>}
          <div className="subtle" style={{ whiteSpace: "pre-wrap" }}>{payloadText(c.payload, lang) || "—"}</div>
        </div>
      ))}
    </div>
  );

  return (
    <main className="main"><div className="dashboard">
      <Link href={`/projects/${projectId}/branches`} style={{ fontSize: 14, color: "var(--teal)" }}>← {t(lang, "Tất cả nhánh")}</Link>
      <div className="dash-head">
        <div>
          <div className="eyebrow">A/B</div>
          <h1>{t(lang, "So sánh nhánh")}</h1>
        </div>
      </div>

      <form method="get" className="card" style={{ display: "flex", gap: 10, alignItems: "end", flexWrap: "wrap" }}>
        <div className="field" style={{ margin: 0 }}>
          <label>{t(lang, "Nhánh A")}</label>
          <select name="a" defaultValue={a}>
            <option value="">{t(lang, "— chọn nhánh —")}</option>
            {branches.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label>{t(lang, "Nhánh B")}</label>
          <select name="b" defaultValue={b}>
            <option value="">{t(lang, "— chọn nhánh —")}</option>
            {branches.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
        </div>
        <button className="btn primary" type="submit">{t(lang, "So sánh")}</button>
      </form>

      {ba && bb && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>{t(lang, "Tổng quan theo loại")}</h3>
          {types.map((ty) => (
            <div key={ty} className="list-row">
              <b>{branchChangeLabel(ty, lang)}</b>
              <span className="pill">{ba.name}: {countOf(ca, ty)}</span>
              <span className="pill">{bb.name}: {countOf(cb, ty)}</span>
            </div>
          ))}
          {!types.length && <p className="subtle">{t(lang, "Cả hai nhánh đều chưa có thay đổi.")}</p>}
        </div>
      )}

      {ba && bb && (
        <div className="grid" style={{ marginTop: 14 }}>
          {col(ba, ca)}
          {col(bb, cb)}
        </div>
      )}
      {!(ba && bb) && <p className="subtle" style={{ marginTop: 14 }}>{t(lang, "Chọn 2 nhánh để xem so sánh.")}</p>}
    </div></main>
  );
}
