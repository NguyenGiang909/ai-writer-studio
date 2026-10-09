"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getJSON, patchJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

type Cast = { characters: string[]; threads: string[]; abilities: string[] };
const EMPTY: Cast = { characters: [], threads: [], abilities: [] };
type Turn = { id: string; task: string; scope_id: string; provider?: string; created_at: string };

const TASK_META: Record<string, [string, string]> = {
  writing: ["✎", "Viết cảnh"], expand: ["✎", "Mở rộng"], scene_expand: ["✎", "Mở rộng cảnh"],
  chapter_write: ["✎", "Viết chương"], revision: ["✎", "Sửa đoạn"], ai_fix: ["✎", "AI sửa cảnh"],
  extraction: ["✓", "Trích dữ kiện"], chapter_facts: ["✓", "Trích chương"],
  summarization: ["≡", "Tóm tắt"], skeleton: ["✧", "Dàn cảnh"], chapter_outline: ["✧", "Dàn ý chương"],
  deep_check: ["⌕", "Soi chương"], deep_check_range: ["⌕", "Soi khoảng"],
  discussion: ["✦", "Thảo luận"], character_profile: ["♙", "Hồ sơ nhân vật"],
};

function hhmm(iso?: string) {
  if (!iso) return "";
  const d = new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + "Z");
  return isNaN(+d) ? "" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

