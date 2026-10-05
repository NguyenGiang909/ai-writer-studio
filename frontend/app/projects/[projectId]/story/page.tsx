import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string, fb: any = []) { try { return await getJSON(path); } catch { return fb; } }

export default async function StoryPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [project, decisions] = await Promise.all([
    safe("/api/v1/projects").then((ps: any[]) => ps.find((p: any) => p.id === projectId) ?? {}),
    safe(`${base}/author-decisions`),
  ]);

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Story design")}</div>
          <h1>{t(lang, "Thiết kế truyện")}</h1>
        </div>
      </div>
      <div className="grid">
        <div className="card">
          <h3>Premise</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>
            {project?.description || t(lang, "Chưa có mô tả — sửa khi tạo project.")}
          </p>
          <PostForm endpoint={`/api/v1/projects/${projectId}`} method="patch"
            submitLabel={t(lang, "Lưu premise")} triggerLabel={t(lang, "✎ Sửa premise")} fields={[
              { name: "name", label: t(lang, "Tên truyện"), defaultValue: project?.name },
              { name: "description", label: "Premise", type: "textarea", defaultValue: project?.description ?? "" },
            ]} />
        </div>
        <div className="card">
          <h3>{t(lang, "Author Decision")}</h3>
          <div className="notice">
            {t(lang, "Các quyết định ở đây có thẩm quyền cao hơn gợi ý AI và được đưa vào Context Builder.")}
          </div>
          {decisions.map((d: any) => (
            <div key={d.id} className="list-row" style={{ alignItems: "baseline" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <b>{d.title}</b> · {d.decision_text}
                {d.rationale && <small className="subtle" style={{ display: "block" }}>{t(lang, "Lý do")}: {d.rationale}</small>}
              </div>
              <PostForm endpoint={`${base}/author-decisions/${d.id}`} method="patch"
                submitLabel={t(lang, "Lưu")} triggerLabel={t(lang, "Sửa")} fields={[
                  { name: "title", label: t(lang, "Mã / tiêu đề"), required: true, defaultValue: d.title },
                  { name: "decision_text", label: t(lang, "Nội dung quyết định"), type: "textarea", required: true, defaultValue: d.decision_text },
                  { name: "rationale", label: t(lang, "Lý do"), type: "textarea", defaultValue: d.rationale ?? "" },
                  { name: "status", label: t(lang, "Trạng thái"), type: "select", defaultValue: d.status ?? "active", options: [
                    { value: "active", label: t(lang, "Đang dùng") },
                    { value: "superseded", label: t(lang, "Đã thay thế") },
                    { value: "archived", label: t(lang, "Lưu trữ") },
                  ] },
                ]} />
              <ActionButton endpoint={`${base}/author-decisions/${d.id}`} method="delete" label={t(lang, "Xoá")} />
            </div>
          ))}
          {!decisions.length && <p className="subtle">{t(lang, "Chưa có quyết định nào.")}</p>}
          <PostForm endpoint={`${base}/author-decisions`} submitLabel={t(lang, "Quyết định")} fields={[
            { name: "title", label: t(lang, "Mã / tiêu đề"), required: true, placeholder: t(lang, "VD: AD-001") },
            { name: "decision_text", label: t(lang, "Nội dung quyết định"), type: "textarea", required: true },
            { name: "rationale", label: t(lang, "Lý do"), type: "textarea" },
          ]} />
        </div>
      </div>
      <p className="subtle" style={{ marginTop: 18 }}>
        {t(lang, "Story database đầy đủ nằm ở")} <Link href={`/projects/${projectId}/characters`} style={{ color: "var(--teal)" }}>{t(lang, "Nhân vật")}</Link>,{" "}
        <Link href={`/projects/${projectId}/world`} style={{ color: "var(--teal)" }}>{t(lang, "Thế giới")}</Link>,{" "}
        <Link href={`/projects/${projectId}/abilities`} style={{ color: "var(--teal)" }}>{t(lang, "Năng lực")}</Link> {t(lang, "và")}{" "}
        <Link href={`/projects/${projectId}/style`} style={{ color: "var(--teal)" }}>{t(lang, "Phong cách")}</Link>.
      </p>
    </div></main>
  );
}
