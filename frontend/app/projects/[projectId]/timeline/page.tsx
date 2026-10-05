import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import ListFilter from "../../../../components/ListFilter";
import TimelineView from "../../../../components/TimelineView";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";
import { stateKeyLabel, stateValueText } from "../../../../lib/stateText";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

const ENTITY_HREF: Record<string, string> = {
  character: "/characters", location: "/world", item: "/world", faction: "/world",
  ability: "/abilities", thread: "/threads",
};
const ENTITY_LABEL: Record<string, string> = {
  character: "→ Nhân vật", location: "→ Thế giới", item: "→ Thế giới", faction: "→ Thế giới",
  ability: "→ Năng lực", thread: "→ Hố",
};
const TYPE_LABEL: Record<string, string> = {
  character: "Nhân vật", item: "Vật", location: "Địa điểm", faction: "Phe",
  ability: "Năng lực", thread: "Hố", lore: "Tri thức",
};

export default async function TimelinePage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [events, states, tree, chars, items, locs, factions, abils, threads] = await Promise.all([
    safe(`${base}/story-events`), safe(`${base}/story-states`), safe(`${base}/manuscript`),
    safe(`${base}/characters`), safe(`${base}/items`), safe(`${base}/locations`),
    safe(`${base}/factions`), safe(`${base}/abilities`), safe(`${base}/threads`),
  ]);
  const names = new Map<string, string>();
  for (const e of [...chars, ...items, ...locs, ...factions, ...abils])
    if (e?.id && e?.name) names.set(e.id, e.name);
  for (const th of threads) if (th?.id && th?.title) names.set(th.id, th.title);
  const entityName = (s: any) => names.get(s.entity_id) ?? s.entity_id.slice(0, 8);
  const groups = new Map<string, any[]>();
  for (const s of states) {
    const g = `${s.entity_type}:${s.entity_id}`;
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(s);
  }
  const sortedGroups = [...groups.values()]
    .map((list) => ({
      list: list.sort((a: any, b: any) => (a.story_time ?? 1e9) - (b.story_time ?? 1e9)),
      latest: Math.max(...list.map((s: any) => s.story_time ?? -1e9)),
    }))
    .sort((a, b) => b.latest - a.latest);
  const sceneOpts = tree.chapters.flatMap((c: any) =>
    c.scenes.map((s: any) => ({ value: s.id, label: `${c.title} · ${s.title || t(lang, "Cảnh")}` })));
  const byStoryTime = [...events].sort((a: any, b: any) => (a.story_time ?? 1e9) - (b.story_time ?? 1e9));
  const byNarrative = [...events].sort((a: any, b: any) => (a.narrative_order ?? 1e9) - (b.narrative_order ?? 1e9));

  const eventFields = (e: any) => [
    { name: "event_type", label: t(lang, "Loại"), required: true, defaultValue: e.event_type ?? "", placeholder: "arrival/reveal/move/…" },
    { name: "summary", label: t(lang, "Tóm tắt"), type: "textarea" as const, required: true, defaultValue: e.summary ?? "" },
    { name: "scene_id", label: t(lang, "Cảnh"), type: "select" as const, options: sceneOpts, defaultValue: e.scene_id ?? "" },
    { name: "story_time", label: t(lang, "Thời gian truyện"), type: "number" as const, defaultValue: e.story_time ?? "" },
    { name: "narrative_order", label: t(lang, "Thứ tự kể"), type: "number" as const, defaultValue: e.narrative_order ?? "" },
  ];

  const eventRow = (e: any, marker: React.ReactNode) => (
    <div key={e.id} className="thread" data-q={`${e.event_type} ${e.summary}`}>
      <div style={{ flex: 1, minWidth: 0 }}>
        {marker} · <span className="pill">{e.event_type}</span>
        <small>{e.summary}</small>
      </div>
      <div className="row-actions">
        {e.scene_id && (
          <Link href={`/projects/${projectId}?scene=${e.scene_id}`} className="issue-link">→ {t(lang, "Mở cảnh")}</Link>
        )}
        <PostForm endpoint={`${base}/story-events/${e.id}`} method="patch" submitLabel={t(lang, "Lưu")}
          triggerLabel={t(lang, "Sửa")} fields={eventFields(e)} />
        <ActionButton endpoint={`${base}/story-events/${e.id}`} method="delete" label={t(lang, "Xoá")}
          confirm={t(lang, "Xoá sự kiện này?")} />
      </div>
    </div>
  );

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Hai lớp thời gian")}</div>
          <h1>Timeline</h1>
        </div>
        <ListFilter for="tl-events" placeholder={t(lang, "Lọc sự kiện…")} />
      </div>
      <p className="subtle">
        {t(lang, "Thời gian trong truyện và thứ tự độc giả đọc là hai trục độc lập — flashback không được lộ kiến thức tương lai.")}
      </p>
      {events.length ? (
        <TimelineView
          dual={
            <div className="grid">
              <div className="card">
                <h3>{t(lang, "Thời gian trong truyện")}</h3>
                {byStoryTime.map((e: any) => eventRow(e, <b>t={e.story_time ?? "?"}</b>))}
              </div>
              <div className="card">
                <h3>{t(lang, "Thứ tự kể")}</h3>
                {byNarrative.map((e: any) => eventRow(e, <b>#{e.narrative_order ?? "?"}</b>))}
              </div>
            </div>
          }
          chrono={
            <div className="card">
              {byStoryTime.map((e: any) => eventRow(e, <b>t={e.story_time ?? "?"}</b>))}
            </div>
          }
          narrative={
            <div className="card">
              {byNarrative.map((e: any) => eventRow(e, <b>#{e.narrative_order ?? "?"}</b>))}
            </div>
          }
        />
      ) : (
        <div className="card" id="tl-events">
          <p className="subtle">{t(lang, "Chưa có sự kiện nào — thêm ở bên dưới hoặc trong Canon & Truth.")}</p>
        </div>
      )}

      <div className="dash-head" style={{ marginTop: 26 }}>
        <div>
          <div className="eyebrow">{t(lang, "Story state theo thời điểm")}</div>
          <h1>{t(lang, "Trạng thái thực thể ({n})", { n: states.length })}</h1>
        </div>
        <ListFilter for="tl-states" placeholder={t(lang, "Lọc trạng thái…")} />
      </div>
      <div className="card" id="tl-states">
        {sortedGroups.map(({ list }) => {
          const head = list[0];
          const last = list[list.length - 1];
          return (
            <details key={`${head.entity_type}:${head.entity_id}`} data-group className="state-group">
              <summary>
                <b>{t(lang, TYPE_LABEL[head.entity_type] ?? head.entity_type)} · {entityName(head)}</b>
                <span className="state-count">{list.length}</span>
                <span className="state-preview">
                  {stateKeyLabel(lang, last.key)} = {stateValueText(lang, last.value_text, names)}
                  {" · "}t={last.story_time ?? "?"}
                </span>
              </summary>
              {list.map((s: any) => (
          <div key={s.id} className="list-row" data-q={`${s.entity_type} ${entityName(s)} ${s.key} ${s.value_text}`}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <b>{t(lang, TYPE_LABEL[s.entity_type] ?? s.entity_type)} · {entityName(s)}</b> · {stateKeyLabel(lang, s.key)} = {stateValueText(lang, s.value_text, names)}{" "}
              <small className="subtle">t={s.story_time ?? "?"} · {lang === "en" ? "order" : "thứ tự"} {s.narrative_order ?? "?"}</small>
            </div>
            <div className="row-actions">
              {ENTITY_HREF[s.entity_type] && (
                <Link href={`/projects/${projectId}${ENTITY_HREF[s.entity_type]}`} className="issue-link">{t(lang, ENTITY_LABEL[s.entity_type] ?? `→ ${s.entity_type}`)}</Link>
              )}
              <PostForm endpoint={`${base}/story-states/${s.id}`} method="patch" submitLabel={t(lang, "Lưu")}
                triggerLabel={t(lang, "Sửa")} fields={[
                  { name: "key", label: t(lang, "Khoá"), required: true, defaultValue: s.key ?? "" },
                  { name: "value_text", label: t(lang, "Giá trị"), required: true, defaultValue: s.value_text ?? "" },
                  { name: "story_time", label: t(lang, "Thời gian truyện"), type: "number", defaultValue: s.story_time ?? "" },
                  { name: "narrative_order", label: t(lang, "Thứ tự kể"), type: "number", defaultValue: s.narrative_order ?? "" },
                ]} />
              <ActionButton endpoint={`${base}/story-states/${s.id}`} method="delete" label={t(lang, "Xoá")}
                confirm={t(lang, "Xoá story state này?")} />
            </div>
          </div>
              ))}
            </details>
          );
        })}
        {!states.length && <p className="subtle">{t(lang, "Chưa có story state — ghi ở Canon & Truth.")}</p>}
      </div>

      <details className="card add-event" style={{ marginTop: 18 }}>
        <summary><h3 style={{ display: "inline" }}>{t(lang, "Thêm sự kiện")}</h3></summary>
        <PostForm endpoint={`${base}/story-events`} submitLabel={t(lang, "Sự kiện")} fields={[
          { name: "event_type", label: t(lang, "Loại"), required: true, placeholder: "arrival/reveal/move/…" },
          { name: "summary", label: t(lang, "Tóm tắt"), type: "textarea", required: true },
          { name: "scene_id", label: t(lang, "Cảnh"), type: "select", options: sceneOpts },
          { name: "story_time", label: t(lang, "Thời gian truyện"), type: "number" },
          { name: "narrative_order", label: t(lang, "Thứ tự kể"), type: "number" },
        ]} />
      </details>
    </div></main>
  );
}
