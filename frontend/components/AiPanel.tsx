"use client";
import { useEffect, useRef, useState } from "react";
import { getJSON, patchJSON, postJSON } from "../lib/api";
import { toast } from "../lib/toast";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { useRouter } from "next/navigation";

type Brief = {
  goal?: string; outline?: string; target_words?: number;
  freedom?: "low" | "medium" | "high";
  must_include?: string; must_avoid?: string; ending_beat?: string;
  mystery_notes?: string; relationship_notes?: string;
};

const FREEDOMS = [
  { v: "low", l: "Thấp" },
  { v: "medium", l: "Vừa" },
  { v: "high", l: "Cao" },
] as const;

export default function AiPanel({ projectId, sceneId }: { projectId: string; sceneId?: string }) {
  const router = useRouter();
  const lang = useLang();
  const [brief, setBrief] = useState<Brief>({ freedom: "medium", target_words: 1400 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [sent, setSent] = useState(false);
  const [reviseNotes, setReviseNotes] = useState("");
  const [reviseMode, setReviseMode] = useState(false);
  const [savedBrief, setSavedBrief] = useState(false);
  const [manifest, setManifest] = useState<string[]>([]);
  const [issues, setIssues] = useState<{ code: string; severity: string; message: string }[]>([]);
  const [phase, setPhase] = useState<"idle" | "saving" | "model">("idle");
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (phase === "idle") return;
    const t0 = Date.now();
    setElapsed(0);
    const iv = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(iv);
  }, [phase]);

  function cancelAI() {
    abortRef.current?.abort();
  }

  useEffect(() => {
    if (!sceneId) { setBrief({ freedom: "medium", target_words: 1400 }); return; }
    getJSON(`/api/v1/projects/${projectId}/manuscript`).then((tree: any) => {
      const scene = tree.chapters.flatMap((c: any) => c.scenes).find((s: any) => s.id === sceneId);
      if (scene?.brief) setBrief({ freedom: "medium", target_words: 1400, ...scene.brief });
      else setBrief({ freedom: "medium", target_words: 1400 });
    }).catch(() => {});
  }, [projectId, sceneId]);

  function set<K extends keyof Brief>(k: K, v: Brief[K]) {
    setBrief((b) => ({ ...b, [k]: v })); setSavedBrief(false);
  }

  function composePrompt(b: Brief): string {
    const parts: string[] = [];
    if (b.goal) parts.push(`Mục tiêu: ${b.goal}`);
    if (b.outline) parts.push(`Xương cảnh:\n${b.outline}`);
    if (b.target_words) parts.push(`Độ dài mục tiêu: ~${b.target_words} từ`);
    parts.push(`AI freedom: ${b.freedom ?? "medium"}`);
    if (b.must_include) parts.push(`Phải có: ${b.must_include}`);
    if (b.must_avoid) parts.push(`Không được: ${b.must_avoid}`);
    if (b.mystery_notes) parts.push(`Giới hạn mystery/lore: ${b.mystery_notes}`);
    if (b.relationship_notes) parts.push(`Giới hạn quan hệ: ${b.relationship_notes}`);
    if (b.ending_beat) parts.push(`Kết cảnh: ${b.ending_beat}`);
    return parts.join("\n");
  }

  async function saveBrief(): Promise<Brief> {
    if (sceneId) {
      await patchJSON(`/api/v1/projects/${projectId}/scenes/${sceneId}`, { brief });
      setSavedBrief(true);
    }
    return brief;
  }

  async function expand() {
    setBusy(true); setPhase("saving"); setError(""); setDraft(""); setSent(false); setIssues([]);
    const ac = new AbortController(); abortRef.current = ac;
    try {
      const b = await saveBrief();
      setPhase("model");
      const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/complete`, {
        task: "writing",
        prompt: composePrompt(b),
        scene_id: sceneId ?? null,
      }, ac.signal);
      setDraft(typeof r === "string" ? r : r.text ?? r.reply ?? JSON.stringify(r));
      if (Array.isArray(r.context)) setManifest(r.context);
      if (Array.isArray(r.issues)) setIssues(r.issues);
      toast(r.provider === "fake" ? t(lang, "Bản nháp từ fake provider — chưa thay đổi Canon") : t(lang, "Đã tạo bản nháp — chưa thay đổi Canon"));
    } catch (e: any) {
      if (e?.name === "AbortError") toast(t(lang, "Đã hủy gọi AI"));
      else {
        const msg = e?.message ?? t(lang, "Lỗi gọi AI");
        setError(
          e?.status === 503 && /No AI provider configured|No connected credential/i.test(msg)
            ? t(lang, "Chưa có provider AI — kết nối trong Settings (Kết nối API) rồi thử lại.")
            : msg
        );
      }
    } finally {
      setBusy(false); setPhase("idle"); abortRef.current = null;
    }
  }

  async function revise() {
    if (!sceneId) { setError(t(lang, "Chọn một cảnh đã có văn trước")); return; }
    setBusy(true); setPhase("saving"); setError(""); setDraft(""); setSent(false); setReviseMode(true); setIssues([]);
    const ac = new AbortController(); abortRef.current = ac;
    try {
      const tree = await getJSON(`/api/v1/projects/${projectId}/manuscript`);
      const scene = tree.chapters.flatMap((c: any) => c.scenes).find((s: any) => s.id === sceneId);
      if (!scene?.prose?.trim()) { setError(t(lang, "Cảnh chưa có văn — dùng 'Tạo bản mở rộng' thay vì sửa")); return; }
      setPhase("model");
      const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/complete`, {
        task: "revision",
        scene_id: sceneId,
        prompt: `ĐOẠN VĂN GỐC:\n${scene.prose}\n\nGHI CHÚ CẦN SỬA:\n${reviseNotes || "(không ghi — tự chỉnh giọng/nhịp)"}`,
      }, ac.signal);
      setDraft(typeof r === "string" ? r : r.text ?? r.reply ?? JSON.stringify(r));
      if (Array.isArray(r.context)) setManifest(r.context);
      if (Array.isArray(r.issues)) setIssues(r.issues);
      toast(t(lang, "Đã có bản sửa — xem và thay thế nếu ưng"));
    } catch (e: any) {
      if (e?.name === "AbortError") toast(t(lang, "Đã hủy gọi AI"));
      else setError(e?.message ?? t(lang, "Lỗi gọi AI"));
    } finally {
      setBusy(false); setPhase("idle"); abortRef.current = null;
    }
  }

  async function replaceProse() {
    if (!sceneId || !draft) return;
    await patchJSON(`/api/v1/projects/${projectId}/scenes/${sceneId}`, { prose: draft });
    setDraft(""); setReviseMode(false);
    toast(t(lang, "Đã thay thế bản thảo bằng bản AI sửa"));
    router.refresh();
  }

  async function insert() {
    if (!sceneId || !draft) return;
    const tree = await getJSON(`/api/v1/projects/${projectId}/manuscript`);
    const scene = tree.chapters.flatMap((c: any) => c.scenes).find((s: any) => s.id === sceneId);
    const prose = (scene?.prose ? scene.prose + "\n\n" : "") + draft;
    await patchJSON(`/api/v1/projects/${projectId}/scenes/${sceneId}`, { prose });
    setDraft("");
    toast(t(lang, "Đã chèn vào bản thảo dưới dạng nội dung cần sửa"));
    router.refresh();
  }

  async function accept() {
    await postJSON(`/api/v1/projects/${projectId}/suggestions`, {
      scene_id: sceneId ?? null,
      change_type: "ai_draft",
      payload: { text: draft, brief },
    });
    setSent(true);
    toast(t(lang, "Đã đưa vào hàng Review · chờ duyệt"));
  }

  return (
    <>
      <div className="field">
        <label>{t(lang, "Mục tiêu cảnh/chương")}</label>
        <input value={brief.goal ?? ""} onChange={(e) => set("goal", e.target.value)}
          placeholder={t(lang, "Minh phát hiện hồ sơ bị xé…")} />
      </div>
      <div className="field">
        <label>{t(lang, "Xương cảnh (5–15 dòng)")}</label>
        <textarea rows={5} value={brief.outline ?? ""} onChange={(e) => set("outline", e.target.value)}
          placeholder={t(lang, "Mỗi dòng một beat: vào hầm lưu trữ → thấy tủ khóa →…")} />
      </div>
      <div className="row">
        <div className="field">
          <label>{t(lang, "Số từ mục tiêu")}</label>
          <input type="number" min={200} step={100} value={brief.target_words ?? 1400}
            onChange={(e) => set("target_words", Number(e.target.value) || 0)} />
        </div>
        <div className="field">
          <label>{t(lang, "AI freedom")}</label>
          <div className="seg">
            {FREEDOMS.map((f) => (
              <button key={f.v} type="button"
                className={`chip${brief.freedom === f.v ? " active" : ""}`}
                onClick={() => set("freedom", f.v)}>{t(lang, f.l)}</button>
            ))}
          </div>
        </div>
      </div>
      <details className="ai-options">
        <summary>
          {t(lang, "Ràng buộc & quyền")} <span>{t(lang, "Phải có · Tránh · Kết · Mystery · Quan hệ")}</span>
        </summary>
        <div className="ai-options-body">
          <div className="row">
            <div className="field">
              <label>{t(lang, "Phải có")}</label>
              <textarea rows={2} value={brief.must_include ?? ""}
                onChange={(e) => set("must_include", e.target.value)}
                placeholder={t(lang, "Motif 'Tôi sẽ không quên'…")} />
            </div>
            <div className="field">
              <label>{t(lang, "Không được")}</label>
              <textarea rows={2} value={brief.must_avoid ?? ""}
                onChange={(e) => set("must_avoid", e.target.value)}
                placeholder={t(lang, "Không reveal tên An trước Ch.28…")} />
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label>{t(lang, "Quyền mystery/lore")}</label>
              <input value={brief.mystery_notes ?? ""}
                onChange={(e) => set("mystery_notes", e.target.value)}
                placeholder={t(lang, "Được gợi ý M-002, không mở M-004")} />
            </div>
            <div className="field">
              <label>{t(lang, "Quyền quan hệ")}</label>
              <input value={brief.relationship_notes ?? ""}
                onChange={(e) => set("relationship_notes", e.target.value)}
                placeholder={t(lang, "Minh–An chỉ ở mức nghi ngờ")} />
            </div>
          </div>
          <div className="field">
            <label>{t(lang, "Kết cảnh (ending beat)")}</label>
            <input value={brief.ending_beat ?? ""}
              onChange={(e) => set("ending_beat", e.target.value)}
              placeholder={t(lang, "Minh giấu trang hồ sơ vào áo")} />
          </div>
        </div>
      </details>
      {sceneId && (
        <button className="btn wide" onClick={() => saveBrief().then(() => toast(t(lang, "Đã lưu Author Brief")))} disabled={busy}>
          {savedBrief ? t(lang, "Brief đã lưu ✓") : t(lang, "Lưu brief vào cảnh")}
        </button>
      )}
      <div className="row" style={{ alignItems: "center", gap: 8 }}>
        <button className="btn primary wide" onClick={expand} disabled={busy} style={{ flex: 1 }}>
          {busy
            ? phase === "saving"
              ? t(lang, "Đang lưu brief…")
              : t(lang, "Đang chờ model… {n}s", { n: elapsed })
            : draft ? t(lang, "✦ Tạo lại bản mở rộng") : t(lang, "✦ Tạo bản mở rộng")}
        </button>
        {busy && phase === "model" && (
          <button className="btn ghost" onClick={cancelAI} title={t(lang, "Hủy gọi AI")}>{t(lang, "Hủy")}</button>
        )}
      </div>
      {busy && phase === "model" && (
        <p className="hint" style={{ marginTop: 6 }}>{t(lang, "Model thật có thể mất ~1 phút.")}</p>
      )}
      {error && <div className="notice" style={{ marginTop: 12 }}>{error}</div>}
      {manifest.length > 0 && (
        <details className="ai-options" style={{ marginTop: 8 }}>
          <summary>
            {t(lang, "Ngữ cảnh AI đã nhận")} <span>{manifest.filter((l) => l.startsWith("included")).length} {t(lang, "phần")} · ~{manifest.reduce((n, l) => n + (Number(/~(\d+)tok/.exec(l)?.[1]) || 0), 0)} tok</span>
          </summary>
          <div className="ai-options-body manifest">
            {manifest.map((l, i) => (
              <div key={i} className={l.startsWith("omitted") ? "ctx-omit" : "ctx-in"}>{l}</div>
            ))}
          </div>
        </details>
      )}
      <details className="ai-options" style={{ marginTop: 8 }}>
        <summary>
          {t(lang, "Sửa đoạn đã viết")} <span>{t(lang, "Gửi nguyên văn + ghi chú sửa")}</span>
        </summary>
        <div className="ai-options-body">
          <div className="field">
            <label>{t(lang, "Ghi chú cần sửa")}</label>
            <textarea rows={3} value={reviseNotes}
              onChange={(e) => setReviseNotes(e.target.value)}
              placeholder={t(lang, "Ví dụ: siết nhịp nhanh hơn, bớt tả cảnh, giữ POV Minh…")} />
          </div>
          <button className="btn wide" onClick={revise} disabled={busy || !sceneId}>
            {busy ? (phase === "model" ? t(lang, "Đang chờ model… {n}s", { n: elapsed }) : t(lang, "Đang sửa…")) : t(lang, "✎ Nhờ AI sửa đoạn này")}
          </button>
        </div>
      </details>
      {draft && (
        <div className="ai-output open">
          <div className="draft-card">
            <h3>{reviseMode ? t(lang, "Bản sửa AI · chưa lưu") : t(lang, "Bản nháp AI · chưa lưu")}</h3>
            {issues.length > 0 && (
              <div className="notice" style={{ marginBottom: 8 }}>
                {t(lang, "⚠ {n} vấn đề continuity trên bản nháp:", { n: issues.length })}
                {issues.map((i, k) => <div key={k}>· {i.message}</div>)}
              </div>
            )}
            <p>{draft}</p>
            <div className="draft-actions">
              <button className="btn" onClick={() => { setDraft(""); setReviseMode(false); toast(t(lang, "Đã bỏ bản nháp AI")); }}>{t(lang, "Bỏ")}</button>
              {reviseMode ? (
                <button className="btn" onClick={replaceProse} disabled={!sceneId}>{t(lang, "Thay thế bản thảo")}</button>
              ) : (
                <button className="btn" onClick={insert} disabled={!sceneId}>{t(lang, "Chèn để sửa")}</button>
              )}
              <button className="btn gold" onClick={accept} disabled={sent}>
                {sent ? t(lang, "Đã gửi Review") : t(lang, "Chấp nhận")}
              </button>
            </div>
          </div>
          <small style={{ color: "var(--muted)" }}>
            {t(lang, "Chấp nhận chỉ đưa nội dung vào hàng Review. Các thay đổi story state vẫn cần duyệt riêng.")}
          </small>
        </div>
      )}
    </>
  );
}
