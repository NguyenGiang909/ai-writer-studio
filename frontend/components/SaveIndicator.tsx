"use client";
import { useEffect, useState } from "react";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export default function SaveIndicator() {
  const lang = useLang();
  const [time, setTime] = useState<string | null>(null);

  useEffect(() => {
    const stamp = () =>
      setTime(new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }));
    stamp();
    const onSaved = () => stamp();
    window.addEventListener("writer:saved", onSaved);
    return () => window.removeEventListener("writer:saved", onSaved);
  }, []);

  return (
    <div className="save">
      <i></i> {t(lang, "Đã lưu")} {time ?? "--:--"}
    </div>
  );
}
