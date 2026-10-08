"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { kindLabel, severityLabel, payloadText } from "../lib/labels";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { postJSON, patchJSON, delJSON } from "../lib/api";

const storeKey = (pid: string) => `writer:dismissed:${pid}`;
const fp = (i: any) => `${i.code}:${JSON.stringify(i.evidence ?? {})}`;

function issueLinks(projectId: string, ev: any) {
  if (!ev) return [];
  const base = `/projects/${projectId}`;
  const out: { href: string; label: string }[] = [];
  if (ev.scene_id) out.push({ href: `${base}?scene=${ev.scene_id}`, label: "→ Mở cảnh" });
  if (ev.thread_id) out.push({ href: `${base}/threads`, label: "→ Hố" });
  if (ev.character_id || ev.knower_id || ev.owner_id)
    out.push({ href: `${base}/characters`, label: "→ Nhân vật" });
  if (ev.ability_id) out.push({ href: `${base}/abilities`, label: "→ Năng lực" });
  if (ev.item_id || ev.location_id) out.push({ href: `${base}/world`, label: "→ Thế giới" });
  if (ev.relationship_id) out.push({ href: `${base}/characters`, label: "→ Quan hệ" });
  if (ev.fact_id) out.push({ href: `${base}/truth`, label: "→ Canon" });
  return out;
}

