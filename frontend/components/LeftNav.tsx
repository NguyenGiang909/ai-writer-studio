import { Suspense } from "react";
import Link from "next/link";
import NavLink from "./NavLink";
import ManuscriptTree from "./ManuscriptTree";
import { t, type Lang } from "../lib/i18n";

const NAV = [
  { suffix: "", icon: "✎", label: "Bản thảo", exact: true },
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

export default function LeftNav({
  lang = "vi",
  projectId,
  tree,
  characters,
  openThreads,
  pendingCount,
}: {
  lang?: Lang;
  projectId: string;
  tree: { volumes: any[]; arcs: any[]; chapters: any[] };
  characters: { id: string; name: string }[];
  openThreads: number;
  pendingCount: number;
}) {
  const badges: Record<string, number> = { threads: openThreads, pending: pendingCount };
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
          {n.badge && badges[n.badge] > 0 && <small>{badges[n.badge]}</small>}
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
      <div className="section-label">{t(lang, "Cây bản thảo")}</div>
      <Suspense fallback={null}>
        <ManuscriptTree
          projectId={projectId}
          volumes={tree.volumes ?? []}
          arcs={tree.arcs ?? []}
          chapters={tree.chapters ?? []}
          characters={characters}
        />
      </Suspense>
    </aside>
  );
}
