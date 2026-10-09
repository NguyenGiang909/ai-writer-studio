import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import ActionButton from "../../../../components/ActionButton";
import ListFilter from "../../../../components/ListFilter";
import ReviewIssues from "../../../../components/ReviewIssues";
import ChapterDeepCheck from "../../../../components/ChapterDeepCheck";
import { kindLabel, statusLabel, payloadText } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

export default async function ReviewPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [pending, resolved, continuity, manuscript] = await Promise.all([
    safe(`${base}/suggestions?status=pending`),
    safe(`${base}/suggestions`),
    safe(`${base}/continuity/check`),
    safe(`${base}/manuscript`),
  ]);
  const allChapters = manuscript.chapters ?? [];
  const chapters = allChapters
    .filter((c: any) => (c.scenes ?? []).some((s: any) => s.prose))
    .map((c: any) => ({ id: c.id, title: c.title, order_index: c.order_index }));
  const arcs = (manuscript.arcs ?? []).map((a: any) => {
    const chs = allChapters.filter((c: any) => c.arc_id === a.id);
    return { id: a.id, title: a.title,
             from: Math.min(...chs.map((c: any) => c.order_index)),
             to: Math.max(...chs.map((c: any) => c.order_index)),
             count: chs.length };
  }).filter((a: any) => a.count > 0);
  const done = resolved.filter((s: any) => s.status !== "pending");
  const count = continuity.count ?? (continuity.issues ?? []).length ?? 0;

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Báo cáo tư vấn")}</div>
          <h1>Continuity</h1>
        </div>
      </div>
      <div className="grid">
        <div className="card">
          <h3>{t(lang, "{n} điểm cần xem", { n: count })}</h3>
          <p className="subtle">{t(lang, "Kiểm tra tự động, chỉ đọc — không tự sửa bản thảo.")}</p>
          <ReviewIssues issues={continuity.issues ?? []} projectId={projectId} />
        </div>
        <ChapterDeepCheck projectId={projectId} chapters={chapters ?? []}
          allChapters={allChapters.map((c: any) => ({ id: c.id, title: c.title, order_index: c.order_index }))}
          arcs={arcs} />
        <div className="card">
          <h3>{t(lang, "Nguyên tắc")}</h3>
          <p>
            {t(lang, "Báo cáo chỉ nêu bằng chứng và tác động có thể có. Tác giả quyết định sửa, bỏ qua hoặc tạo Retcon.")}{" "}
            {t(lang, "Gợi ý được duyệt sẽ trở thành")} <b>{t(lang, "Suy ra (INFERRED)")}</b> — {t(lang, "chưa phải")} <b>CANON</b>.
          </p>
        </div>
      </div>

      <div className="dash-head" style={{ marginTop: 26 }}>
        <div>
          <div className="eyebrow">{t(lang, "Gợi ý → Duyệt → Áp dụng")}</div>
          <h1>{t(lang, "Đề xuất chờ duyệt ({n})", { n: pending.length })}</h1>
        </div>
        <ListFilter for="rev-pending" placeholder={t(lang, "Lọc gợi ý…")} />
      </div>
      <div className="grid" id="rev-pending">
        {pending.map((s: any) => (
          <div key={s.id} className="card" data-q={`${s.change_type ?? s.kind} ${payloadText(s.payload, lang)}`}>
            <div className="review-item">
              <header>
                <span><b>{kindLabel(s.change_type ?? s.kind, lang)}</b></span>
                <span className="pill">{statusLabel(s.status, lang)}</span>
              </header>
              <p style={{ whiteSpace: "pre-wrap" }}>{payloadText(s.payload, lang) || "—"}</p>
              <div style={{ display: "flex", gap: 8, marginTop: 6, alignItems: "center" }}>
                <ActionButton endpoint={`${base}/suggestions/${s.id}/approve`} label={t(lang, "✓ Duyệt")} />
                <ActionButton endpoint={`${base}/suggestions/${s.id}/reject`} label={t(lang, "✗ Từ chối")} />
                {s.scene_id && (
                  <Link href={`/projects/${projectId}?scene=${s.scene_id}`} className="issue-link" style={{ marginLeft: "auto" }}>→ {t(lang, "Mở cảnh")}</Link>
                )}
              </div>
            </div>
          </div>
        ))}
        {!pending.length && (
          <div className="card"><p className="subtle">{t(lang, "Không có đề xuất nào đang chờ.")}</p></div>
        )}
      </div>

      <div className="dash-head" style={{ marginTop: 26 }}>
        <div>
          <div className="eyebrow">{t(lang, "Lịch sử")}</div>
          <h1>{t(lang, "Đã xử lý ({n})", { n: done.length })}</h1>
        </div>
        <ListFilter for="rev-done" placeholder={t(lang, "Lọc gợi ý…")} />
      </div>
      <div className="card" id="rev-done">
        {done.map((s: any) => (
          <div key={s.id} className="list-row" data-q={`${s.change_type ?? s.kind} ${s.status}`}>
            <b>{kindLabel(s.change_type ?? s.kind, lang)}</b> —{" "}
            <span style={{ color: s.status === "approved" ? "#3d7f60" : "var(--red)" }}>{statusLabel(s.status, lang)}</span>
            {s.scene_id && (
              <Link href={`/projects/${projectId}?scene=${s.scene_id}`} className="issue-link" style={{ marginLeft: "auto" }}>→ {t(lang, "Mở cảnh")}</Link>
            )}
          </div>
        ))}
        {!done.length && <p className="subtle">{t(lang, "Chưa có.")}</p>}
      </div>
    </div></main>
  );
}
