"use client";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { getJSON, postJSON, patchJSON, delJSON } from "../lib/api";
import { styleStatusLabel, strengthLabel, scopeLabel } from "../lib/labels";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

type Rule = {
  id: string; profile_id: string; profile_name?: string | null;
  preference_type: string; pattern: string; strength: string; status: string;
  source: string; attribute?: string | null; scope_type?: string | null;
  scope_id?: string | null; evidence?: string | null; updated_at?: string | null;
};

type Proposal = {
  profiles: { name: string; instructions: string }[];
  rules: { attribute?: string; pattern: string; preference_type?: string;
           strength?: string; evidence?: string; profile_index?: number }[];
  canon_facts: { predicate: string; value_text: string }[];
};

const SRC_LABEL: Record<string, string> = {
  explicit: "tác giả nói", approved_edit: "sửa được duyệt",
  observed_edit: "tác giả tự sửa", inferred: "AI suy ra", preset: "preset",
};

export default function StyleRulesPanel({ projectId }: { projectId: string }) {
  const lang = useLang();
  const [rules, setRules] = useState<Rule[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");
  // dạy trực tiếp
  const [ins, setIns] = useState("");
  const [insStr, setInsStr] = useState("PREFERRED");
  // học từ diff
  const [orig, setOrig] = useState("");
  const [rev, setRev] = useState("");
  const [cmt, setCmt] = useState("");
  // preset
  const [presets, setPresets] = useState<{ name: string; title: string }[]>([]);
  const [presetName, setPresetName] = useState("");
  const [presetText, setPresetText] = useState("");
  const [prop, setProp] = useState<Proposal | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [pickedC, setPickedC] = useState<Set<number>>(new Set());

  async function reload() {
    try {
      const r = await getJSON(`/api/v1/projects/${projectId}/style-rules`);
      setRules(r.rules ?? []); setCounts(r.counts ?? {});
    } catch (e: any) { setErr(e?.message ?? "load error"); }
  }
  useEffect(() => { reload(); }, [projectId]);
  useEffect(() => {
    getJSON(`/api/v1/projects/${projectId}/style/presets`)
      .then((d) => setPresets(d.presets ?? [])).catch(() => {});
  }, [projectId]);

  async function setStatus(id: string, status: string) {
    try { await patchJSON(`/api/v1/projects/${projectId}/style-rules/${id}`, { status }); await reload(); }
    catch (e: any) { setErr(e?.message ?? "patch error"); }
  }
  async function remove(id: string) {
    try { await delJSON(`/api/v1/projects/${projectId}/style-rules/${id}`); await reload(); }
    catch (e: any) { setErr(e?.message ?? "delete error"); }
  }

  async function teach(e: React.FormEvent) {
    e.preventDefault();
    if (!ins.trim() || busy) return;
    setBusy("ins"); setErr("");
    try {
      await postJSON(`/api/v1/projects/${projectId}/style-rules/learn`,
        { instruction: ins.trim(), strength: insStr });
      setIns(""); await reload();
    } catch (e2: any) { setErr(e2?.message ?? t(lang, "Lỗi lưu gu")); }
    setBusy("");
  }

  async function learnDiff(e: React.FormEvent) {
    e.preventDefault();
    if (!orig.trim() || !rev.trim() || busy) return;
    setBusy("diff"); setErr("");
    try {
      const r = await postJSON(`/api/v1/projects/${projectId}/style-rules/learn`,
        { original: orig, revised: rev, comment: cmt || undefined });
      const n = (r.rules ?? []).length;
      if (!n) setErr(t(lang, "AI không rút được quy tắc nào từ diff này (hoặc provider chưa cấu hình)."));
      setOrig(""); setRev(""); setCmt(""); await reload();
    } catch (e2: any) { setErr(e2?.message ?? t(lang, "Lỗi học từ diff")); }
    setBusy("");
  }

  async function importPreset() {
    if (busy || (!presetName && !presetText.trim())) return;
    setBusy("preset"); setErr("");
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/style/import-preset`,
        presetText.trim() ? { text: presetText } : { preset_name: presetName });
      setProp({ profiles: r.profiles ?? [], rules: r.rules ?? [], canon_facts: r.canon_facts ?? [] });
      setPicked(new Set((r.rules ?? []).map((_x: any, i: number) => i)));
      setPickedC(new Set((r.canon_facts ?? []).map((_x: any, i: number) => i)));
      if (!(r.rules?.length || r.canon_facts?.length || r.profiles?.length))
        setErr(t(lang, "AI không trích được gì từ preset (kiểm tra provider)."));
    } catch (e2: any) { setErr(e2?.message ?? t(lang, "Lỗi import preset")); }
    setBusy("");
  }

  async function applyPreset() {
    if (!prop || busy) return;
    setBusy("apply"); setErr("");
    try {
      const rules = prop.rules.filter((_r, i) => picked.has(i));
      const facts = prop.canon_facts.filter((_r, i) => pickedC.has(i));
      const r: any = await postJSON(`/api/v1/projects/${projectId}/style/apply-preset`,
        { profiles: prop.profiles, rules, canon_facts: facts });
      setProp(null); setPresetText("");
      await reload();
      const a = r.applied ?? {};
      setErr(t(lang, "Đã áp: {p} hồ sơ, {r} luật, {c} dữ kiện canon.",
        { p: a.profiles ?? 0, r: a.rules ?? 0, c: a.canon_facts ?? 0 }));
    } catch (e2: any) { setErr(e2?.message ?? t(lang, "Lỗi áp preset")); }
    setBusy("");
  }

  const cand = rules.filter((r) => r.status === "candidate");
  const conf = rules.filter((r) => r.status === "confirmed");
  const dead = rules.filter((r) => r.status === "rejected" || r.status === "superseded");

  function row(r: Rule, dead = false) {
    return (
      <div key={r.id} className="list-row" style={dead ? { opacity: 0.55 } : undefined}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <span className={`pill${r.strength === "HARD" ? " warn" : ""}`}>{strengthLabel(r.strength, lang)}</span>
          <span className="pill">{r.preference_type === "avoid" ? t(lang, "Tránh") : t(lang, "Ưu tiên")}</span>
          {r.attribute && <span className="pill">{r.attribute}</span>}
          {r.scope_type && <span className="pill">{scopeLabel(r.scope_type, lang)}</span>}
          <small className="subtle">{t(lang, "nguồn: {s}", { s: SRC_LABEL[r.source] ?? r.source })}{r.profile_name ? ` · ${r.profile_name}` : ""}</small>
        </div>
        <div style={{ marginTop: 4 }}>{r.pattern}</div>
        {r.evidence && <div className="subtle" style={{ fontStyle: "italic", marginTop: 2 }}>“{r.evidence}”</div>}
        <div style={{ display: "inline-flex", gap: 6, marginTop: 6 }}>
          {r.status === "candidate" && (
            <>
              <button className="btn primary small" onClick={() => setStatus(r.id, "confirmed")}>{t(lang, "Duyệt")}</button>
              <button className="btn ghost small" onClick={() => setStatus(r.id, "rejected")}>{t(lang, "Từ chối")}</button>
            </>
          )}
          {r.status === "confirmed" && (
            <button className="btn ghost small" onClick={() => setStatus(r.id, "rejected")}>{t(lang, "Ngừng áp dụng")}</button>
          )}
          {dead && (
            <button className="btn ghost small" onClick={() => setStatus(r.id, "confirmed")}>{t(lang, "Áp lại")}</button>
          )}
          <button className="btn ghost small" onClick={() => remove(r.id)}>{t(lang, "Xoá")}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="card style-rules-panel">
      <h3>{t(lang, "AI đã học được gì — gu văn tác giả")}</h3>
      <p className="subtle">
        {t(lang, "Luật 'đang áp dụng' được tự đưa vào mọi prompt viết/sửa. Luật 'chờ duyệt' là đề xuất AI rút ra từ cách bạn sửa — chỉ có hiệu lực sau khi bạn bấm Duyệt. {c} đang áp, {w} chờ duyệt.",
          { c: counts.confirmed ?? 0, w: counts.candidate ?? 0 })}
      </p>

      {cand.length > 0 && (
        <>
          <h4 style={{ margin: "10px 0 4px" }}>{t(lang, "Chờ duyệt ({n})", { n: cand.length })}</h4>
          {cand.map((r) => row(r))}
        </>
      )}
      <h4 style={{ margin: "10px 0 4px" }}>{t(lang, "Đang áp dụng ({n})", { n: conf.length })}</h4>
      {conf.map((r) => row(r))}
      {!conf.length && <p className="subtle">{t(lang, "Chưa có luật nào — dạy AI bên dưới hoặc import preset.")}</p>}
      {dead.length > 0 && (
        <details style={{ marginTop: 10 }}>
          <summary className="subtle">{t(lang, "Đã từ chối/thay thế ({n})", { n: dead.length })}</summary>
          {dead.map((r) => row(r, true))}
        </details>
      )}

      <div className="dash-head" style={{ marginTop: 18 }}>
        <div><div className="eyebrow">{t(lang, "Dạy AI")}</div><h1 style={{ fontSize: 18 }}>{t(lang, "Dạy gu mới")}</h1></div>
      </div>
      <form onSubmit={teach} className="style-teach-form">
        <input className="input" aria-label={t(lang,"Dạy gu mới")} value={ins}
          onChange={(e) => setIns(e.target.value)}
          placeholder={t(lang, "VD: Đoạn trần thuật gộp 3-8 câu một đoạn, không một câu một dòng")} />
        <select className="input" aria-label={t(lang,"Mức độ áp dụng")} value={insStr} onChange={(e) => setInsStr(e.target.value)}>
          <option value="HARD">{t(lang, "BẮT BUỘC")}</option>
          <option value="PREFERRED">{t(lang, "Ưu tiên")}</option>
          <option value="AVOID">{t(lang, "Nên tránh")}</option>
          <option value="OPEN">{t(lang, "Tự do")}</option>
        </select>
        <button className="btn primary" disabled={!!busy || !ins.trim()}>{t(lang, "Lưu luật")}</button>
      </form>

      <details style={{ marginTop: 12 }}>
        <summary>{t(lang, "Học từ bản sửa — dán đoạn gốc + đoạn bạn đã sửa, AI rút luật chờ duyệt")}</summary>
        <form onSubmit={learnDiff} style={{ display: "grid", gap: 8, marginTop: 8 }}>
          <div className="style-diff-fields">
            <textarea className="input" rows={5} value={orig} onChange={(e) => setOrig(e.target.value)}
              placeholder={t(lang, "Đoạn gốc (bản AI / bản cũ)")} />
            <textarea className="input" rows={5} value={rev} onChange={(e) => setRev(e.target.value)}
              placeholder={t(lang, "Đoạn bạn đã sửa")} />
          </div>
          <input className="input" value={cmt} onChange={(e) => setCmt(e.target.value)}
            placeholder={t(lang, "Lời giải thích (tuỳ chọn): 'câu nào cũng chửi nghe nhạt'")} />
          <div>
            <button className="btn" disabled={!!busy || !orig.trim() || !rev.trim()}>
              {busy === "diff" ? t(lang, "AI đang đọc diff…") : t(lang, "Rút luật (chờ duyệt)")}
            </button>
          </div>
        </form>
      </details>

      <details style={{ marginTop: 12 }}>
        <summary>{t(lang, "Import preset — style-guide có sẵn hoặc dán preset truyện khác")}</summary>
        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
          {presets.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <select className="input" value={presetName} onChange={(e) => setPresetName(e.target.value)} style={{ minWidth: 220 }}>
                <option value="">{t(lang, "Chọn preset đóng gói…")}</option>
                {presets.map((p) => <option key={p.name} value={p.name}>{p.title}</option>)}
              </select>
              <span className="subtle">{t(lang, "hoặc")}</span>
            </div>
          )}
          <textarea className="input" rows={5} value={presetText} onChange={(e) => setPresetText(e.target.value)}
            placeholder={t(lang, "Dán preset / style-guide của truyện (markdown tuỳ ý) — AI sẽ trích ra hồ sơ + luật + dữ kiện canon để bạn duyệt")} />
          <div>
            <button className="btn" onClick={importPreset} disabled={!!busy || (!presetName && !presetText.trim())}>
              {busy === "preset" ? t(lang, "AI đang trích preset…") : t(lang, "Trích đề xuất")}
            </button>
          </div>
        </div>
      </details>

      {err && <p className="subtle" style={{ color: "var(--amber, #b8860b)" }}>{err}</p>}

      {prop && createPortal(
        <div className="project-modal open" role="dialog" aria-modal="true" onClick={() => setProp(null)}>
          <div className="project-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 780 }}>
            <div className="project-dialog-head">
              <div><h2>{t(lang, "Đề xuất từ preset — chọn phần áp dụng")}</h2>
              <p>{t(lang, "Luật vào 'đang áp dụng', dữ kiện vào Canon (CANON) — cả hai đều chỉ ghi phần bạn tick.")}</p></div>
              <button className="project-close" onClick={() => setProp(null)}>×</button>
            </div>
            <div className="project-content" style={{ maxHeight: "60vh", overflow: "auto" }}>
              {prop.profiles.length > 0 && (
                <>
                  <h4>{t(lang, "Hồ sơ giọng ({n})", { n: prop.profiles.length })}</h4>
                  {prop.profiles.map((p, i) => (
                    <div key={i} className="list-row">
                      <b>{p.name}</b>
                      <div className="subtle" style={{ whiteSpace: "pre-wrap" }}>{(p.instructions ?? "").slice(0, 300)}</div>
                    </div>
                  ))}
                </>
              )}
              {prop.rules.length > 0 && (
                <>
                  <h4 style={{ marginTop: 10 }}>{t(lang, "Luật văn phong ({n})", { n: prop.rules.length })}</h4>
                  {prop.rules.map((r, i) => (
                    <label key={i} className="list-row" style={{ display: "flex", gap: 8, cursor: "pointer" }}>
                      <input type="checkbox" checked={picked.has(i)}
                        onChange={(e) => { const s = new Set(picked); e.target.checked ? s.add(i) : s.delete(i); setPicked(s); }} />
                      <span>
                        <span className="pill">{strengthLabel(r.strength ?? "PREFERRED", lang)}</span>{" "}
                        {r.preference_type === "avoid" && <span className="pill">{t(lang, "Tránh")}</span>}{" "}
                        {r.pattern}
                        {r.attribute && <div className="subtle">{r.attribute}</div>}
                      </span>
                    </label>
                  ))}
                </>
              )}
              {prop.canon_facts.length > 0 && (
                <>
                  <h4 style={{ marginTop: 10 }}>{t(lang, "Dữ kiện canon ({n})", { n: prop.canon_facts.length })}</h4>
                  {prop.canon_facts.map((f, i) => (
                    <label key={i} className="list-row" style={{ display: "flex", gap: 8, cursor: "pointer" }}>
                      <input type="checkbox" checked={pickedC.has(i)}
                        onChange={(e) => { const s = new Set(pickedC); e.target.checked ? s.add(i) : s.delete(i); setPickedC(s); }} />
                      <span><b>{f.predicate}</b> — {f.value_text}</span>
                    </label>
                  ))}
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 8, padding: "12px 0 0" }}>
              <button className="btn primary" onClick={applyPreset} disabled={!!busy}>
                {busy === "apply" ? t(lang, "Đang áp…") : t(lang, "Áp phần đã chọn")}
              </button>
              <button className="btn ghost" onClick={() => setProp(null)}>{t(lang, "Đóng")}</button>
            </div>
          </div>
        </div>, document.body)}
    </div>
  );
}
