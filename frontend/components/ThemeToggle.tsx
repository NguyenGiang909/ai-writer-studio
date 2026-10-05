"use client";
import { useEffect, useState } from "react";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export default function ThemeToggle() {
  const lang = useLang();
  const [dark, setDark] = useState(false);
  useEffect(() => {
    setDark(document.documentElement.dataset.theme === "dark");
  }, []);
  function toggle() {
    const next = !dark;
    setDark(next);
    if (next) document.documentElement.dataset.theme = "dark";
    else delete document.documentElement.dataset.theme;
    try {
      localStorage.setItem("writer-theme", next ? "dark" : "light");
    } catch {}
  }
  return (
    <button className="theme-toggle" onClick={toggle} title={dark ? t(lang, "Light Mode") : t(lang, "Dark Mode")} aria-label={dark ? t(lang, "Bật Light Mode") : t(lang, "Bật Dark Mode")}>
      {dark ? "☀" : "◐"}
    </button>
  );
}