export default function ChapterCastPanel({
  projectId, chapter, characters, threads, abilities, variant = "rail",
}: {
  projectId: string;
  chapter: { id: string; order_index: number; cast_json?: string | null;
             scenes?: { id: string; title?: string | null }[] } | null;
  characters: { id: string; name: string; role?: string | null }[];
  threads: { id: string; title: string; status?: string }[];
  abilities: { id: string; name: string; ability_type?: string | null }[];
  variant?: "rail" | "inline";
}) {
  const lang = useLang();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  const cast: Cast = useMemo(() => {
    try {
      const c = JSON.parse(chapter?.cast_json ?? "{}");
      return { ...EMPTY, ...(typeof c === "object" && c ? c : {}) };
    } catch { return EMPTY; }
  }, [chapter?.cast_json]);

  // nhật ký hoạt động của chương — scope_id ∈ scene ids của chương ∪ chính chapter
  useEffect(() => {
    if (!chapter) return;
    const scopeIds = new Set([chapter.id, ...(chapter.scenes ?? []).map((s) => s.id)]);
    let dead = false;
    const pull = () =>
      getJSON(`/api/v1/projects/${projectId}/ai/turns?limit=60`)
        .then((d) => { if (!dead) setTurns((d.turns ?? []).filter((x: Turn) => scopeIds.has(x.scope_id)).slice(0, 16)); })
        .catch(() => {});
    pull();
    const iv = setInterval(pull, 20000);
    return () => { dead = true; clearInterval(iv); };
  }, [chapter?.id, projectId]);

  const needle = q.trim().toLowerCase();
  const show = (name?: string | null) => !needle || (name ?? "").toLowerCase().includes(needle);
  const openThreads = threads.filter((th) => th.status === "OPEN" || cast.threads.includes(th.id));
  const nameOf = useMemo(() => {
    const m = new Map<string, string>();
    for (const c of characters) m.set(`c:${c.id}`, `♙ ${c.name}`);
    for (const th of threads) m.set(`t:${th.id}`, `≋ ${th.title}`);
    for (const a of abilities) m.set(`a:${a.id}`, `✦ ${a.name}`);
    return m;
  }, [characters, threads, abilities]);

  async function toggle(kind: keyof Cast, id: string) {
    if (busy || !chapter) return;
    const next: Cast = {
      ...cast,
      [kind]: cast[kind].includes(id)
        ? cast[kind].filter((x) => x !== id)
        : [...cast[kind], id],
    };
    setBusy(true);
    try {
      await patchJSON(`/api/v1/projects/${projectId}/chapters/${chapter.id}`,
        { cast_json: JSON.stringify(next) });
      router.refresh();
    } finally { setBusy(false); }
  }

  function row(kind: keyof Cast, id: string, label: string, extra?: string) {
    const on = cast[kind].includes(id);
    return (
      <label key={id} className={"cast-row" + (on ? " on" : "")}>
        <input type="checkbox" checked={on} disabled={busy}
               onChange={() => toggle(kind, id)} />
        <span className="cast-name">{label}</span>
        {extra && <small>{extra}</small>}
      </label>
    );
  }

  if (!chapter) return null;

  const picked: [keyof Cast, string][] = [
    ...cast.characters.map((i) => ["characters", i] as [keyof Cast, string]),
    ...cast.threads.map((i) => ["threads", i] as [keyof Cast, string]),
    ...cast.abilities.map((i) => ["abilities", i] as [keyof Cast, string]),
  ];

  const body = (
    <>
      <section className="console-sec">
        <div className="console-label">{t(lang, "Dàn vai")}</div>
        {picked.length > 0 && (
          <div className="cast-chips">
            {picked.map(([kind, id]) => (
              <span key={`${kind}:${id}`} className="cast-chip">
                {nameOf.get(`${kind === "characters" ? "c" : kind === "threads" ? "t" : "a"}:${id}`) ?? "—"}
                <button type="button" aria-label={t(lang, "Bỏ chọn")}
                        disabled={busy} onClick={() => toggle(kind, id)}>×</button>
              </span>
            ))}
          </div>
        )}
        <details className="cast-group">
          <summary><span>♙ {t(lang, "Nhân vật")}</span><b className="badge-sm">{cast.characters.length || ""}</b></summary>
          {characters.filter((c) => show(c.name) || cast.characters.includes(c.id))
            .map((c) => row("characters", c.id, c.name, c.role ?? undefined))}
          {!characters.length && <p className="subtle">{t(lang, "Chưa có nhân vật — tạo ở mục Nhân vật")}</p>}
        </details>
        <details className="cast-group">
          <summary><span>≋ {t(lang, "Hố & năng lực")}</span><b className="badge-sm">{(cast.threads.length + cast.abilities.length) || ""}</b></summary>
          <div className="cast-sub">{t(lang, "Hố đang mở")}</div>
          {openThreads.filter((th) => show(th.title) || cast.threads.includes(th.id))
            .map((th) => row("threads", th.id, th.title))}
          {!openThreads.length && <p className="subtle">{t(lang, "Không có hố đang mở")}</p>}
          <div className="cast-sub">{t(lang, "Năng lực")}</div>
          {abilities.filter((a) => show(a.name) || cast.abilities.includes(a.id))
            .map((a) => row("abilities", a.id, a.name, a.ability_type ?? undefined))}
          {!abilities.length && <p className="subtle">{t(lang, "Chưa có năng lực — tạo ở mục Năng lực")}</p>}
        </details>
      </section>
      <section className="console-sec log">
        <div className="console-label">{t(lang, "Nhật ký")}</div>
        <div className="log-list">
          {turns.length === 0 && <p className="subtle" style={{ padding: "0 4px" }}>{t(lang, "Chưa có hoạt động AI trong chương")}</p>}
          {turns.map((x) => {
            const [ic, lb] = TASK_META[x.task] ?? ["·", x.task];
            return (
              <div key={x.id} className="log-row" title={x.provider}>
                <time>{hhmm(x.created_at)}</time>
                <span className="log-task">{ic} {t(lang, lb)}</span>
              </div>
            );
          })}
        </div>
      </section>
    </>
  );

  const filter = (characters.length > 12 || openThreads.length + abilities.length > 12) && (
    <input className="cast-filter" placeholder={t(lang, "Lọc tên…")}
           value={q} onChange={(e) => setQ(e.target.value)} />
  );

  if (variant === "inline") {
    return (
      <details className="skeleton cast-inline">
        <summary>
          <span className="skel-title">{t(lang, "Bảng chương")} · CH.{chapter.order_index}</span>
          {picked.length > 0 && <span className="cast-counts">{picked.length} {t(lang, "đã chọn")}</span>}
        </summary>
        <div className="cast-inline-body">{filter}{body}</div>
      </details>
    );
  }
  return (
    <aside className="cast-rail" aria-label={t(lang, "Bảng chương")}>
      <div className="cast-head">{t(lang, "Bảng chương")} · CH.{chapter.order_index}</div>
      {filter}
      {body}
    </aside>
  );
}
