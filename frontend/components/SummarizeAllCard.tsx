"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getJSON, postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { scopeLabel } from "../lib/labels";
import { toast } from "../lib/toast";

type PendingItem = { scope_type: string; scope_id: string; label: string; reason: string };
type Coverage = { levels: Record<string, any>; pending: PendingItem[]; pending_count: number };

const SCOPE_ORDER = ["scene", "chapter", "arc", "volume", "story"];

export default function SummarizeAllCard({ projectId }: { projectId: string }) {
  const lang = useLang();
  const router = useRouter();
  const [cov, setCov] = useState<Coverage | null>(null);
  const [running, setRunning] = useState(false);
  const [idx, setIdx] = useState(0);
  const [cur, setCur] = useState("");
  const [fails, setFails] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);

  async function load() {
    try { setCov(await getJSON(`/api/v1/projects/${projectId}/summaries/coverage`)); }
    catch { setCov(null); }
  }
  useEffect(() => { load(); }, [projectId]);

  useEffect(() => {
    if (!running) return;
    const iv = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(iv);
  }, [running]);

  async function run() {
    const items = cov?.pending ?? [];
    if (!items.length) return;
    setRunning(true); setIdx(0); setFails(0); setElapsed(0);
    cancelledRef.current = false;
    let done = 0, failed = 0;
    for (const item of items) {
      if (cancelledRef.current) break;
      setCur(item.label);
      const ac = new AbortController();
      abortRef.current = ac;
      try {
        await postJSON(`/api/v1/projects/${projectId}/summaries/generate`,
          { scope_type: item.scope_type, scope_id: item.scope_id }, ac.signal);
        done++;
      } catch (e: any) {
        if (e?.name === "AbortError") break;
        failed++; setFails(failed);
      }
      setIdx(done + failed);
    }
    setRunning(false); abortRef.current = null;
    if (cancelledRef.current) {
      toast(t(lang, "Đã dừng — {n} mục đã tóm tắt", { n: done }));
    } else if (failed) {
      toast(t(lang, "Xong {n}/{t} mục — {f} lỗi", { n: done, t: items.length, f: failed }));
    } else {
      toast(t(lang, "Đã tóm tắt {n} mục", { n: done }));
    }
    await load();
    router.refresh();
  }

  function cancel() {
    cancelledRef.current = true;
    abortRef.current?.abort();
  }

  const pending = cov?.pending_count ?? 0;
  const total = cov?.pending.length ?? 0;
  return (
    <section className="card">
      <h3>{t(lang, "Tóm tắt toàn bộ")}</h3>
      {!running && pending > 0 && (
        <>
          <p className="subtle" style={{ fontSize: 13, marginTop: -6 }}>
            {t(lang, "{n} phạm vi còn thiếu hoặc đã cũ — chạy từ cảnh lên toàn truyện.", { n: pending })}
          </p>
          <button className="btn primary" onClick={run}>
            {t(lang, "Tóm tắt {n} mục", { n: pending })}
          </button>
        </>
      )}
      {!running && pending === 0 && cov && (
        <p className="subtle" style={{ fontSize: 13, marginTop: -6 }}>
          {t(lang, "Mọi phạm vi đã có tóm tắt mới.")}
        </p>
      )}
      {running && (
        <div className="sum-progress">
          <div className="bar"><i style={{ width: `${total ? (idx / total) * 100 : 0}%` }} /></div>
          <div className="subtle" style={{ fontSize: 13, marginTop: 6 }}>
            {t(lang, "Đang tóm tắt {i}/{n}: {label}", { i: Math.min(idx + 1, total), n: total, label: cur })}
            {" · "}{elapsed}s{fails ? ` · ${t(lang, "{n} lỗi", { n: fails })}` : ""}
          </div>
          <button className="btn ghost small" onClick={cancel} style={{ marginTop: 8 }}>
            {t(lang, "Dừng")}
          </button>
        </div>
      )}
      {cov && (
        <div className="sum-levels">
          {SCOPE_ORDER.map((st) => {
            const lv = cov.levels?.[st];
            if (!lv || !lv.total) return null;
            return (
              <span key={st} className="pill" title={t(lang, "mới/cần tóm tắt")}>
                {scopeLabel(st, lang)} {lv.fresh}/{lv.total - lv.skipped}
              </span>
            );
          })}
        </div>
      )}
    </section>
  );
}
