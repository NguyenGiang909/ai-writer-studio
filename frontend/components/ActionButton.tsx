"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { postJSON, patchJSON, delJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export default function ActionButton({
  endpoint,
  label,
  method = "post",
  body,
  confirm,
  gold = false,
}: {
  endpoint: string;
  label: string;
  method?: "post" | "patch" | "delete";
  body?: unknown;
  confirm?: string;
  gold?: boolean;
}) {
  const router = useRouter();
  const lang = useLang();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (confirm && !window.confirm(confirm)) return;
    setBusy(true);
    setError(null);
    try {
      if (method === "post") await postJSON(endpoint, body);
      else if (method === "patch") await patchJSON(endpoint, body ?? {});
      else await delJSON(endpoint);
      router.refresh();
    } catch (err: any) {
      setError(err?.message ?? t(lang, "Lỗi"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <button onClick={run} disabled={busy} className={`btn${gold ? " gold" : ""}`} style={{ padding: "4px 12px", fontSize: 12 }}>
        {busy ? "…" : label}
      </button>
      {error && <span className="err">{error}</span>}
    </span>
  );
}
