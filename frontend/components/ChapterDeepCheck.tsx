"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { API, delJSON, getJSON, postJSON, patchJSON } from "../lib/api";
import { severityLabel } from "../lib/labels";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

type Finding = {
  id: string; scope_id: string; scope_type?: string; scope_label?: string | null;
  chapter_title?: string | null;
  chapter_order?: number | null; created_at: string;
  issues: { code: string; severity: string; message: string; suggestion?: string;
            scene_id?: string | null; chapter_id?: string | null; chapter_order?: number | null }[];
};

export default function ChapterDeepCheck({
  projectId, chapters, allChapters, arcs = [],
}: {
  projectId: string;
  chapters: { id: string; title: string; order_index: number }[];
  allChapters?: { id: string; title: string; order_index: number }[];
  arcs?: { id: string; title: string; from: number; to: number; count: number }[];
}) {
  const lang = useLang();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [chid, setChid] = useState(chapters[0]?.id ?? "");
  const allChs = allChapters?.length ? allChapters : chapters;
  const [scope, setScope] = useState<"chapter" | "range">("chapter");
  const [fromO, setFromO] = useState(allChs[0]?.order_index ?? 1);
  const [toO, setToO] = useState(allChs[allChs.length - 1]?.order_index ?? 1);
  const [warns, setWarns] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [err, setErr] = useState("");
  const abort = useRef<AbortController | null>(null);
  const [fixing, setFixing] = useState("");
  const [fixElapsed, setFixElapsed] = useState(0);
  const [preview, setPreview] = useState<{ sceneId: string; text: string } | null>(null);
  const fixAbort = useRef<AbortController | null>(null);
  const [rex, setRex] = useState("");
  const [rexBusy, setRexBusy] = useState(false);

  async function reextract() {
    if (!chid || rexBusy) return;
    setRexBusy(true); setErr("");
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/chapters/${chid}/reextract`, {});
      const rm = r.removed ?? {};
      setRex(t(lang, "Đã thay {a} dữ kiện (xoá {b} cũ). Xem lại dữ kiện chương trong trang Tủ truyện.",
        { a: r.added ?? 0, b: (rm.events ?? 0) + (rm.states ?? 0) + (rm.beats ?? 0) + (rm.facts ?? 0) }));
    } catch (e: any) { setErr(e?.message ?? t(lang, "Lỗi trích lại")); }
    finally { setRexBusy(false); }
  }

  async function insertAfter() {
    const ch = chapters.find((c) => c.id === chid);
    if (!ch) return;
    const title = window.prompt(t(lang,
      "Tên chương mới — sẽ chèn NGAY SAU chương {n}, các chương sau tự dời (đồng bộ cả dữ kiện/sự kiện/tóm tắt):",
      { n: ch.order_index }));
    if (!title?.trim()) return;
    try {
      await postJSON(`/api/v1/projects/${projectId}/chapters/insert`,
        { title: title.trim(), order_index: ch.order_index + 1 });
      window.location.reload();
    } catch (e: any) { setErr(e?.message ?? t(lang, "Lỗi chèn chương")); }
  }

  useEffect(() => {
    if (!fixing) return;
    const iv = setInterval(() => setFixElapsed((s) => s + 1), 1000);
    return () => clearInterval(iv);
  }, [fixing]);

  async function aiFix(issue: { message: string; scene_id?: string | null }, key: string) {
    if (!issue.scene_id || fixing) return;
    setFixing(key); setFixElapsed(0);
    fixAbort.current = new AbortController();
    try {
      const r: any = await postJSON(
        `/api/v1/projects/${projectId}/scenes/${issue.scene_id}/ai-fix`,
        { issue: issue.message }, fixAbort.current.signal);
      setPreview({ sceneId: issue.scene_id, text: r.revised ?? "" });
    } catch (e: any) {
      if (e?.name !== "AbortError") setErr(e?.message ?? t(lang, "Lỗi gọi AI"));
    } finally { setFixing(""); }
  }

  async function applyFix() {
    if (!preview) return;
    await patchJSON(`/api/v1/projects/${projectId}/scenes/${preview.sceneId}`, { prose: preview.text });
    setPreview(null);
    setRex(t(lang, "Đã áp dụng bản sửa — bấm 'Trích lại dữ kiện chương' để cập nhật dữ kiện."));
  }

  async function reload() {
    try {
      const r = await getJSON(`/api/v1/projects/${projectId}/audit/findings`);
      setFindings(r.findings ?? []);
    } catch {}
  }
  useEffect(() => { reload(); }, [projectId]);

  useEffect(() => {
    if (!busy) return;
    const iv = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(iv);
  }, [busy]);

  async function run() {
    if (busy) return;
    setBusy(true); setErr(""); setElapsed(0); setWarns([]);
    abort.current = new AbortController();
    try {
      if (scope === "chapter") {
        if (!chid) return;
        await postJSON(`/api/v1/projects/${projectId}/chapters/${chid}/deep-check`, {},
          abort.current.signal);
      } else {
        const r: any = await postJSON(`/api/v1/projects/${projectId}/deep-check`,
          { from_order: fromO, to_order: toO }, abort.current.signal);
        if (r?.warnings?.length) setWarns(r.warnings);
      }
      await reload();
    } catch (e: any) {
      if (e?.name !== "AbortError") setErr(e?.message ?? t(lang, "Lỗi không xác định"));
    } finally { setBusy(false); }
  }

  async function remove(id: string) {
    try { await delJSON(`/api/v1/audit/findings/${id}`); await reload(); } catch {}
  }

  return (
    <div className="card">
      <h3>{t(lang, "AI soi sâu")}</h3>
      <p className="subtle">
        {t(lang, "Chương: model đọc cả chương bắt lỗi nghĩa trong chương. Khoảng: soi xuyên nhiều chương (hố bị quên, nhân vật biến mất, mạch chệch) qua tóm tắt + mẫu văn — không lặp lỗi đã soi ở từng chương.")}
      </p>
      <div className="mode" style={{ marginBottom: 8 }}>
        <button className={`btn${scope === "chapter" ? " primary" : " ghost"}`}
          onClick={() => setScope("chapter")} disabled={busy}>
          {t(lang, "Chương")}
        </button>
        <button className={`btn${scope === "range" ? " primary" : " ghost"}`}
          onClick={() => setScope("range")} disabled={busy}>
          {t(lang, "Khoảng")}
        </button>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {scope === "chapter" ? (
          <select className="input" value={chid} onChange={(e) => setChid(e.target.value)}
            disabled={busy} style={{ minWidth: 240 }}>
            {chapters.map((c) => (
              <option key={c.id} value={c.id}>
                {t(lang, "Chương {n}", { n: c.order_index })} — {c.title}
              </option>
            ))}
          </select>
        ) : (
          <>
            <select className="input" value={fromO} disabled={busy}
              onChange={(e) => setFromO(Number(e.target.value))} style={{ minWidth: 150 }}>
              {allChs.map((c) => (
                <option key={c.id} value={c.order_index}>{t(lang, "Từ Ch{n}", { n: c.order_index })} — {c.title}</option>
              ))}
            </select>
            <select className="input" value={toO} disabled={busy}
              onChange={(e) => setToO(Number(e.target.value))} style={{ minWidth: 150 }}>
              {allChs.map((c) => (
                <option key={c.id} value={c.order_index}>{t(lang, "Đến Ch{n}", { n: c.order_index })} — {c.title}</option>
              ))}
            </select>
            {arcs.length > 0 && (
              <select className="input" disabled={busy} defaultValue=""
                onChange={(e) => {
                  const a = arcs.find((x) => x.id === e.target.value);
                  if (a) { setFromO(a.from); setToO(a.to); }
                  e.target.value = "";
                }} style={{ minWidth: 150 }}>
                <option value="">{t(lang, "Chọn theo hồi…")}</option>
                {arcs.map((a) => (
                  <option key={a.id} value={a.id}>{a.title} ({a.count} {t(lang, "chương")})</option>
                ))}
              </select>
            )}
          </>
        )}
        {!busy ? (
          <button className="btn primary" onClick={run}
            disabled={scope === "chapter" ? !chid : fromO > toO}>
            {scope === "chapter" ? t(lang, "Soi chương này") : t(lang, "Soi khoảng này")}
          </button>
        ) : (
          <>
            <span className="subtle">{t(lang, "Đang soi… {s}s", { s: elapsed })}</span>
            <button className="btn ghost" onClick={() => abort.current?.abort()}>
              {t(lang, "Hủy")}
            </button>
          </>
        )}
      </div>
      {scope === "chapter" && (
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
        <button className="btn ghost" onClick={reextract} disabled={!chid || rexBusy}
          title={t(lang, "Xoá dữ kiện AI đã trích của chương rồi trích lại từ văn hiện tại — dùng sau khi sửa prose. Dữ kiện tác giả nhập tay được giữ.")}>
          {rexBusy ? t(lang, "Đang trích lại…") : t(lang, "Trích lại dữ kiện chương")}
        </button>
        <button className="btn ghost" onClick={insertAfter} disabled={!chid}
          title={t(lang, "Chèn chương bổ sung ngay sau chương đang chọn — toàn bộ thứ tự chương/sự kiện/trạng thái/tóm tắt phía sau tự dời")}>
          {t(lang, "＋ Chương sau")}
        </button>
        {rex && <span className="subtle">{rex}</span>}
      </div>
      )}
      {warns.length > 0 && (
        <p className="subtle">⚠ {warns.join(" · ")}</p>
      )}
      {err && <p style={{ color: "var(--red)" }}>{err}</p>}

      <div className="review-list" style={{ marginTop: 12 }}>
        {findings.map((f) => (
          <div key={f.id} className="review-item">
            <header>
              <span>
                <b>{f.scope_label
                  ? f.scope_label
                  : t(lang, "Chương {n}", { n: f.chapter_order ?? "?" })}</b>
                {f.chapter_title ? ` — ${f.chapter_title}` : ""}
                {f.scope_type === "range" && (
                  <span className="pill" style={{ marginLeft: 6 }}>{t(lang, "Khoảng")}</span>
                )}
                <span className="subtle"> · {(f.created_at ?? "").slice(0, 16).replace("T", " ")}</span>
              </span>
              <button className="btn ghost small" onClick={() => remove(f.id)}>
                {t(lang, "Xoá")}
              </button>
            </header>
            {!f.issues.length && <p className="subtle">{t(lang, "Không phát hiện lỗi nào.")}</p>}
            {f.issues.map((i, k) => {
              const sev = severityLabel(i.severity, lang);
              return (
                <div key={k} style={{ padding: "6px 0", borderTop: "1px solid var(--border)" }}>
                  <span className={`pill${sev.warn ? " warn" : ""}`}>{sev.label}</span>{" "}
                  <span>{i.message}</span>
                  {i.suggestion && <p className="subtle" style={{ marginTop: 2 }}>→ {i.suggestion}</p>}
                  {i.chapter_order != null && (
                    <Link href={`/projects/${projectId}/read?chapter=${i.chapter_order}`}
                      className="issue-link">→ {t(lang, "Đọc chương {n}", { n: i.chapter_order })}</Link>
                  )}{" "}
                  {i.scene_id && (
                    <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                      <Link href={`/projects/${projectId}?scene=${i.scene_id}`} className="issue-link">
                        → {t(lang, "Mở cảnh")}
                      </Link>
                      <button className="btn ghost small" disabled={!!fixing}
                        onClick={() => aiFix(i, `${f.id}:${k}`)}>
                        {fixing === `${f.id}:${k}`
                          ? t(lang, "AI đang sửa… {s}s", { s: fixElapsed })
                          : t(lang, "AI sửa cảnh này")}
                      </button>
                      {fixing === `${f.id}:${k}` && (
                        <button className="btn ghost small" onClick={() => fixAbort.current?.abort()}>
                          {t(lang, "Hủy")}
                        </button>
                      )}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
        {!findings.length && (
          <p className="subtle">{t(lang, "Chưa soi chương nào. Chọn chương rồi bấm Soi.")}</p>
        )}
      </div>

      {preview && createPortal(
        <div className="project-modal open" role="dialog" aria-modal="true" onClick={() => setPreview(null)}>
          <div className="project-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 760 }}>
            <div className="project-dialog-head">
              <div><h2>{t(lang, "Bản AI sửa — kiểm trước khi áp dụng")}</h2>
              <p>{t(lang, "Bản cũ tự lưu trong Lịch sử cảnh, khôi phục được")}</p></div>
              <button className="project-close" onClick={() => setPreview(null)}>×</button>
            </div>
            <div className="project-content">
              <textarea className="input" style={{ width: "100%", minHeight: 320, fontFamily: "inherit" }}
                value={preview.text} onChange={(e) => setPreview({ ...preview, text: e.target.value })} />
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <button className="btn primary" onClick={applyFix}>{t(lang, "Áp dụng")}</button>
                <button className="btn ghost" onClick={() => setPreview(null)}>{t(lang, "Bỏ")}</button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
