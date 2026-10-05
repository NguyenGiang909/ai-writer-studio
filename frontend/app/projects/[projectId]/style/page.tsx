import { getJSON } from "../../../../lib/api";
import PostForm from "../../../../components/PostForm";
import { scopeLabel } from "../../../../lib/labels";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

export default async function StylePage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [profiles, samples, prefs] = await Promise.all([
    safe(`${base}/style-profiles`), safe(`${base}/style-samples`), safe(`${base}/style-preferences`),
  ]);

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Voice guide")}</div>
          <h1>{t(lang, "Phong cách")}</h1>
        </div>
        <PostForm endpoint={`${base}/style-profiles`} submitLabel={t(lang, "Hồ sơ giọng")} triggerClass="btn primary" triggerLabel={t(lang, "＋ Hồ sơ")} fields={[
          { name: "name", label: t(lang, "Tên"), required: true },
          { name: "scope_type", label: t(lang, "Phạm vi"), type: "select", options: [
            { value: "global", label: t(lang, "Toàn truyện") }, { value: "arc", label: t(lang, "Hồi") },
            { value: "character", label: t(lang, "Nhân vật") }, { value: "scene_type", label: t(lang, "Loại cảnh") }] },
          { name: "instructions", label: t(lang, "Chỉ dẫn"), type: "textarea" },
        ]} />
      </div>
      <div className="grid">
        {profiles.map((p: any) => (
          <div key={p.id} className="card">
            <h3>{p.name}</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{p.instructions}</p>
            <span className="pill">{scopeLabel(p.scope_type, lang)}{p.active ? "" : ` · ${t(lang, "tắt")}`}</span>
          </div>
        ))}
        {!profiles.length && (
          <div className="card">
            <h3>{t(lang, "Giọng kể")}</h3>
            <p className="subtle">{t(lang, "Chưa có style profile — tạo profile để AI bám đúng giọng truyện.")}</p>
          </div>
        )}
      </div>

      <div className="dash-head" style={{ marginTop: 26 }}>
        <div><div className="eyebrow">{t(lang, "Văn mẫu & ưu tiên")}</div><h1>{t(lang, "Văn mẫu · Ưu tiên")}</h1></div>
      </div>
      <div className="grid">
        <div className="card">
          <h3>{t(lang, "Văn mẫu ({n})", { n: samples.length })}</h3>
          {samples.map((s: any) => (
            <div key={s.id} className="list-row">
              <b>{s.title || s.sample_type}</b> <small className="subtle">{s.sample_type}</small>
              <div className="subtle" style={{ whiteSpace: "pre-wrap" }}>{s.text?.slice(0, 160)}{s.text?.length > 160 ? "…" : ""}</div>
            </div>
          ))}
          <PostForm endpoint={`${base}/style-samples`} submitLabel={t(lang, "Văn mẫu")} fields={[
            { name: "style_profile_id", label: t(lang, "Hồ sơ giọng"), type: "select", options: profiles.map((p: any) => ({ value: p.id, label: p.name })) },
            { name: "sample_type", label: t(lang, "Loại mẫu"), placeholder: t(lang, "hội thoại / chiến đấu / miêu tả…") },
            { name: "title", label: t(lang, "Tiêu đề") },
            { name: "text", label: t(lang, "Văn mẫu"), type: "textarea", required: true },
          ]} />
        </div>
        <div className="card">
          <h3>{t(lang, "Ưu tiên ({n})", { n: prefs.length })}</h3>
          {prefs.map((p: any) => (
            <div key={p.id} className="list-row">
              <b>{p.preference_type === "avoid" ? t(lang, "Tránh") : t(lang, "Ưu tiên")}</b> <small className="subtle">{profiles.find((x: any) => x.id === p.style_profile_id)?.name}</small>
              <div className="subtle">{p.pattern}</div>
            </div>
          ))}
          {!prefs.length && <p className="subtle">{t(lang, "Chưa có ưu tiên nào.")}</p>}
          <PostForm endpoint={`${base}/style-preferences`} submitLabel={t(lang, "Ưu tiên")} fields={[
            { name: "style_profile_id", label: t(lang, "Hồ sơ giọng"), type: "select", options: profiles.map((p: any) => ({ value: p.id, label: p.name })) },
            { name: "preference_type", label: t(lang, "Loại"), type: "select", options: [
              { value: "prefer", label: t(lang, "Ưu tiên dùng") }, { value: "avoid", label: t(lang, "Tránh dùng") }] },
            { name: "pattern", label: t(lang, "Mẫu / mô tả"), type: "textarea", required: true },
          ]} />
        </div>
      </div>
    </div></main>
  );
}
