"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { kindLabel, severityLabel, payloadText } from "../lib/labels";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

const storeKey = (pid: string) => `writer:dismissed:${pid}`;
const fp = (i: any) => `${i.code}:${JSON.stringify(i.evidence ?? {})}`;

function issueLinks(projectId: string, ev: any) {
  if (!ev) return [];
  const base = `/projects/${projectId}`;
  const out: { href: string; label: string }[] = [];
  if (ev.scene_id) out.push({ href: `${base}?scene=${ev.scene_id}`, label: "→ Mở cảnh" });
  if (ev.thread_id) out.push({ href: `${base}/threads`, label: "→ Hố" });
  if (ev.character_id || ev.knower_id || ev.owner_id)
    out.push({ href: `${base}/characters`, label: "→ Nhân vật" });
  if (ev.ability_id) out.push({ href: `${base}/abilities`, label: "→ Năng lực" });
  if (ev.item_id || ev.location_id) out.push({ href: `${base}/world`, label: "→ Thế giới" });
  if (ev.relationship_id) out.push({ href: `${base}/characters`, label: "→ Quan hệ" });
  if (ev.fact_id) out.push({ href: `${base}/truth`, label: "→ Canon" });
  return out;
}

export default function ReviewIssues({
  issues,
  projectId,
}: {
  issues: any[];
  projectId: string;
}) {
  const lang = useLang();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [showHidden, setShowHidden] = useState(false);
  const [fq, setFq] = useState("");

  useEffect(() => {
    try {
      setDismissed(new Set(JSON.parse(localStorage.getItem(storeKey(projectId)) ?? "[]")));
    } catch {}
  }, [projectId]);

  function dismiss(id: string, on: boolean) {
    setDismissed((s) => {
      const n = new Set(s);
      on ? n.add(id) : n.delete(id);
      try { localStorage.setItem(storeKey(projectId), JSON.stringify([...n])); } catch {}
      return n;
    });
  }

  const rows = issues.map((i: any) => ({ ...i, _fp: fp(i) }));
  const needle = fq.trim().toLowerCase();
  const filtered = needle
    ? rows.filter((r) => `${kindLabel(r.code, lang)} ${r.message} ${payloadText(r.evidence, lang)}`.toLowerCase().includes(needle))
    : rows;
  const visible = filtered.filter((r) => showHidden || !dismissed.has(r._fp));
  const hiddenCount = rows.length - rows.filter((r) => !dismissed.has(r._fp)).length;

  return (
    <>
      {rows.length > 10 && (
        <input className="list-filter" style={{ width: "100%", marginBottom: 8 }}
          value={fq} onChange={(e) => setFq(e.target.value)}
          placeholder={t(lang, "Lọc điểm cần xem…")} aria-label={t(lang, "Lọc điểm cần xem")} />
      )}
      {hiddenCount > 0 && (
        <button className="btn ghost small" style={{ marginBottom: 8 }} onClick={() => setShowHidden((v) => !v)}>
          {showHidden ? t(lang, "Ẩn lại {n} mục đã xem", { n: hiddenCount }) : t(lang, "Hiện {n} mục đã đánh dấu đã xem", { n: hiddenCount })}
        </button>
      )}
      <div className="review-list">
        {visible.map((i: any) => {
          const sev = severityLabel(i.severity, lang);
          const gone = dismissed.has(i._fp);
          return (
            <div key={i._fp} className={`review-item${gone ? " dismissed" : ""}`}>
              <header>
                <span className={sev.warn ? "danger" : ""}>{kindLabel(i.code, lang)}</span>
                <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  <span className={`pill${sev.warn ? " warn" : ""}`}>{sev.label}</span>
                  <button className="btn ghost small" onClick={() => dismiss(i._fp, !gone)}>
                    {gone ? t(lang, "Bỏ ẩn") : t(lang, "Đã xem")}
                  </button>
                </span>
              </header>
              <p>{i.message}</p>
              {i.evidence && <p className="subtle">{payloadText(i.evidence, lang)}</p>}
              {issueLinks(projectId, i.evidence).length > 0 && (
                <div className="issue-actions">
                  {issueLinks(projectId, i.evidence).map((l) => (
                    <Link key={l.href + l.label} href={l.href} className="issue-link">{t(lang, l.label)}</Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {!visible.length && (
          <p className="subtle">
            {issues.length ? t(lang, "Tất cả điểm đã được đánh dấu đã xem.") : t(lang, "Không phát hiện vấn đề liên tục nào.")}
          </p>
        )}
      </div>
    </>
  );
}
