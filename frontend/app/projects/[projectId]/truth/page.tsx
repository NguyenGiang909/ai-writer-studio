import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import { truthStatusLabel, knowledgeStateLabel, statusLabel, kindLabel } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string, fallback: any = []) { try { return await getJSON(path); } catch { return fallback; } }

const TRUTH_COLOR: Record<string, string> = { CANON: "var(--teal)", INFERRED: "var(--gold)", PLANNED: "#6a7fbf", RUMOR: "#8d9095", REJECTED: "var(--red)" };

const TRUTH_OPTS_VI = [
  ["CANON", "Canon"], ["INFERRED", "Suy ra"], ["PLANNED", "Dự kiến"], ["RUMOR", "Tin đồn"],
];

const KNOW_OPTS_VI = [
  ["KNOWS", "Biết"], ["BELIEVES", "Tin rằng"], ["SUSPECTS", "Nghi ngờ"],
  ["DOES_NOT_KNOW", "Chưa biết"], ["FALSE_BELIEF", "Hiểu sai"],
];

export default async function TruthPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const TRUTH_OPTS = TRUTH_OPTS_VI.map(([value, label]) => ({ value, label: t(lang, label) }));
  const KNOW_OPTS = KNOW_OPTS_VI.map(([value, label]) => ({ value, label: t(lang, label) }));
  const base = `/api/v1/projects/${projectId}`;
  const [facts, decisions, events, knowledge, secrets, states, tree, characters, items, locations, abilities, relationships] = await Promise.all([
    safe(`${base}/canon-facts`), safe(`${base}/author-decisions`), safe(`${base}/story-events`),
    safe(`${base}/knowledge-states`), safe(`${base}/secrets`), safe(`${base}/story-states`), safe(`${base}/manuscript`, { chapters: [] }),
    safe(`${base}/characters`), safe(`${base}/items`), safe(`${base}/locations`),
    safe(`${base}/abilities`), safe(`${base}/relationships`),
  ]);
  const entityName = (type: string, id: string) =>
    type === "character" ? characters.find((c: any) => c.id === id)?.name
    : type === "item" ? items.find((i: any) => i.id === id)?.name
    : type === "location" ? locations.find((l: any) => l.id === id)?.name
    : type === "ability" ? abilities.find((a: any) => a.id === id)?.name
    : id?.slice(0, 8);
  const sceneOpts = (tree.chapters ?? []).flatMap((c: any) =>
    (c.scenes ?? []).map((s: any) => ({ value: s.id, label: `${c.title} · ${s.title || t(lang, "Cảnh")}` })));
  const factLabel = (id: string) => { const f = facts.find((x: any) => x.id === id); return f ? `${f.predicate} = ${f.value_text}` : id.slice(0, 8); };
  const knowerName = (id: string) => characters.find((c: any) => c.id === id)?.name ?? (id === "reader" ? t(lang, "Độc giả") : id?.slice(0, 8));
  const entityOpts = [
    ...characters.map((c: any) => ({ value: `character:${c.id}`, label: `${t(lang, "Nhân vật")} · ${c.name}` })),
    ...items.map((i: any) => ({ value: `item:${i.id}`, label: `${t(lang, "Vật phẩm")} · ${i.name}` })),
    ...locations.map((l: any) => ({ value: `location:${l.id}`, label: `${t(lang, "Địa điểm")} · ${l.name}` })),
    ...abilities.map((a: any) => ({ value: `ability:${a.id}`, label: `${t(lang, "Năng lực")} · ${a.name}` })),
    ...relationships.map((r: any) => ({
      value: `relationship:${r.id}`,
      label: `${t(lang, "Quan hệ")} · ${knowerName(r.source_character_id)} ↔ ${knowerName(r.target_character_id)}`,
    })),
  ];

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head"><div><div className="eyebrow">{t(lang, "Sự thật theo thời điểm")}</div><h1>Canon &amp; Story Truth</h1></div></div>
      <div className="grid">

        <section className="card">
          <h3>{t(lang, "Sự thật Canon ({n})", { n: facts.length })}</h3>
          {facts.map((f: any) => (
            <div key={f.id} className="list-row">
              <span style={{ fontSize: 12, padding: "3px 9px", borderRadius: 99, background: (TRUTH_COLOR[f.truth_status] ?? "#8d9095") + "22", color: TRUTH_COLOR[f.truth_status] ?? "#8d9095", fontWeight: 700 }}>{truthStatusLabel(f.truth_status, lang)}</span>{" "}
              <b>{kindLabel(f.subject_type, lang)}</b> · {f.predicate} = {f.value_text} {f.locked && "🔒"}
              <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
                {f.truth_status !== "CANON" && <ActionButton endpoint={`${base}/canon-facts/${f.id}`} method="patch" body={{ truth_status: "CANON" }} label="→ Canon" />}
                {!f.locked && <ActionButton endpoint={`${base}/canon-facts/${f.id}`} method="patch" body={{ locked: true }} label={t(lang, "Khoá")} />}
                {f.truth_status !== "REJECTED" && <ActionButton endpoint={`${base}/canon-facts/${f.id}`} method="patch" body={{ truth_status: "REJECTED" }} label={t(lang, "Bác bỏ")} />}
                {!f.locked && <ActionButton endpoint={`${base}/canon-facts/${f.id}`} method="delete" label="✕" confirm={t(lang, "Xoá sự thật này? Kiến thức/bí mật gắn kèm cũng mất.")} />}
              </div>
            </div>
          ))}
          <PostForm endpoint={`${base}/canon-facts`} submitLabel={t(lang, "Sự thật canon")} fields={[
            { name: "subject_type", label: t(lang, "Đối tượng"), required: true, placeholder: t(lang, "nhân vật / thế giới / truyện…") },
            { name: "predicate", label: t(lang, "Thuộc tính"), required: true },
            { name: "value_text", label: t(lang, "Giá trị"), type: "textarea", required: true },
            { name: "truth_status", label: t(lang, "Trạng thái"), type: "select", options: TRUTH_OPTS },
          ]} />
          <h3 className="section-label">{t(lang, "Bí mật ({n})", { n: secrets.length })}</h3>
          {secrets.map((s: any) => (
            <div key={s.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <span><b>{s.title}</b> <small className="subtle">{statusLabel(s.status, lang)} → {factLabel(s.fact_id)}</small></span>
              <ActionButton endpoint={`${base}/secrets/${s.id}`} method="delete" label="✕" confirm={t(lang, "Xoá bí mật {name}?", { name: s.title })} />
            </div>
          ))}
          <PostForm endpoint={`${base}/secrets`} submitLabel={t(lang, "Bí mật")} fields={[
            { name: "fact_id", label: t(lang, "Sự thật canon"), type: "select", options: facts.map((f: any) => ({ value: f.id, label: `${f.predicate} = ${f.value_text}` })) },
            { name: "title", label: t(lang, "Tên bí mật"), required: true },
          ]} />
        </section>

        <section className="card">
          <h3>{t(lang, "Quyết định tác giả ({n})", { n: decisions.length })}</h3>
          {decisions.map((d: any) => (
            <div key={d.id} className="list-row"><b>{d.title}</b> <small className="subtle">{statusLabel(d.status, lang)}</small>
              <div className="subtle">{d.decision_text}</div>
              <div style={{ marginTop: 6, display: "flex", gap: 6 }}>
                {d.status === "active" && <ActionButton endpoint={`${base}/author-decisions/${d.id}`} method="patch" body={{ status: "revoked" }} label={t(lang, "Thu hồi")} />}
                <ActionButton endpoint={`${base}/author-decisions/${d.id}`} method="delete" label="✕" confirm={t(lang, "Xoá quyết định {name}?", { name: d.title })} />
              </div>
            </div>
          ))}
          <PostForm endpoint={`${base}/author-decisions`} submitLabel={t(lang, "Quyết định")} fields={[
            { name: "title", label: t(lang, "Tiêu đề"), required: true },
            { name: "decision_text", label: t(lang, "Quyết định"), type: "textarea", required: true },
          ]} />
          <h3 className="section-label">{t(lang, "Sự kiện truyện ({n})", { n: events.length })}</h3>
          {events.map((e: any) => (
            <div key={e.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
              <span><b>{e.event_type}</b> {e.summary} <small className="subtle">· {lang === "en" ? "order" : "thứ tự"} {e.narrative_order ?? "—"}</small></span>
              <ActionButton endpoint={`${base}/story-events/${e.id}`} method="delete" label="✕" confirm={t(lang, "Xoá sự kiện này?")} />
            </div>
          ))}
          <PostForm endpoint={`${base}/story-events`} submitLabel={t(lang, "Sự kiện")} fields={[
            { name: "event_type", label: t(lang, "Loại"), required: true },
            { name: "summary", label: t(lang, "Tóm tắt"), type: "textarea", required: true },
            { name: "scene_id", label: t(lang, "Cảnh"), type: "select", options: sceneOpts },
            { name: "narrative_order", label: t(lang, "Thứ tự kể"), type: "number" },
            { name: "story_time", label: t(lang, "Thời gian truyện"), type: "number" },
          ]} />
        </section>

        <section className="card">
          <h3>{t(lang, "Kiến thức ({n})", { n: knowledge.length })}</h3>
          {knowledge.map((k: any) => (
            <div key={k.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
              <span>
                <b>{knowerName(k.knower_id)}</b> <span className="badge-sm">{knowledgeStateLabel(k.state, lang)}</span> {factLabel(k.fact_id)}
                <small className="subtle"> · {t(lang, "biết từ thứ tự {n}", { n: k.acquired_narrative_order ?? "?" })} · {t(lang, "lộ {n}%", { n: k.disclosure_level })}</small>
              </span>
              <ActionButton endpoint={`${base}/knowledge-states/${k.id}`} method="delete" label="✕" confirm={t(lang, "Xoá kiến thức này?")} />
            </div>
          ))}
          <PostForm endpoint={`${base}/knowledge-states`} submitLabel={t(lang, "Kiến thức")} fields={[
            { name: "knower_id", label: t(lang, "Người biết"), type: "select", options: [{ value: "reader", label: t(lang, "Độc giả") }, ...characters.map((c: any) => ({ value: c.id, label: c.name }))] },
            { name: "fact_id", label: t(lang, "Sự thật canon"), type: "select", options: facts.map((f: any) => ({ value: f.id, label: `${f.predicate} = ${f.value_text}` })) },
            { name: "state", label: t(lang, "Trạng thái"), type: "select", options: KNOW_OPTS },
            { name: "disclosure_level", label: t(lang, "Mức lộ (%)"), type: "number" },
            { name: "acquired_narrative_order", label: t(lang, "Biết từ thứ tự kể"), type: "number" },
            { name: "acquired_story_time", label: t(lang, "Biết từ thời điểm truyện"), type: "number" },
          ]} />
          <h3 className="section-label">{t(lang, "Trạng thái truyện ({n})", { n: states.length })}</h3>
          {states.map((st: any) => (
            <div key={st.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
              <span>
                <b>{entityName(st.entity_type, st.entity_id) ?? st.entity_id?.slice(0, 8)}</b>{" "}
                <small className="subtle">{st.entity_type}</small> · {st.key} = <b>{st.value_text}</b>
                <small className="subtle"> · t={st.story_time ?? "—"}</small>
              </span>
              <ActionButton endpoint={`${base}/story-states/${st.id}`} method="delete" label="✕" confirm={t(lang, "Xoá trạng thái này?")} />
            </div>
          ))}
          <PostForm endpoint={`${base}/story-states`} submitLabel={t(lang, "Trạng thái")} fields={[
            { name: "entity", label: t(lang, "Thực thể"), type: "entity", options: entityOpts, required: true },
            { name: "key", label: t(lang, "Khóa trạng thái"), type: "select", required: true, options: [
              { value: "lifecycle", label: t(lang, "Vòng đời (ALIVE/DEAD/MISSING/…)") },
              { value: "location", label: t(lang, "Vị trí (tên địa điểm)") },
              { value: "ownership", label: t(lang, "Thuộc về (ID nhân vật)") },
              { value: "status", label: t(lang, "Trạng thái (UNLOCKED/ENDED/…)") },
            ]},
            { name: "value_text", label: t(lang, "Giá trị"), required: true, placeholder: t(lang, "DEAD · Hầm số 4 · <id nhân vật>…") },
            { name: "story_time", label: t(lang, "Tại thời điểm truyện"), type: "number" },
            { name: "narrative_order", label: t(lang, "Thứ tự kể"), type: "number" },
          ]} />
        </section>
      </div>
    </div></main>
  );
}
