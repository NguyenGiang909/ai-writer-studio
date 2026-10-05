import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import { branchStatusLabel } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

export default async function BranchesPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const branches = await safe(`${base}/branches`);
  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head"><div><div className="eyebrow">{t(lang, "Giả thuyết tách Canon")}</div><h1>{t(lang, "Nhánh What-if")}</h1></div></div>
      <p className="subtle">
        {t(lang, "Truyện gốc không đổi. Gộp nhánh chỉ tạo Quyết định tác giả — Canon và bản thảo không bị đụng vào.")}
      </p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <PostForm endpoint={`${base}/branches`} submitLabel={t(lang, "Nhánh mới")} fields={[
          { name: "name", label: t(lang, "Tên giả thuyết"), required: true, placeholder: t(lang, "Nếu X chết ở chương 320…") },
        ]} />
        {branches.length >= 2 && (
          <Link href={`/projects/${projectId}/branches/compare`} className="btn" style={{ textDecoration: "none" }}>
            {t(lang, "So sánh nhánh")}
          </Link>
        )}
      </div>
      <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
        {branches.map((b: any) => (
          <div key={b.id} style={{ border: "1px solid var(--line)", borderRadius: 12, padding: 14, background: "var(--panel)", display: "flex", alignItems: "center", gap: 10 }}>
            <Link href={`/projects/${projectId}/branches/${b.id}`} style={{ fontWeight: 650, color: "inherit", textDecoration: "none" }}>
              {b.name}
            </Link>
            <span className="pill">{branchStatusLabel(b.status, lang)}</span>
            <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
              {b.status === "draft" && <ActionButton endpoint={`${base}/branches/${b.id}`} method="patch" body={{ status: "selected" }} label={t(lang, "Chọn")} />}
              {b.status === "draft" && <ActionButton endpoint={`${base}/branches/${b.id}`} method="patch" body={{ status: "discarded" }} label={t(lang, "Bỏ nhánh")} />}
            </span>
          </div>
        ))}
        {!branches.length && <p style={{ color: "var(--muted)" }}>{t(lang, "Chưa có nhánh what-if nào.")}</p>}
      </div>
    </div></main>
  );
}
