"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { patchJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export const TIER_LABEL: Record<string, string> = {
  low: "Yếu",
  standard: "Thường",
  strong: "Mạnh",
};

export default function TierSelect({ id, tier, override }: {
  id: string;
  tier: string;            // tier hiệu lực (đã resolve auto)
  override: string | null; // tier user tự đặt — null nghĩa auto
}) {
  const router = useRouter();
  const lang = useLang();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function change(v: string) {
    setBusy(true); setError(null);
    try {
      await patchJSON(`/api/v1/account/credentials/${id}`, { tier: v === "auto" ? null : v });
      router.refresh();
    } catch (e: any) {
      setError(e?.message ?? t(lang, "Lỗi"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <select
        className="input"
        style={{ padding: "3px 8px", fontSize: 12, width: "auto" }}
        disabled={busy}
        value={override ?? "auto"}
        onChange={(e) => change(e.target.value)}
        title={t(lang, "Năng lực API: ảnh hưởng cách app chia nhỏ request — không phải chất lượng văn")}
      >
        <option value="auto">{t(lang, "Tự động")} ({t(lang, TIER_LABEL[tier] ?? tier)})</option>
        <option value="low">{t(lang, "Yếu")}</option>
        <option value="standard">{t(lang, "Thường")}</option>
        <option value="strong">{t(lang, "Mạnh")}</option>
      </select>
      {error && <span className="err">{error}</span>}
    </span>
  );
}
