"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { getJSON, postJSON } from "../lib/api";
import { t, type Lang } from "../lib/i18n";
import WriterPen, { penLabel } from "./WriterPen";

type Step = { key: string; status: string; error?: string; at: string; name?: string };
type Run = {
  id: string; phase: string; status: string; prompt: string;
  stage_payload?: any; last_error?: string; live: boolean;
  display_phase?: string;
  target_chapters?: number | null; words_per_scene?: number | null;
  call_mode?: string | null; flow?: string | null;
  goal_mode?: string | null;
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
  build: { icon: "❖", label: "Dàn ý & viết theo hồi" },
  writing: { icon: "✎", label: "Viết văn" },
};

const PHASE_LINKS: Record<string, { href: string; label: string }> = {
  cast: { href: "/characters", label: "Mở Nhân vật" },
  world: { href: "/world", label: "Mở Thế giới" },
  outline: { href: "", label: "Mở Bản thảo" },
  build: { href: "", label: "Mở Bản thảo" },
  writing: { href: "", label: "Mở Bản thảo" },
};

export const GOAL_META: Record<string, { label: string; desc: string }> = {
  end: {
    label: "Viết hết — chạy liền tới đích",
    desc: "AI chạy liên tục: hết hồi này sang hồi sau cho tới khi đạt mục tiêu hoặc hết khung. Muốn canh điểm dừng vẫn có nút “Dừng sau hồi này”.",
  },
  waves: {
    label: "Theo tiến độ — xong mỗi hồi thì dừng",
    desc: "Sau mỗi hồi viết xong, AI dừng chờ: bạn xem hồi vừa viết, có thể ghi định hướng cho hồi sau rồi Duyệt để AI dàn tiếp — goal đặt dần theo ý bạn.",
  },
};

export const FLOW_META: Record<string, { label: string; desc: string }> = {
  rolling: {
    label: "Theo sóng — từng hồi một",
    desc: "Dàn hồi → viết hết hồi đó → hồi sau học theo văn đã viết. Chạy liên tục, có thể bấm dừng sau hồi đang viết.",
  },
  batch: {
    label: "Toàn bộ — khung trước, viết sau",
    desc: "Dàn hết toàn bộ chương/cảnh rồi mới viết. Duyệt khung một lần trước khi viết.",
  },
};

const STEP_KIND: Record<string, string> = {
  "premise.generate": "Tiền đề",
  "cast.generate": "Dàn nhân vật",
  "world.generate": "Thế giới",
  "world.lore": "Thế giới · lore",
  "world.rules": "Thế giới · luật",
  "world.places": "Thế giới · địa danh",
  "outline.generate": "Dàn ý tổng",
  "outline.skeleton": "Khung quyển · hồi",
  "outline.chapters": "Dàn chương",
  "chapter_scenes": "Dàn cảnh",
  "scene_write": "Viết cảnh",
  "chapter_facts": "Trích diễn biến",
  "__wave_pause__": "Dừng cuối sóng",
};

const STATUS_META: Record<string, { label: string; cls: string }> = {
  running: { label: "Đang chạy", cls: "live" },
  awaiting_review: { label: "Chờ duyệt", cls: "warn" },
  paused: { label: "Đã tạm dừng", cls: "" },
  complete: { label: "Hoàn tất", cls: "ok" },
  failed: { label: "Lỗi", cls: "err" },
};

