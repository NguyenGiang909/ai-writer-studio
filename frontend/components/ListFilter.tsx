"use client";
import { useState } from "react";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

/** Ô tìm nhanh: lọc các phần tử có [data-q] bên trong container `for` (id). */
export default function ListFilter({
  for: targetId,
  placeholder,
}: {
  for: string;
  placeholder?: string;
}) {
  const lang = useLang();
  const [q, setQ] = useState("");

  function apply(v: string) {
    setQ(v);
    const box = document.getElementById(targetId);
    if (!box) return;
    const needle = v.trim().toLowerCase();
    box.querySelectorAll<HTMLElement>("[data-q]").forEach((el) => {
      el.style.display = !needle || (el.dataset.q ?? "").toLowerCase().includes(needle) ? "" : "none";
    });
    // ẩn header nhóm khi mọi row con bị ẩn; <details> có kết quả tự mở khi lọc
    box.querySelectorAll<HTMLElement>("[data-group]").forEach((g) => {
      const anyVisible = Array.from(g.querySelectorAll<HTMLElement>("[data-q]")).some(
        (el) => el.style.display !== "none"
      );
      g.style.display = anyVisible || !needle ? "" : "none";
      if (g instanceof HTMLDetailsElement) g.open = !!needle && anyVisible;
    });
  }

  return (
    <input
      className="list-filter"
      value={q}
      onChange={(e) => apply(e.target.value)}
      placeholder={placeholder ?? t(lang, "Lọc nhanh…")}
      aria-label={t(lang, "Lọc danh sách")}
    />
  );
}
