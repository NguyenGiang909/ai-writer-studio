import Link from "next/link";
import { getJSON } from "../lib/api";
import PostForm from "../components/PostForm";
import ActionButton from "../components/ActionButton";
import ThemeToggle from "../components/ThemeToggle";
import ImportButton from "../components/ImportButton";
import AiAuthoringStart from "../components/AiAuthoringStart";
import LangToggle from "../components/LangToggle";
import { getLang } from "../lib/lang-server";
import { t } from "../lib/i18n";

export default async function Home() {
  const lang = await getLang();
  let projects: any[] = [];
  let apiDown = false;
  try {
    projects = await getJSON("/api/v1/projects");
  } catch {
    apiDown = true;
  }
  const stats: Record<string, { chapters: number; words: string; threads: number }> = {};
  await Promise.all(projects.map(async (p: any) => {
    try {
      const [tree, threads] = await Promise.all([
        getJSON(`/api/v1/projects/${p.id}/manuscript`),
        getJSON(`/api/v1/projects/${p.id}/threads`).catch(() => []),
      ]);
      const w = tree.chapters.flatMap((c: any) => c.scenes)
        .reduce((n: number, s: any) => n + (s.prose?.trim() ? s.prose.trim().split(/\s+/).length : 0), 0);
      stats[p.id] = {
        chapters: tree.chapters.length,
        words: w >= 1000 ? `${(w / 1000).toFixed(1).replace(".", ",")}k` : String(w),
        threads: threads.filter((t: any) => t.status === "OPEN").length,
      };
    } catch {}
  }));
  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <span className="mark">A</span> AI Writer Studio
        </div>
        <span className="crumb" style={{ fontSize: 13 }}>
          Writer-first Story OS
        </span>
        <Link href="/account" className="account-shortcut" style={{ textDecoration: "none", marginLeft: "auto" }}>
          {t(lang, "Tài khoản")}
        </Link>
        <Link href="/settings" className="account-shortcut" style={{ textDecoration: "none" }}>
          ⚙ {t(lang, "Cài đặt")}
        </Link>
        <LangToggle />
        <ThemeToggle />
      </header>
      <main className="page">
        <div className="dashboard">
          <div className="dash-head">
            <div>
              <div className="eyebrow">{t(lang, "Dự án của bạn")}</div>
              <h1>{t(lang, "Chọn câu chuyện để tiếp tục viết")}</h1>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <AiAuthoringStart lang={lang} />
              <ImportButton />
              <PostForm
              endpoint="/api/v1/projects"
              submitLabel={t(lang, "Thêm dự án")}
              fields={[
                { name: "name", label: t(lang, "Tên dự án"), required: true, placeholder: t(lang, "Ví dụ: Mùa Trăng Cuối") },
                { name: "description", label: t(lang, "Mô tả ngắn"), type: "textarea", placeholder: t(lang, "Ý tưởng trung tâm") },
              ]}
              />
            </div>
          </div>
          {apiDown && (
            <div className="notice" style={{ marginTop: 16 }}>
              {t(lang, "Không kết nối được API ({url}). Chạy backend:", { url: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000" })}{" "}
              <code>uvicorn app.main:app --port 8000</code>
            </div>
          )}
          <div className="project-grid" style={{ marginTop: 22 }}>
            {projects.map((p: any) => (
              <article key={p.id} className="project-card">
                <div className="project-card-top">
                  <div className="project-icon">
                    {p.name.split(/\s+/).slice(0, 2).map((x: string) => x[0]).join("").toUpperCase()}
                  </div>
                  <div>
                    <h3>{p.name}</h3>
                    <p>{p.description || t(lang, "Chưa có mô tả")}</p>
                  </div>
                </div>
                {stats[p.id] && (
                  <div className="project-stats">
                    <div><b>{stats[p.id].chapters}</b><span>{t(lang, "Chương")}</span></div>
                    <div><b>{stats[p.id].words}</b><span>{t(lang, "Từ")}</span></div>
                    <div><b>{stats[p.id].threads}</b><span>{t(lang, "Hố mở")}</span></div>
                  </div>
                )}
                <div className="project-card-actions">
                  <Link href={`/projects/${p.id}`} className="btn primary" style={{ flex: 1, textAlign: "center", textDecoration: "none" }}>
                    {t(lang, "Tiếp tục viết")}
                  </Link>
                  <ActionButton
                    endpoint={`/api/v1/projects/${p.id}`}
                    method="delete"
                    label={t(lang, "Xoá")}
                    confirm={t(lang, "Xoá vĩnh viễn \"{name}\"? Toàn bộ chương, cảnh, nhân vật, canon và dữ liệu liên quan sẽ mất.", { name: p.name })}
                  />
                </div>
              </article>
            ))}
            <PostForm
              endpoint="/api/v1/projects"
              submitLabel={t(lang, "Tạo dự án")}
              triggerClass="project-card empty-project"
              trigger={
                <>
                  <div className="project-icon">＋</div>
                  <h3>{t(lang, "Tạo dự án mới")}</h3>
                  <p>{t(lang, "Bắt đầu từ ý tưởng hoặc nhập bản thảo có sẵn.")}</p>
                </>
              }
              fields={[
                { name: "name", label: t(lang, "Tên dự án"), required: true, placeholder: t(lang, "Ví dụ: Mùa Trăng Cuối") },
                { name: "description", label: t(lang, "Mô tả ngắn"), type: "textarea", placeholder: t(lang, "Ý tưởng trung tâm") },
              ]}
            />
            {!projects.length && !apiDown && (
              <p style={{ color: "var(--muted)" }}>{t(lang, "Chưa có dự án nào — tạo dự án đầu tiên của bạn.")}</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
