import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import ActionButton from "../../../../components/ActionButton";
import { scopeLabel, payloadText } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string, fallback: any = []) { try { return await getJSON(path); } catch { return fallback; } }

const TARGET_OPTS_VI = [
  { value: "thread", label: "Hố" }, { value: "scene", label: "Cảnh" },
  { value: "chapter", label: "Chương" }, { value: "canon_fact", label: "Sự thật canon" },
];

export default async function MemoryPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const TARGET_OPTS = TARGET_OPTS_VI.map((o) => ({ ...o, label: t(lang, o.label) }));
  const base = `/api/v1/projects/${projectId}`;
  const [summaries, backlog, retcons, tree] = await Promise.all([
    safe(`${base}/summaries`), safe(`${base}/summaries/stale-backlog`),
    safe(`${base}/retcon-proposals`), safe(`${base}/manuscript`, { chapters: [] }),
  ]);
  const chapters = tree.chapters ?? [];
  const scopeOpts = [
    ...chapters.flatMap((c: any) => [
      { value: `chapter:${c.id}`, label: `${t(lang, "Chương")} ${c.order_index}. ${c.title}` },
      ...(c.scenes ?? []).map((s: any) => ({ value: `scene:${s.id}`, label: `↳ ${s.title || t(lang, "Cảnh")}` })),
    ]),
    { value: `story:${projectId}`, label: t(lang, "Toàn truyện") },
  ];
  const scopeName = (type: string, id: string) => {
    for (const c of chapters) {
      if (c.id === id) return c.title;
      const s = (c.scenes ?? []).find((x: any) => x.id === id);
      if (s) return `${c.title} · ${s.title || t(lang, "Cảnh")}`;
    }
    return id?.slice(0, 8) ?? "?";
  };

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head"><div><div className="eyebrow">{t(lang, "Bộ nhớ phân cấp")}</div><h1>Long-Novel Memory</h1></div></div>
      <p className="subtle">
        {t(lang, "Tóm tắt là bản nháp phụ trợ, không phải Canon. Retcon và impact chỉ xem trước — không tự áp dụng.")}
      </p>
      <div className="grid">
        <section className="card">
          <h3>{t(lang, "Tóm tắt phân cấp ({n})", { n: summaries.length })}</h3>
          {summaries.map((s: any) => (
            <div key={s.id} className="list-row">
              <b>{scopeLabel(s.scope_type, lang)}</b>{" "}
              <small className="subtle">{scopeName(s.scope_type, s.scope_id)}</small>{" "}
              {s.stale && <span className="pill warn">{t(lang, "Đã lỗi thời")}</span>}
              <div style={{ fontSize: 14, marginTop: 4 }}>{s.summary}</div>
              {!s.stale && <ActionButton endpoint={`${base}/summaries/${s.id}/invalidate`} label={t(lang, "Vô hiệu chuỗi")} />}
            </div>
          ))}
          <PostForm endpoint={`${base}/summaries`} submitLabel={t(lang, "Tóm tắt")} fields={[
            { name: "scope", label: t(lang, "Phạm vi"), type: "scope", options: scopeOpts },
            { name: "summary", label: t(lang, "Nội dung tóm tắt"), type: "textarea", required: true },
          ]} />
          <h3 className="section-label">{t(lang, "Chờ cập nhật ({n})", { n: backlog.length })}</h3>
          {backlog.map((b: any) => (
            <div key={b.id} className="list-row" style={{ fontSize: 14, padding: "8px 0" }}>
              {scopeLabel(b.scope_type, lang)} · {scopeName(b.scope_type, b.scope_id)}
            </div>
          ))}
        </section>

        <section className="card">
          <h3>{t(lang, "Đề xuất Retcon ({n})", { n: retcons.length })}</h3>
          {retcons.map((r: any) => (
            <div key={r.id} className="list-row">
              <b>{scopeLabel(r.target_type, lang)}</b> → {scopeName(r.target_type, r.target_id)}
              <div style={{ fontSize: 14, marginTop: 4 }}>{r.proposal}</div>
              <details style={{ fontSize: 13, color: "var(--muted)", marginTop: 6 }}>
                <summary>{t(lang, "Ảnh hưởng ({n} mục)", { n: r.impact?.affected?.length ?? 0 })}</summary>
                {(r.impact?.affected ?? []).map((a: any, i: number) => (
                  <div key={i} style={{ padding: "4px 0" }}>
                    · {payloadText(a, lang) || scopeName(a.scope_type ?? a.type, a.scope_id ?? a.id)}
                  </div>
                ))}
                {!(r.impact?.affected ?? []).length && <div style={{ padding: "4px 0" }}>{t(lang, "Không có mục bị ảnh hưởng.")}</div>}
              </details>
            </div>
          ))}
          <PostForm endpoint={`${base}/retcon-proposals`} submitLabel={t(lang, "Đề xuất retcon")} fields={[
            { name: "target_type", label: t(lang, "Loại đối tượng"), type: "select", options: TARGET_OPTS },
            { name: "target_id", label: t(lang, "ID đối tượng"), required: true },
            { name: "proposal", label: t(lang, "Đề xuất thay đổi"), type: "textarea", required: true },
          ]} />
        </section>
      </div>
    </div></main>
  );
}
