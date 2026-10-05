import Link from "next/link";
import { getJSON } from "../../../../../lib/api";
import PostForm from "../../../../../components/PostForm";
import ActionButton from "../../../../../components/ActionButton";
import { branchStatusLabel, branchChangeLabel, payloadText } from "../../../../../lib/labels";
import { getLang } from "../../../../../lib/lang-server";
import { t } from "../../../../../lib/i18n";

const TYPE_OPTS_VI = [
  ["canon_override", "Ghi đè canon"], ["thread_plan", "Kế hoạch hố"], ["scene_plan", "Kế hoạch cảnh"],
  ["chapter_plan", "Kế hoạch chương"], ["plan_note", "Ghi chú"],
];

export default async function BranchDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; branchId: string }>;
}) {
  const { projectId, branchId } = await params;
  const lang = await getLang();
  const TYPE_OPTS = TYPE_OPTS_VI.map(([value, label]) => ({ value, label: t(lang, label) }));
  const base = `/api/v1/projects/${projectId}`;
  const branches: any[] = await getJSON(`${base}/branches`).catch(() => []);
  const branch = branches.find((b: any) => b.id === branchId);
  const changes: any[] = await getJSON(`${base}/branches/${branchId}/changes`).catch(() => []);

  return (
    <main className="main"><div className="dashboard">
      <Link href={`/projects/${projectId}/branches`} style={{ fontSize: 14, color: "var(--teal)" }}>← {t(lang, "Tất cả nhánh")}</Link>
      <div className="dash-head"><div><h1>
        {branch?.name ?? t(lang, "Nhánh")}{" "}
        <small style={{ fontSize: 14, color: "var(--muted)" }}>{branchStatusLabel(branch?.status, lang)}</small>
      </h1></div></div>
      {(branch?.status === "draft" || branch?.status === "selected") && (
        <PostForm endpoint={`${base}/branches/${branchId}/changes`} submitLabel={t(lang, "Thay đổi")} fields={[
          { name: "change_type", label: t(lang, "Loại"), type: "select", options: TYPE_OPTS },
          { name: "payload", label: t(lang, "Nội dung (JSON)"), type: "json", required: true, placeholder: '{"key":"value"}' },
        ]} />
      )}
      <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
        {changes.map((c: any) => (
          <section key={c.id} className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <b>{branchChangeLabel(c.change_type, lang)}</b>
              {c.merged_decision_id
                ? <span className="pill" style={{ color: "#559d78" }}>{t(lang, "Đã gộp → quyết định {id}", { id: c.merged_decision_id.slice(0, 8) })}</span>
                : <ActionButton endpoint={`${base}/branches/${branchId}/changes/${c.id}/merge`} label={t(lang, "Gộp → Quyết định tác giả")} />}
            </div>
            <p style={{ color: "var(--ink2)", margin: "8px 0 0", whiteSpace: "pre-wrap" }}>{payloadText(c.payload, lang) || "—"}</p>
          </section>
        ))}
        {!changes.length && <p className="subtle">{t(lang, "Chưa có thay đổi nào trong nhánh.")}</p>}
      </div>
    </div></main>
  );
}