export default function AuthoringRoom({ projectId, lang }: { projectId: string; lang: Lang }) {
  const [data, setData] = useState<Status | null>(null);
  const [prompt, setPrompt] = useState("");
  const [hint, setHint] = useState("");
  const [targetCh, setTargetCh] = useState("");
  const [wordsScene, setWordsScene] = useState("900");
  const [callMode, setCallMode] = useState("safe");
  const [flow, setFlow] = useState("rolling");
  const [goalMode, setGoalMode] = useState("end");
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
  // rolling: phase lưu là "build" gộp — hiển thị tách outline/writing theo display_phase
  const dispPhase = run ? (run.display_phase ?? run.phase) : "";
  const phaseIdx = run ? (data?.phases ?? []).indexOf(dispPhase) : -1;
  const arcs = data?.context?.arcs ?? [];
  const curWave = arcs.findIndex((a) => a.state === "current");
  const [openPh, setOpenPh] = useState<string | null>(null);

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
              <label style={{ fontSize: 13, color: "var(--muted)" }}>{t(lang, "Kiểu mục tiêu")}</label>
              <select
                value={goalMode}
                onChange={(e) => setGoalMode(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="end">{t(lang, GOAL_META.end.label)}</option>
                <option value="waves">{t(lang, GOAL_META.waves.label)}</option>
              </select>
            </div>
            <div className="field" style={{ flex: 1, margin: 0 }}>
              <label style={{ fontSize: 13, color: "var(--muted)" }}>{t(lang, "Cách chạy")}</label>
              <select
                value={goalMode === "waves" ? "rolling" : flow}
                onChange={(e) => setFlow(e.target.value)}
                disabled={goalMode === "waves"}
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
            {t(lang, GOAL_META[goalMode]?.desc ?? "")}
            {goalMode === "end" && <> {t(lang, FLOW_META[flow]?.desc ?? "")}</>}
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
              flow: goalMode === "waves" ? "rolling" : flow,
              goal_mode: goalMode,
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
              const open = openPh === ph;
              return (
                <button
                  key={ph}
                  type="button"
                  className={`auth-stage ${state}${open ? " open" : ""}`}
                  onClick={() => setOpenPh(open ? null : ph)}
                  aria-expanded={open}
                  title={t(lang, "Bấm để xem nội dung")}
                >
                  <span className="auth-ico">{meta.icon}</span>
                  <div>
                    <b>{t(lang, meta.label)}</b>
                    <small>
                      {state === "done" && t(lang, "xong")}
                      {state === "active" && t(lang,
                        run.status === "paused" ? "tạm dừng" :
                        run.status === "failed" ? "lỗi" : "đang chạy")}
                      {state === "review" && t(lang, "chờ duyệt")}
                      {state === "todo" && t(lang, "chưa tới")}
                    </small>
                  </div>
                  <span className={`auth-caret${open ? " up" : ""}`} aria-hidden>▸</span>
                </button>
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
                {t(lang, (PHASE_META[dispPhase]?.label ?? dispPhase))}
              </h2>
              <span className={`pill ${STATUS_META[run.status]?.cls ?? ""}`}>
                {t(lang, STATUS_META[run.status]?.label ?? run.status)}
              </span>
            </div>
            {(run.progress?.scenes ?? 0) > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <small style={{ color: "var(--muted)" }}>
                    <b style={{ color: "var(--ink)", fontVariantNumeric: "tabular-nums" }}>{run.progress!.with_prose}/{run.progress!.scenes}</b> {t(lang, "cảnh có văn")}
                  </small>
                  {run.target_chapters ? (
                    <small style={{ color: "var(--muted)" }}>{t(lang, "mục tiêu ~")}{run.target_chapters} {t(lang, "chương")}</small>
                  ) : null}
                </div>
                <div
                  className="bar"
                  role="progressbar"
                  aria-valuenow={Math.round((run.progress!.with_prose / run.progress!.scenes) * 100)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <i style={{ width: `${Math.round((run.progress!.with_prose / run.progress!.scenes) * 100)}%` }} />
                </div>
              </div>
            )}
            <div style={{ marginTop: 8 }}>
              <small style={{ color: "var(--muted)" }}>
                {run.flow === "rolling" ? t(lang, "Theo sóng") : t(lang, "Toàn bộ")}
                {" · "}
                {run.call_mode === "fast" ? t(lang, "Nhanh") : t(lang, "An toàn")}
                {run.flow === "rolling" && (
                  <>
                    {" · "}
                    {run.goal_mode === "waves" ? t(lang, "theo tiến độ") : t(lang, "viết hết")}
                  </>
                )}
                {run.flow === "rolling" && arcs.length > 0 && curWave >= 0 && (
                  <>
                    {" · "}
                    <b style={{ color: "var(--ink)", fontVariantNumeric: "tabular-nums" }}>
                      {t(lang, "Hồi")} {curWave + 1}/{arcs.length}
                    </b>
                  </>
                )}
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

            {run.status === "awaiting_review" && run.phase === "build" ? (
              <div className="notice" style={{ marginTop: 12 }}>
                {run.goal_mode === "waves"
                  ? t(lang, "Hồi vừa viết xong — xem lại rồi bấm Duyệt để AI dàn hồi tiếp theo. Ô gợi ý dưới có thể mang định hướng cho hồi sau.")
                  : t(lang, "Hồi đã viết xong theo yêu cầu dừng — duyệt để AI tiếp tục hồi tiếp theo.")}
                {" "}
                <Link href={`/projects/${projectId}`}>{t(lang, "Mở Bản thảo")} →</Link>
              </div>
            ) : run.status === "awaiting_review" && (
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
                  placeholder={t(lang,
                    run.phase === "build"
                      ? "Định hướng cho hồi sau (tuỳ chọn)…"
                      : "Gợi ý chỉnh cho lần tạo lại (tuỳ chọn)…")}
                  style={{ width: "100%" }}
                />
              </div>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
              {run.status === "awaiting_review" && (
                <button
                  className="btn primary"
                  disabled={busy}
                  onClick={() => {
                    // checkpoint sóng: ô gợi ý trở thành goal cho hồi kế
                    act("approve", run.phase === "build"
                      ? { hint: hint.trim() || undefined } : undefined);
                    setHint("");
                  }}
                >
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
              {run.status === "running" && run.phase === "build" && run.goal_mode !== "waves" && (
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
              {steps.map((s) => {
                const m = s.key.match(/^(.*)\.[0-9a-f-]{36}$/i);
                const kind = m ? m[1] : s.key;
                return (
                <li key={s.key + s.at} className={`astep ${s.status}`}>
                  <span>{s.status === "done" ? "✓" : s.status === "failed" ? "✗" : "…"}</span>
                  <code title={s.key}>{t(lang, STEP_KIND[kind] ?? kind)}{s.name ? ` — ${s.name}` : ""}</code>
                  {s.error && <small className="muted"> — {s.error.slice(0, 80)}</small>}
                </li>
                );
              })}
            </ul>
          </div>

          {/* panel nội dung stage đang mở — full width dưới 3 cột */}
          {openPh && (
            <section className="card phase-detail" style={{ margin: 0 }}>
              <PhaseDetail
                ph={openPh}
                ctx={data?.context}
                run={run}
                steps={steps}
                lang={lang}
                projectId={projectId}
              />
            </section>
          )}
        </div>
      )}
    </div>
  );
}

/** Nội dung thật của từng stage — chỉ đọc, không chỉnh sửa ở đây */
function PhaseDetail({ ph, ctx, run, steps, lang, projectId }: {
  ph: string; ctx?: Ctx; run: Run; steps: Step[]; lang: Lang; projectId: string;
}) {
  const meta = PHASE_META[ph] ?? { icon: "•", label: ph };
  const link = PHASE_LINKS[ph];
  const counts = ctx?.counts ?? {};
  const linkEl = link ? (
    <Link href={`/projects/${projectId}${link.href}`} className="btn" style={{ fontSize: 12, textDecoration: "none" }}>
      {t(lang, link.label)} →
    </Link>
  ) : null;

  let body: ReactNode = null;
  if (ph === "premise") {
    const p = ctx?.premise ?? {};
    body = p.title || p.logline || p.premise ? (
      <>
        {p.title && <p className="pd-line"><b>{t(lang, "Tên truyện")}:</b> {p.title}</p>}
        {p.logline && <p className="pd-line"><i>{p.logline}</i></p>}
        {p.premise && <p className="pd-line">{p.premise}</p>}
        {(p.genre || p.tone || p.themes) && (
          <p className="pd-line muted">
            {[p.genre && `${t(lang, "Thể loại")}: ${p.genre}`, p.tone && `Tone: ${p.tone}`,
              p.themes && `${t(lang, "Chủ đề")}: ${Array.isArray(p.themes) ? p.themes.join(", ") : p.themes}`]
              .filter(Boolean).join(" · ")}
          </p>
        )}
      </>
    ) : <p className="muted">{t(lang, "Chưa có — bước Tiền đề sẽ sinh tựa đề, logline và premise.")}</p>;
  } else if (ph === "cast") {
    const names = ctx?.cast ?? [];
    body = names.length > 0 ? (
      <>
        <p className="pd-line muted">{names.length} {t(lang, "nhân vật")}</p>
        <div className="pd-chips">{names.map((n) => <span key={n} className="pd-chip">{n}</span>)}</div>
      </>
    ) : <p className="muted">{t(lang, "Chưa có nhân vật — bước Nhân vật sẽ dàn dàn diễn viên.")}</p>;
  } else if (ph === "world") {
    const rows: [string, number][] = [
      [t(lang, "địa danh"), counts.locations ?? 0],
      [t(lang, "phe"), counts.factions ?? 0],
      [t(lang, "vật"), counts.items ?? 0],
      [t(lang, "năng lực"), counts.abilities ?? 0],
    ];
    body = rows.some(([, n]) => n > 0) ? (
      <div className="pd-stats">
        {rows.map(([label, n]) => (
          <span key={label} className="pd-stat"><b>{n}</b> {label}</span>
        ))}
      </div>
    ) : <p className="muted">{t(lang, "Chưa có thế giới — bước Thế giới sẽ tạo lore, luật và địa danh.")}</p>;
  } else if (ph === "outline" || ph === "build") {
    const arcs = ctx?.arcs ?? [];
    body = arcs.length > 0 ? (
      <>
        <p className="pd-line muted">
          {counts.chapters ?? 0} {t(lang, "chương")} · {counts.scenes ?? 0} {t(lang, "cảnh")}
          {" · "}{arcs.length} {t(lang, "hồi")}
        </p>
        <ul className="pd-arcs">
          {arcs.map((a) => (
            <li key={a.id} className={a.state}>
              <span className="pd-arc-ico">{a.state === "done" ? "✓" : a.state === "current" ? "▶" : "○"}</span>
              {a.title}
              {a.chapters > 0 && <small className="muted"> · {a.chapters} {t(lang, "chương")}</small>}
            </li>
          ))}
        </ul>
      </>
    ) : <p className="muted">{t(lang, "Chưa có dàn ý — bước Dàn ý sẽ dựng hồi, chương và cảnh.")}</p>;
  } else if (ph === "writing") {
    const lastWritten = steps.find((s) => s.status === "done" && s.key.startsWith("scene_write"));
    body = (counts.with_prose ?? 0) > 0 ? (
      <>
        <p className="pd-line">
          <b style={{ fontVariantNumeric: "tabular-nums" }}>{counts.with_prose}/{counts.scenes}</b>{" "}
          {t(lang, "cảnh có văn")}
          {run.target_chapters ? ` · ${t(lang, "mục tiêu ~")}${run.target_chapters} ${t(lang, "chương")}` : ""}
        </p>
        {lastWritten?.name && (
          <p className="pd-line muted">{t(lang, "Vừa viết xong")}: {lastWritten.name}</p>
        )}
      </>
    ) : <p className="muted">{t(lang, "Chưa có văn — đến lượt, bước Viết văn sẽ viết từng cảnh theo dàn ý.")}</p>;
  }

  return (
    <>
      <div className="pd-head">
        <span className="auth-ico">{meta.icon}</span>
        <h3 style={{ margin: 0 }}>{t(lang, meta.label)}</h3>
        <span style={{ flex: 1 }} />
        {linkEl}
      </div>
      <div className="pd-body">{body}</div>
    </>
  );
}
