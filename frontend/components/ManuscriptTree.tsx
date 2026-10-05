"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import PostForm from "./PostForm";
import ChapterOutlineModal from "./ChapterOutlineModal";
import { sceneTypeLabel } from "../lib/labels";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";

const STATUS_DOT: Record<string, string> = { done: "done", draft: "draft", writing: "draft" };
const STATUS_LABEL: Record<string, string> = {
  done: "✓ Hoàn tất",
  draft: "● Bản nháp",
  writing: "● Bản nháp",
};
const words = (s?: string | null) => (s?.trim() ? s.trim().split(/\s+/).length : 0);
const fmtK = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1).replace(".", ",")}k` : String(n));

function chapterName(c: any) {
  const m = /^Chương\s*(\d+)[.:]?\s*(.*)$/i.exec((c.title ?? "").trim());
  if (m) return `${m[1]} · ${m[2] || c.title}`;
  return `${c.order_index} · ${c.title}`;
}

type Props = {
  projectId: string;
  volumes: any[];
  arcs: any[];
  chapters: any[];
  characters: { id: string; name: string }[];
};

export default function ManuscriptTree({ projectId, volumes, arcs, chapters, characters }: Props) {
  const lang = useLang();
  const search = useSearchParams();
  const selected = search.get("scene");
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());
  const [closedGroups, setClosedGroups] = useState<Set<string>>(new Set());
  const [q, setQ] = useState("");
  const [outlineCh, setOutlineCh] = useState<any | null>(null);

  const toggleGroup = (id: string) =>
    setClosedGroups((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const needle = q.trim().toLowerCase();
  const matchChapter = (c: any) =>
    !needle || (c.title ?? "").toLowerCase().includes(needle)
      || c.scenes.some((s: any) => (s.title ?? "").toLowerCase().includes(needle));

  useEffect(() => {
    function onToggle(e: Event) {
      const id = (e as CustomEvent<string>).detail;
      setOpenIds((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
    }
    window.addEventListener("writer:toggle-chapter", onToggle);
    return () => window.removeEventListener("writer:toggle-chapter", onToggle);
  }, []);

  const povName = (c: any) =>
    characters.find((ch) => ch.id === c.scenes.find((s: any) => s.pov_character_id)?.pov_character_id)?.name;

  const arcIds = new Set(arcs.map((a) => a.id));
  const volIds = new Set(volumes.map((v) => v.id));
  const arcsByVolume: Record<string, any[]> = {};
  const looseArcs: any[] = [];
  for (const a of arcs) {
    if (a.volume_id && volIds.has(a.volume_id)) (arcsByVolume[a.volume_id] ??= []).push(a);
    else looseArcs.push(a);
  }
  const chaptersByArc: Record<string, any[]> = {};
  const chaptersByVolume: Record<string, any[]> = {};
  const looseChapters: any[] = [];
  for (const c of chapters) {
    if (c.arc_id && arcIds.has(c.arc_id)) (chaptersByArc[c.arc_id] ??= []).push(c);
    else if (c.volume_id && volIds.has(c.volume_id)) (chaptersByVolume[c.volume_id] ??= []).push(c);
    else looseChapters.push(c);
  }
  const totalWords = chapters.reduce(
    (n: number, c: any) => n + c.scenes.reduce((m: number, s: any) => m + words(s.prose), 0),
    0
  );

  const chapterRow = (c: any) => {
    if (!matchChapter(c)) return null;
    const dot = STATUS_DOT[c.status] ?? "plan";
    const label = t(lang, STATUS_LABEL[c.status] ?? "○ Kế hoạch");
    const w = c.scenes.reduce((n: number, s: any) => n + words(s.prose), 0);
    const pov = povName(c);
    const active = c.scenes.some((s: any) => s.id === selected);
    const open = active || openIds.has(c.id);
    return (
      <div
        key={c.id}
        className={`chapter-row${active ? " active" : ""}`}
        draggable
        data-chapter-id={c.id}
        data-first-scene={c.scenes[0]?.id ?? ""}
      >
        <span className="drag-handle">⋮⋮</span>
        <div className="chapter-main">
          <button
            type="button"
            className="chapter-toggle"
            aria-expanded={open}
            onClick={(e) => {
              e.stopPropagation();
              setOpenIds((s) => { const n = new Set(s); n.has(c.id) ? n.delete(c.id) : n.add(c.id); return n; });
            }}
          >{open ? "▾" : "▸"}</button>
          <i className={`status-dot ${dot}`}></i>
          <span className="chapter-name">{chapterName(c)}</span>
          <span className="chapter-count">{w ? fmtK(w) : "—"}</span>
        </div>
        <div className="chapter-meta">
          <span>{pov ? `POV ${pov}` : t(lang, "Chưa chọn POV")}</span>
          <span>{c.scenes.length} {t(lang, "cảnh")}</span>
          <span>{label}</span>
          <button
            type="button"
            className="chapter-ai"
            title={t(lang, "AI gợi ý cảnh cho chương này")}
            onClick={(e) => { e.stopPropagation(); setOutlineCh(c); }}
          >✦</button>
        </div>
        {open && (
          <div className="scene-list">
            {c.scenes.map((s: any, i: number) => (
              <Link
                key={s.id}
                href={`/projects/${projectId}?scene=${s.id}`}
                className={`scene-row${selected === s.id ? " active" : ""}`}
                style={{ textDecoration: "none" }}
              >
                <span>{i + 1}</span>
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.title || t(lang, "Cảnh không tên")}
                </span>
                <small>{s.scene_type ? sceneTypeLabel(s.scene_type, lang) : words(s.prose) ? t(lang, "Đã viết") : t(lang, "Chưa viết")}</small>
              </Link>
            ))}
            <PostForm
              endpoint={`/api/v1/projects/${projectId}/chapters/${c.id}/scenes`}
              submitLabel={t(lang, "Cảnh")}
              triggerLabel={t(lang, "＋ Cảnh")}
              triggerClass="scene-row"
              fields={[
                { name: "title", label: t(lang, "Tiêu đề cảnh") },
                { name: "order_index", label: t(lang, "Thứ tự"), type: "number", defaultValue: String(c.scenes.length) },
              ]}
            />
          </div>
        )}
      </div>
    );
  };

  const arcGroup = (a: any) => {
    const chs = (chaptersByArc[a.id] ?? []).filter(matchChapter);
    if (needle && !chs.length && !(a.title ?? "").toLowerCase().includes(needle)) return null;
    const closed = !needle && closedGroups.has(a.id);
    return (
      <div key={a.id} className="arc-group">
        <button className="tree-node-toggle arc-toggle" aria-expanded={!closed} onClick={() => toggleGroup(a.id)}>
          <span className="arrow">{closed ? "›" : "⌄"}</span>
          <span>{a.title}</span>
          <small>{chs.length} ch.</small>
        </button>
        {!closed && <div className="tree-children chapter-list">{chs.map(chapterRow)}</div>}
      </div>
    );
  };

  return (
    <div className="manuscript-tree">
      <div className="tree-tools">
        <input
          className="list-filter"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t(lang, "Tìm chương / cảnh…")}
          aria-label={t(lang, "Tìm chương")}
          style={{ width: "100%", marginBottom: 4 }}
        />
        <span>
          {chapters.length} {t(lang, "chương")}{" · "}{totalWords.toLocaleString("vi-VN")} {t(lang, "từ")}
        </span>
      </div>
      {volumes.map((v: any) => {
        const vChapters = [
          ...(chaptersByVolume[v.id] ?? []),
          ...(arcsByVolume[v.id] ?? []).flatMap((a: any) => chaptersByArc[a.id] ?? []),
        ];
        const vWords = vChapters.reduce(
          (n: number, c: any) => n + c.scenes.reduce((m: number, s: any) => m + words(s.prose), 0),
          0
        );
        const vAnyMatch =
          (chaptersByVolume[v.id] ?? []).some(matchChapter) ||
          (arcsByVolume[v.id] ?? []).some(
            (a: any) => (a.title ?? "").toLowerCase().includes(needle) || (chaptersByArc[a.id] ?? []).some(matchChapter)
          );
        if (needle && !vAnyMatch && !(v.title ?? "").toLowerCase().includes(needle)) return null;
        const vClosed = !needle && closedGroups.has(v.id);
        return (
          <div key={v.id}>
            <button className="tree-node-toggle" aria-expanded={!vClosed} onClick={() => toggleGroup(v.id)}>
              <span className="arrow">{vClosed ? "›" : "⌄"}</span>
              <span>{v.title}</span>
              <small>{vWords ? fmtK(vWords) : `${vChapters.length} ch.`}</small>
            </button>
            {!vClosed && (
              <div className="tree-children">
                {(arcsByVolume[v.id] ?? []).map(arcGroup)}
                {(chaptersByVolume[v.id] ?? []).map(chapterRow)}
              </div>
            )}
          </div>
        );
      })}
      {looseArcs.map(arcGroup)}
      {(() => {
        const looseMatch = looseChapters.filter(matchChapter);
        if (!looseChapters.length || (needle && !looseMatch.length)) return null;
        const looseClosed = !needle && closedGroups.has("__loose");
        const looseWords = looseChapters.reduce(
          (n: number, c: any) => n + c.scenes.reduce((m: number, s: any) => m + words(s.prose), 0), 0);
        return (
          <div>
            <button className="tree-node-toggle" aria-expanded={!looseClosed} onClick={() => toggleGroup("__loose")}>
              <span className="arrow">{looseClosed ? "›" : "⌄"}</span>
              <span>{volumes.length ? t(lang, "Chương ngoài quyển") : t(lang, "Quyển 1")}</span>
              <small>{looseWords ? fmtK(looseWords) : `${looseChapters.length} ch.`}</small>
            </button>
            {!looseClosed && (
              <div className="tree-children"><div className="chapter-list">{looseChapters.map(chapterRow)}</div></div>
            )}
          </div>
        );
      })()}
      <div className="tree-add-row">
        <PostForm
          endpoint={`/api/v1/projects/${projectId}/chapters`}
          submitLabel={t(lang, "Thêm chương")}
          triggerLabel={t(lang, "＋ Chương")}
          triggerClass="tree-add"
          fields={[
            { name: "title", label: t(lang, "Tiêu đề chương"), required: true },
            {
              name: "volume_id",
              label: t(lang, "Thuộc quyển (tuỳ chọn)"),
              type: "select",
              options: [{ value: "", label: "—" }, ...volumes.map((v: any) => ({ value: v.id, label: v.title }))],
            },
            {
              name: "arc_id",
              label: t(lang, "Thuộc hồi (tuỳ chọn)"),
              type: "select",
              options: [{ value: "", label: "—" }, ...arcs.map((a: any) => ({ value: a.id, label: a.title }))],
            },
            { name: "order_index", label: t(lang, "Thứ tự"), type: "number", defaultValue: String(chapters.length + 1) },
          ]}
        />
        <PostForm
          endpoint={`/api/v1/projects/${projectId}/arcs`}
          submitLabel={t(lang, "Thêm hồi")}
          triggerLabel={t(lang, "＋ Hồi")}
          triggerClass="tree-add"
          fields={[
            { name: "title", label: t(lang, "Tên hồi"), required: true },
            {
              name: "volume_id",
              label: t(lang, "Thuộc quyển (tuỳ chọn)"),
              type: "select",
              options: [{ value: "", label: "—" }, ...volumes.map((v: any) => ({ value: v.id, label: v.title }))],
            },
          ]}
        />
        <PostForm
          endpoint={`/api/v1/projects/${projectId}/volumes`}
          submitLabel={t(lang, "Thêm quyển")}
          triggerLabel={t(lang, "＋ Quyển")}
          triggerClass="tree-add"
          fields={[{ name: "title", label: t(lang, "Tên quyển"), required: true }]}
        />
      </div>
      {outlineCh && (
        <ChapterOutlineModal
          projectId={projectId}
          chapter={outlineCh}
          onClose={() => setOutlineCh(null)}
        />
      )}
    </div>
  );
}
