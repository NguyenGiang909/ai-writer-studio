"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getJSON, postJSON } from "../lib/api";
import { t, type Lang } from "../lib/i18n";

type Step = { key: string; status: string; error?: string; at: string };
type Run = {
  id: string; phase: string; status: string; prompt: string;
  stage_payload?: any; last_error?: string; live: boolean;
};
type Status = { run: Run | null; steps: Step[]; phases: string[] };

const PHASE_META: Record<string, { icon: string; label: string }> = {
  premise: { icon: "◈", label: "Tiền đề" },
  cast: { icon: "♙", label: "Nhân vật" },
  world: { icon: "◎", label: "Thế giới" },
  outline: { icon: "≋", label: "Dàn ý" },
  writing: { icon: "✎", label: "Viết văn" },
};

const PHASE_LINKS: Record<string, { href: string; label: string }> = {
  cast: { href: "/characters", label: "Mở Nhân vật" },
  world: { href: "/world", label: "Mở Thế giới" },
  outline: { href: "", label: "Mở Bản thảo" },
  writing: { href: "", label: "Mở Bản thảo" },
};

export default function AuthoringRoom({ projectId, lang }: { projectId: string; lang: Lang }) {
  const [data, setData] = useState<Status | null>(null);
  const [prompt, setPrompt] = useState("");
  const [hint, setHint] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = (await getJSON(`/api/v1/projects/${projectId}/authoring/status`)) as Status;
      setData(s);
    } catch (e: any) {
      setErr(e?.message ?? "");
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
    timer.current = setInterval(refresh, 2500);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [refresh]);

  const act = async (path: string, body?: unknown) => {
    setBusy(true); setErr("");
    try {
      await postJSON(`/api/v1/projects/${projectId}/authoring/${path}`, body);
      await refresh();
    } catch (e: any) {
      setErr(e?.message ?? "Lỗi");
    } finally {
      setBusy(false);
    }
  };

  const run = data?.run ?? null;
  const steps = data?.steps ?? [];
  const phaseIdx = run ? (data?.phases ?? []).indexOf(run.phase) : -1;

  return (
    <div className="dashboard" style={{ maxWidth: 1100 }}>
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Phòng tạo truyện")}</div>
          <h1>{t(lang, "AI tự tạo truyện")}</h1>
          <p style={{ color: "var(--muted)", marginTop: 6, maxWidth: 620 }}>
            {t(lang, "AI điền dàn nhân vật, thế giới, dàn ý và viết cảnh — dừng lại ở cuối mỗi giai đoạn để bạn duyệt. Mọi thứ tạo ra đều sửa/xoá được như bình thường.")}
          </p>
        </div>
      </div>

      {!run && (
        <section className="card" style={{ marginTop: 18, maxWidth: 640 }}>
          <h2 style={{ marginTop: 0 }}>{t(lang, "Ý tưởng / định hướng")}</h2>
          <p style={{ color: "var(--muted)", marginTop: 0, fontSize: 14 }}>
            {t(lang, "Truyện đã có khung thì để trống — AI sẽ đọc nội dung hiện có và viết phần còn thiếu. Truyện mới cần ít nhất 1 câu ý tưởng.")}
          </p>
          <div className="field">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              placeholder={t(lang, "Ví dụ: một chủ quán mì ở phố cổ phát hiện khách quen đều là linh hồn chưa siêu thoát…")}
              style={{ width: "100%" }}
            />
          </div>
          {err && <div className="notice" style={{ marginTop: 8 }}>{err}</div>}
          <button
            className="btn primary"
            disabled={busy}
            onClick={() => act("start", { prompt: prompt.trim() || undefined })}
          >
            {busy ? t(lang, "Đang khởi động…") : t(lang, "Bắt đầu tạo truyện")}
          </button>
        </section>
      )}

      {run && (
        <div className="authoring-grid" style={{ marginTop: 18 }}>
          {/* cột trái: stepper stage */}
          <div className="auth-stages">
            {(data?.phases ?? []).map((ph, i) => {
              const meta = PHASE_META[ph] ?? { icon: "•", label: ph };
              const state =
                run.status === "complete" || i < phaseIdx ? "done"
                : i === phaseIdx ? (run.status === "awaiting_review" ? "review" : "active")
                : "todo";
              return (
                <div key={ph} className={`auth-stage ${state}`}>
                  <span className="auth-ico">{meta.icon}</span>
                  <div>
                    <b>{t(lang, meta.label)}</b>
                    <small>
                      {state === "done" && t(lang, "xong")}
                      {state === "active" && t(lang, "đang chạy")}
                      {state === "review" && t(lang, "chờ duyệt")}
                      {state === "todo" && t(lang, "chưa tới")}
                    </small>
                  </div>
                </div>
              );
            })}
          </div>

          {/* cột giữa: payload stage hiện tại + điều khiển */}
          <section className="card" style={{ margin: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h2 style={{ margin: 0, flex: 1 }}>
                {t(lang, (PHASE_META[run.phase]?.label ?? run.phase))}
                <span className={`pill ${run.status}`} style={{ marginLeft: 10 }}>{run.status}</span>
              </h2>
            </div>

            {run.stage_payload?.premise && (
              <div className="auth-payload">
                <h3>{run.stage_payload.title}</h3>
                <p><i>{run.stage_payload.logline}</i></p>
                <p>{run.stage_payload.premise}</p>
                <p className="muted">
                  {run.stage_payload.genre} · {run.stage_payload.tone}
                </p>
              </div>
            )}
            {run.stage_payload && !run.stage_payload.premise && (
              <pre className="auth-payload-json">{JSON.stringify(run.stage_payload, null, 2)}</pre>
            )}

            {run.status === "awaiting_review" && (
              <div className="notice" style={{ marginTop: 12 }}>
                {t(lang, "Giai đoạn này đã xong — kiểm tra kết quả (có thể sửa trực tiếp ở trang tương ứng), rồi duyệt để tiếp tục.")}
                {PHASE_LINKS[run.phase] && (
                  <> <Link href={`/projects/${projectId}${PHASE_LINKS[run.phase].href}`}>
                    {t(lang, PHASE_LINKS[run.phase].label)} →</Link></>
                )}
              </div>
            )}
            {run.last_error && (
              <div className="notice" style={{ marginTop: 12 }}>⚠ {run.last_error}</div>
            )}
            {err && <div className="notice" style={{ marginTop: 8 }}>{err}</div>}

            {run.status === "awaiting_review" && run.phase !== "writing" && (
              <div className="field" style={{ marginTop: 12 }}>
                <input
                  value={hint}
                  onChange={(e) => setHint(e.target.value)}
                  placeholder={t(lang, "Gợi ý chỉnh cho lần tạo lại (tuỳ chọn)…")}
                  style={{ width: "100%" }}
                />
              </div>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
              {run.status === "awaiting_review" && (
                <button className="btn primary" disabled={busy} onClick={() => act("approve")}>
                  {t(lang, "Duyệt & tiếp tục")}
                </button>
              )}
              {run.status === "awaiting_review" && run.phase !== "writing" && (
                <button
                  className="btn"
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm(t(lang, "Tạo lại sẽ xoá kết quả AI của giai đoạn này rồi chạy lại. Tiếp tục?"))) {
                      act("regenerate", { hint: hint.trim() || undefined });
                      setHint("");
                    }
                  }}
                >
                  {t(lang, "Tạo lại")}
                </button>
              )}
              {run.status === "running" && (
                <button className="btn" disabled={busy} onClick={() => act("pause")}>
                  {t(lang, "Tạm dừng")}
                </button>
              )}
              {(run.status === "paused" || run.status === "failed") && (
                <button className="btn primary" disabled={busy} onClick={() => act("resume")}>
                  {t(lang, "Tiếp tục")}
                </button>
              )}
              {run.status === "complete" && (
                <Link href={`/projects/${projectId}`} className="btn primary" style={{ textDecoration: "none" }}>
                  {t(lang, "Mở bản thảo →")}
                </Link>
              )}
            </div>
          </section>

          {/* cột phải: step log */}
          <div className="card auth-log" style={{ margin: 0 }}>
            <h3 style={{ marginTop: 0 }}>{t(lang, "Nhật ký bước")}</h3>
            {steps.length === 0 && <p className="muted">{t(lang, "Chưa có bước nào.")}</p>}
            <ul className="auth-steps">
              {steps.map((s) => (
                <li key={s.key + s.at} className={`astep ${s.status}`}>
                  <span>{s.status === "done" ? "✓" : s.status === "failed" ? "✗" : "…"}</span>
                  <code>{s.key}</code>
                  {s.error && <small className="muted"> — {s.error.slice(0, 80)}</small>}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
