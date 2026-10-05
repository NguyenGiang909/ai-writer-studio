import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import { kindLabel, statusLabel, threadTypeLabel, beatTypeLabel, payloadText, cap } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t as tr } from "../../../../lib/i18n";

async function safe(path: string, fallback: any = []) { try { return await getJSON(path); } catch { return fallback; } }

const BADGE_WARN = new Set(["DORMANT", "PLANNED", "ABANDONED"]);

const THREAD_TYPE_OPTS = [
  ["mystery", "Bí ẩn"], ["foreshadow", "Gợi mở"], ["promise", "Lời hứa"],
  ["conflict", "Xung đột"], ["secret", "Bí mật"], ["question", "Câu hỏi"],
  ["quest", "Hành trình"], ["future_payoff", "Trả nợ sau"], ["custom", "Tùy ý"],
].map(([value, label]) => ({ value, label }));

const BEAT_OPTS = [
  ["setup", "Gieo mầm"], ["reinforcement", "Nhắc lại"], ["escalation", "Đẩy cao"],
  ["misdirection", "Đánh lạc hướng"], ["payoff", "Trả nợ"], ["considered", "Đã xem xét · để sau"],
].map(([value, label]) => ({ value, label }));

export default async function ThreadsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [threads, deps, tree, suggestions] = await Promise.all([
    safe(`${base}/threads`), safe(`${base}/thread-dependencies`), safe(`${base}/manuscript`, { chapters: [] }),
    safe(`${base}/suggestions?status=pending`),
  ]);
  const chapters = tree.chapters ?? [];
  const sceneOpts = chapters.flatMap((c: any) =>
    (c.scenes ?? []).map((s: any) => ({ value: s.id, label: `${c.title} · ${s.title || tr(lang, "Cảnh")}` })));
  const beatsByThread: Record<string, any[]> = {};
  await Promise.all(threads.map(async (t: any) => { beatsByThread[t.id] = await safe(`${base}/threads/${t.id}/beats`); }));
  const title = (id: string) => threads.find((t: any) => t.id === id)?.title ?? id.slice(0, 8);
  const open = threads.filter((t: any) => t.status === "OPEN");
  const narrOrders = chapters.flatMap((c: any) =>
    (c.scenes ?? []).map((s: any) => s.narrative_order).filter((n: any) => n != null));
  const current = narrOrders.length
    ? Math.max(...narrOrders)
    : Math.max(0, ...chapters.map((c: any) => c.order_index ?? 0));

  const threadForm = (
    <PostForm endpoint={`${base}/threads`} submitLabel={tr(lang, "Hố mới")}
      triggerLabel={tr(lang, "＋ Thêm Thread")} triggerClass="btn primary" fields={[
        { name: "title", label: tr(lang, "Tên hố"), required: true },
        { name: "thread_type", label: tr(lang, "Loại"), type: "select", options: THREAD_TYPE_OPTS.map((o) => ({ ...o, label: tr(lang, o.label) })) },
        { name: "description", label: tr(lang, "Mô tả / ý đồ tác giả"), type: "textarea" },
        { name: "planned_payoff_order", label: tr(lang, "Chương payoff dự kiến"), type: "number" },
      ]} />
  );

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{tr(lang, "Story intelligence")}</div>
          <h1>{tr(lang, "Threads / Hố")}</h1>
        </div>
        {threadForm}
      </div>
      <div className="grid">
        <div className="card">
          <h3>{tr(lang, "Đang mở · {n}", { n: open.length })}</h3>
          {threads.map((t: any) => {
            const warn = BADGE_WARN.has(t.status);
            const beats = beatsByThread[t.id] ?? [];
            const payoff = beats.filter((x: any) => x.beat_type === "payoff").length;
            const pct = beats.length ? Math.round((payoff / beats.length) * 100) : 0;
            const touched = beats.map((b: any) => b.narrative_order).filter((n: any) => n != null);
            const lastTouched = touched.length ? Math.max(...touched) : null;
            const gap = lastTouched != null ? current - lastTouched : current;
            const stale = t.status === "OPEN" && gap >= 15;
            const overdue = t.status === "OPEN" && t.planned_payoff_order != null && current > t.planned_payoff_order;
            return (
              <div key={t.id} className="thread">
                <div style={{ minWidth: 0, flex: 1 }}>
                  <b>{t.title}</b>
                  <small>
                    {t.thread_type !== "custom" ? `${threadTypeLabel(t.thread_type, lang)} · ` : ""}
                    {cap((t.description ?? "")
                      .replace(/\s*[-–]\s*/g, " · ")
                      .replace(/nhắc gần nhất\s*\?/i, "chưa nhắc lại"))}
                    {beats.length > 0 && ` · ${beats.length} ${tr(lang, "beat")}`}
                  </small>
                  <small className="subtle" style={{ display: "block", marginTop: 4 }}>
                    {lastTouched != null ? tr(lang, "chạm cuối ở thứ tự {n}", { n: lastTouched }) : tr(lang, "chưa có beat")}
                    {t.status === "OPEN" && ` · ${tr(lang, "cách hiện tại ~{n}", { n: gap })}`}
                    {overdue && ` · ${tr(lang, "quá cửa sổ payoff (dự kiến {n})", { n: t.planned_payoff_order })}`}
                  </small>
                  {beats.length > 0 && (
                    <div className="bar"><i style={{ width: `${Math.max(pct, 8)}%` }} /></div>
                  )}
                  <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
                    {t.status === "OPEN" && <ActionButton endpoint={`${base}/threads/${t.id}/beats`} method="post" body={{ beat_type: "reinforcement", narrative_order: current }} label={tr(lang, "Nhắc lại")} />}
                    {t.status === "OPEN" && <ActionButton endpoint={`${base}/threads/${t.id}/beats`} method="post" body={{ beat_type: "considered", narrative_order: current, notes: tr(lang, "Đã cân nhắc, tạm để") }} label={tr(lang, "Đã xem xét · để sau")} />}
                    {t.status !== "RESOLVED" && <ActionButton endpoint={`${base}/threads/${t.id}`} method="patch" body={{ status: "RESOLVED" }} label={tr(lang, "Đánh dấu xong")} />}
                    {t.status === "OPEN" && <ActionButton endpoint={`${base}/threads/${t.id}`} method="patch" body={{ status: "DORMANT" }} label={tr(lang, "Tạm ngưng")} />}
                    {t.status === "DORMANT" && <ActionButton endpoint={`${base}/threads/${t.id}`} method="patch" body={{ status: "OPEN" }} label={tr(lang, "Mở lại")} />}
                    <PostForm endpoint={`${base}/threads/${t.id}`} method="patch" submitLabel={tr(lang, "Lưu")} triggerClass="btn ghost sm" triggerLabel={tr(lang, "Sửa")} fields={[
                      { name: "title", label: tr(lang, "Tên hố"), required: true, defaultValue: t.title },
                      { name: "thread_type", label: tr(lang, "Loại"), type: "select", options: THREAD_TYPE_OPTS.map((o) => ({ ...o, label: tr(lang, o.label) })), defaultValue: t.thread_type },
                      { name: "status", label: tr(lang, "Trạng thái"), type: "select", options: ["OPEN", "DORMANT", "RESOLVED", "PLANNED", "ABANDONED"].map((v) => ({ value: v, label: statusLabel(v, lang) })), defaultValue: t.status },
                      { name: "description", label: tr(lang, "Mô tả / ý đồ tác giả"), type: "textarea", defaultValue: t.description },
                      { name: "planned_payoff_order", label: tr(lang, "Chương payoff dự kiến"), type: "number", defaultValue: t.planned_payoff_order != null ? String(t.planned_payoff_order) : undefined },
                    ]} />
                    <ActionButton endpoint={`${base}/threads/${t.id}`} method="delete" label={tr(lang, "Xoá")} confirm={tr(lang, "Xoá hố {name} và toàn bộ beat?", { name: t.title })} />
                  </div>
                </div>
                <span className={`pill badge${warn || stale || overdue ? " warn" : ""}`}>
                  {overdue ? tr(lang, "Quá hạn payoff") : stale ? tr(lang, "Nằm im ~{n}", { n: gap }) : statusLabel(t.status, lang)}
                </span>
              </div>
            );
          })}
          {!threads.length && <p className="subtle">{tr(lang, "Chưa có hố nào.")}</p>}
        </div>
        <div className="card">
          <h3>{tr(lang, "Gợi ý của AI")}</h3>
          <div className="notice">
            {tr(lang, "Đây là gợi ý lập kế hoạch. AI không tự đóng Thread hoặc thay đổi Canon — mọi thay đổi qua Review.")}
          </div>
          {suggestions.slice(0, 3).map((s: any) => (
            <div key={s.id} className="thread">
              <div style={{ minWidth: 0, flex: 1 }}>
                <b>{s.title ?? kindLabel(s.change_type ?? s.kind, lang)}</b>
                <small>{payloadText(s.payload) || s.rationale || s.body || ""}</small>
                <div style={{ marginTop: 10 }}>
                  <Link href={`/projects/${projectId}/review`} className="btn" style={{ textDecoration: "none" }}>
                    {tr(lang, "Xem bằng chứng")}
                  </Link>
                </div>
              </div>
            </div>
          ))}
          {!suggestions.length && <p className="subtle">{tr(lang, "Chưa có gợi ý nào đang chờ.")}</p>}
          <h3 className="section-label">{tr(lang, "Phụ thuộc giữa các hố ({n})", { n: deps.length })}</h3>
          {deps.map((d: any) => (
            <div key={d.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <span><b>{title(d.thread_id)}</b> {tr(lang, "phụ thuộc")} <b>{title(d.depends_on_thread_id)}</b></span>
              <ActionButton endpoint={`${base}/thread-dependencies/${d.id}`} method="delete" label="✕" />
            </div>
          ))}
          <PostForm endpoint={`${base}/thread-dependencies`} submitLabel={tr(lang, "Phụ thuộc")} fields={[
            { name: "thread_id", label: tr(lang, "Hố"), type: "select", options: threads.map((t: any) => ({ value: t.id, label: t.title })) },
            { name: "depends_on_thread_id", label: tr(lang, "Phụ thuộc vào"), type: "select", options: threads.map((t: any) => ({ value: t.id, label: t.title })) },
          ]} />
        </div>
      </div>

      <div className="dash-head" style={{ marginTop: 26 }}>
        <div>
          <div className="eyebrow">Beats</div>
          <h1>{tr(lang, "Beat theo hố")}</h1>
        </div>
      </div>
      <div className="grid">
        {threads.map((t: any) => (
          <section key={t.id} className="card">
            <h3>{t.title}</h3>
            {(beatsByThread[t.id] ?? []).map((b: any) => (
              <div key={b.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <span>
                  <b>{beatTypeLabel(b.beat_type, lang)}</b>
                  {b.narrative_order != null && <small className="subtle"> · {lang === "en" ? "order" : "thứ tự"} {b.narrative_order}</small>}
                  {b.notes && <div className="subtle">{b.notes}</div>}
                </span>
                <ActionButton endpoint={`${base}/thread-beats/${b.id}`} method="delete" label="✕" confirm={tr(lang, "Xoá beat này?")} />
              </div>
            ))}
            <PostForm endpoint={`${base}/threads/${t.id}/beats`} submitLabel="Beat" fields={[
              { name: "beat_type", label: tr(lang, "Loại beat"), type: "select", options: BEAT_OPTS.map((o) => ({ ...o, label: tr(lang, o.label) })) },
              { name: "scene_id", label: tr(lang, "Cảnh"), type: "select", options: sceneOpts },
              { name: "narrative_order", label: tr(lang, "Thứ tự kể"), type: "number" },
              { name: "notes", label: tr(lang, "Ghi chú") },
            ]} />
          </section>
        ))}
      </div>
    </div></main>
  );
}
