"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { postJSON, patchJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

export type Field = {
  name: string;
  label: string;
  type?: "text" | "textarea" | "number" | "checkbox" | "select" | "json" | "scope" | "entity";
  options?: { value: string; label: string }[];
  placeholder?: string;
  required?: boolean;
  defaultValue?: string;
};

export default function PostForm({
  endpoint,
  fields,
  submitLabel,
  wide = false,
  triggerClass,
  triggerLabel,
  trigger,
  method = "post",
}: {
  endpoint: string;
  method?: "post" | "patch";
  fields: Field[];
  submitLabel?: string;
  wide?: boolean;
  triggerClass?: string;
  triggerLabel?: string;
  trigger?: React.ReactNode;
}) {
  const router = useRouter();
  const lang = useLang();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const submit = submitLabel ?? t(lang, "Thêm");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    const payload: Record<string, unknown> = {};
    try {
      for (const f of fields) {
        const raw = fd.get(f.name);
        if (f.type === "checkbox") {
          payload[f.name] = raw === "on";
        } else if (f.type === "number") {
          if (raw !== null && String(raw) !== "") payload[f.name] = Number(raw);
        } else if (f.type === "json") {
          const text = String(raw ?? "").trim();
          if (!text) continue;
          try {
            payload[f.name] = JSON.parse(text);
          } catch {
            throw new Error(t(lang, 'Trường "{label}" không phải JSON hợp lệ', { label: f.label || f.name }));
          }
        } else if (f.type === "scope") {
          const [scope_type, scope_id] = String(raw ?? "").split(":");
          if (scope_type && scope_id) {
            payload["scope_type"] = scope_type;
            payload["scope_id"] = scope_id;
          }
        } else if (f.type === "entity") {
          const [entity_type, entity_id] = String(raw ?? "").split(":");
          if (entity_type && entity_id) {
            payload["entity_type"] = entity_type;
            payload["entity_id"] = entity_id;
          }
        } else {
          const text = String(raw ?? "");
          if (text !== "") payload[f.name] = text;
        }
      }
      if (method === "patch") await patchJSON(endpoint, payload);
      else await postJSON(endpoint, payload);
      (e.target as HTMLFormElement).reset();
      setOpen(false);
      router.refresh();
    } catch (err: any) {
      setError(err?.message ?? t(lang, "Lỗi không xác định"));
    } finally {
      setBusy(false);
    }
  }

  if (!open)
    return (
      <button
        type="button"
        className={triggerClass ?? `btn${wide ? " wide" : ""}`}
        onClick={() => setOpen(true)}
      >
        {trigger ?? triggerLabel ?? `＋ ${submit}`}
      </button>
    );
  return (
    <form onSubmit={onSubmit} className="postform">
      {fields.map((f) => (
        <div key={f.name} className="field" style={{ margin: 0 }}>
          {f.label ? <label>{f.label}</label> : null}
          {f.type === "textarea" || f.type === "json" ? (
            <textarea name={f.name} placeholder={f.placeholder} required={f.required} rows={3} defaultValue={f.defaultValue} />
          ) : f.type === "select" || f.type === "scope" || f.type === "entity" ? (
            <select name={f.name} required={f.required} defaultValue={f.defaultValue ?? f.options?.[0]?.value}>
              {f.options?.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : f.type === "checkbox" ? (
            <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13 }}>
              <input name={f.name} type="checkbox" /> {f.label}
            </label>
          ) : (
            <input
              name={f.name}
              type={f.type === "number" ? "number" : "text"}
              placeholder={f.placeholder}
              required={f.required}
              defaultValue={f.defaultValue}
            />
          )}
        </div>
      ))}
      {error && <div className="err">{error}</div>}
      <div className="postform-row">
        <button type="submit" disabled={busy} className="btn primary">
          {busy ? t(lang, "Đang lưu…") : submit}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="btn">
          {t(lang, "Huỷ")}
        </button>
      </div>
    </form>
  );
}
