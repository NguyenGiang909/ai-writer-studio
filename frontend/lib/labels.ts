// Vietnamese-facing labels for raw backend enums/codes.
// Never render raw enum strings (pending, OPEN, continuity:pov_knowledge) to the UI.
// Pass lang="en" (server: await getLang(); client: useLang()) for English.

import { LANG_COOKIE, type Lang } from "./i18n";

export const cap = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const L = (lang?: Lang): Lang =>
  lang ?? (typeof document !== "undefined" && document.cookie.includes(`${LANG_COOKIE}=en`) ? "en" : "vi");

const WORDS: Record<string, string> = {
  continuity: "Liên tục",
  pov_knowledge: "mâu thuẫn kiến thức POV",
  travel_time: "khoảng cách di chuyển",
  item_detail: "chi tiết vật phẩm",
  canon_fact: "Sự thật canon",
  story_event: "Sự kiện",
  story_state: "Trạng thái truyện",
  knowledge: "Kiến thức",
  knowledge_change: "Thay đổi kiến thức",
  thread_beat: "Nhịp hố",
  thread_touch: "Chạm hố",
  KNOWLEDGE_LEAK: "Lộ kiến thức",
  KNOWLEDGE_LEAK_TIME: "Lộ kiến thức (thời gian)",
  RESTRICTED_APPEARANCE: "Nhân vật bị hạn chế xuất hiện",
  LOCATION_CONFLICT: "Mâu thuẫn vị trí",
  ABILITY_NOT_UNLOCKED: "Năng lực chưa mở",
  ITEM_OWNER_MISMATCH: "Vật phẩm sai chủ",
  RELATIONSHIP_CONFLICT: "Mâu thuẫn quan hệ",
  STALE_THREAD: "Hố nằm im lâu",
  THREAD_OVERDUE: "Hố quá hạn trả nợ",
  character: "Nhân vật",
  scene: "Cảnh",
  thread: "Hố",
  location: "Địa điểm",
  ability: "Năng lực",
  item: "Vật phẩm",
  relationship: "Quan hệ",
  summary: "Tóm tắt",
  retcon: "Retcon",
  ai_draft: "Bản nháp AI",
  entity: "Thực thể",
};

const WORDS_EN: Record<string, string> = {
  continuity: "Continuity",
  pov_knowledge: "POV knowledge conflict",
  travel_time: "travel distance",
  item_detail: "item detail",
  canon_fact: "Canon fact",
  story_event: "Story event",
  story_state: "Story state",
  knowledge: "Knowledge",
  knowledge_change: "Knowledge change",
  thread_beat: "Thread beat",
  thread_touch: "Thread touch",
  KNOWLEDGE_LEAK: "Knowledge leak",
  KNOWLEDGE_LEAK_TIME: "Knowledge leak (story time)",
  RESTRICTED_APPEARANCE: "Restricted character appearance",
  LOCATION_CONFLICT: "Location conflict",
  ABILITY_NOT_UNLOCKED: "Ability not unlocked",
  ITEM_OWNER_MISMATCH: "Item owner mismatch",
  RELATIONSHIP_CONFLICT: "Relationship conflict",
  STALE_THREAD: "Thread gone quiet",
  THREAD_OVERDUE: "Thread payoff overdue",
  character: "Character",
  scene: "Scene",
  thread: "Thread",
  location: "Location",
  ability: "Ability",
  item: "Item",
  relationship: "Relationship",
  summary: "Summary",
  retcon: "Retcon",
  ai_draft: "AI draft",
  entity: "Entity",
};

/** "continuity:foo_bar" → "Kiến thức POV"; "canon_fact" → "Sự thật canon" */
export function kindLabel(raw?: string | null, lang?: Lang): string {
  if (!raw) return L(lang) === "en" ? "Change" : "Thay đổi";
  const W = L(lang) === "en" ? WORDS_EN : WORDS;
  const str = String(raw);
  // "continuity:foo_bar" → chỉ lấy phần mô tả (đã nằm trong mục Liên tục)
  if (str.startsWith("continuity:")) {
    const seg = str.slice(11);
    return cap(W[seg] ?? seg.split("_").map((w) => W[w] ?? w).join(" "));
  }
  const pretty = str
    .split(":")
    .map((seg) => W[seg] ?? seg.split("_").map((w) => W[w] ?? w).join(" "))
    .join(" · ");
  return cap(pretty);
}