export default function ReviewIssues({
  issues,
  projectId,
}: {
  issues: any[];
  projectId: string;
}) {
  const lang = useLang();
  const router = useRouter();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [showHidden, setShowHidden] = useState(false);
  const [fq, setFq] = useState("");
  const [resolving, setResolving] = useState("");
  const [fixing, setFixing] = useState("");
  const [fixElapsed, setFixElapsed] = useState(0);
  const [preview, setPreview] = useState<{ sceneId: string; fp: string; text: string } | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!fixing) return;
    const iv = setInterval(() => setFixElapsed((s) => s + 1), 1000);
    return () => clearInterval(iv);
  }, [fixing]);

  async function keepValue(i: any, opt: { value: string; ids: string[] }) {
    setResolving(i._fp);
    try {
      if (i.code === "CANON_CONFLICT") {
        const losers = (i.evidence.options as any[])
          .filter((o) => o.value !== opt.value)
          .flatMap((o) => o.ids as string[]);
        for (const id of losers)
          await patchJSON(`/api/v1/projects/${projectId}/canon-facts/${id}`, { truth_status: "REJECTED" });
      } else if (i.code === "STATE_CONFLICT") {
        const losers = (i.evidence.options as any[])
          .filter((o) => o.value !== opt.value)
          .flatMap((o) => o.ids as string[]);
        for (const id of losers)
          await delJSON(`/api/v1/projects/${projectId}/story-states/${id}`);
      }
      router.refresh();
    } finally { setResolving(""); }
  }

  async function aiFix(i: any) {
    const sceneId = i.evidence?.scene_id;
    if (!sceneId || fixing) return;
    setFixing(i._fp); setFixElapsed(0);
    abort.current = new AbortController();
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/scenes/${sceneId}/ai-fix`,
        { issue: i.message }, abort.current.signal);
      setPreview({ sceneId, fp: i._fp, text: r.revised ?? "" });
    } catch (e: any) {
      if (e?.name !== "AbortError") alert(e?.message ?? t(lang, "Lỗi gọi AI"));
    } finally { setFixing(""); }
  }

  async function applyFix() {
    if (!preview) return;
    await patchJSON(`/api/v1/projects/${projectId}/scenes/${preview.sceneId}`, { prose: preview.text });
    setPreview(null);
    router.refresh();
  }

  useEffect(() => {
    try {
      setDismissed(new Set(JSON.parse(localStorage.getItem(storeKey(projectId)) ?? "[]")));
    } catch {}
  }, [projectId]);

  function dismiss(id: string, on: boolean) {
    setDismissed((s) => {
      const n = new Set(s);
      on ? n.add(id) : n.delete(id);
      try { localStorage.setItem(storeKey(projectId), JSON.stringify([...n])); } catch {}
      return n;
    });
  }

  const rows = issues.map((i: any) => ({ ...i, _fp: fp(i) }));
  const needle = fq.trim().toLowerCase();
  const filtered = needle
    ? rows.filter((r) => `${kindLabel(r.code, lang)} ${r.message} ${payloadText(r.evidence, lang)}`.toLowerCase().includes(needle))
    : rows;
  const visible = filtered.filter((r) => showHidden || !dismissed.has(r._fp));
  const hiddenCount = rows.length - rows.filter((r) => !dismissed.has(r._fp)).length;

  return (
    <>
      {rows.length > 10 && (
        <input className="list-filter" style={{ width: "100%", marginBottom: 8 }}
          value={fq} onChange={(e) => setFq(e.target.value)}
          placeholder={t(lang, "Lọc điểm cần xem…")} aria-label={t(lang, "Lọc điểm cần xem")} />
      )}
      {hiddenCount > 0 && (
        <button className="btn ghost small" style={{ marginBottom: 8 }} onClick={() => setShowHidden((v) => !v)}>
          {showHidden ? t(lang, "Ẩn lại {n} mục đã xem", { n: hiddenCount }) : t(lang, "Hiện {n} mục đã đánh dấu đã xem", { n: hiddenCount })}
        </button>
      )}
      <div className="review-list">
        {visible.map((i: any) => {
          const sev = severityLabel(i.severity, lang);
          const gone = dismissed.has(i._fp);
          return (
            <div key={i._fp} className={`review-item${gone ? " dismissed" : ""}`}>
              <header>
                <span className={sev.warn ? "danger" : ""}>{kindLabel(i.code, lang)}</span>
                <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  <span className={`pill${sev.warn ? " warn" : ""}`}>{sev.label}</span>
                  <button className="btn ghost small" onClick={() => dismiss(i._fp, !gone)}>
                    {gone ? t(lang, "Bỏ ẩn") : t(lang, "Đã xem")}
                  </button>
                </span>
              </header>
              <p>{i.message}</p>
              {i.evidence && <p className="subtle">{payloadText(i.evidence, lang)}</p>}
              {Array.isArray(i.evidence?.options) && (
                <div className="issue-actions" style={{ flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
                  <span className="subtle">{t(lang, "Chọn giá trị đúng:")}</span>
                  {(i.evidence.options as any[]).map((o, k) => (
                    <button key={k} className="btn ghost small" disabled={resolving === i._fp}
                      onClick={() => keepValue(i, o)} title={t(lang, "Các bản còn lại sẽ bị đánh dấu bác bỏ")}>
                      {resolving === i._fp ? "…" : `✓ ${String(o.value).slice(0, 60)}`}
                    </button>
                  ))}
                </div>
              )}
              <div className="issue-actions">
                {issueLinks(projectId, i.evidence).map((l) => (
                  <Link key={l.href + l.label} href={l.href} className="issue-link">{t(lang, l.label)}</Link>
                ))}
                {i.evidence?.scene_id && (
                  <button className="btn ghost small" disabled={!!fixing} onClick={() => aiFix(i)}>
                    {fixing === i._fp
                      ? t(lang, "AI đang sửa… {s}s", { s: fixElapsed })
                      : t(lang, "AI sửa cảnh này")}
                  </button>
                )}
                {fixing === i._fp && (
                  <button className="btn ghost small" onClick={() => abort.current?.abort()}>
                    {t(lang, "Hủy")}
                  </button>
                )}
              </div>
            </div>
          );
        })}
        {!visible.length && (
          <p className="subtle">
            {issues.length ? t(lang, "Tất cả điểm đã được đánh dấu đã xem.") : t(lang, "Không phát hiện vấn đề liên tục nào.")}
          </p>
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
    </>
  );
}
