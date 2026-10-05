"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { getJSON, postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import { toast } from "../lib/toast";

type Stats = { chapters: number; words: string; threads: number };
const fmtK = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1).replace(".", ",")}k` : String(n));
const words = (s?: string | null) => (s?.trim() ? s.trim().split(/\s+/).length : 0);
const initials = (name: string) =>
  name.split(/\s+/).slice(0, 2).map((x) => x[0]).join("").toUpperCase();

export default function ProjectModal({ currentId, currentName }: { currentId: string; currentName?: string }) {
  const router = useRouter();
  const lang = useLang();
  const [open, setOpen] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [stats, setStats] = useState<Record<string, Stats>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const ps: any[] = await getJSON("/api/v1/projects");
        setProjects(ps);
        const entries = await Promise.all(
          ps.map(async (p: any) => {
            try {
              const [tree, threads] = await Promise.all([
                getJSON(`/api/v1/projects/${p.id}/manuscript`),
                getJSON(`/api/v1/projects/${p.id}/threads`).catch(() => []),
              ]);
              const w = tree.chapters.flatMap((c: any) => c.scenes).reduce((n: number, s: any) => n + words(s.prose), 0);
              return [p.id, { chapters: tree.chapters.length, words: fmtK(w), threads: threads.filter((t: any) => t.status === "OPEN").length }];
            } catch {
              return [p.id, { chapters: 0, words: "0", threads: 0 }];
            }
          })
        );
        setStats(Object.fromEntries(entries));
      } catch {
        toast(t(lang, "Không tải được danh sách dự án"));
      }
    })();
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    if (open) {
      document.addEventListener("keydown", onKey);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const name = String(fd.get("name") ?? "").trim();
    if (!name) return;
    const genre = String(fd.get("genre") ?? "").trim();
    const desc = String(fd.get("description") ?? "").trim();
    setBusy(true);
    try {
      const p = await postJSON("/api/v1/projects", {
        name,
        description: [genre && t(lang, "Thể loại: {g}", { g: genre }), desc].filter(Boolean).join(" — ") || null,
      });
      toast(t(lang, "Đã tạo dự án {name}", { name }));
      setOpen(false);
      setShowForm(false);
      router.push(`/projects/${p.id}`);
    } catch (err: any) {
      toast(err?.message ?? t(lang, "Không tạo được dự án"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        className="project-switch"
        aria-label={t(lang, "Mở danh sách dự án; dự án hiện tại: {name}", { name: currentName ?? "" })}
        onClick={() => setOpen(true)}
      >
        <span>{t(lang, "Dự án /")}</span>
        <b>{currentName ?? "…"}</b>
        <span className="chev">⌄</span>
      </button>
      {open && createPortal(
        <div className="project-modal open" role="dialog" aria-modal="true" onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
          <div className="project-dialog">
            <div className="project-dialog-head">
              <div>
                <h2>{t(lang, "Dự án của bạn")}</h2>
                <p>{t(lang, "Chọn dự án để tiếp tục viết hoặc tạo một câu chuyện mới.")}</p>
              </div>
              <button className="btn primary" onClick={() => setShowForm(true)}>
                {t(lang, "＋ Thêm dự án")}
              </button>
              <button className="project-close" aria-label={t(lang, "Đóng")} onClick={() => setOpen(false)}>
                ×
              </button>
            </div>
            <div className="project-content">
              {showForm && (
                <form className="new-project-form open" onSubmit={create}>
                  <div className="form-grid">
                    <div className="field">
                      <label>{t(lang, "Tên dự án")}</label>
                      <input name="name" required placeholder={t(lang, "Ví dụ: Mùa Trăng Cuối")} autoFocus />
                    </div>
                    <div className="field">
                      <label>{t(lang, "Thể loại")}</label>
                      <input name="genre" placeholder={t(lang, "Kỳ ảo, trinh thám…")} />
                    </div>
                  </div>
                  <div className="field">
                    <label>{t(lang, "Mô tả ngắn")}</label>
                    <textarea name="description" rows={2} placeholder={t(lang, "Ý tưởng trung tâm của câu chuyện")} />
                  </div>
                  <div className="form-actions">
                    <button type="button" className="btn" onClick={() => setShowForm(false)}>
                      {t(lang, "Hủy")}
                    </button>
                    <button type="submit" className="btn primary" disabled={busy}>
                      {busy ? t(lang, "Đang tạo…") : t(lang, "Tạo dự án")}
                    </button>
                  </div>
                </form>
              )}
              <div className="project-grid">
                {projects.map((p) => (
                  <article key={p.id} className={`project-card${p.id === currentId ? " current" : ""}`}>
                    <div className="project-card-top">
                      <div className="project-icon">{initials(p.name)}</div>
                      <div>
                        <h3>{p.name}</h3>
                        <p>{p.description || t(lang, "Chưa có mô tả")}</p>
                      </div>
                      {p.id === currentId && (
                        <span className="pill" style={{ marginLeft: "auto" }}>
                          {t(lang, "Hiện tại")}
                        </span>
                      )}
                    </div>
                    <div className="project-stats">
                      <div>
                        <b>{stats[p.id]?.chapters ?? "…"}</b>
                        <span>{t(lang, "Chương")}</span>
                      </div>
                      <div>
                        <b>{stats[p.id]?.words ?? "…"}</b>
                        <span>{t(lang, "Từ")}</span>
                      </div>
                      <div>
                        <b>{stats[p.id]?.threads ?? "…"}</b>
                        <span>{t(lang, "Hố mở")}</span>
                      </div>
                    </div>
                    <div className="project-card-actions">
                      <button
                        className={`btn${p.id === currentId ? " primary" : ""}`}
                        onClick={() => {
                          setOpen(false);
                          if (p.id !== currentId) router.push(`/projects/${p.id}`);
                          else toast(t(lang, "Đây là dự án đang mở"));
                        }}
                      >
                        {p.id === currentId ? t(lang, "Tiếp tục viết") : t(lang, "Mở dự án")}
                      </button>
                    </div>
                  </article>
                ))}
                <button className="project-card empty-project" onClick={() => setShowForm(true)}>
                  <div className="project-icon">＋</div>
                  <h3>{t(lang, "Tạo dự án mới")}</h3>
                  <p>{t(lang, "Bắt đầu từ ý tưởng hoặc nhập bản thảo có sẵn.")}</p>
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
