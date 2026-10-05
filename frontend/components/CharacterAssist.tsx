"use client";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { patchJSON, postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { statusLabel, roleLabel } from "../lib/labels";
import { useLang } from "../lib/use-lang";
import { toast } from "../lib/toast";

const ROLES = ["protagonist", "deuteragonist", "antagonist", "supporting", "minor"];
const STATUSES = ["active", "inactive", "dead", "exited", "retired"];

type Draft = {
  name: string; role: string; summary: string; voice_notes: string;
  status: string; aliases: string;
};

export default function CharacterAssist({ projectId }: { projectId: string }) {
  const lang = useLang();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [hint, setHint] = useState("");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [existingId, setExistingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!busy) return;
    const iv = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(iv);
  }, [busy]);

  async function scan() {
    if (!name.trim() || busy) return;
    setBusy(true); setElapsed(0); setDraft(null);
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const r: any = await postJSON(`/api/v1/projects/${projectId}/characters/assist`,
        { name: name.trim(), hint: hint.trim() || null }, ac.signal);
      const d = r.draft ?? {};
      setExistingId(r.existing_id ?? null);
      setDraft({
        name: d.name ?? name.trim(),
        role: ROLES.includes(d.role) ? d.role : "supporting",
        summary: d.summary ?? "",
        voice_notes: d.voice_notes ?? "",
        status: STATUSES.includes(d.status) ? d.status : "active",
        aliases: (d.aliases ?? []).join(", "),
      });
      if (!r.excerpts_used) toast(t(lang, "Không thấy tên này trong bản thảo — nháp chỉ dựa trên gợi ý"));
    } catch (e: any) {
      if (e?.name !== "AbortError") toast(e?.message ?? t(lang, "Lỗi gọi AI"));
    } finally { setBusy(false); abortRef.current = null; }
  }

  async function save() {
    if (!draft || saving) return;
    setSaving(true);
    try {
      const body = {
        name: draft.name.trim() || name.trim(),
        role: draft.role || null,
        summary: draft.summary.trim() || null,
        voice_notes: draft.voice_notes.trim() || null,
      };
      let cid = existingId;
      if (cid) {
        await patchJSON(`/api/v1/projects/${projectId}/characters/${cid}`, { ...body, status: draft.status });
      } else {
        const c: any = await postJSON(`/api/v1/projects/${projectId}/characters`, body);
        cid = c.id;
      }
      const aliases = draft.aliases.split(",").map((a) => a.trim()).filter(Boolean);
      for (const alias of aliases) {
        await postJSON(`/api/v1/projects/${projectId}/aliases`, { character_id: cid, alias });
      }
      toast(t(lang, existingId ? "Đã cập nhật nhân vật" : "Đã tạo nhân vật — nháp AI, sửa tuỳ ý"));
      router.refresh();
      setOpen(false); setDraft(null); setName(""); setHint("");
    } catch (e: any) {
      toast(e?.message ?? t(lang, "Lỗi lưu nhân vật"));
    } finally { setSaving(false); }
  }

  return (
    <>
      <button className="btn ghost" onClick={() => setOpen(true)}>
        {t(lang, "✦ AI gợi ý hồ sơ")}
      </button>
      {open && createPortal(
        <div className="project-modal open" onClick={() => !busy && !saving && setOpen(false)}>
          <div className="project-dialog" style={{ width: "min(560px, 94vw)" }} onClick={(e) => e.stopPropagation()}>
            <div className="project-dialog-head">
              <b>{t(lang, "AI gợi ý hồ sơ nhân vật")}</b>
              <button className="project-close" onClick={() => setOpen(false)} disabled={busy || saving} aria-label="Đóng">×</button>
            </div>
            <div className="project-content">
              <p className="hint">
                {t(lang, "Quét bản thảo tìm tên → AI đề xuất nháp. Bạn sửa rồi mới lưu — không tự động ghi.")}
              </p>
              <div className="row" style={{ alignItems: "flex-end" }}>
                <div style={{ flex: 1 }}>
                  <input value={name} placeholder={t(lang, "Tên nhân vật")}
                         onChange={(e) => setName(e.target.value)} disabled={busy}
                         style={{ width: "100%" }} />
                </div>
                <button className="btn primary" onClick={scan} disabled={busy || !name.trim()}>
                  {busy ? t(lang, "Đang quét… {n}s", { n: elapsed }) : t(lang, "Quét bản thảo")}
                </button>
                {busy && (
                  <button className="btn ghost small" onClick={() => abortRef.current?.abort()}>
                    {t(lang, "Hủy")}
                  </button>
                )}
              </div>
              <input value={hint} placeholder={t(lang, "Gợi ý thêm cho AI (tuỳ chọn): vai trò, quan hệ…")}
                     onChange={(e) => setHint(e.target.value)} disabled={busy}
                     style={{ width: "100%", marginTop: 8 }} />
              {draft && (
                <div style={{ marginTop: 14, display: "grid", gap: 10 }}>
                  {existingId && (
                    <p className="notice" style={{ fontSize: 12, margin: 0 }}>
                      {t(lang, "Nhân vật này đã có trong truyện — lưu sẽ cập nhật hồ sơ hiện có.")}
                    </p>
                  )}
                  <div className="field"><label>{t(lang, "Tên")}</label>
                    <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></div>
                  <div className="row">
                    <div className="field"><label>{t(lang, "Vai trò")}</label>
                      <select value={draft.role} onChange={(e) => setDraft({ ...draft, role: e.target.value })}>
                        {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r, lang)}</option>)}
                        {!ROLES.includes(draft.role) && <option value={draft.role}>{draft.role}</option>}
                      </select></div>
                    <div className="field"><label>{t(lang, "Trạng thái")}</label>
                      <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
                        {STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s, lang)}</option>)}
                      </select></div>
                  </div>
                  <div className="field"><label>{t(lang, "Tóm tắt")}</label>
                    <textarea rows={3} value={draft.summary}
                              onChange={(e) => setDraft({ ...draft, summary: e.target.value })} /></div>
                  <div className="field"><label>{t(lang, "Giọng nhân vật")}</label>
                    <textarea rows={2} value={draft.voice_notes}
                              onChange={(e) => setDraft({ ...draft, voice_notes: e.target.value })} /></div>
                  <div className="field"><label>{t(lang, "Bí danh (phẩy)")}</label>
                    <input value={draft.aliases}
                           onChange={(e) => setDraft({ ...draft, aliases: e.target.value })} /></div>
                  <div className="form-actions">
                    <button className="btn primary wide" onClick={save} disabled={saving}>
                      {saving ? t(lang, "Đang lưu…") : existingId ? t(lang, "Cập nhật nhân vật") : t(lang, "Tạo nhân vật")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>, document.body)}
    </>
  );
}
