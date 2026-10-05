"use client";
// Client-side language state. Server components use lib/lang-server.ts instead.

import { useEffect, useState } from "react";
import { LANG_COOKIE, type Lang } from "./i18n";

export function getLangClient(): Lang {
  if (typeof document === "undefined") return "vi";
  return document.cookie.includes(`${LANG_COOKIE}=en`) ? "en" : "vi";
}

export function useLang(): Lang {
  const [lang, setLang] = useState<Lang>("vi");
  useEffect(() => {
    setLang(getLangClient());
    const on = () => setLang(getLangClient());
    window.addEventListener("writer:lang", on);
    return () => window.removeEventListener("writer:lang", on);
  }, []);
  return lang;
}
