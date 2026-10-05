import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import { roleLabel } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

const ROLES_VI = [
  ["brainstorm", "Động não"], ["plot_doctor", "Bác sĩ cốt truyện"],
  ["character_analyst", "Phân tích nhân vật"], ["continuity_analyst", "Phân tích liên tục"],
  ["devils_advocate", "Phản biện"], ["reader_simulation", "Giả lập độc giả"], ["style", "Phong cách"],
];

export default async function DiscussionsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const ROLES = ROLES_VI.map(([value, label]) => ({ value, label: t(lang, label) }));
  const base = `/api/v1/projects/${projectId}`;
  const threads = await safe(`${base}/discussions`);
  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head"><div><div className="eyebrow">Story room</div><h1>{t(lang, "Thảo luận với AI")}</h1></div></div>
      <p style={{ color: "var(--muted)", fontSize: 13 }}>
        {t(lang, "Ý tưởng trong chat không phải Canon — muốn đưa vào truyện phải qua Đề xuất → Duyệt.")}
      </p>
      <PostForm endpoint={`${base}/discussions`} submitLabel={t(lang, "Phiên thảo luận")} fields={[
        { name: "title", label: t(lang, "Chủ đề"), required: true },
        { name: "role", label: t(lang, "Vai trò AI"), type: "select", options: ROLES },
      ]} />
      <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
        {threads.map((t: any) => (
          <Link key={t.id} href={`/projects/${projectId}/discussions/${t.id}`}
            style={{ display: "block", border: "1px solid var(--line)", borderRadius: 12, padding: 14, background: "var(--panel)", textDecoration: "none", color: "inherit" }}>
            <b>{t.title}</b> <small style={{ color: "var(--muted)" }}>· {roleLabel(t.role, lang)}</small>
          </Link>
        ))}
        {!threads.length && <p style={{ color: "var(--muted)" }}>{t(lang, "Chưa có phiên thảo luận nào.")}</p>}
      </div>
    </div></main>
  );
}