const STATUS_VI: Record<string, string> = {
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  rejected: "Đã từ chối",
  OPEN: "Đang mở",
  DORMANT: "Tạm ngưng",
  RESOLVED: "Đã xử lý",
  PLANNED: "Kế hoạch",
  ABANDONED: "Đã bỏ",
  draft: "Bản nháp",
  done: "Hoàn tất",
  writing: "Đang viết",
  plan: "Kế hoạch",
  active: "Đang dùng",
  inactive: "Ngưng",
  dead: "Đã chết",
  exited: "Đã rời",
  retired: "Về hưu",
  applied: "Đã áp dụng",
};
const STATUS_EN: Record<string, string> = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  OPEN: "Open",
  DORMANT: "Dormant",
  RESOLVED: "Resolved",
  PLANNED: "Planned",
  ABANDONED: "Abandoned",
  draft: "Draft",
  done: "Done",
  writing: "Writing",
  plan: "Planned",
  active: "Active",
  inactive: "Inactive",
  dead: "Dead",
  exited: "Exited",
  retired: "Retired",
  applied: "Applied",
};

export function statusLabel(raw?: string | null, lang?: Lang): string {
  const M = L(lang) === "en" ? STATUS_EN : STATUS_VI;
  return (
    M[String(raw ?? "")] ??
    cap(String(raw ?? "—").replace(/_/g, " ").toLowerCase())
  );
}

export const truthStatusLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ CANON: "Canon", INFERRED: "Inferred", PLANNED: "Planned", RUMOR: "Rumor", REJECTED: "Rejected" })[String(raw ?? "")] ?? cap(String(raw ?? ""))
    : ({ CANON: "Canon", INFERRED: "Suy ra", PLANNED: "Dự kiến", RUMOR: "Tin đồn", REJECTED: "Bác bỏ" })[String(raw ?? "")] ?? cap(String(raw ?? ""));

export const knowledgeStateLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ KNOWS: "Knows", BELIEVES: "Believes", SUSPECTS: "Suspects", DOES_NOT_KNOW: "Doesn't know", FALSE_BELIEF: "False belief" })[String(raw ?? "")] ?? cap(String(raw ?? ""))
    : ({ KNOWS: "Biết", BELIEVES: "Tin rằng", SUSPECTS: "Nghi ngờ", DOES_NOT_KNOW: "Chưa biết", FALSE_BELIEF: "Hiểu sai" })[String(raw ?? "")] ?? cap(String(raw ?? ""));

export const branchStatusLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ draft: "Draft", selected: "Selected", discarded: "Discarded", merged: "Merged" })[String(raw ?? "")] ?? cap(String(raw ?? ""))
    : ({ draft: "Bản nháp", selected: "Đã chọn", discarded: "Đã bỏ", merged: "Đã gộp" })[String(raw ?? "")] ?? cap(String(raw ?? ""));

export const branchChangeLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ canon_override: "Canon override", thread_plan: "Thread plan", scene_plan: "Scene plan", chapter_plan: "Chapter plan", plan_note: "Note", ai_draft: "AI draft" })[String(raw ?? "")] ?? kindLabel(raw, lang)
    : ({ canon_override: "Ghi đè canon", thread_plan: "Kế hoạch hố", scene_plan: "Kế hoạch cảnh", chapter_plan: "Kế hoạch chương", plan_note: "Ghi chú", ai_draft: "Bản nháp AI" })[String(raw ?? "")] ?? kindLabel(raw, lang);

/** Strip accents + lowercase for keyword matching on free-text roles. */
const unacc = (s: string) =>
  s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[đĐ]/g, "d").toLowerCase();

