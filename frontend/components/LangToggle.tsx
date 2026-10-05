"use client";
import { useRouter } from "next/navigation";
import { LANG_COOKIE } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export default function LangToggle() {
  const router = useRouter();
  const lang = useLang();
  function toggle() {
    const next = lang === "en" ? "vi" : "en";
    document.cookie = `${LANG_COOKIE}=${next};path=/;max-age=31536000;samesite=lax`;
    window.dispatchEvent(new Event("writer:lang"));
    router.refresh();
  }
  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      title={lang === "en" ? "Chuyển sang tiếng Việt" : "Switch to English"}
      aria-label="Language"
      style={{ width: "auto", padding: "0 9px", fontSize: 11, fontWeight: 700, letterSpacing: ".04em" }}
    >
      {lang === "en" ? "VI" : "EN"}
    </button>
  );
}
