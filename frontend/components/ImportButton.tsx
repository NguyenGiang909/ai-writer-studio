"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { toast } from "../lib/toast";

export default function ImportButton({ className = "" }: { className?: string }) {
  const lang = useLang();
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const r = await fetch(`${API}/api/v1/projects/import`, { method: "POST", body: fd });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        toast(`${t(lang, "Nhập thất bại")}: ${d.detail ?? r.status}`);
        return;
      }
      const d = await r.json();
      toast(t(lang, "Đã nhập “{name}”", { name: d.project?.name ?? "" }));
      router.push(`/projects/${d.project.id}`);
    } catch {
      toast(t(lang, "Nhập thất bại"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <input ref={input} type="file" accept=".json,application/json" hidden onChange={onFile} />
      <button className={`btn ${className}`} disabled={busy} onClick={() => input.current?.click()}
        title={t(lang, "Nhập file backup .json đã tải từ Sao lưu")}>
        {busy ? t(lang, "Đang nhập…") : t(lang, "Nhập project (.json)")}
      </button>
    </>
  );
}
