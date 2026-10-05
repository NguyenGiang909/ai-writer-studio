import Link from "next/link";
import { getJSON } from "../../../../../lib/api";
import ChatThread from "../../../../../components/ChatThread";
import { roleLabel } from "../../../../../lib/labels";
import { getLang } from "../../../../../lib/lang-server";
import { t } from "../../../../../lib/i18n";

export default async function DiscussionThreadPage({
  params,
}: {
  params: Promise<{ projectId: string; threadId: string }>;
}) {
  const { projectId, threadId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const threads: any[] = await getJSON(`${base}/discussions`).catch(() => []);
  const thread = threads.find((t: any) => t.id === threadId);
  const sums: any[] = await getJSON(`${base}/summaries?scope_type=discussion`).catch(() => []);
  const summary = sums.find((s: any) => s.scope_id === threadId);

  return (
    <main className="main"><div className="dashboard">
      <Link href={`/projects/${projectId}/discussions`} style={{ fontSize: 13, color: "var(--teal)" }}>← {t(lang, "Tất cả thảo luận")}</Link>
      <div className="dash-head">
        <div>
          <h1>{thread?.title ?? t(lang, "Thảo luận")}{" "}
            <small style={{ fontSize: 13, color: "var(--muted)" }}>{roleLabel(thread?.role, lang)}</small>
          </h1>
        </div>
      </div>
      {summary && (
        <div className="card" style={{ marginBottom: 14 }}>
          <h3 style={{ marginTop: 0 }}>{t(lang, "Tóm tắt cuộc thảo luận")}</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{summary.summary}</p>
          <small className="subtle">{t(lang, "AI tự tóm tắt sau mỗi 8 tin nhắn — tóm tắt này vẫn được đưa vào ngữ cảnh AI.")}</small>
        </div>
      )}
      <ChatThread
        projectId={projectId}
        threadId={threadId}
        context={lang === "en" ? `discussion room "${thread?.title ?? ""}" (role: ${roleLabel(thread?.role)})` : `phòng thảo luận "${thread?.title ?? ""}" (vai trò: ${roleLabel(thread?.role)})`}
        full
      />
    </div></main>
  );
}
