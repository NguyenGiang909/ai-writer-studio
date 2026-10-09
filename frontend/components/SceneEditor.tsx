"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { API, getJSON, patchJSON, postJSON } from "../lib/api";
import { sceneTypeLabel } from "../lib/labels";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { toast } from "../lib/toast";
import SceneHistory from "./SceneHistory";
import ChapterCastPanel from "./ChapterCastPanel";

const SCENE_TYPES = [
  "mystery", "discovery", "relationship", "intimacy", "daily_life",
  "reflection", "conflict", "transition", "reveal", "dialogue",
];

type Scene = {
  id: string;
  project_id: string;
  chapter_id: string;
  title: string | null;
  order_index: number;
  prose: string;
  skeleton: string | null;
  pov_character_id: string | null;
  scene_type: string | null;
  story_time: number | null;
  narrative_order: number | null;
  location_id: string | null;
};

export default function SceneEditor({
  projectId,
  scene,
  chapter,
  chapterTitle,
  sceneIndex,
  sceneTotal,
  characters,
  threads = [],
  abilities = [],
  locations = [],
  reviewHref,
  memoryHref,
  prevScene,
  nextScene,
}: {
  projectId: string;
  scene: Scene;
  chapter?: { id: string; order_index: number; cast_json?: string | null } | null;
  chapterTitle: string;
  sceneIndex?: number;
  sceneTotal?: number;
  characters: { id: string; name: string }[];
  threads?: { id: string; title: string; status?: string }[];
  abilities?: { id: string; name: string; ability_type?: string | null }[];
  locations?: { id: string; name: string }[];
  reviewHref?: string;
  memoryHref?: string;
  prevScene?: { href: string; label: string } | null;
  nextScene?: { href: string; label: string } | null;
}) {
  const lang = useLang();
  const [title, setTitle] = useState(scene.title ?? "");
  const [prose, setProse] = useState(scene.prose ?? "");
  const [skeleton, setSkeleton] = useState(scene.skeleton ?? "");
  const [pov, setPov] = useState(scene.pov_character_id ?? "");
  const [sceneType, setSceneType] = useState(scene.scene_type ?? "");
  const [storyTime, setStoryTime] = useState(scene.story_time ?? "");
  const [narrOrder, setNarrOrder] = useState(scene.narrative_order ?? "");
  const [loc, setLoc] = useState(scene.location_id ?? "");
  const [state, setState] = useState<"saved" | "dirty" | "saving" | "error">("saved");
  const [extracting, setExtracting] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pending = useRef<Record<string, unknown>>({});
  const proseRef = useRef<HTMLTextAreaElement>(null);
  const scenePath = `/api/v1/projects/${projectId}/scenes/${scene.id}`;

  // router.refresh() (vd: AiPanel "Chèn để sửa") đưa prop scene.prose mới —
  // sync vào state để editor hiển thị văn mới; KHÔNG sync khi đang có sửa tay
  // chưa flush (pending/timer) để không nuốt ký tự đang gõ.
  useEffect(() => {
    const dirty = Object.keys(pending.current).length > 0 || !!timer.current;
    if (dirty) return;
    const v = scene.prose ?? "";
    setProse((cur) => (cur !== v ? v : cur));
    const sk = scene.skeleton ?? "";
    setSkeleton((cur) => (cur !== sk ? sk : cur));
  }, [scene.prose, scene.skeleton]);

  function queueSave(patch: Record<string, unknown>) {
    Object.assign(pending.current, patch);
    if ("prose" in patch && sumId) setSumStale(true);
    setState("dirty");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(flush, 800);
  }
  async function flush() {
    const body = pending.current;
    pending.current = {};
    if (!Object.keys(body).length) return;
    setState("saving");
    try {
      await patchJSON(scenePath, body);
      setState("saved");
      window.dispatchEvent(new CustomEvent("writer:saved"));
    } catch {
      setState("error");
    }
  }
  function flushNow() {
    if (timer.current) { clearTimeout(timer.current); timer.current = null; }
    const body = pending.current;
    pending.current = {};
    if (!Object.keys(body).length) return;
    fetch(`${API}${scenePath}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      keepalive: true,
    }).catch(() => {});
  }
  useEffect(() => {
    const el = proseRef.current;
    if (el) { el.style.height = "auto"; el.style.height = `${el.scrollHeight}px`; }
  }, [prose]);
  useEffect(() => {
    const onHide = () => { if (document.visibilityState === "hidden") flushNow(); };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", flushNow);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", flushNow);
      flushNow();
    };
  }, []);

  const [skelBusy, setSkelBusy] = useState(false);
  const [skelElapsed, setSkelElapsed] = useState(0);
  const skelAbort = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!skelBusy) return;
    const t0 = Date.now(); setSkelElapsed(0);
    const iv = setInterval(() => setSkelElapsed(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(iv);
  }, [skelBusy]);

  async function suggestSkeleton() {
    if (skelBusy) return;
    if (skeleton.trim() && !window.confirm(t(lang, "Thay toàn bộ xương cảnh hiện tại bằng gợi ý AI?"))) return;
    setSkelBusy(true);
    const ac = new AbortController(); skelAbort.current = ac;
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/complete`,
        { task: "skeleton", scene_id: scene.id, prompt: "" }, ac.signal);
      const text = (r.reply ?? "").trim();
      if (!text) throw new Error(t(lang, "AI không trả về nội dung"));
      setSkeleton(text);
      queueSave({ skeleton: text });
    } catch (e: any) {
      if (e?.name !== "AbortError") toast(e?.message ?? t(lang, "Lỗi gợi ý xương cảnh"));
    } finally {
      setSkelBusy(false); skelAbort.current = null;
    }
  }

  // --- tóm tắt cảnh (StorySummary scope=scene — nạp lại vào ngữ cảnh AI) ---
  const [sumId, setSumId] = useState<string | null>(null);
  const [sumText, setSumText] = useState("");
  const [sumStale, setSumStale] = useState(false);
  const [sumBusy, setSumBusy] = useState(false);
  const [sumElapsed, setSumElapsed] = useState(0);
  const sumAbort = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!sumBusy) return;
    const t0 = Date.now(); setSumElapsed(0);
    const iv = setInterval(() => setSumElapsed(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(iv);
  }, [sumBusy]);
  useEffect(() => {
    getJSON(`/api/v1/projects/${projectId}/summaries?scope_type=scene`).then((rows: any[]) => {
      const s = (rows ?? []).find((r: any) => r.scope_id === scene.id);
      if (s) { setSumId(s.id); setSumText(s.summary ?? ""); setSumStale(!!s.stale); }
      else { setSumId(null); setSumText(""); setSumStale(false); }
    }).catch(() => {});
  }, [projectId, scene.id]);

  async function suggestSummary() {
    if (sumBusy) return;
    if (timer.current) { clearTimeout(timer.current); await flush(); }
    if (!prose.trim()) { toast(t(lang, "Cảnh chưa có văn để tóm tắt")); return; }
    setSumBusy(true);
    const ac = new AbortController(); sumAbort.current = ac;
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/complete`,
        { task: "summarization", scene_id: scene.id, prompt: prose.slice(-8000) }, ac.signal);
      const text = (r.reply ?? "").trim();
      if (!text) throw new Error(t(lang, "AI không trả về nội dung"));
      setSumText(text); setSumStale(false);
    } catch (e: any) {
      if (e?.name !== "AbortError") toast(e?.message ?? t(lang, "Lỗi tóm tắt"));
    } finally {
      setSumBusy(false); sumAbort.current = null;
    }
  }

  async function saveSummary() {
    if (!sumText.trim()) return;
    try {
      if (sumId) await patchJSON(`/api/v1/projects/${projectId}/summaries/${sumId}`, { summary: sumText.trim(), stale: false });
      else {
        const s: any = await postJSON(`/api/v1/projects/${projectId}/summaries`,
          { scope_type: "scene", scope_id: scene.id, summary: sumText.trim() });
        setSumId(s.id);
      }
      setSumStale(false);
      toast(t(lang, "Đã lưu tóm tắt cảnh"));
    } catch (e: any) {
      toast(e?.message ?? t(lang, "Lỗi lưu tóm tắt"));
    }
  }

  async function extract() {
    if (extracting) return;
    if (timer.current) { clearTimeout(timer.current); await flush(); }
    if (!prose.trim()) { toast(t(lang, "Cảnh chưa có văn để trích xuất")); return; }
    setExtracting(true);
    try {
      const r: any = await postJSON(
        `/api/v1/projects/${projectId}/scenes/${scene.id}/extract-suggestions`, {});
      toast(r.created > 0
        ? t(lang, "AI trích được {n} gợi ý → xem trong Review", { n: r.created })
        : t(lang, "AI không thấy dữ kiện mới cần gợi ý"));
    } catch (e: any) {
      toast(e?.message ?? t(lang, "Lỗi trích xuất"));
    } finally {
      setExtracting(false);
    }
  }

  const words = prose.trim() ? prose.trim().split(/\s+/).length : 0;
  const povName = characters.find((c) => c.id === pov)?.name ?? t(lang, "Người kể");

  return (
    <>
      <div className="editor-head">
        <div className="title-block">
          <div className="eyebrow">
            {t(lang, "Bản thảo")}{sceneIndex && sceneTotal ? ` · ${t(lang, "Cảnh {a}/{b}", { a: sceneIndex, b: sceneTotal })}` : ""}
          </div>
          <h1>{chapterTitle}</h1>
          <div className="meta">
            <span>{words} {t(lang, "từ")}</span>
            <span>{t(lang, "POV:")} {povName}</span>
            <span className={`save-state ${state}`}>
              {state === "saved" && t(lang, "● Đã lưu")}
              {state === "dirty" && t(lang, "○ Chưa lưu")}
              {state === "saving" && t(lang, "… Đang lưu")}
              {state === "error" && t(lang, "⚠ Lỗi lưu")}
            </span>
          </div>
        </div>
        <div className="head-actions">
          <button className="btn" onClick={extract} disabled={extracting || !prose.trim()}
            title={t(lang, "AI đọc văn cảnh này, trích fact/sự kiện/thực thể mới → đẩy vào Review chờ duyệt")}>
            {extracting ? t(lang, "Đang trích…") : t(lang, "Trích xuất dữ kiện")}
          </button>
          <button className="btn" onClick={() => setShowHistory(true)}
            title={t(lang, "Các phiên bản prose đã lưu của cảnh này — xem lại / khôi phục")}>
            {t(lang, "Phiên bản")}
          </button>
          {memoryHref && (
            <Link href={memoryHref} className="btn" style={{ textDecoration: "none" }}>
              {t(lang, "Lịch sử")}
            </Link>
          )}
          {reviewHref && (
            <Link href={reviewHref} className="btn gold" style={{ textDecoration: "none" }}>
              {t(lang, "Review sau viết")}
            </Link>
          )}
        </div>
      </div>
      <div className="editor-shell">
        <ChapterCastPanel
          variant="rail"
          projectId={projectId}
          chapter={chapter ?? null}
          sceneId={scene.id}
          characters={characters}
          threads={threads}
          abilities={abilities}
        />
        <article className="editor-wrap">
        <input
          className="scene-title-input chapter-title"
          value={title}
          onChange={(e) => { setTitle(e.target.value); queueSave({ title: e.target.value }); }}
          placeholder={t(lang, "Tiêu đề cảnh")}
        />
        <ChapterCastPanel
          variant="inline"
          projectId={projectId}
          chapter={chapter ?? null}
          sceneId={scene.id}
          characters={characters}
          threads={threads}
          abilities={abilities}
        />
        <div className="status-strip">
          <span className="pill draft">{t(lang, "Bản nháp của tác giả")}</span>
          <label className="pill" style={{ gap: 6 }}>
            POV
            <select
              value={pov}
              onChange={(e) => { setPov(e.target.value); queueSave({ pov_character_id: e.target.value || null }); }}
              style={{ font: "inherit", fontSize: 12, border: 0, background: "transparent", color: "inherit", outline: "none" }}
            >
              <option value="">{t(lang, "Người kể")}</option>
              {characters.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
          <label className="pill" style={{ gap: 6 }}>
            {t(lang, "Loại")}
            <select
              value={sceneType}
              onChange={(e) => { setSceneType(e.target.value); queueSave({ scene_type: e.target.value || null }); }}
              style={{ font: "inherit", fontSize: 12, border: 0, background: "transparent", color: "inherit", outline: "none" }}
            >
              <option value="">{t(lang, "Chưa phân loại")}</option>
              {SCENE_TYPES.map((st) => (
                <option key={st} value={st}>{sceneTypeLabel(st, lang)}</option>
              ))}
              {sceneType && !SCENE_TYPES.includes(sceneType) && (
                <option value={sceneType}>{sceneTypeLabel(sceneType, lang)}</option>
              )}
            </select>
          </label>
          <label className="pill" style={{ gap: 6 }} title={t(lang, "Thời điểm trong truyện (story time) — khác thứ tự đọc; flashback có story_time nhỏ hơn")}>
            {t(lang, "T.truyện")}
            <input type="number" value={storyTime}
              onChange={(e) => { setStoryTime(e.target.value); queueSave({ story_time: e.target.value === "" ? null : Number(e.target.value) }); }}
              style={{ font: "inherit", fontSize: 12, border: 0, background: "transparent", color: "inherit", outline: "none", width: 46 }}
              placeholder="—" />
          </label>
          <label className="pill" style={{ gap: 6 }} title={t(lang, "Thứ tự đọc (narrative order)")}>
            {t(lang, "T.đọc")}
            <input type="number" value={narrOrder}
              onChange={(e) => { setNarrOrder(e.target.value); queueSave({ narrative_order: e.target.value === "" ? null : Number(e.target.value) }); }}
              style={{ font: "inherit", fontSize: 12, border: 0, background: "transparent", color: "inherit", outline: "none", width: 46 }}
              placeholder="—" />
          </label>
          {locations.length > 0 && (
            <label className="pill" style={{ gap: 6 }} title={t(lang, "Địa điểm diễn ra cảnh — dùng để kiểm tra nhân vật có mặt đúng chỗ không")}>
              {t(lang, "Nơi")}
              <select
                value={loc}
                onChange={(e) => { setLoc(e.target.value); queueSave({ location_id: e.target.value || null }); }}
                style={{ font: "inherit", fontSize: 12, border: 0, background: "transparent", color: "inherit", outline: "none" }}
              >
                <option value="">—</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
            </label>
          )}
        </div>
        <details className="skeleton" open>
          <summary>
            <span className="skel-title">{t(lang, "Ghi chú xương cảnh")}</span>
            {skelBusy ? (
              <>
                <span className="skel-busy">{t(lang, "Đang tạo… {n}s", { n: skelElapsed })}</span>
                <button type="button" className="btn ghost small skel-ai"
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); skelAbort.current?.abort(); }}>
                  {t(lang, "Hủy")}
                </button>
              </>
            ) : (
              <button type="button" className="btn ghost small skel-ai"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); suggestSkeleton(); }}>
                {t(lang, "AI gợi ý")}
              </button>
            )}
          </summary>
          <textarea
            value={skeleton}
            onChange={(e) => { setSkeleton(e.target.value); queueSave({ skeleton: e.target.value }); }}
            placeholder={t(lang, "• Beat 1\n• Beat 2\n• Kết cảnh bằng…")}
            rows={4}
            spellCheck={false}
          />
        </details>
        <details className="skeleton scene-summary">
          <summary>
            <span className="skel-title">
              {t(lang, "Tóm tắt cảnh")}
              {sumStale && <em className="stale-mark">{t(lang, "đã cũ — văn đã sửa")}</em>}
            </span>
            <span className="skel-actions">
              {sumText.trim() && (
                <button type="button" className="btn ghost small skel-ai"
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); saveSummary(); }}>
                  {t(lang, "Lưu tóm tắt")}
                </button>
              )}
              {sumBusy ? (
                <>
                  <span className="skel-busy">{t(lang, "Đang tóm tắt… {n}s", { n: sumElapsed })}</span>
                  <button type="button" className="btn ghost small skel-ai"
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); sumAbort.current?.abort(); }}>
                    {t(lang, "Hủy")}
                  </button>
                </>
              ) : (
                <button type="button" className="btn ghost small skel-ai"
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); suggestSummary(); }}>
                  {t(lang, "AI tóm tắt")}
                </button>
              )}
            </span>
          </summary>
          <textarea
            value={sumText}
            onChange={(e) => setSumText(e.target.value)}
            placeholder={t(lang, "3-5 câu diễn biến chính của cảnh — AI dùng làm ngữ cảnh cho các cảnh/chương sau.")}
            rows={3}
            spellCheck={false}
          />
        </details>
        <textarea
          ref={proseRef}
          className="manuscript manuscript-input"
          value={prose}
          onChange={(e) => { setProse(e.target.value); queueSave({ prose: e.target.value }); }}
          onSelect={(e) => {
            const el = e.currentTarget;
            window.dispatchEvent(new CustomEvent("writer:prose-select", {
              detail: {
                sceneId: scene.id,
                start: el.selectionStart,
                end: el.selectionEnd,
                text: el.value.slice(el.selectionStart, el.selectionEnd),
              },
            }));
          }}
          placeholder={t(lang, "Bắt đầu viết…")}
          spellCheck={false}
        />
        {(prevScene || nextScene) && (
          <nav className="scene-nav" aria-label={t(lang, "Chuyển cảnh")}>
            {prevScene ? (
              <Link href={prevScene.href} className="scene-nav-link prev" title={prevScene.label} onClick={flushNow}>
                <span className="nav-dir">‹ {t(lang, "Cảnh trước")}</span>
                <span className="nav-label">{prevScene.label}</span>
              </Link>
            ) : <span />}
            {nextScene ? (
              <Link href={nextScene.href} className="scene-nav-link next" title={nextScene.label} onClick={flushNow}>
                <span className="nav-dir">{t(lang, "Cảnh sau")} ›</span>
                <span className="nav-label">{nextScene.label}</span>
              </Link>
            ) : <span />}
          </nav>
        )}
      </article>
        <div className="editor-side-r" aria-hidden="true" />
      </div>
      {showHistory && (
        <SceneHistory
          projectId={projectId}
          sceneId={scene.id}
          lang={lang}
          onClose={() => setShowHistory(false)}
          onRestore={(p) => {
            // prose đã được server ghi + snapshot trạng thái hiện tại — chỉ đồng bộ UI
            if (timer.current) { clearTimeout(timer.current); timer.current = null; }
            pending.current = {};
            setProse(p);
            setState("saved");
          }}
        />
      )}
    </>
  );
}
