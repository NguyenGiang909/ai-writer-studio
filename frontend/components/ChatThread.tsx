"use client";
import React, { useEffect, useRef, useState } from "react";
import { getJSON, patchJSON, postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

function mdTable(lines: string[], start: number) {
  const isRow = (l?: string) => !!l && l.trim().startsWith("|");
  const isSep = (l?: string) => !!l && l.includes("-") && /^\s*\|?[\s:|-]+\|?\s*$/.test(l);
  if (!isRow(lines[start]) || !isSep(lines[start + 1])) return null;
  const parse = (l: string) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  const head = parse(lines[start]);
  const rows: string[][] = [];
  let i = start + 2;
  while (i < lines.length && isRow(lines[i])) { rows.push(parse(lines[i])); i++; }
  return { head, rows, next: i };
}

// inline markdown tối thiểu: **đậm** / *nghiêng* — reply AI hay gửi markdown
function inlineMd(text: string): React.ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((seg, i) => {
    if (seg.startsWith("**") && seg.endsWith("**")) return <strong key={i}>{seg.slice(2, -2)}</strong>;
    if (seg.startsWith("*") && seg.endsWith("*") && seg.length > 2) return <em key={i}>{seg.slice(1, -1)}</em>;
    return seg;
  });
}

function renderContent(content: string) {
  const lines = content.split("\n");
  const out: React.ReactNode[] = [];
  let buf: string[] = [];
  const flush = () => {
    if (buf.length) {
      out.push(
        <span key={`t${out.length}`}>
          {buf.map((l, i) => (
            <React.Fragment key={i}>{i > 0 && "\n"}{inlineMd(l)}</React.Fragment>
          ))}
        </span>
      );
      buf = [];
    }
  };
  let i = 0;
  while (i < lines.length) {
    const tb = mdTable(lines, i);
    if (tb) {
      flush();
      out.push(
        <table key={`m${i}`} className="chat-md-table">
          <thead><tr>{tb.head.map((c, j) => <th key={j}>{c}</th>)}</tr></thead>
          <tbody>
            {tb.rows.map((r, ri) => <tr key={ri}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}
          </tbody>
        </table>
      );
      i = tb.next;
    } else { buf.push(lines[i]); i++; }
  }
  flush();
  return <>{out}</>;
}

function toast(msg: string) {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

export default function ChatThread({
  projectId,
  threadId,
  context,
  sceneId,
  full = false,
}: {
  projectId: string;
  threadId: string;
  context?: string;
  sceneId?: string;
  /** full = trang thread riêng (khung cao hơn); mặc định = panel nhỏ */
  full?: boolean;
}) {
  const lang = useLang();
  const [msgs, setMsgs] = useState<any[] | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let dead = false;
    getJSON(`/api/v1/projects/${projectId}/discussions/${threadId}/messages`)
      .then((m: any[]) => { if (!dead) setMsgs(m); })
      .catch(() => { if (!dead) setMsgs([]); });
    return () => { dead = true; };
  }, [projectId, threadId]);

  useEffect(() => {
    boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight });
  }, [msgs, busy]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true); setError("");
    try {
      const mine: any = await postJSON(
        `/api/v1/projects/${projectId}/discussions/${threadId}/messages`, { content: text });
      setMsgs((m) => [...(m ?? []), mine]);
      setInput("");
      const ai: any = await postJSON(
        `/api/v1/projects/${projectId}/discussions/${threadId}/ai-reply`,
        { context: context ?? null, scene_id: sceneId ?? null });
      setMsgs((m) => [...(m ?? []), ai]);
    } catch (e: any) {
      setError(e?.message ?? t(lang, "Lỗi gọi AI"));
    } finally {
      setBusy(false);
    }
  }

  async function pin(m: any) {
    try {
      const r: any = await patchJSON(
        `/api/v1/projects/${projectId}/discussions/${threadId}/messages/${m.id}`,
        { pinned: !m.pinned });
      setMsgs((ms) => (ms ?? []).map((x) => (x.id === m.id ? { ...x, pinned: r.pinned } : x)));
    } catch { /* optional */ }
  }

  async function toDecision(m: any) {
    try {
      await postJSON(`/api/v1/projects/${projectId}/author-decisions`, {
        title: m.content.split("\n")[0].slice(0, 80),
        decision_text: m.content,
        rationale: t(lang, "Chốt từ thảo luận #{id}", { id: threadId.slice(0, 8) }),
      });
      toast(t(lang, "Đã lưu thành Quyết định tác giả"));
    } catch (e: any) { setError(e?.message ?? t(lang, "Lỗi lưu quyết định")); }
  }

  async function toCanon(m: any) {
    try {
      await postJSON(`/api/v1/projects/${projectId}/suggestions`, {
        change_type: "canon_fact",
        scene_id: sceneId ?? null,
        payload: { text: m.content, source: "discussion" },
      });
      toast(t(lang, "Đã đưa vào hàng Review — chờ tác giả duyệt"));
    } catch (e: any) { setError(e?.message ?? t(lang, "Lỗi tạo gợi ý")); }
  }

  return (
    <div className={full ? "chat-wrap" : ""}>
      <div className={`chat-box${full ? " full" : ""}`} ref={boxRef}>
        {msgs === null && <p className="hint" style={{ margin: 0 }}>{t(lang, "Đang tải…")}</p>}
        {msgs?.length === 0 && (
          <p className="hint" style={{ margin: 0 }}>
            {t(lang, "Hỏi gì cũng được — AI thấy bối cảnh truyện và tin đã ghim. Ghim 📌 tin quan trọng để AI nhớ xuyên suốt.")}
          </p>
        )}
        {(msgs ?? []).map((m) => (
          <div key={m.id} className={`chat-msg ${m.author === "ai" ? "ai" : "me"}`}>
            {m.pinned && <span className="pin-mark">📌 </span>}
            {renderContent(m.content)}
            <span className="chat-actions">
              <button
                type="button"
                className="pin-btn"
                title={m.pinned ? t(lang, "Bỏ ghim") : t(lang, "Ghim — AI luôn đọc tin này")}
                onClick={() => pin(m)}
              >{m.pinned ? "📌" : "📍"}</button>
              {m.author === "ai" && (
                <>
                  <button type="button" className="pin-btn" title={t(lang, "Lưu nội dung này thành Quyết định tác giả")}
                    onClick={() => toDecision(m)}>{t(lang, "✔ Quyết định")}</button>
                  <button type="button" className="pin-btn" title={t(lang, "Đưa nội dung này vào hàng Review như đề xuất canon")}
                    onClick={() => toCanon(m)}>{t(lang, "⚑ Canon")}</button>
                </>
              )}
            </span>
          </div>
        ))}
        {busy && <div className="chat-msg ai">{t(lang, "Đang nghĩ…")}</div>}
      </div>
      {error && <div className="notice">{error}</div>}
      <div className="chat-input">
        <textarea
          rows={full ? 3 : 2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder={busy ? t(lang, "AI đang trả lời…") : t(lang, "Nói với AI… (Enter gửi, Shift+Enter xuống dòng)")}
          disabled={busy}
        />
        <button className="btn primary" onClick={send} disabled={busy || !input.trim()}>
          {t(lang, "Gửi")}
        </button>
      </div>
    </div>
  );
}
