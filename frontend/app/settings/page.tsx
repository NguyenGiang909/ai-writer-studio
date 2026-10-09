import Link from "next/link";
import { getJSON } from "../../lib/api";
import PostForm from "../../components/PostForm";
import ActionButton from "../../components/ActionButton";
import ThemeToggle from "../../components/ThemeToggle";
import LangToggle from "../../components/LangToggle";
import TierSelect from "../../components/TierSelect";
import { getLang } from "../../lib/lang-server";
import { t } from "../../lib/i18n";

async function safe(path: string) { try { return await getJSON(path); } catch { return []; } }

const PROVIDERS = ["openai", "anthropic", "gemini", "openrouter", "deepseek", "kiraai", "custom"];
const TASKS = [
  ["discussion", "Thảo luận"], ["writing", "Viết / mở rộng"], ["extraction", "Trích xuất"],
  ["summarization", "Tóm tắt"], ["review", "Kiểm tra"],
].map(([value, label]) => ({ value, label }));
const taskLabel = (t: string) => TASKS.find((x) => x.value === t)?.label ?? t;

export default async function Settings() {
  const lang = await getLang();
  const [credentials, prefs, projects, usage] = await Promise.all([
    safe("/api/v1/account/credentials"),
    safe("/api/v1/account/model-preferences"),
    safe("/api/v1/projects"),
    safe("/api/v1/account/usage"),
  ]);
  const usageRows = usage?.rows ?? [];
  const byTask = usage?.by_task ?? {};
  return (
    <div className="app">
    <header className="top">
      <Link href="/" className="brand" style={{ textDecoration: "none" }}>
        <span className="mark">A</span> AI Writer Studio
      </Link>
      <span className="crumb">{t(lang, "Kết nối API")}</span>
      <Link href="/account" className="account-shortcut" style={{ textDecoration: "none", marginLeft: "auto" }}>
        {t(lang, "Tài khoản")}
      </Link>
      <LangToggle />
      <ThemeToggle />
    </header>
    <main className="page"><div className="dashboard settings-screen">
      <div className="dash-head"><div><div className="eyebrow">{t(lang, "Cài đặt")}</div><h1>{t(lang, "Kết nối API")}</h1></div></div>
      <p className="settings-note">
        {t(lang, "Khoá API được mã hoá phía máy chủ và không bao giờ trả về — chỉ hiện phần đuôi gợi nhớ.")}
      </p>

      <div className="settings-grid">
      <section className="card">
        <h3>{t(lang, "Nhà cung cấp AI (BYOK)")}</h3>
        <p className="subtle">
          {t(lang, "Năng lực API (Yếu/Thường/Mạnh) quyết định app có chia nhỏ request không — gateway yếu sẽ được gửi prompt ngắn; không liên quan chất lượng văn.")}
        </p>
        {credentials.map((c: any) => (
          <div key={c.id} className="list-row">
            <b>{c.provider}</b> <code style={{ fontSize: 12 }}>{c.key_hint}</code>{" "}
            {c.base_url && <code style={{ fontSize: 11, color: "var(--muted)" }}>{c.base_url}</code>}{" "}
            <small style={{ color: c.status === "connected" ? "#559d78" : "var(--red)" }}>
              {c.status === "connected" ? t(lang, "Đã kết nối") : c.status === "error" ? t(lang, "Lỗi") : c.status}
            </small>
            <TierSelect id={c.id} tier={c.tier ?? "standard"} override={c.tier_override ?? null} />
            <span style={{ marginLeft: 8 }}>
              <ActionButton endpoint={`/api/v1/account/credentials/${c.id}/test`} label={t(lang, "Kiểm tra")} />
            </span>
            {c.status === "connected" && (
              <span style={{ marginLeft: 8 }}>
                <ActionButton endpoint={`/api/v1/account/credentials/${c.id}`} method="delete" label={t(lang, "Ngắt kết nối")} />
              </span>
            )}
          </div>
        ))}
        {!credentials.length && <p className="subtle">{t(lang, "Chưa kết nối nhà cung cấp nào.")}</p>}
        <PostForm endpoint="/api/v1/account/credentials" submitLabel={t(lang, "Kết nối")} fields={[
          { name: "provider", label: t(lang, "Nhà cung cấp"), type: "select", options: PROVIDERS.map((p) => ({ value: p, label: p })) },
          { name: "secret", label: "API key", required: true, placeholder: "sk-…" },
          { name: "base_url", label: t(lang, "Base URL (tuỳ chọn)"), placeholder: "vd http://localhost:1234/v1 — chỉ cần cho custom/LM Studio" },
          { name: "tier", label: t(lang, "Năng lực API"), type: "select", defaultValue: "auto", options: [
            { value: "auto", label: t(lang, "Tự động theo nhà cung cấp") },
            { value: "low", label: t(lang, "Yếu — gateway chậm/giới hạn request dài") },
            { value: "standard", label: t(lang, "Thường — endpoint tự host, chưa rõ giới hạn") },
            { value: "strong", label: t(lang, "Mạnh — context lớn, gửi trọn chương được") },
          ] },
        ]} />
      </section>

      <section className="card">
        <h3>{t(lang, "Định tuyến model")}</h3>
        <p className="subtle">{t(lang, "Ưu tiên: tác vụ → dự án → tài khoản → mặc định hệ thống.")}</p>
        {prefs.map((p: any) => (
          <div key={p.id} className="list-row">
            <b>{t(lang, taskLabel(p.task))}</b> → {p.provider} / <code style={{ fontSize: 12 }}>{p.model}</code>
            {p.project_id && <small style={{ color: "var(--muted)" }}>{t(lang, " · dự án {id}", { id: p.project_id.slice(0, 8) })}</small>}
          </div>
        ))}
        <PostForm endpoint="/api/v1/account/model-preferences" submitLabel={t(lang, "Quy tắc")} fields={[
          { name: "task", label: t(lang, "Tác vụ"), type: "select", options: TASKS.map((o) => ({ ...o, label: t(lang, o.label) })) },
          { name: "provider", label: t(lang, "Nhà cung cấp"), type: "select", options: PROVIDERS.map((p) => ({ value: p, label: p })) },
          { name: "model", label: "Model", required: true, placeholder: "gpt-4.1-mini / claude-…" },
          { name: "project_id", label: t(lang, "Dự án (tuỳ chọn)"), type: "select", options: [
            { value: "", label: t(lang, "— mặc định tài khoản —") },
            ...projects.map((p: any) => ({ value: p.id, label: p.name })),
          ] },
        ]} />
      </section>

      <section className="card" style={{ gridColumn: "1 / -1" }}>
        <h3>{t(lang, "Sử dụng AI")}</h3>
        <p className="subtle">{t(lang, "Lượt gọi gần đây theo tác vụ — token từ nhà cung cấp.")}</p>
        {Object.keys(byTask).length > 0 && (
          <div className="list-row" style={{ flexWrap: "wrap", gap: 12 }}>
            {Object.entries(byTask).map(([task, s]: [string, any]) => (
              <span key={task} className="pill">
                {t(lang, taskLabel(task))}: {s.calls} {t(lang, "lượt")} · {s.total_tokens.toLocaleString()} tok
              </span>
            ))}
          </div>
        )}
        {usageRows.slice(0, 20).map((r: any) => (
          <div key={r.id} className="list-row">
            <small style={{ color: "var(--muted)" }}>{(r.created_at || "").slice(0, 16).replace("T", " ")}</small>
            <b>{t(lang, taskLabel(r.task))}</b>
            <span>{r.provider}/{r.model}</span>
            <small style={{ color: "var(--muted)" }}>
              {r.prompt_tokens.toLocaleString()} → {r.completion_tokens.toLocaleString()} tok
            </small>
          </div>
        ))}
        {!usageRows.length && <p className="subtle">{t(lang, "Chưa có lượt gọi AI nào.")}</p>}
      </section>
      </div>
    </div></main>
    </div>
  );
}
