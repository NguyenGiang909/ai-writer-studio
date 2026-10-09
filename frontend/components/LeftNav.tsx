import { Suspense } from "react";
import Link from "next/link";
import NavLink from "./NavLink";
import ManuscriptTree from "./ManuscriptTree";
import ChapterCastPanel from "./ChapterCastPanel";
import { t, type Lang } from "../lib/i18n";
import { API, getJSON } from "../lib/api";

const NAV = [
  { suffix: "", icon: "✎", label: "Bản thảo", exact: true },
  { suffix: "/authoring", icon: "✧", label: "Tạo truyện (AI)", badge: "authoring" },
  { suffix: "/read", icon: "❖", label: "Đọc lại" },
  { suffix: "/story", icon: "◇", label: "Thiết kế truyện" },
  { suffix: "/characters", icon: "♙", label: "Nhân vật" },
  { suffix: "/world", icon: "◎", label: "Thế giới" },
  { suffix: "/abilities", icon: "✦", label: "Năng lực" },
  { suffix: "/threads", icon: "≋", label: "Threads / Hố", badge: "threads" },
  { suffix: "/timeline", icon: "⌁", label: "Timeline" },
  { suffix: "/style", icon: "¶", label: "Phong cách" },
  { suffix: "/review", icon: "✓", label: "Continuity", badge: "pending" },
];

const EXTRA_NAV = [
  { suffix: "/truth", icon: "◈", label: "Canon & Truth" },
  { suffix: "/discussions", icon: "✦", label: "Thảo luận AI" },
  { suffix: "/signals", icon: "♒", label: "Dấu hiệu" },
  { suffix: "/memory", icon: "▤", label: "Memory" },
  { suffix: "/branches", icon: "⑂", label: "What-if" },
];

export default async function LeftNav({
  lang = "vi",
  projectId,
  tree,
  characters,
  threads,
  abilities,
  openThreads,
  pendingCount,
}: {
  lang?: Lang;
  projectId: string;
  tree: { volumes: any[]; arcs: any[]; chapters: any[] };
  characters: { id: string; name: string }[];
  threads: { id: string; title: string; status?: string }[];
  abilities: { id: string; name: string; ability_type?: string | null }[];
  openThreads: number;
  pendingCount: number;
}) {
  const badges: Record<string, number> = { threads: openThreads, pending: pendingCount };
  let aiIds: string[] | undefined;
  let authoringStatus: string | null = null;
  try {
    const prov = await getJSON(`/api/v1/projects/${projectId}/authoring/provenance`);
    if (prov?.items?.length) aiIds = prov.items.map((i: any) => i.entity_id);
  } catch {}
  try {
    const st = await getJSON(`/api/v1/projects/${projectId}/authoring/status`);
    if (st?.run?.status && st.run.status !== "completed") authoringStatus = st.run.status;
  } catch {}
  return (
    <aside className="left">
      <div className="mode">
        <button className="active">Writer</button>
        <button>Architect</button>
      </div>
      <div className="section-label">{t(lang, "Không gian viết")}</div>
      {NAV.map((n) => (
        <NavLink key={n.suffix} href={`/projects/${projectId}${n.suffix}`} exact={n.exact} className="nav-item">
          <span>{n.icon}</span> {t(lang, n.label)}
          {n.badge === "authoring"
            ? authoringStatus && <small title={t(lang, "Đang có phiên tạo truyện")}>{authoringStatus === "running" ? "●" : authoringStatus === "awaiting_review" ? "⏸" : "⚠"}</small>
            : n.badge && badges[n.badge] > 0 && <small>{badges[n.badge]}</small>}
        </NavLink>
      ))}
      <details className="nav-extra">
        <summary className="section-label">{t(lang, "Mở rộng")}</summary>
        {EXTRA_NAV.map((n) => (
          <NavLink key={n.suffix} href={`/projects/${projectId}${n.suffix}`} className="nav-item">
            <span>{n.icon}</span> {t(lang, n.label)}
          </NavLink>
        ))}
      </details>
      <div className="section-label">{t(lang, "Cá nhân")}</div>
      <Link href="/account" className="nav-item" style={{ textDecoration: "none" }}>
        <span>◯</span> {t(lang, "Tài khoản & Credit")}
      </Link>
      <Link href="/settings" className="nav-item" style={{ textDecoration: "none" }}>
        <span>⚙</span> {t(lang, "Kết nối API")}
      </Link>
      <a href={`${API}/api/v1/projects/${projectId}/export`} className="nav-item" style={{ textDecoration: "none" }}
         download title={t(lang, "Tải toàn bộ project — nhân vật, canon, threads, memory…")}>
        <span>⤓</span> {t(lang, "Sao lưu (.json)")}
      </a>
      <a href={`${API}/api/v1/projects/${projectId}/export?format=markdown`} className="nav-item" style={{ textDecoration: "none" }}
         download title={t(lang, "Chỉ bản thảo: chương + cảnh, prose sạch")}>
        <span>⤓</span> {t(lang, "Bản thảo (.md)")}
      </a>
      <div className="section-label">{t(lang, "Cây bản thảo")}</div>
      <Suspense fallback={null}>
        <ManuscriptTree
          projectId={projectId}
          volumes={tree.volumes ?? []}
          arcs={tree.arcs ?? []}
          chapters={tree.chapters ?? []}
          characters={characters}
          aiIds={aiIds}
        />
        <ChapterCastPanel
          projectId={projectId}
          chapters={tree.chapters ?? []}
          characters={characters}
          threads={threads}
          abilities={abilities}
        />
      </Suspense>
    </aside>
  );
}
