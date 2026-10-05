import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import ListFilter from "../../../../components/ListFilter";
import { cap } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

export default async function AbilitiesPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const abilities = await safe(`${base}/abilities`);

  const abilityFields = (a: any) => [
    { name: "name", label: t(lang, "Tên"), required: true, defaultValue: a.name },
    { name: "ability_type", label: t(lang, "Loại"), defaultValue: a.ability_type },
    { name: "can_do", label: t(lang, "Có thể"), type: "textarea" as const, defaultValue: a.can_do },
    { name: "cannot_do", label: t(lang, "Không thể"), type: "textarea" as const, defaultValue: a.cannot_do },
    { name: "limits", label: t(lang, "Giới hạn"), type: "textarea" as const, defaultValue: a.limits },
    { name: "cost", label: t(lang, "Cái giá"), type: "textarea" as const, defaultValue: a.cost },
    { name: "conditions", label: t(lang, "Điều kiện"), type: "textarea" as const, defaultValue: a.conditions },
    { name: "counters", label: t(lang, "Khắc chế"), type: "textarea" as const, defaultValue: a.counters },
  ];

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Rules engine")}</div>
          <h1>{t(lang, "Năng lực")}</h1>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <ListFilter for="ability-list" />
          <PostForm endpoint={`${base}/abilities`} submitLabel={t(lang, "Năng lực")} triggerClass="btn primary" triggerLabel={t(lang, "＋ Năng lực")} fields={abilityFields({}).map(({ defaultValue, ...f }) => f)} />
        </div>
      </div>
      <div className="grid" id="ability-list">
        {abilities.map((a: any) => (
          <div key={a.id} className="card" data-q={`${a.name} ${a.ability_type ?? ""} ${a.can_do ?? ""}`}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
              <h3 style={{ margin: 0 }}>{a.name}</h3>
              <span style={{ display: "inline-flex", gap: 4 }}>
                <PostForm endpoint={`${base}/abilities/${a.id}`} method="patch" submitLabel={t(lang, "Lưu")} triggerClass="btn ghost sm" triggerLabel={t(lang, "Sửa")} fields={abilityFields(a)} />
                <ActionButton endpoint={`${base}/abilities/${a.id}`} method="delete" label="✕" confirm={t(lang, "Xoá {name}?", { name: a.name })} />
              </span>
            </div>
            {a.can_do && <p>{a.can_do}</p>}
            {a.cannot_do && <p className="subtle">{t(lang, "Không thể:")} {a.cannot_do}</p>}
            {a.limits && <span className="pill">{t(lang, "Giới hạn:")} {a.limits}</span>}
            {a.cost && <span className="pill warn">{t(lang, "Cái giá:")} {a.cost}</span>}
            {a.ability_type && <small className="subtle" style={{ display: "block", marginTop: 8 }}>{cap(a.ability_type)}</small>}
          </div>
        ))}
        {!abilities.length && <div className="card"><p className="subtle">{t(lang, "Chưa có năng lực / quy tắc nào.")}</p></div>}
      </div>
    </div></main>
  );
}
