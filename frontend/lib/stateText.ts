import type { Lang } from "./i18n";

/** Hiển thị story-state key=value theo ngôn ngữ UI.
 *  value_text là free-text của tác giả — dịch theo convention (enum UPPER,
 *  VERB_rest, A→B, UUID) rồi fallback giữ nguyên. */

const KEY_LABELS: Record<string, [string, string]> = {
  ownership: ["Sở hữu", "Ownership"],
  lifecycle: ["Sinh tử", "Lifecycle"],
  location: ["Vị trí", "Location"],
  allegiance: ["Phe", "Allegiance"],
  occupation: ["Nghề", "Occupation"],
  cultivation: ["Cảnh giới", "Cultivation"],
  injury: ["Vết thương", "Injury"],
  knowledge: ["Tri thức", "Knowledge"],
  relationship: ["Quan hệ", "Relationship"],
  status: ["Trạng thái", "Status"],
};

const TOKEN_LABELS: Record<string, [string, string]> = {
  ALIVE: ["Còn sống", "Alive"],
  DEAD: ["Đã chết", "Dead"],
  SEALED: ["Bị phong ấn", "Sealed"],
  MISSING: ["Mất tích", "Missing"],
  DESTROYED: ["Bị phá huỷ", "Destroyed"],
  UNKNOWN: ["Chưa rõ", "Unknown"],
};

const VERB_PATTERNS: Record<string, [string, string]> = {
  STOLEN_BY: ["Bị {x} đánh cắp", "Stolen by {x}"],
  RECOVERED_BY: ["{x} thu hồi", "Recovered by {x}"],
  SECRETLY_PROTECTS: ["Bí mật bảo vệ {x}", "Secretly protects {x}"],
  PROTECTS: ["Bảo vệ {x}", "Protects {x}"],
  SEALED: ["Bị phong ấn tại {x}", "Sealed at {x}"],
  AWAKE_IN: ["Thức tỉnh trong {x}", "Awake in {x}"],
  HELD_BY: ["{x} giữ", "Held by {x}"],
  OWNED_BY: ["{x} sở hữu", "Owned by {x}"],
  KILLED_BY: ["Bị {x} giết", "Killed by {x}"],
  BETRAYED_BY: ["Bị {x} phản", "Betrayed by {x}"],
  SERVES: ["Phục vụ {x}", "Serves {x}"],
  FLED_TO: ["Bỏ trốn tới {x}", "Fled to {x}"],
  MOVED_TO: ["Chuyển tới {x}", "Moved to {x}"],
};

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function stateKeyLabel(lang: Lang | undefined, key: string): string {
  const hit = KEY_LABELS[key];
  if (hit) return lang === "en" ? hit[1] : hit[0];
  return key.replaceAll("_", " ");
}

function piece(lang: Lang | undefined, raw: string, names?: Map<string, string>,
               asName = false): string {
  const v = raw.trim();
  if (!v) return v;
  if (UUID_RE.test(v)) return names?.get(v) ?? `${v.slice(0, 8)}…`;
  const token = TOKEN_LABELS[v];
  if (token && !asName) return lang === "en" ? token[1] : token[0];
  if (!asName) {
    // VERB_rest / VERB_BY_rest — verb là chuỗi UPPER dài nhất khớp map
    for (const verb of Object.keys(VERB_PATTERNS).sort((a, b) => b.length - a.length)) {
      if (v === verb) continue;
      if (v.startsWith(verb + "_")) {
        const rest = piece(lang, v.slice(verb.length + 1), names, true);
        const fmt = VERB_PATTERNS[verb];
        return (lang === "en" ? fmt[1] : fmt[0]).replace("{x}", rest);
      }
    }
  }
  return v.replaceAll("_", " ");
}

export function stateValueText(
  lang: Lang | undefined,
  value: string | null | undefined,
  names?: Map<string, string>,
): string {
  const v = (value ?? "").trim();
  if (!v) return "—";
  // chuyển tiếp A→B: dịch từng vế, giữ mũi tên
  if (v.includes("→"))
    return v.split("→").map((p) => piece(lang, p, names)).join(" → ");
  return piece(lang, v, names);
}
