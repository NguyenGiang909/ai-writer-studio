import Link from "next/link";
import { getJSON } from "../../../../lib/api";
import { getLang } from "../../../../lib/lang-server";
import { t } from "../../../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return null; } }

const DORMANCY_LABEL: Record<string, string> = {
  dormant: "Ngủ quên", never: "Chưa từng xuất hiện", ok: "Còn mặt", gone: "Đã rời truyện",
};
const HEALTH_LABEL: Record<string, string> = {
  overdue: "Quá hạn payoff", stale: "Nằm im", untouched: "Chưa chạm", ok: "Ổn", closed: "Đã đóng",
};
const FLAG_COLOR: Record<string, string> = {
  dormant: "var(--red)", never: "var(--red)", overdue: "var(--red)", stale: "#c9a227",
  untouched: "#c9a227", ok: "#559d78", closed: "var(--muted)", gone: "var(--muted)",
};

export default async function SignalsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  const lang = await getLang();
  const data = await safe(`/api/v1/projects/${projectId}/signals`);
  const dormancy: any[] = data?.cast_dormancy ?? [];
  const health: any[] = data?.thread_health ?? [];
  const reps: any[] = data?.repetition ?? [];
  const flagged = dormancy.filter((d) => d.flag === "dormant" || d.flag === "never");
  const flaggedThreads = health.filter((h) => h.flag !== "ok" && h.flag !== "closed");

  return (
    <main className="main"><div className="dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow">{t(lang, "Sức khoẻ tiểu thuyết dài")}</div>
          <h1>{t(lang, "Dấu hiệu")}</h1>
        </div>
      </div>
      <p className="subtle">
        {t(lang, "Ba tín hiệu cho truyện dài: nhân vật biến mất quá lâu, hố truyện nằm im, và câu văn lặp lại giữa các cảnh.")}
      </p>
      <div className="grid">

        <div className="card">
          <h3>{t(lang, "Nhân vật ngủ quên")} <small className="subtle">({flagged.length})</small></h3>
          {flagged.map((d: any) => (
            <div key={d.character_id} className="list-row">
              <b>{d.name}</b>
              <small style={{ color: FLAG_COLOR[d.flag] }}>{t(lang, DORMANCY_LABEL[d.flag])}</small>
              <small className="subtle">
                {d.last_seen_order != null
                  ? t(lang, "thấy cuối ở thứ tự {n}", { n: d.last_seen_order })
                  : t(lang, "chưa xuất hiện trong văn")}
                {d.gap != null && ` · ~${d.gap}`}
              </small>
            </div>
          ))}
          {!flagged.length && <p className="subtle">{t(lang, "Không có nhân vật nào ngủ quên.")}</p>}
          {dormancy.some((d) => d.flag === "gone") && (
            <p className="subtle" style={{ marginTop: 8 }}>
              {t(lang, "Đã rời truyện")}: {dormancy.filter((d) => d.flag === "gone").map((d) => d.name).join(", ")}
            </p>
          )}
        </div>

        <div className="card">
          <h3>{t(lang, "Sức khoẻ hố truyện")} <small className="subtle">({flaggedThreads.length})</small></h3>
          {health.map((h: any) => (
            <div key={h.thread_id} className="list-row">
              <b>{h.title}</b>
              <small style={{ color: FLAG_COLOR[h.flag] }}>{t(lang, HEALTH_LABEL[h.flag] ?? h.flag)}</small>
              <small className="subtle">
                {h.beats} {t(lang, "beat")}
                {h.last_order != null && ` · ${t(lang, "chạm cuối")} #${h.last_order}`}
                {h.gap != null && ` · ~${h.gap}`}
              </small>
            </div>
          ))}
          {!health.length && <p className="subtle">{t(lang, "Chưa có thread nào.")}</p>}
        </div>

        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>{t(lang, "Câu lặp lại")} <small className="subtle">({reps.length})</small></h3>
          <p className="subtle">{t(lang, "Câu xuất hiện ở ≥2 cảnh — có thể là motif chủ đích hoặc lặp vô ý.")}</p>
          {reps.map((r: any) => (
            <div key={r.text} className="list-row" style={{ alignItems: "baseline" }}>
              <span style={{ flex: 1 }}>“{r.text}”</span>
              <small className="subtle">×{r.count}</small>
              <span style={{ display: "inline-flex", gap: 6, flexWrap: "wrap" }}>
                {r.scenes.map((s: any) => (
                  <Link key={s.id} href={`/projects/${projectId}?scene=${s.id}`}
                        style={{ fontSize: 12 }}>{s.title || t(lang, "Cảnh")}</Link>
                ))}
              </span>
            </div>
          ))}
          {!reps.length && <p className="subtle">{t(lang, "Không phát hiện câu lặp.")}</p>}
        </div>
      </div>
    </div></main>
  );
}
