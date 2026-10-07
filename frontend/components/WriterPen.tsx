"use client";

import { t, type Lang } from "../lib/i18n";

/** Bút máy viết trên giấy — chạy khi `working`, nghiêng nâng khi idle.
 * Port từ parker_style_writer_animation_v5 (user-provided). */
export default function WriterPen({ working, label }: { working: boolean; label: string }) {
  return (
    <div className={`wpen-stage ${working ? "working" : "idle"}`} aria-live="polite">
      <div className="wpen-paper">
        <svg className="wpen-scribble" viewBox="0 0 96 15" aria-hidden="true">
          <path d="M1 8 C6 4,10 4,14 8 C18 12,23 12,27 8 C31 4,36 4,40 8 C44 12,49 12,53 8 C57 4,62 4,66 8 C70 12,75 12,79 8 C83 4,88 4,95 8" />
        </svg>
        <div className="wpen-status">
          <span className="wpen-dot" />
          <span>{label}</span>
        </div>
      </div>
      <div className="wpen-pen" aria-hidden="true">
        <div className="wpen-img" />
      </div>
    </div>
  );
}

/** Label mô tả step đang chạy thật — cho cảm giác "đang làm" cụ thể. */
export function penLabel(run: { status: string; phase: string } | null,
                       runningStepKey: string | undefined,
                       lang: Lang): string {
  if (!run) return t(lang, "Sẵn sàng");
  if (run.status === "running") {
    const k = runningStepKey || "";
    if (k.startsWith("scene_write.")) return t(lang, "Đang viết cảnh…");
    if (k.startsWith("chapter_scenes.")) return t(lang, "Đang dàn cảnh…");
    if (k.startsWith("chapter_facts.")) return t(lang, "Đang trích diễn biến…");
    if (k.startsWith("outline.")) return t(lang, "Đang dàn khung…");
    if (k.startsWith("world.")) return t(lang, "Đang dựng thế giới…");
    if (k.startsWith("cast.")) return t(lang, "Đang tạo nhân vật…");
    if (k.startsWith("premise.")) return t(lang, "Đang phác premise…");
    return t(lang, "AI đang làm việc…");
  }
  if (run.status === "awaiting_review") return t(lang, "Chờ bạn duyệt");
  if (run.status === "paused") return t(lang, "Đã tạm dừng");
  if (run.status === "failed") return t(lang, "Có lỗi — bấm Tiếp tục để thử lại");
  if (run.status === "complete") return t(lang, "Hoàn tất");
  return t(lang, "Sẵn sàng");
}
