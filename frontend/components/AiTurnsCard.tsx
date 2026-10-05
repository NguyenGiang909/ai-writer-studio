"use client";
import { useEffect, useState } from "react";
import { delJSON, getJSON, postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { toast } from "../lib/toast";

type Turn = {
  id: string; task: string; scope_id: string; provider: string; model: string;
  prompt_excerpt: string; reply_text: string; created_at: string;
};

export default function AiTurnsCard({ projectId }: { projectId: string }) {
  const lang = useLang();
  const [data, setData] = useState<{ total: number; turns: Turn[] } | null>(null);
  const [keep, setKeep] = useState(50);
  const [busy, setBusy] = useState(false);
  const loc = lang === "en" ? "en-US" : "vi-VN";

  async function load() {
    try { setData(await getJSON(`/api/v1/projects/${projectId}/ai/turns?limit=200`)); }
    catch { setData({ total: 0, turns: [] }); }
  }
  useEffect(() => { load(); }, [projectId]);

  async function remove(id: string) {
    try {
      await delJSON(`/api/v1/projects/${projectId}/ai/turns/${id}`);
      toast(t(lang, "Đã xoá turn"));
      await load();
    } catch (e: any) { toast(e?.message ?? "error"); }
  }

  async function prune() {
    setBusy(true);
    try {
      const r = await postJSON(`/api/v1/projects/${projectId}/ai/turns/prune`, { keep });
      toast(t(lang, "Đã dọn {n} turn", { n: r.deleted }));
      await load();
    } catch (e: any) { toast(e?.message ?? "error"); }
    finally { setBusy(false); }
  }

  const turns = data?.turns ?? [];
  return (
    <section className="card ai-turns">
      <h3>{t(lang, "Lịch sử AI ({n})", { n: data?.total ?? 0 })}</h3>
      <p className="subtle" style={{ fontSize: 13, marginTop: -6 }}>
        {t(lang, "Mọi lượt gọi AI đều được ghi lại để đối chiếu — mới nhất trước.")}
      </p>
      {(data?.total ?? 0) > 0 && (
        <div className="turn-prune">
          <span className="subtle">{t(lang, "Giữ lại")}</span>
          <input type="number" min={0} value={keep}
                 onChange={(e) => setKeep(Math.max(0, Number(e.target.value) || 0))} />
          <span className="subtle">{t(lang, "turn mới nhất")}</span>
          <button className="btn ghost small" onClick={prune} disabled={busy}>
            {t(lang, "Dọn bớt")}
          </button>
        </div>
      )}
      {!turns.length && <p className="subtle">{t(lang, "Chưa có lượt AI nào được ghi.")}</p>}
      {turns.map((tr) => (
        <details key={tr.id} className="list-row turn">
          <summary>
            <span className="pill">{tr.task}</span>{" "}
            <small className="subtle">
              {tr.provider}{tr.model ? `/${tr.model}` : ""} ·{" "}
              {new Date(tr.created_at + "Z").toLocaleString(loc)}
            </small>
          </summary>
          <div className="turn-body">
            <div className="eyebrow">{t(lang, "Prompt (trích)")}</div>
            <pre>{tr.prompt_excerpt || "—"}</pre>
            <div className="eyebrow">{t(lang, "Phản hồi")}</div>
            <pre>{tr.reply_text || "—"}</pre>
            <button className="btn ghost small danger" onClick={() => remove(tr.id)}>×</button>
          </div>
        </details>
      ))}
      {(data?.total ?? 0) > turns.length && (
        <p className="subtle" style={{ fontSize: 12 }}>
          … +{(data?.total ?? 0) - turns.length}
        </p>
      )}
    </section>
  );
}
