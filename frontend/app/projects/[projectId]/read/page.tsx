import Link from "next/link";
import { redirect } from "next/navigation";
import { getJSON } from "../../../../lib/api";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";
import ChapterSelect from "../../../../components/ChapterSelect";

export default async function ReadPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ chapter?: string }>;
}) {
  const { projectId } = await params;
  const { chapter: chapterId } = await searchParams;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;

  let tree: any = { chapters: [] };
  try {
    tree = await getJSON(`${base}/manuscript`);
  } catch {
    /* giữ rỗng */
  }
  const chapters: any[] = tree.chapters ?? [];
  if (!chapters.length) {
    return (
      <main className="main">
        <div style={{ padding: 60, color: "var(--muted)" }}>
          {t(lang, "Chưa có chương nào để đọc.")}
        </div>
      </main>
    );
  }
  if (!chapterId) redirect(`/projects/${projectId}/read?chapter=${chapters[0].id}`);

  const idx = chapters.findIndex((c) => c.id === chapterId);
  const ch = idx >= 0 ? chapters[idx] : chapters[0];
  const prev = idx > 0 ? chapters[idx - 1] : null;
  const next = idx >= 0 && idx < chapters.length - 1 ? chapters[idx + 1] : null;
  const words = ch.scenes.reduce(
    (n: number, s: any) => n + ((s.prose || "").trim() ? (s.prose as string).trim().split(/\s+/).length : 0), 0);

  const opts = chapters.map((c: any) => ({ value: c.id, label: c.title }));

  return (
    <main className="main read-mode">
      <div className="read-wrap">
        <div className="read-nav">
          {prev ? (
            <Link className="btn ghost small" href={`/projects/${projectId}/read?chapter=${prev.id}`}>
              ‹ {prev.title}
            </Link>
          ) : <span />}
          <ChapterSelect options={opts} current={ch.id} base={`/projects/${projectId}/read`} />
          {next ? (
            <Link className="btn ghost small" href={`/projects/${projectId}/read?chapter=${next.id}`}>
              {next.title} ›
            </Link>
          ) : <span />}
        </div>
        <h1 className="read-title">{ch.title}</h1>
        <p className="subtle" style={{ textAlign: "center", marginTop: -8 }}>
          {words} {t(lang, "từ")} · {ch.scenes.length} {t(lang, "Cảnh")}
        </p>
        {ch.scenes.map((s: any, i: number) => (
          <section key={s.id} className="read-scene">
            {s.title && <h3 className="read-scene-title">{s.title}</h3>}
            {(s.prose || "").trim() ? (
              (s.prose as string).split(/\n{2,}/).map((p: string, j: number) => (
                <p key={j} className="read-p">{p}</p>
              ))
            ) : (
              <p className="subtle" style={{ fontStyle: "italic" }}>{t(lang, "Cảnh {n} chưa có văn.", { n: i + 1 })}</p>
            )}
          </section>
        ))}
        <div className="read-nav" style={{ marginTop: 40 }}>
          {prev ? (
            <Link className="btn" href={`/projects/${projectId}/read?chapter=${prev.id}`}>‹ {prev.title}</Link>
          ) : <span />}
          {next ? (
            <Link className="btn" href={`/projects/${projectId}/read?chapter=${next.id}`}>{next.title} ›</Link>
          ) : <span />}
        </div>
      </div>
    </main>
  );
}
