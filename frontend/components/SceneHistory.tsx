"use client";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { getJSON, postJSON } from "../lib/api";
import { t, type Lang } from "../lib/i18n";
import { toast } from "../lib/toast";

type Version = {
  id: string;
  scene_id: string;
  title: string | null;
  created_at: string;
  chars: number;
  excerpt: string;
};

export default function SceneHistory({
  projectId,
  sceneId,
  lang,
  onClose,
  onRestore,
}: {
  projectId: string;
  sceneId: string;
  lang: Lang;
  onClose: () => void;
  onRestore: (prose: string) => void;
}) {
  const base = `/api/v1/projects/${projectId}/scenes/${sceneId}/versions`;
  const [versions, setVersions] = useState<Version[]>([]);
  const [preview, setPreview] = useState<{ id: string; prose: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getJSON(base).then(setVersions).catch(() => setVersions([]));
  }, [sceneId]);

  async function togglePreview(id: string) {
    if (preview?.id === id) { setPreview(null); return; }
    const v = await getJSON(`${base}/${id}`).catch(() => null);
    if (v) setPreview({ id, prose: v.prose ?? "" });
  }

  async function restore(v: Version) {
    if (!confirm(t(lang, "Khôi phục bản này? Prose hiện tại sẽ được lưu thành một phiên bản mới trước khi ghi đè."))) return;
    setBusy(true);
    const s = await postJSON(`${base}/${v.id}/restore`, {}).catch(() => null);
    setBusy(false);
    if (!s) { toast(t(lang, "Khôi phục thất bại")); return; }
    toast(t(lang, "Đã khôi phục phiên bản cũ"));
    onRestore(s.prose ?? "");
    onClose();
  }

  return createPortal(
    <div className="project-modal open" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="project-dialog" style={{ width: "min(640px, 94vw)" }} onClick={(e) => e.stopPropagation()}>
        <div className="project-dialog-head">
          <div>
            <h2 style={{ fontSize: 18 }}>{t(lang, "Lịch sử phiên bản")}</h2>
            <p>{t(lang, "Mỗi phiên bản là prose cũ trước khi bị ghi đè. Khôi phục sẽ tự lưu prose hiện tại thành một phiên bản.")}</p>
          </div>
          <button className="project-close" onClick={onClose} aria-label={t(lang, "Đóng")}>×</button>
        </div>
        <div className="project-content">
        {versions.length === 0 ? (
          <p className="subtle">{t(lang, "Chưa có phiên bản nào — sửa prose lần đầu sẽ tạo mốc đầu tiên.")}</p>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {versions.map((v) => (
              <div key={v.id} className="list-row" style={{ alignItems: "flex-start" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div>
                    <b>{new Date(v.created_at).toLocaleString(lang === "vi" ? "vi-VN" : "en-US")}</b>
                    <span className="subtle"> · {v.chars} {t(lang, "ký tự")}</span>
                    {v.title && <span className="subtle"> · {v.title}</span>}
                  </div>
                  <div className="subtle" style={{ marginTop: 2 }}>{v.excerpt || t(lang, "(trống)")}{v.chars > 160 ? "…" : ""}</div>
                  {preview?.id === v.id && (
                    <pre style={{ whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto", margin: "8px 0 0",
                                  padding: 10, background: "var(--card2, var(--bg))", borderRadius: 6,
                                  fontSize: 13, fontFamily: "inherit" }}>
                      {preview.prose || t(lang, "(trống)")}
                    </pre>
                  )}
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  <button className="btn ghost small" onClick={() => togglePreview(v.id)}>
                    {preview?.id === v.id ? t(lang, "Gập") : t(lang, "Xem")}
                  </button>
                  <button className="btn small" disabled={busy} onClick={() => restore(v)}>
                    {t(lang, "Khôi phục")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </div>
    </div>,
    document.body
  );
}
