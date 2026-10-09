"use client";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { patchJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

type Cast = { characters: string[]; threads: string[]; abilities: string[] };
const EMPTY: Cast = { characters: [], threads: [], abilities: [] };

export default function ChapterCastPanel({
  projectId, chapter, characters, threads, abilities,
}: {
  projectId: string;
  chapter: { id: string; order_index: number; cast_json?: string | null } | null;
  characters: { id: string; name: string; role?: string | null }[];
  threads: { id: string; title: string; status?: string }[];
  abilities: { id: string; name: string; ability_type?: string | null }[];
}) {
  const lang = useLang();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");

  const cast: Cast = useMemo(() => {
    try {
      const c = JSON.parse(chapter?.cast_json ?? "{}");
      return { ...EMPTY, ...(typeof c === "object" && c ? c : {}) };
    } catch { return EMPTY; }
  }, [chapter?.cast_json]);

  const needle = q.trim().toLowerCase();
  const show = (name?: string | null) => !needle || (name ?? "").toLowerCase().includes(needle);
  const openThreads = threads.filter((th) => th.status === "OPEN" || cast.threads.includes(th.id));

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

  const groups = (
    <>
      <details className="cast-group">
        <summary>
          <span>♙ {t(lang, "Nhân vật trong chương")}</span>
          <b className="badge-sm">{cast.characters.length || ""}</b>
        </summary>
        {characters.filter((c) => show(c.name) || cast.characters.includes(c.id))
          .map((c) => row("characters", c.id, c.name, c.role ?? undefined))}
        {!characters.length && <p className="subtle">{t(lang, "Chưa có nhân vật — tạo ở mục Nhân vật")}</p>}
      </details>
      <details className="cast-group">
        <summary>
          <span>≋ {t(lang, "Hố & năng lực")}</span>
          <b className="badge-sm">{(cast.threads.length + cast.abilities.length) || ""}</b>
        </summary>
        <div className="cast-sub">{t(lang, "Hố đang mở")}</div>
        {openThreads.filter((th) => show(th.title) || cast.threads.includes(th.id))
          .map((th) => row("threads", th.id, th.title))}
        {!openThreads.length && <p className="subtle">{t(lang, "Không có hố đang mở")}</p>}
        <div className="cast-sub">{t(lang, "Năng lực")}</div>
        {abilities.filter((a) => show(a.name) || cast.abilities.includes(a.id))
          .map((a) => row("abilities", a.id, a.name, a.ability_type ?? undefined))}
        {!abilities.length && <p className="subtle">{t(lang, "Chưa có năng lực — tạo ở mục Năng lực")}</p>}
      </details>
    </>
  );

  const counts = [
    cast.characters.length && `${cast.characters.length}♙`,
    cast.threads.length && `${cast.threads.length}≋`,
    cast.abilities.length && `${cast.abilities.length}✦`,
  ].filter(Boolean).join(" · ");

  if (!chapter) return null;
  return (
    <>
      <aside className="cast-rail" aria-label={t(lang, "Dàn vai")}>
        <div className="cast-head">{t(lang, "Dàn vai")} · CH.{chapter.order_index}</div>
        {(characters.length > 12 || openThreads.length + abilities.length > 12) && (
          <input className="cast-filter" placeholder={t(lang, "Lọc tên…")}
                 value={q} onChange={(e) => setQ(e.target.value)} />
        )}
        {groups}
      </aside>
      <details className="skeleton cast-inline">
        <summary>
          <span className="skel-title">{t(lang, "Dàn vai")}</span>
          {counts && <span className="cast-counts">{counts}</span>}
        </summary>
        <div className="cast-inline-body">{groups}</div>
      </details>
    </>
  );
}
