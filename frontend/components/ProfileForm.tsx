"use client";
import { useEffect, useState } from "react";
import { toast } from "../lib/toast";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

const KEY = "writer-profile-v1";

export default function ProfileForm() {
  const lang = useLang();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
      setName(saved.name || "");
      setEmail(saved.email || "");
    } catch {}
  }, []);

  function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      localStorage.setItem(KEY, JSON.stringify({ name: name.trim(), email: email.trim() }));
      toast(t(lang, "Đã lưu hồ sơ trên thiết bị này"));
    } catch {
      toast(t(lang, "Không thể lưu trên thiết bị này"));
    }
  }

  return (
    <form onSubmit={save}>
      <div className="field">
        <label htmlFor="profileName">{t(lang, "Tên hiển thị")}</label>
        <input id="profileName" maxLength={80} autoComplete="name" placeholder={t(lang, "Tên của bạn")} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="profileEmail">{t(lang, "Email liên hệ")}</label>
        <input id="profileEmail" type="email" autoComplete="email" placeholder="ban@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <button className="btn primary" type="submit">{t(lang, "Lưu hồ sơ")}</button>
    </form>
  );
}
