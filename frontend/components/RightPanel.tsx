"use client";
import Link from "next/link";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AiPanel from "./AiPanel";
import QuickChat from "./QuickChat";
import { getJSON, postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { toast } from "../lib/toast";

type Tab = "discuss" | "expand" | "check";

const SECTION_CTX: [RegExp, string][] = [
  [/story$/, "mục Thiết kế truyện (premise, arc, cấu trúc)"],
  [/characters$/, "mục Nhân vật — hồ sơ, vai trò, quan hệ"],
  [/world$/, "mục Thế giới — địa điểm, bối cảnh"],
  [/abilities$/, "mục Năng lực / hệ thống sức mạnh"],
  [/threads$/, "mục Threads / Hố — các vấn đề cốt truyện còn mở"],
  [/timeline$/, "mục Timeline — trình tự sự kiện"],
  [/style$/, "mục Phong cách viết"],
  [/review$/, "mục Continuity & Review — gợi ý chờ duyệt"],
  [/truth$/, "mục Canon & Truth"],
  [/memory$/, "mục Memory"],
  [/branches/, "mục What-if branches"],
];

export default function RightPanel({
  projectId,
  chapters,
  characters,
  counts,
}: {
  projectId: string;
  chapters: any[];
  characters: { id: string; name: string }[];
  counts: { canon: number; decisions: number; threads: number; styles: number; continuity: number };
}) {
  const lang = useLang();
  const search = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const sceneId = search.get("scene") ?? undefined;
  const [tab, setTab] = useState<Tab>("discuss");
  const [ctxOpen, setCtxOpen] = useState(false);
  const [chaptersLive, setChaptersLive] = useState(chapters);
  const [suggest, setSuggest] = useState("");
  const [suggestBusy, setSuggestBusy] = useState(false);
  const [ctxManifest, setCtxManifest] = useState<string[] | null>(null);

  useEffect(() => setCtxManifest(null), [sceneId]);

  async function toggleCtx() {
    const next = !ctxOpen;
    setCtxOpen(next);
    if (next && !ctxManifest) {
      try {
        const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/context-manifest`, {
          task: "writing", scene_id: scene?.id ?? null,
        });
        setCtxManifest(r.manifest ?? []);
      } catch { setCtxManifest([]); }
    }
  }

  // props của layout có thể cũ sau soft-navigation — fetch lại khi cần
  useEffect(() => setChaptersLive(chapters), [chapters]);
  useEffect(() => {
    if (!sceneId) return;
    const found = chaptersLive.some((c) => c.scenes?.some((s: any) => s.id === sceneId));
    if (!found)
      getJSON(`/api/v1/projects/${projectId}/manuscript`)
        .then((t: any) => setChaptersLive(t.chapters ?? []))
        .catch(() => {});
  }, [sceneId, projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  const scenes = chaptersLive.flatMap((c) => (c.scenes ?? []).map((s: any) => ({ ...s, chapter: c })));
  const scene = scenes.find((s) => s.id === sceneId) ?? null;
  const povName = characters.find((c) => c.id === scene?.pov_character_id)?.name;

  const section = SECTION_CTX.find(([re]) => re.test(pathname ?? ""));
  const context = scene
    ? t(lang, 'Cảnh "{t}" — {c}', { t: scene.title ?? t(lang, "(chưa đặt tên)"), c: scene.chapter.title })
    : section?.[1] ? t(lang, section[1]) : t(lang, "tổng quan bản thảo");

  function pick(tab: Tab, label: string) {
    setTab(tab);
    toast(`${t(lang, label)} ${t(lang, "đã được chọn")}`);
  }

  async function suggestSection() {
    setSuggestBusy(true); setSuggest("");
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/ai/complete`, {
        task: "discussion",
        prompt: `Tác giả đang làm việc ở ${context}. Hãy xem xét dữ kiện truyện và đề xuất 3–5 ý cụ thể để bổ sung/cải thiện phần này. Nếu cần thông tin thêm, hỏi lại tác giả.`,
      });
      setSuggest(r.text ?? r.reply ?? "");
    } catch (e: any) {
      toast(e?.message ?? t(lang, "Lỗi gọi AI"));
    } finally {
      setSuggestBusy(false);
    }
  }

  async function sendSuggestionToReview() {
    await postJSON(`/api/v1/projects/${projectId}/suggestions`, {
      scene_id: null,
      change_type: "ai_draft",
      payload: { text: suggest, context },
    });
    setSuggest("");
    toast(t(lang, "Đã đưa gợi ý vào hàng Review"));
    router.refresh();
  }

  return (
    <aside className="right">
      <div className="right-head">
        <h2>{t(lang, "Trợ lý AI")}</h2>
        <div className="tabs">
          <button className={`tab${tab === "discuss" ? " active" : ""}`} onClick={() => pick("discuss", "Thảo luận")}>
            {t(lang, "Thảo luận")}
          </button>
          <button className={`tab${tab === "expand" ? " active" : ""}`} onClick={() => pick("expand", "Mở rộng")}>
            {t(lang, "Mở rộng")}
          </button>
          <button className={`tab${tab === "check" ? " active" : ""}`} onClick={() => pick("check", "Kiểm tra")}>
            {t(lang, "Kiểm tra")}
          </button>
        </div>
      </div>
      <div className="ai-body">
        <div className="notice">
          <b>{t(lang, "Writer mode")}</b> · {t(lang, "AI tạo bản nháp để bạn xem. Không nội dung nào tự trở thành Canon.")}
        </div>

        {tab === "discuss" && (
          <QuickChat projectId={projectId} context={context} sceneId={scene?.id} />
        )}

        {tab === "expand" && (
          <>
            {scene ? (
              <>
                <div className="context-chip">{t(lang, "Đang gắn:")} {context}</div>
                <AiPanel key={scene.id} projectId={projectId} sceneId={scene.id} />
              </>
            ) : (
              <>
                <p className="hint">
                  {section
                    ? t(lang, "Không có cảnh nào đang mở — AI có thể gợi ý cho mục bạn đang xem.")
                    : t(lang, "Chọn một cảnh trong cây bản thảo để mở rộng văn.")}
                </p>
                <button className="btn primary wide" onClick={suggestSection} disabled={suggestBusy}>
                  {suggestBusy ? t(lang, "Đang suy nghĩ…") : `✦ ${t(lang, section ? "AI gợi ý cho mục này" : "AI gợi ý cho truyện")}`}
                </button>
                {suggest && (
                  <div className="ai-output open">
                    <div className="draft-card">
                      <h3>{t(lang, "Gợi ý AI · chưa áp dụng")}</h3>
                      <p>{suggest}</p>
                      <div className="draft-actions">
                        <button className="btn" onClick={() => setSuggest("")}>{t(lang, "Bỏ")}</button>
                        <button className="btn gold" onClick={sendSuggestionToReview}>{t(lang, "Gửi vào Review")}</button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <button className="context-btn" onClick={toggleCtx}>
              {ctxOpen ? t(lang, "⌃ Ẩn ngữ cảnh được sử dụng") : t(lang, "⌄ Ngữ cảnh được sử dụng")}
            </button>
            <div className={`context${ctxOpen ? " open" : ""}`}>
              <dl>
                <dt>{t(lang, "Vị trí hiện tại")}</dt>
                <dd>{scene ? `${scene.chapter.title} · ${scene.title ?? t(lang, "Cảnh")}` : section?.[1] ? t(lang, section[1]) : "—"}</dd>
                <dt>{t(lang, "Thực thể")}</dt>
                <dd>{characters.map((c) => c.name).join(", ") || t(lang, "chưa có")}</dd>
                <dt>{t(lang, "Nguồn ngữ cảnh")}</dt>
                <dd>
                  Canon {counts.canon} · {t(lang, "Quyết định")} {counts.decisions} · {t(lang, "Hố")} {counts.threads} · {t(lang, "Phong cách")}{" "}
                  {counts.styles}
                </dd>
                <dt>{t(lang, "Đã lược bỏ")}</dt>
                <dd>{t(lang, "Kiến thức ngoài POV {pov} không đưa vào ngữ cảnh.", { pov: povName ?? t(lang, "người kể") })}</dd>
              </dl>
              {ctxManifest && (
                <div className="manifest">
                  {ctxManifest.length === 0 && <div className="ctx-omit">{t(lang, "Không lấy được manifest")}</div>}
                  {ctxManifest.map((l, i) => (
                    <div key={i} className={l.startsWith("omitted") ? "ctx-omit" : "ctx-in"}>{l}</div>
                  ))}
                </div>
              )}
            </div>
            <p className="hint" style={{ marginTop: 14 }}>
              {t(lang, "Kết nối provider trong")}{" "}
              <Link href="/settings" style={{ color: "var(--teal)" }}>
                Settings
              </Link>{" "}
              {t(lang, "để dùng AI thảo luận và mở rộng bản thảo.")}
            </p>
          </>
        )}

        {tab === "check" && (
          <>
            <p className="hint">
              {counts.continuity > 0
                ? `${counts.continuity} ${t(lang, "điểm continuity cần xem — báo cáo chỉ nêu bằng chứng, bạn quyết định.")}`
                : t(lang, "Chưa phát hiện vấn đề continuity.")}
            </p>
            <Link
              href={`/projects/${projectId}/review`}
              className="btn gold wide"
              style={{ display: "block", textAlign: "center", textDecoration: "none" }}
            >
              {lang === "en" ? "Open Continuity & Review" : "Mở Continuity & Review"}
            </Link>
          </>
        )}
      </div>
    </aside>
  );
}
