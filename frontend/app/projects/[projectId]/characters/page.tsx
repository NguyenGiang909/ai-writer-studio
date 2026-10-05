import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import KnowledgePeek from "../../../../components/KnowledgePeek";
import { roleLabel, statusLabel, cap, charImportance, relImportance, importanceLabel } from "../../../../lib/labels";
import ActionButton from "../../../../components/ActionButton";
import ListFilter from "../../../../components/ListFilter";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

export default async function CharactersPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [characters, aliases, arcs, relationships] = await Promise.all([
    safe(`${base}/characters`), safe(`${base}/aliases`), safe(`${base}/character-arcs`), safe(`${base}/relationships`),
  ]);
  const charName = (id: string) => characters.find((c: any) => c.id === id)?.name ?? id?.slice(0, 8);
  const charOpts = characters.map((c: any) => ({ value: c.id, label: c.name }));

  // Nhóm theo mức quan trọng: 0 Quan trọng · 1 Khá quan trọng · 2 Trung bình · 3 Thùng rác
  const STD_ROLES = [
    { value: "protagonist", label: t(lang, "Nhân vật chính") },
    { value: "deuteragonist", label: t(lang, "Nhân vật phụ chính") },
    { value: "antagonist", label: t(lang, "Phản diện") },
    { value: "supporting", label: t(lang, "Vai phụ") },
    { value: "minor", label: t(lang, "Thoáng qua") },
  ];
  const STD_STATUS = ["active", "inactive", "dead", "exited", "retired"];
  const impOpts = [0, 1, 2, 3].map((v) => ({ value: String(v), label: importanceLabel(v, lang) }));
  const byOrder = (a: any, b: any) => (a.sort_order ?? 0) - (b.sort_order ?? 0);
  const groups: any[][] = [[], [], [], []];
  for (const c of characters) groups[charImportance(c)].push(c);
  groups.forEach((g) => g.sort(byOrder));
  const relGroups: any[][] = [[], [], [], []];
  for (const r of relationships) relGroups[relImportance(r)].push(r);
  relGroups.forEach((g) => g.sort(byOrder));
  const roleOptsFor = (c: any) => {
    const opts = [...STD_ROLES];
    if (c.role && !opts.some((o) => o.value === c.role))
      opts.push({ value: c.role, label: cap(c.role) });
    return opts;
  };
  const statusOptsFor = (c: any) => {
    const opts = STD_STATUS.map((v) => ({ value: v, label: statusLabel(v, lang) }));
    if (c.status && !opts.some((o) => o.value === c.status))
      opts.push({ value: c.status, label: cap(c.status) });
    return opts;
  };

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Story bible")}</div>
          <h1>{t(lang, "Nhân vật")}</h1>
        </div>
        <PostForm endpoint={`${base}/characters`} submitLabel={t(lang, "Nhân vật")} triggerClass="btn primary" triggerLabel={t(lang, "＋ Nhân vật")} fields={[
          { name: "name", label: t(lang, "Tên"), required: true },
          { name: "role", label: t(lang, "Vai trò"), type: "select", options: [
            { value: "protagonist", label: t(lang, "Nhân vật chính") }, { value: "deuteragonist", label: t(lang, "Nhân vật phụ chính") },
            { value: "antagonist", label: t(lang, "Phản diện") }, { value: "supporting", label: t(lang, "Vai phụ") },
            { value: "minor", label: t(lang, "Thoáng qua") }] },
          { name: "summary", label: t(lang, "Tóm tắt"), type: "textarea" },
          { name: "voice_notes", label: t(lang, "Giọng nhân vật"), type: "textarea" },
        ]} />
      </div>
      <div className="grid">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <h3 style={{ margin: 0 }}>{t(lang, "Nhân vật ({n})", { n: characters.length })}</h3>
            <ListFilter for="char-list" />
          </div>
          <div id="char-list" data-sort-list="characters">
          {groups.map((list, tier) =>
            list.length ? (
              <div key={tier} data-group data-bucket={tier}>
                <h4 className="imp-h" data-tier={tier}>
                  {importanceLabel(tier, lang)} · {list.length}
                </h4>
                {list.map((c: any) => (
                  <div key={c.id} className="person sort-row" draggable data-drag-id={c.id} data-q={`${c.name} ${c.role ?? ""} ${(c.summary ?? "").slice(0, 200)}`}>
                    <span className="drag-handle">⋮⋮</span>
                    <div className="avatar">{c.name?.[0] ?? "?"}</div>
                    <div className="person-main">
                      <b>{c.name}</b>
                      <small>{[roleLabel(c.role, lang), c.status ? statusLabel(c.status, lang) : ""].filter(Boolean).join(" · ")}</small>
                      {c.summary && <small>{cap(c.summary)}</small>}
                    </div>
                    <div className="row-actions">
                      <div className="move-col">
                        <ActionButton endpoint={`${base}/characters/${c.id}/move`} body={{ direction: "up" }} label="↑" />
                        <ActionButton endpoint={`${base}/characters/${c.id}/move`} body={{ direction: "down" }} label="↓" />
                      </div>
                      <PostForm
                        endpoint={`${base}/characters/${c.id}`}
                        method="patch"
                        submitLabel={t(lang, "Lưu")}
                        triggerClass="btn ghost sm"
                        triggerLabel={t(lang, "Sửa")}
                        fields={[
                          { name: "name", label: t(lang, "Tên"), required: true, defaultValue: c.name },
                          { name: "role", label: t(lang, "Vai trò"), type: "select", options: roleOptsFor(c), defaultValue: c.role },
                          { name: "status", label: t(lang, "Trạng thái"), type: "select", options: statusOptsFor(c), defaultValue: c.status },
                          { name: "importance", label: t(lang, "Mức quan trọng"), type: "select", options: impOpts, defaultValue: String(charImportance(c)) },
                          { name: "summary", label: t(lang, "Tóm tắt"), type: "textarea", defaultValue: c.summary },
                          { name: "voice_notes", label: t(lang, "Giọng nhân vật"), type: "textarea", defaultValue: c.voice_notes },
                        ]}
                      />
                      <ActionButton endpoint={`${base}/characters/${c.id}`} method="delete" label="✕" confirm={t(lang, "Xoá {name}? Bí danh/arc/quan hệ đi theo.", { name: c.name })} />
                    </div>
                  </div>
                ))}
              </div>
            ) : null
          )}
          </div>
          {!characters.length && <p className="subtle">{t(lang, "Chưa có nhân vật nào.")}</p>}

          <h3 className="section-label">{t(lang, "Bí danh ({n})", { n: aliases.length })}</h3>
          {aliases.map((a: any) => (
            <div key={a.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <span><b>{a.alias}</b> <small className="subtle">→ {charName(a.character_id)}</small></span>
              <ActionButton endpoint={`${base}/aliases/${a.id}`} method="delete" label="✕" confirm={t(lang, "Xoá bí danh {name}?", { name: a.alias })} />
            </div>
          ))}
          <PostForm endpoint={`${base}/aliases`} submitLabel={t(lang, "Bí danh")} fields={[
            { name: "character_id", label: t(lang, "Nhân vật"), type: "select", options: charOpts },
            { name: "alias", label: t(lang, "Bí danh"), required: true },
          ]} />

          <h3 className="section-label">{t(lang, "Arc nhân vật ({n})", { n: arcs.length })}</h3>
          {arcs.map((a: any) => (
            <div key={a.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
              <span><b>{a.title}</b> <small className="subtle">{charName(a.character_id)} · {statusLabel(a.status, lang)}</small></span>
              <span style={{ display: "inline-flex", gap: 4 }}>
                <PostForm endpoint={`${base}/character-arcs/${a.id}`} method="patch" submitLabel={t(lang, "Lưu")} triggerClass="btn ghost sm" triggerLabel={t(lang, "Sửa")} fields={[
                  { name: "title", label: t(lang, "Tên arc"), required: true, defaultValue: a.title },
                  { name: "status", label: t(lang, "Trạng thái"), type: "select", options: ["planned", "active", "done", "abandoned"].map((v) => ({ value: v, label: statusLabel(v, lang) })), defaultValue: a.status },
                  { name: "opening_state", label: t(lang, "Trạng thái mở đầu"), type: "textarea", defaultValue: a.opening_state },
                  { name: "target_state", label: t(lang, "Trạng thái đích"), type: "textarea", defaultValue: a.target_state },
                ]} />
                <ActionButton endpoint={`${base}/character-arcs/${a.id}`} method="delete" label="✕" confirm={t(lang, "Xoá arc {name}?", { name: a.title })} />
              </span>
            </div>
          ))}
          <PostForm endpoint={`${base}/character-arcs`} submitLabel={t(lang, "Arc")} fields={[
            { name: "character_id", label: t(lang, "Nhân vật"), type: "select", options: charOpts },
            { name: "title", label: t(lang, "Tên arc"), required: true },
            { name: "opening_state", label: t(lang, "Trạng thái mở đầu"), type: "textarea" },
            { name: "target_state", label: t(lang, "Trạng thái đích"), type: "textarea" },
          ]} />
        </div>

        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <h3 style={{ margin: 0 }}>{t(lang, "Quan hệ ({n})", { n: relationships.length })}</h3>
            <ListFilter for="rel-list" />
          </div>
          <div id="rel-list" data-sort-list="relationships">
          {relGroups.map((list, tier) =>
            list.length ? (
              <div key={tier} data-group data-bucket={tier}>
                <h4 className="imp-h" data-tier={tier}>
                  {importanceLabel(tier, lang)} · {list.length}
                </h4>
                {list.map((r: any) => (
                  <div key={r.id} className="list-row sort-row" draggable data-drag-id={r.id} style={{ display: "flex", gap: 8, alignItems: "flex-start" }} data-q={`${charName(r.source_character_id)} ${r.relationship_type} ${charName(r.target_character_id)} ${r.notes ?? ""}`}>
                    <span className="drag-handle">⋮⋮</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <b>{charName(r.source_character_id)}</b> —{r.relationship_type}→ <b>{charName(r.target_character_id)}</b>
                      <div className="subtle">{r.notes}</div>
                    </div>
                    <div className="row-actions">
                      <div className="move-col">
                        <ActionButton endpoint={`${base}/relationships/${r.id}/move`} body={{ direction: "up" }} label="↑" />
                        <ActionButton endpoint={`${base}/relationships/${r.id}/move`} body={{ direction: "down" }} label="↓" />
                      </div>
                      <PostForm
                        endpoint={`${base}/relationships/${r.id}`}
                        method="patch"
                        submitLabel={t(lang, "Lưu")}
                        triggerClass="btn ghost sm"
                        triggerLabel={t(lang, "Sửa")}
                        fields={[
                          { name: "relationship_type", label: t(lang, "Loại quan hệ"), required: true, defaultValue: r.relationship_type },
                          { name: "importance", label: t(lang, "Mức quan trọng"), type: "select", options: impOpts, defaultValue: String(relImportance(r)) },
                          { name: "notes", label: t(lang, "Ghi chú"), type: "textarea", defaultValue: r.notes },
                        ]}
                      />
                      <ActionButton endpoint={`${base}/relationships/${r.id}`} method="delete" label="✕" confirm={t(lang, "Xoá quan hệ này?")} />
                    </div>
                  </div>
                ))}
              </div>
            ) : null
          )}
          </div>
          {!relationships.length && <p className="subtle">{t(lang, "Chưa có quan hệ nào.")}</p>}
          <PostForm endpoint={`${base}/relationships`} submitLabel={t(lang, "Quan hệ")} fields={[
            { name: "source_character_id", label: t(lang, "Từ nhân vật"), type: "select", options: charOpts },
            { name: "target_character_id", label: t(lang, "Đến nhân vật"), type: "select", options: charOpts },
            { name: "relationship_type", label: t(lang, "Loại quan hệ"), required: true, placeholder: t(lang, "đồng minh / đối thủ / gia đình…") },
            { name: "notes", label: t(lang, "Ghi chú"), type: "textarea" },
          ]} />
        </div>

        <KnowledgePeek projectId={projectId} characters={characters} />
      </div>
    </div></main>
  );
}
