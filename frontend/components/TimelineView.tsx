"use client";
import { useState, type ReactNode } from "react";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

type Mode = "dual" | "time" | "order";

export default function TimelineView({
  dual,
  chrono,
  narrative,
}: {
  dual: ReactNode;
  chrono: ReactNode;
  narrative: ReactNode;
}) {
  const lang = useLang();
  const [mode, setMode] = useState<Mode>("dual");
  const btn = (m: Mode, label: string) => (
    <button key={m} className={mode === m ? "active" : ""} onClick={() => setMode(m)}>
      {label}
    </button>
  );
  return (
    <>
      <div className="mode" style={{ maxWidth: 460, marginBottom: 14 }}>
        {btn("dual", t(lang, "Hai trục"))}
        {btn("time", t(lang, "Theo thời gian truyện"))}
        {btn("order", t(lang, "Theo thứ tự kể"))}
      </div>
      <div id="tl-events">
        {mode === "dual" && dual}
        {mode === "time" && chrono}
        {mode === "order" && narrative}
      </div>
    </>
  );
}