/** Group characters into display tiers. Handles both enum roles and free-text Vietnamese roles. */
export function roleTier(raw?: string | null): number {
  const s = unacc(String(raw ?? ""));
  if (!s) return 4;
  // cameo / one-off first — "Đối đầu nhỏ", "thoáng qua", "xuất hiện 1 lần"
  if (/(thoang qua|minor|nho\b|mot lan|1 lan|xuat hien)/.test(s)) return 3;
  // lead
  if (/(protagonist|nhan vat chinh|\bpov\b|trung tam)/.test(s)) return 0;
  // deuteragonist / antagonist / secondary leads
  if (/(deuteragonist|phu chinh|antagonist|phan dien|doi dau|doi thu|chinh dien|thu linh|chu su)/.test(s)) return 1;
  // everything else recognisably supporting
  if (/(supporting|phu\b|dong hanh|an si|than linh|chinh tri|quan su|co van|hai\b|dao mon|mo ho|than thich|gia dinh|qua khu|su phu|su do|de tu)/.test(s)) return 2;
  return 4;
}

export const TIER_LABELS_VI = ["Nhân vật chính", "Phụ chính & phản diện", "Nhân vật phụ", "Thoáng qua", "Chưa phân loại"];
export const TIER_LABELS_EN = ["Leads", "Deuteragonists & antagonists", "Supporting", "Cameo", "Unclassified"];

export const tierLabel = (tier: number, lang?: Lang): string =>
  (L(lang) === "en" ? TIER_LABELS_EN : TIER_LABELS_VI)[tier] ?? "";

/** Importance buckets: 0 Quan trọng · 1 Khá quan trọng · 2 Trung bình · 3 Thùng rác */
export const IMPORTANCE_LABELS_VI = ["Quan trọng", "Khá quan trọng", "Trung bình", "Thùng rác"];
export const IMPORTANCE_LABELS_EN = ["Important", "Fairly important", "Average", "Junk bin"];

export const importanceLabel = (i: number, lang?: Lang): string =>
  (L(lang) === "en" ? IMPORTANCE_LABELS_EN : IMPORTANCE_LABELS_VI)[i] ?? "";

/** Effective bucket: stored importance wins; fall back to role-derived tier (unclassified → 2). */
export function charImportance(c: { importance?: number | null; role?: string | null }): number {
  if (c.importance != null) return c.importance;
  const t = roleTier(c.role);
  return t === 4 ? 2 : t;
}

export const relImportance = (r: { importance?: number | null }): number =>
  r.importance ?? 2;

export const roleLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ assistant: "Assistant", brainstorm: "Brainstorm", plot_doctor: "Plot doctor", character_analyst: "Character analyst", continuity_analyst: "Continuity analyst", devils_advocate: "Devil's advocate", reader_simulation: "Reader simulation", style: "Style", protagonist: "Protagonist", deuteragonist: "Deuteragonist", antagonist: "Antagonist", supporting: "Supporting", minor: "Minor" })[String(raw ?? "")] ?? cap(String(raw ?? ""))
    : ({ assistant: "Trợ lý", brainstorm: "Động não", plot_doctor: "Bác sĩ cốt truyện", character_analyst: "Phân tích nhân vật", continuity_analyst: "Phân tích liên tục", devils_advocate: "Phản biện", reader_simulation: "Giả lập độc giả", style: "Phong cách", protagonist: "Nhân vật chính", deuteragonist: "Nhân vật phụ chính", antagonist: "Phản diện", supporting: "Vai phụ", minor: "Thoáng qua" })[String(raw ?? "")] ?? cap(String(raw ?? ""));

