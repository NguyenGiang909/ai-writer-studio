"use client";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { toast } from "../lib/toast";

type Row = { title: string; beat: string; on: boolean };

function parseOutline(text: string): Row[] {
  const rows: Row[] = [];
  for (const raw of (text || "").split("\n")) {
    const line = raw.trim().replace(/^[-*•]\s*/, "").replace(/^\d+[.)]\s*/, "");
    if (!line) continue;
    const m = /^(.+?)\s*[—–]\s*(.+)$/.exec(line) || /^(.+?)\s+-\s+(.+)$/.exec(line);
    if (m) rows.push({ title: m[1].trim(), beat: m[2].trim(), on: true });
    else rows.push({ title: line, beat: "", on: true });
    if (rows.length >= 12) break;
  }
  return rows;
}

export default function ChapterOutlineModal({
  projectId, chapter, onClose,
}: {
  projectId: string;
  chapter: { id: string; title: string; order_index: number };
  onClose: () => void;
}) {
  const lang = useLang();
  const router = useRouter();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [creating, setCreating] = useState(false);
  const [err, setErr] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!busy) return;
    const t0 = Date.now(); setElapsed(0);
    const iv = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(iv);
  }, [busy]);

  async function generate() {
    setBusy(true); setErr("");
    const ac = new AbortController(); abortRef.current = ac;
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/complete`, {
        task: "chapter_outline", chapter_id: chapter.id, prompt: "",
      }, ac.signal);
      const parsed = parseOutline(r.reply ?? r.text ?? "");
      if (!parsed.length) throw new Error(t(lang, "AI không trả về cảnh nào — thử lại"));
      setRows(parsed);
    } catch (e: any) {
      if (e?.name === "AbortError") { onClose(); return; }
      setErr(e?.message ?? t(lang, "Lỗi gọi AI"));
    } finally { setBusy(false); abortRef.current = null; }
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { generate(); }, []);

  async function createScenes() {
    const picked = (rows ?? []).filter((r) => r.on && r.title.trim());
    if (!picked.length) return;
    setCreating(true);
    try {
      await postJSON(`/api/v1/projects/${projectId}/chapters/${chapter.id}/scenes/batch`, {
        scenes: picked.map((r) => ({
          title: r.title.trim(),
          skeleton: r.beat ? `• ${r.beat}` : null,
        })),
      });
      toast(t(lang, "Đã tạo {n} cảnh — vẫn là bản nháp, sửa tuỳ ý", { n: picked.length }));
      router.refresh();
      onClose();
    } catch (e: any) {
      toast(e?.message ?? t(lang, "Lỗi tạo cảnh"));
    } finally { setCreating(false); }
  }

  const picked = (rows ?? []).filter((r) => r.on).length;

  return createPortal(
    <div className="project-modal open" onClick={onClose}>
      <div className="project-dialog" style={{ width: "min(620px, 94vw)" }} onClick={(e) => e.stopPropagation()}>
        <div className="project-dialog-head">
          <div>
            <h2>{t(lang, "Gợi ý cảnh — Chương {n}", { n: chapter.order_index })}</h2>
            <p>{chapter.title} · {t(lang, "nháp AI — chưa tạo gì, bạn duyệt từng dòng")}</p>
          </div>
          <button className="project-close" onClick={onClose} aria-label="Đóng">×</button>
        </div>
        <div className="project-content">
          {busy && (
            <p className="hint">
              {t(lang, "Đang chờ model… {n}s (model thật có thể mất ~1 phút).", { n: elapsed })}
              {" "}
              <button className="btn ghost small" onClick={() => abortRef.current?.abort()}>{t(lang, "Hủy")}</button>
            </p>
          )}
          {err && <div className="notice">{err}</div>}
          {rows && !busy && (
            <>
              <div className="outline-rows">
                {rows.map((r, i) => (
                  <div key={i} className={`outline-row${r.on ? "" : " off"}`}>
                    <input type="checkbox" checked={r.on}
                      onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, on: e.target.checked } : x))} />
                    <div className="outline-fields">
                      <input value={r.title} placeholder={t(lang, "Tên cảnh")}
                        onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, title: e.target.value } : x))} />
                      <input value={r.beat} placeholder={t(lang, "Beat ngắn → vào xương cảnh")}
                        onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, beat: e.target.value } : x))} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="form-actions">
                <button className="btn ghost" onClick={generate} disabled={busy}>{t(lang, "Tạo lại")}</button>
                <button className="btn" onClick={onClose}>{t(lang, "Bỏ")}</button>
                <button className="btn primary" onClick={createScenes} disabled={creating || !picked}>
                  {creating ? t(lang, "Đang tạo…") : t(lang, "Tạo {n} cảnh", { n: picked })}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
