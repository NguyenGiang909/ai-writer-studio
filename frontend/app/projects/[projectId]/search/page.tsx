import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

type Hit = {
  type: string;
  id: string;
  label: string;
  context?: string;
  snippet?: string;
  scene_id?: string | null;
};

const TYPE_LABEL: Record<string, string> = {
  scene: "Cảnh",
  chapter: "Chương",
  character: "Nhân vật",
  canon: "Canon",
  thread: "Thread",
  event: "Sự kiện",
  location: "Địa điểm",
};

const TYPE_ORDER = ["scene", "chapter", "character", "canon", "thread", "event", "location"];

function href(pid: string, h: Hit): string {
  switch (h.type) {
    case "scene": return `/projects/${pid}?scene=${h.id}`;
    case "chapter": return h.scene_id ? `/projects/${pid}?scene=${h.scene_id}` : `/projects/${pid}`;
    case "character": return `/projects/${pid}/characters`;
    case "canon": return `/projects/${pid}/truth`;
    case "thread": return `/projects/${pid}/threads`;
    case "event": return `/projects/${pid}/timeline`;
    case "location": return `/projects/${pid}/world`;
    default: return `/projects/${pid}`;
  }
}

export default async function SearchPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ q?: string }>;
}) {
  const { projectId } = await params;
  const { q } = await searchParams;
  const lang = await getLang();
  const query = (q ?? "").trim();

  let results: Hit[] = [];
  if (query) {
    try {
      const data = await getJSON(`/api/v1/projects/${projectId}/search?q=${encodeURIComponent(query)}`);
      results = data.results ?? [];
    } catch {
      results = [];
    }
  }

  const grouped = TYPE_ORDER
    .map((ty) => ({ ty, hits: results.filter((r) => r.type === ty) }))
    .filter((g) => g.hits.length);

  return (
    <main className="main">
      <div className="dashboard" style={{ maxWidth: 860 }}>
        <div className="dash-head">
          <div>
            <h1>{t(lang, "Tìm kiếm")}</h1>
            <p className="subtle">
              {query
                ? t(lang, "{n} kết quả cho “{q}”", { n: results.length, q: query })
                : t(lang, "Nhập từ khóa ở ô tìm kiếm phía trên.")}
            </p>
          </div>
        </div>
        {query && results.length === 0 && (
          <section className="card">
            <p className="subtle" style={{ margin: 0 }}>
              {t(lang, "Không có kết quả nào — thử từ khóa khác hoặc ngắn gọn hơn.")}
            </p>
          </section>
        )}
        {grouped.map((g) => (
          <section className="card" key={g.ty}>
            <h3 style={{ marginTop: 0 }}>{t(lang, TYPE_LABEL[g.ty])} <small className="subtle">({g.hits.length})</small></h3>
            <div style={{ display: "grid", gap: 6 }}>
              {g.hits.map((h) => (
                <Link key={`${h.type}-${h.id}`} href={href(projectId, h)} className="list-row" style={{ textDecoration: "none" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div><b>{h.label}</b>{h.context ? <span className="subtle"> · {h.context}</span> : null}</div>
                    {h.snippet && <div className="subtle" style={{ marginTop: 2 }}>{h.snippet}</div>}
                  </div>
                  <span className="subtle">→</span>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
