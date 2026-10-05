import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import ListFilter from "../../../../components/ListFilter";
import { kindLabel } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

export default async function WorldPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [locations, factions, items, entities] = await Promise.all([
    safe(`${base}/locations`), safe(`${base}/factions`), safe(`${base}/items`), safe(`${base}/world-entities`),
  ]);
  const cf = (n: string) => t(lang, "Xoá {name}?", { name: n });

  const nameDescFields = (o: any, extra: any[] = []) => [
    { name: "name", label: t(lang, "Tên"), required: true, defaultValue: o.name },
    ...extra,
    { name: "description", label: t(lang, "Mô tả"), type: "textarea" as const, defaultValue: o.description },
  ];
  const RowBtns = ({ path, fields }: { path: string; fields: any[] }) => (
    <span style={{ display: "inline-flex", gap: 4, flexShrink: 0 }}>
      <PostForm endpoint={path} method="patch" submitLabel={t(lang, "Lưu")} triggerClass="btn ghost sm" triggerLabel={t(lang, "Sửa")} fields={fields} />
    </span>
  );

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "World bible")}</div>
          <h1>{t(lang, "Thế giới")}</h1>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <ListFilter for="world-list" />
          <PostForm endpoint={`${base}/locations`} submitLabel={t(lang, "Địa điểm")} triggerClass="btn primary" triggerLabel={t(lang, "＋ Địa điểm")} fields={[
            { name: "name", label: t(lang, "Tên"), required: true },
            { name: "description", label: t(lang, "Mô tả"), type: "textarea" },
          ]} />
        </div>
      </div>
      <div id="world-list">
        <div className="grid" data-group>
          {locations.map((l: any) => (
            <div key={l.id} className="card" data-q={`${l.name} ${l.description ?? ""}`}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
                <h3 style={{ margin: 0 }}>{l.name}</h3>
                <span style={{ display: "inline-flex", gap: 4 }}>
                  <RowBtns path={`${base}/locations/${l.id}`} fields={nameDescFields(l)} />
                  <ActionButton endpoint={`${base}/locations/${l.id}`} method="delete" label="✕" confirm={cf(l.name)} />
                </span>
              </div>
              <p>{l.description}</p>
            </div>
          ))}
          {!locations.length && <div className="card"><p className="subtle">{t(lang, "Chưa có địa điểm nào.")}</p></div>}
        </div>

        <div className="dash-head" style={{ marginTop: 26 }}>
          <div><div className="eyebrow">Entities</div><h1>{t(lang, "Phe phái · Vật phẩm · Lore")}</h1></div>
        </div>
        <div className="grid">
          <div className="card" data-group>
            <h3>{t(lang, "Phe phái ({n})", { n: factions.length })}</h3>
            {factions.map((f: any) => (
              <div key={f.id} className="list-row" data-q={`${f.name} ${f.description ?? ""}`} style={{ display: "flex", gap: 8 }}>
                <div style={{ flex: 1 }}><b>{f.name}</b><div className="subtle">{f.description}</div></div>
                <RowBtns path={`${base}/factions/${f.id}`} fields={nameDescFields(f)} />
                <ActionButton endpoint={`${base}/factions/${f.id}`} method="delete" label="✕" confirm={cf(f.name)} />
              </div>
            ))}
            <PostForm endpoint={`${base}/factions`} submitLabel={t(lang, "Phe phái")} fields={[
              { name: "name", label: t(lang, "Tên"), required: true }, { name: "description", label: t(lang, "Mô tả"), type: "textarea" },
            ]} />
          </div>
          <div className="card" data-group>
            <h3>{t(lang, "Vật phẩm ({n})", { n: items.length })}</h3>
            {items.map((i: any) => (
              <div key={i.id} className="list-row" data-q={`${i.name} ${i.description ?? ""}`} style={{ display: "flex", gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <b>{i.name}</b> {i.unique_item ? <span className="pill">{t(lang, "độc nhất")}</span> : null}
                  <div className="subtle">{i.description}</div>
                </div>
                <RowBtns path={`${base}/items/${i.id}`} fields={nameDescFields(i)} />
                <ActionButton endpoint={`${base}/items/${i.id}`} method="delete" label="✕" confirm={cf(i.name)} />
              </div>
            ))}
            <PostForm endpoint={`${base}/items`} submitLabel={t(lang, "Vật phẩm")} fields={[
              { name: "name", label: t(lang, "Tên"), required: true },
              { name: "description", label: t(lang, "Mô tả"), type: "textarea" },
              { name: "unique_item", label: t(lang, "Độc nhất"), type: "checkbox" },
            ]} />
          </div>
          <div className="card" data-group>
            <h3>{t(lang, "Thực thể thế giới / Lore ({n})", { n: entities.length })}</h3>
            {entities.map((e: any) => (
              <div key={e.id} className="list-row" data-q={`${e.name} ${e.entity_type ?? ""} ${e.description ?? ""}`} style={{ display: "flex", gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <b>{e.name}</b> <small className="subtle">{kindLabel(e.entity_type, lang)}</small>
                  <div className="subtle">{e.description}</div>
                </div>
                <RowBtns path={`${base}/world-entities/${e.id}`} fields={nameDescFields(e, [
                  { name: "entity_type", label: t(lang, "Loại"), defaultValue: e.entity_type },
                ])} />
                <ActionButton endpoint={`${base}/world-entities/${e.id}`} method="delete" label="✕" confirm={cf(e.name)} />
              </div>
            ))}
            <PostForm endpoint={`${base}/world-entities`} submitLabel={t(lang, "Thực thể")} fields={[
              { name: "name", label: t(lang, "Tên"), required: true },
              { name: "entity_type", label: t(lang, "Loại"), placeholder: t(lang, "truyền thuyết / quy tắc / sinh vật…") },
              { name: "description", label: t(lang, "Mô tả"), type: "textarea" },
            ]} />
          </div>
        </div>
      </div>
    </div></main>
  );
}
