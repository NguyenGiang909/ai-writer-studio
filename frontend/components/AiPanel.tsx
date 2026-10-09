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
  const [sel, setSel] = useState<{ start: number; end: number; text: string } | null>(null);
  const [reviseSel, setReviseSel] = useState<{ start: number; end: number; text: string } | null>(null);
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

  // Bôi đen trong SceneEditor → revision chỉ ăn đoạn chọn (prompt nhỏ,
  // tránh 60s gateway trên cảnh dài + không đụng phần còn lại).
  // Đọc cả DOM selection lúc mount/mở block vì user hay bôi đen TRƯỚC khi
  // mở panel (event đã dispatch trước khi listener tồn tại).
  // Cuộn trang tới đoạn đang bôi đen — textarea auto-height nên phải đo
  // offset caret qua mirror-div (không scrollIntoView được trong textarea).
  function scrollToSelection() {
    const ta = document.querySelector<HTMLTextAreaElement>(".manuscript-input");
    if (!ta || !sel) return;
    const cs = getComputedStyle(ta);
    const mirror = document.createElement("div");
    mirror.style.cssText =
      `position:absolute;visibility:hidden;left:-9999px;top:0;` +
      `width:${ta.clientWidth}px;white-space:pre-wrap;word-wrap:break-word;` +
      `font:${cs.font};line-height:${cs.lineHeight};padding:${cs.padding};`;
    mirror.textContent = ta.value.slice(0, sel.start);
    const marker = document.createElement("span");
    marker.textContent = "​";
    mirror.appendChild(marker);
    document.body.appendChild(mirror);
    const y = ta.getBoundingClientRect().top + window.scrollY + marker.offsetTop - window.innerHeight / 3;
    document.body.removeChild(mirror);
    window.scrollTo({ top: Math.max(0, y), behavior: "smooth" });
    ta.focus();
    ta.setSelectionRange(sel.start, sel.end);
  }
  function readDomSelection() {
    const ta = document.querySelector<HTMLTextAreaElement>(".manuscript-input");
    if (!ta || ta.selectionEnd <= ta.selectionStart) { setSel(null); return; }
    setSel({ start: ta.selectionStart, end: ta.selectionEnd, text: ta.value.slice(ta.selectionStart, ta.selectionEnd) });
  }
  useEffect(() => {
    setSel(null);
    readDomSelection();
    const onSel = (ev: Event) => {
      const d = (ev as CustomEvent).detail;
      if (!d || d.sceneId !== sceneId) { setSel(null); return; }
      setSel(d.end > d.start ? { start: d.start, end: d.end, text: d.text } : null);
    };
    window.addEventListener("writer:prose-select", onSel);
    return () => window.removeEventListener("writer:prose-select", onSel);
  }, [projectId, sceneId]); // eslint-disable-line react-hooks/exhaustive-deps

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
    setReviseSel(sel);
    try {
      const tree = await getJSON(`/api/v1/projects/${projectId}/manuscript`);
      const scene = tree.chapters.flatMap((c: any) => c.scenes).find((s: any) => s.id === sceneId);
      if (!scene?.prose?.trim()) { setError(t(lang, "Cảnh chưa có văn — dùng 'Tạo bản mở rộng' thay vì sửa")); return; }
      setPhase("model");
      let prompt: string;
      if (sel) {
        const i = scene.prose.indexOf(sel.text);
        const before = i > 0 ? scene.prose.slice(Math.max(0, i - 400), i) : "";
        const after = i >= 0 ? scene.prose.slice(i + sel.text.length, i + sel.text.length + 400) : "";
        prompt = `ĐOẠN VĂN CẦN SỬA (là một phần trong cảnh — chỉ trả về ĐOẠN NÀY đã sửa, văn xuôi thuần, TUYỆT ĐỐI không kèm lại văn trước/sau):\n${sel.text}\n\nVĂN LIỀN TRƯỚC (chỉ tham chiếu, không lặp lại):\n…${before}\n\nVĂN LIỀN SAU (chỉ tham chiếu, không lặp lại):\n${after}…\n\nGHI CHÚ CẦN SỬA:\n${reviseNotes || "(không ghi — tự chỉnh giọng/nhịp)"}`;
      } else {
        prompt = `ĐOẠN VĂN GỐC:\n${scene.prose}\n\nGHI CHÚ CẦN SỬA:\n${reviseNotes || "(không ghi — tự chỉnh giọng/nhịp)"}`;
      }
      const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/complete`, {
        task: "revision",
        scene_id: sceneId,
        prompt,
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
    if (reviseSel) {
      const tree = await getJSON(`/api/v1/projects/${projectId}/manuscript`);
      const scene = tree.chapters.flatMap((c: any) => c.scenes).find((s: any) => s.id === sceneId);
      const prose: string = scene?.prose ?? "";
      let { start, end, text } = reviseSel;
      if (prose.slice(start, end) !== text) {
        const i = prose.indexOf(text);
        if (i < 0 || prose.indexOf(text, i + 1) >= 0) {
          setError(t(lang, "Văn đã đổi — bôi đen lại đoạn cần sửa")); return;
        }
        start = i; end = i + text.length;
      }
      await patchJSON(`/api/v1/projects/${projectId}/scenes/${sceneId}`,
        { prose: prose.slice(0, start) + draft.trim() + prose.slice(end) });
      setDraft(""); setReviseMode(false); setReviseSel(null); setSel(null);
      toast(t(lang, "Đã thay thế đoạn chọn"));
    } else {
      await patchJSON(`/api/v1/projects/${projectId}/scenes/${sceneId}`, { prose: draft });
      setDraft(""); setReviseMode(false);
      toast(t(lang, "Đã thay thế bản thảo bằng bản AI sửa"));
    }
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
        <summary onClick={readDomSelection}>
          {t(lang, "Sửa đoạn đã viết")} <span>{t(lang, "Bôi đen 1 đoạn để chỉ sửa đoạn đó")}</span>
        </summary>
        <div className="ai-options-body">
          <div className="field">
            <label>{t(lang, "Ghi chú cần sửa")}</label>
            <textarea rows={3} value={reviseNotes}
              onChange={(e) => setReviseNotes(e.target.value)}
              placeholder={t(lang, "Ví dụ: siết nhịp nhanh hơn, bớt tả cảnh, giữ POV Minh…")} />
          </div>
          <div className="seg" style={{ marginBottom: 8 }}>
            <button type="button" className="chip"
              onClick={() => setReviseNotes(t(lang, "Làm tự nhiên: gỡ lối văn AI (đối lập thừa, câu kết sở thị, cụm ba máy móc, từ hoa mỹ rỗng) — giữ nguyên nội dung, POV và giọng kể"))}>
              {t(lang, "✎ Làm tự nhiên (gỡ văn AI)")}
            </button>
          </div>
          {sel && (
            <div className="hint" style={{ marginBottom: 8 }}>
              {t(lang, "Đang chọn {n} ký tự — AI chỉ sửa đoạn này:", { n: sel.end - sel.start })}{" "}
              <em>{sel.text.length > 70 ? sel.text.slice(0, 70) + "…" : sel.text}</em>{" "}
              <button type="button" className="btn ghost small" onClick={scrollToSelection}
                title={t(lang, "Cuộn tới đoạn đang chọn")}>{t(lang, "→")}</button>
              <button type="button" className="btn ghost small" onClick={() => setSel(null)}>{t(lang, "Bỏ chọn")}</button>
            </div>
          )}
          <button className="btn wide" onClick={revise} disabled={busy || !sceneId}>
            {busy ? (phase === "model" ? t(lang, "Đang chờ model… {n}s", { n: elapsed }) : t(lang, "Đang sửa…"))
              : sel ? t(lang, "✎ Sửa đoạn đang chọn") : t(lang, "✎ Nhờ AI sửa đoạn này")}
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
              <button className="btn" onClick={() => { setDraft(""); setReviseMode(false); setReviseSel(null); toast(t(lang, "Đã bỏ bản nháp AI")); }}>{t(lang, "Bỏ")}</button>
              {reviseMode ? (
                <button className="btn" onClick={replaceProse} disabled={!sceneId}>
                  {reviseSel ? t(lang, "Thay thế đoạn chọn") : t(lang, "Thay thế bản thảo")}
                </button>
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