export const scopeLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ global: "Whole story", arc: "Arc", character: "Character", scene_type: "Scene type", chapter: "Chapter", scene: "Scene", story: "Whole story", volume: "Volume", thread: "Thread", canon_fact: "Canon fact", discussion: "Discussion" })[String(raw ?? "")] ?? cap(String(raw ?? ""))
    : ({ global: "Toàn truyện", arc: "Hồi", character: "Nhân vật", scene_type: "Loại cảnh", chapter: "Chương", scene: "Cảnh", story: "Toàn truyện", volume: "Quyển", thread: "Hố", canon_fact: "Sự thật canon", discussion: "Thảo luận" })[String(raw ?? "")] ?? cap(String(raw ?? ""));

export function severityLabel(raw?: string | null, lang?: Lang): { label: string; warn: boolean } {
  const s = String(raw ?? "").toLowerCase();
  const en = L(lang) === "en";
  if (["error", "high", "danger", "critical"].includes(s)) return { label: en ? "High" : "Cao", warn: true };
  if (["warning", "warn", "medium"].includes(s)) return { label: en ? "Medium" : "Vừa", warn: false };
  return { label: en ? "Low" : "Thấp", warn: false };
}

export const beatTypeLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ setup: "Setup", reinforcement: "Reinforce", escalation: "Escalate", misdirection: "Misdirect", payoff: "Payoff", considered: "Considered" })[String(raw ?? "")] ?? cap(String(raw ?? "—"))
    : ({ setup: "Gieo mầm", reinforcement: "Nhắc lại", escalation: "Đẩy cao", misdirection: "Đánh lạc hướng", payoff: "Trả nợ", considered: "Đã xem xét" })[String(raw ?? "")] ?? cap(String(raw ?? "—"));

export const threadTypeLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ mystery: "Mystery", foreshadow: "Foreshadow", promise: "Promise", conflict: "Conflict", secret: "Secret", question: "Question", quest: "Quest", future_payoff: "Future payoff", philosophical: "Philosophical", custom: "Custom" })[String(raw ?? "")] ?? cap(String(raw ?? ""))
    : ({ mystery: "Bí ẩn", foreshadow: "Gợi mở", promise: "Lời hứa", conflict: "Xung đột", secret: "Bí mật", question: "Câu hỏi", quest: "Hành trình", future_payoff: "Trả nợ sau", philosophical: "Câu hỏi triết học", custom: "Tùy ý" })[String(raw ?? "")] ?? cap(String(raw ?? ""));

export const sceneTypeLabel = (raw?: string | null, lang?: Lang): string =>
  L(lang) === "en"
    ? ({ action: "Action", dialogue: "Dialogue", exposition: "Exposition", transition: "Transition", reveal: "Reveal", conflict: "Conflict", flashback: "Flashback", montage: "Montage", mystery: "Mystery", discovery: "Discovery", relationship: "Relationship", intimacy: "Intimacy", daily_life: "Slice of life", reflection: "Reflection" })[String(raw ?? "")] ?? cap(String(raw ?? ""))
    : ({ action: "Hành động", dialogue: "Hội thoại", exposition: "Dẫn truyện", transition: "Chuyển tiếp", reveal: "Lật mở", conflict: "Xung đột", flashback: "Hồi ức", montage: "Dàn cảnh", mystery: "Bí ẩn", discovery: "Khám phá", relationship: "Quan hệ", intimacy: "Thân mật", daily_life: "Đời sống", reflection: "Chiêm nghiệm" })[String(raw ?? "")] ?? cap(String(raw ?? ""));

/** Pull human-readable text out of a suggestion/issue payload instead of dumping JSON. */
export function payloadText(payload: any, _lang?: Lang): string {
  if (!payload) return "";
  if (typeof payload === "string") return payload;
  const KEYS = ["text", "rationale", "body", "description", "message", "note", "notes", "title", "proposal"];
  const parts = KEYS.map((k) => payload[k]).filter((v) => typeof v === "string" && v.trim());
  if (parts.length) return parts.join(" — ");
  const rest = Object.entries(payload)
    .filter(([k, v]) => typeof v === "string" && v.trim() && k !== "needs_author_review"
      && !/_id$/.test(k)
      && !/^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(v))
    .map(([k, v]) => `${k}: ${v}`);
  return rest.join("\n");
}
