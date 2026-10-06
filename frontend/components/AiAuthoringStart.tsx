"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createPortal } from "react-dom";
import { postJSON } from "../lib/api";
import { t, type Lang } from "../lib/i18n";

export default function AiAuthoringStart({ lang }: { lang: Lang }) {
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const router = useRouter();

  const go = async () => {
    setBusy(true); setErr("");
    try {
      const proj = await postJSON("/api/v1/projects", { name: "Truyện mới AI" });
      await postJSON(`/api/v1/projects/${proj.id}/authoring/start`, { prompt: prompt.trim() });
      router.push(`/projects/${proj.id}/authoring`);
    } catch (e: any) {
      setErr(e?.message ?? "Lỗi khởi tạo");
      setBusy(false);
    }
  };

  return (
    <>
      <button className="btn ghost" onClick={() => setOpen(true)}>
        ✦ {t(lang, "Tạo bằng AI")}
      </button>
      {open && createPortal(
        <div className="project-modal open" onClick={() => !busy && setOpen(false)}>
          <div className="project-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>{t(lang, "AI tự tạo truyện")}</h3>
            <p style={{ color: "var(--muted)", margin: "6px 0 12px" }}>
              {t(lang, "Nhập ý tưởng — AI sẽ đề xuất premise, nhân vật, thế giới, dàn ý rồi viết từng cảnh. Bạn duyệt ở cuối mỗi giai đoạn.")}
            </p>
            <div className="field">
              <textarea
                autoFocus
                rows={4}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={t(lang, "Ví dụ: một chủ quán mì ở phố cổ phát hiện khách quen đều là linh hồn chưa siêu thoát…")}
                style={{ width: "100%" }}
              />
            </div>
            {err && <div className="notice" style={{ marginTop: 8 }}>{err}</div>}
            <div style={{ display: "flex", gap: 8, marginTop: 14, justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => setOpen(false)} disabled={busy}>
                {t(lang, "Huỷ")}
              </button>
              <button className="btn primary" disabled={busy || prompt.trim().length < 3} onClick={go}>
                {busy ? t(lang, "Đang tạo…") : t(lang, "Bắt đầu")}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
