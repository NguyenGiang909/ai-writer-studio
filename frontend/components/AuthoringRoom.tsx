"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getJSON, postJSON } from "../lib/api";
import { t, type Lang } from "../lib/i18n";
import WriterPen, { penLabel } from "./WriterPen";

type Step = { key: string; status: string; error?: string; at: string };
type Run = {
  id: string; phase: string; status: string; prompt: string;
  stage_payload?: any; last_error?: string; live: boolean;
  target_chapters?: number | null; words_per_scene?: number | null;
  call_mode?: string | null; flow?: string | null;
  pause_after_wave?: boolean; wave_arc?: string | null;
  progress?: { scenes: number; with_prose: number };
};
type ArcInfo = { id: string; title: string; state: string; chapters: number };
type Ctx = {
  premise?: Record<string, string>; skeleton?: any;
  arcs?: ArcInfo[]; cast?: string[]; counts?: Record<string, number>;
};
type Status = { run: Run | null; steps: Step[]; phases: string[]; context?: Ctx };

const PHASE_META: Record<string, { icon: string; label: string }> = {
  premise: { icon: "◈", label: "Tiền đề" },
  cast: { icon: "♙", label: "Nhân vật" },
  world: { icon: "◎", label: "Thế giới" },
  outline: { icon: "≋", label: "Dàn ý" },
  build: { icon: "❖", label: "Dựng theo hồi" },
  writing: { icon: "✎", label: "Viết văn" },
};

const PHASE_LINKS: Record<string, { href: string; label: string }> = {
  cast: { href: "/characters", label: "Mở Nhân vật" },
  world: { href: "/world", label: "Mở Thế giới" },
  outline: { href: "", label: "Mở Bản thảo" },
  build: { href: "", label: "Mở Bản thảo" },
  writing: { href: "", label: "Mở Bản thảo" },
};

const FLOW_META: Record<string, { label: string; desc: string }> = {
  rolling: {
    label: "Theo sóng — từng hồi một",
    desc: "Dàn hồi → viết hết hồi đó → hồi sau học theo văn đã viết. Chạy liên tục, có thể bấm dừng sau hồi đang viết.",
  },
  batch: {
    label: "Toàn bộ — khung trước, viết sau",
    desc: "Dàn hết toàn bộ chương/cảnh rồi mới viết. Duyệt khung một lần trước khi viết.",
  },
};

export default function AuthoringRoom({ projectId, lang }: { projectId: string; lang: Lang }) {
  const [data, setData] = useState<Status | null>(null);
  const [prompt, setPrompt] = useState("");
  const [hint, setHint] = useState("");
  const [targetCh, setTargetCh] = useState("");
  const [wordsScene, setWordsScene] = useState("900");
  const [callMode, setCallMode] = useState("safe");
  const [flow, setFlow] = useState("rolling");
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
          <div style={{ display: "flex", gap: 12, marginTop: 4 }}>
            <div className="field" style={{ flex: 1, margin: 0 }}>
              <label style={{ fontSize: 13, color: "var(--muted)" }}>{t(lang, "Số chương mục tiêu")}</label>
              <input
                type="number" min={1} max={500}
                value={targetCh}
                onChange={(e) => setTargetCh(e.target.value)}
                placeholder={t(lang, "Để trống = AI tự quyết")}
                style={{ width: "100%" }}
              />
            </div>
            <div className="field" style={{ flex: 1, margin: 0 }}>
              <label style={{ fontSize: 13, color: "var(--muted)" }}>{t(lang, "Chữ mỗi cảnh")}</label>
              <input
                type="number" min={200} max={5000} step={100}
                value={wordsScene}
                onChange={(e) => setWordsScene(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
            <div className="field" style={{ flex: 1, margin: 0 }}>
              <label style={{ fontSize: 13, color: "var(--muted)" }}>{t(lang, "Cách chạy")}</label>
              <select
                value={flow}
                onChange={(e) => setFlow(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="rolling">{t(lang, FLOW_META.rolling.label)}</option>
                <option value="batch">{t(lang, FLOW_META.batch.label)}</option>
              </select>
            </div>
            <div className="field" style={{ flex: 1, margin: 0 }}>
              <label style={{ fontSize: 13, color: "var(--muted)" }}>{t(lang, "Chế độ gọi AI")}</label>
              <select
                value={callMode}
                onChange={(e) => setCallMode(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="safe">{t(lang, "An toàn — nhiều call nhỏ")}</option>
                <option value="fast">{t(lang, "Nhanh — ít call (API mạnh)")}</option>
              </select>
            </div>
          </div>
          <p style={{ color: "var(--muted)", fontSize: 12, margin: "6px 0 0" }}>
            {t(lang, FLOW_META[flow]?.desc ?? "")}
          </p>
          {err && <div className="notice" style={{ marginTop: 8 }}>{err}</div>}
          <button
            className="btn primary"
            disabled={busy}
            onClick={() => act("start", {
              prompt: prompt.trim() || undefined,
              target_chapters: targetCh.trim() ? parseInt(targetCh, 10) : undefined,
              words_per_scene: wordsScene.trim() ? parseInt(wordsScene, 10) : undefined,
              call_mode: callMode,
              flow: flow,
            })}
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
            <WriterPen
              working={run.status === "running"}
              label={penLabel(run, steps.find((s) => s.status === "running")?.key, lang)}
            />
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h2 style={{ margin: 0, whiteSpace: "nowrap" }}>
                {t(lang, (PHASE_META[run.phase]?.label ?? run.phase))}
              </h2>
              <span className={`pill ${run.status}`}>{run.status}</span>
            </div>
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginTop: 6 }}>
              {(run.progress?.scenes ?? 0) > 0 && (
                <small style={{ color: "var(--muted)" }}>
                  {run.progress!.with_prose}/{run.progress!.scenes} {t(lang, "cảnh có văn")}
                  {run.target_chapters ? ` · ${t(lang, "mục tiêu ~")}${run.target_chapters} ${t(lang, "chương")}` : ""}
                </small>
              )}
              <small style={{ color: "var(--muted)" }}>
                {run.flow === "rolling" ? t(lang, FLOW_META.rolling.label) : t(lang, FLOW_META.batch.label)}
                {" · "}
                {run.call_mode === "fast" ? t(lang, "Nhanh — ít call (API mạnh)") : t(lang, "An toàn — nhiều call nhỏ")}
              </small>
            </div>
            {run.phase === "build" && (data?.context?.arcs?.length ?? 0) > 0 && (
              <div className="auth-waves" style={{ marginTop: 10 }}>
                {(data!.context!.arcs!).map((a) => (
                  <span key={a.id} className={`wave-chip ${a.state}`} title={a.title}>
                    {a.state === "done" ? "✓" : a.state === "current" ? "▶" : "○"} {a.title}
                    {a.chapters > 0 && <small> {a.chapters}ch</small>}
                  </span>
                ))}
              </div>
            )}

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
              {run.status === "running" && run.phase === "build" && (
                <button
                  className={`btn${run.pause_after_wave ? " primary" : ""}`}
                  disabled={busy}
                  title={t(lang, "Hồi đang viết xong thì dừng lại chờ duyệt — bấm lại để huỷ")}
                  onClick={() => act("pause-after-wave")}
                >
                  {run.pause_after_wave ? t(lang, "✓ Sẽ dừng sau hồi này") : t(lang, "Dừng sau hồi này")}
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
