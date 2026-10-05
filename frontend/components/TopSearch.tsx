"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export default function TopSearch({ projectId }: { projectId: string }) {
  const lang = useLang();
  const router = useRouter();
  const sp = useSearchParams();
  const [q, setQ] = useState(sp.get("q") ?? "");

  function go() {
    const v = q.trim();
    if (v) router.push(`/projects/${projectId}/search?q=${encodeURIComponent(v)}`);
  }

  return (
    <div className="top-search">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") go(); }}
        placeholder={t(lang, "Tìm chương, nhân vật, chi tiết…")}
        aria-label={t(lang, "Tìm kiếm")}
      />
    </div>
  );
}
