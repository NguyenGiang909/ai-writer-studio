"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getJSON, putJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

type Cast = { characters: string[]; threads: string[]; abilities: string[] };
const EMPTY: Cast = { characters: [], threads: [], abilities: [] };
type Turn = { id: string; task: string; scope_id: string; provider?: string;
              created_at: string; latency_ms?: number | null };

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
  projectId, chapter, characters, threads, abilities, variant = "rail", sceneId,
}: {
  projectId: string;
  chapter: { id: string; order_index: number; cast_json?: string | null;
             scenes?: { id: string; title?: string | null; order_index?: number;
                        words?: number }[] } | null;
  characters: { id: string; name: string; role?: string | null }[];
  threads: { id: string; title: string; status?: string; must_resolve?: boolean; important?: boolean }[];
  abilities: { id: string; name: string; ability_type?: string | null }[];
  variant?: "rail" | "inline";
  sceneId?: string;
}) {
  const lang = useLang();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [castErr, setCastErr] = useState("");

  const parsed: Cast = useMemo(() => {
    try {
      const c = JSON.parse(chapter?.cast_json ?? "{}");
      return { ...EMPTY, ...(typeof c === "object" && c ? c : {}) };
    } catch { return EMPTY; }
  }, [chapter?.cast_json]);

  const [cast, setCast] = useState<Cast>(parsed);
  useEffect(() => setCast(parsed), [parsed]);

  // nhật ký: turn của chương trước, chương rỗng/ít thì lấp bằng hoạt động project
  useEffect(() => {
    if (!chapter) return;
    const scopeIds = new Set([chapter.id, ...(chapter.scenes ?? []).map((s) => s.id)]);
    let dead = false;
    const pull = () =>
      getJSON(`/api/v1/projects/${projectId}/ai/turns?limit=60`)
        .then((d) => {
          if (dead) return;
          const all: Turn[] = d.turns ?? [];
          const own = all.filter((x) => scopeIds.has(x.scope_id));
          const rest = all.filter((x) => !scopeIds.has(x.scope_id));
          setTurns([...own, ...rest].slice(0, 16));
        })
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
    const previous = cast;
    setCast(next);
    setBusy(true);
    setCastErr("");
    try {
      // endpoint riêng validate id + trả cast đã lưu (C15) — trước PATCH
      // cast_json trần, id rác lọt vào lặng lẽ không ai hay
      const res = await putJSON(
        `/api/v1/projects/${projectId}/chapters/${chapter.id}/cast`, { [kind]: next[kind] });
      const saved = res?.cast ?? next;
      // verify read-after-write: server trả gì phải khớp thứ mình gửi
      const ok = ([kind] as (keyof Cast)[])
        .every((k) => JSON.stringify([...saved[k]].sort())
          === JSON.stringify([...next[k]].sort()));
      if (!ok) setCastErr(t(lang, "Đã lưu nhưng dữ liệu đọc lại khác — tải lại trang"));
      router.refresh();
    } catch (e) {
      setCast(previous);
      setCastErr(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  }

  function row(kind: keyof Cast, id: string, label: string, extra?: string) {
    const on = cast[kind].includes(id);
    return (
      <label key={id} className={"cast-row" + (on ? " on" : "")}>
        <input type="checkbox" aria-label={label} checked={on} disabled={busy}
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
      <section className="console-sec priority-reminders">
        {(["must_resolve","important"] as const).map(key=>{
          const pending=threads.filter(th=>!["RESOLVED","ABANDONED"].includes(th.status||"")&&(key==="must_resolve"?th.must_resolve:th.important&&!th.must_resolve));
          if(!pending.length)return null;
          return <details className="cast-group" key={key} open><summary><span>{t(lang,key==="must_resolve"?"Hố bắt buộc lấp":"Hố quan trọng")}</span><b className="badge-sm">{pending.length}</b></summary>
            {pending.map(th=><div className="priority-reminder" key={th.id}>{row("threads",th.id,th.title)}</div>)}
          </details>;
        })}
        <Link href={`/projects/${projectId}/threads`} className="issue-link">{t(lang,"Quản lý hố ưu tiên")} →</Link>
      </section>
      <section className="console-sec">
        <div className="console-label">{t(lang, "Dàn vai")}</div>
        {castErr && <p className="err">{castErr}</p>}
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
      {(chapter.scenes?.length ?? 0) > 0 && (
        <section className="console-sec">
          <div className="console-label">{t(lang, "Cảnh")}</div>
          <div className="sc-list">
            {chapter.scenes!.map((s, i) => {
              const words = s.words ?? 0;
              return (
                <Link key={s.id} href={`/projects/${projectId}?scene=${s.id}`}
                      className={"sc-mini" + (s.id === sceneId ? " on" : "")}
                      title={s.title ?? ""}>
                  <b>{i + 1}</b>
                  <span className="sc-name">{s.title || t(lang, "Cảnh chưa đặt tên")}</span>
                  <small>{words ? `${words}từ` : "·"}</small>
                </Link>
              );
            })}
          </div>
        </section>
      )}
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
                {x.latency_ms != null && (
                  <small className="subtle">{(x.latency_ms / 1000).toFixed(0)}s</small>
                )}
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
