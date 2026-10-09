import Link from "next/link";
import React, { Suspense } from "react";
import { getJSON } from "../../../lib/api";
import ThemeToggle from "../../../components/ThemeToggle";
import LangToggle from "../../../components/LangToggle";
import { getLang } from "../../../lib/lang-server";
import { t } from "../../../lib/i18n";
import AppBehaviors from "../../../components/AppBehaviors";
import LeftNav from "../../../components/LeftNav";
import RightPanel from "../../../components/RightPanel";
import ProjectModal from "../../../components/ProjectModal";
import SaveIndicator from "../../../components/SaveIndicator";
import TopSearch from "../../../components/TopSearch";

async function safe(path: string, fallback: any = []) {
  try {
    return await getJSON(path);
  } catch {
    return fallback;
  }
}

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await getLang();
  const base = `/api/v1/projects/${projectId}`;
  const [projects, tree, characters, threads, abilities, suggestions, facts, decisions, styles, continuity] =
    await Promise.all([
      safe("/api/v1/projects"),
      safe(`${base}/manuscript`, { volumes: [], arcs: [], chapters: [] }),
      safe(`${base}/characters`),
      safe(`${base}/threads`),
      safe(`${base}/abilities`),
      safe(`${base}/suggestions?status=pending`),
      safe(`${base}/canon-facts`),
      safe(`${base}/author-decisions`),
      safe(`${base}/style-profiles`),
      safe(`${base}/continuity/check`, { count: 0 }),
    ]);
  const project = projects.find((p: any) => p.id === projectId) ?? null;
  const openThreads = threads.filter((t: any) => t.status === "OPEN").length;

  return (
    <div className="app">
      <header className="top">
        <button className="icon-btn menu-toggle" aria-label={t(lang, "Mở điều hướng")}>☰</button>
        <Link href="/" className="brand" style={{ textDecoration: "none" }}>
          <span className="mark">A</span> AI Writer Studio
        </Link>
        <ProjectModal currentId={projectId} currentName={project?.name} />
        <Suspense fallback={<div className="top-search" />}>
          <TopSearch projectId={projectId} />
        </Suspense>
        <SaveIndicator />
        <Link href="/account" className="account-shortcut" style={{ textDecoration: "none" }}>
          {t(lang, "Tài khoản")}
        </Link>
        <LangToggle />
        <ThemeToggle />
        <button className="icon-btn ai-toggle" aria-label={t(lang, "Mở trợ lý AI")}>✦</button>
      </header>
      <div className="shell">
        <LeftNav
          lang={lang}
          projectId={projectId}
          tree={tree}
          characters={characters}
          threads={threads}
          abilities={abilities}
          openThreads={openThreads}
          pendingCount={suggestions.length}
        />
        {children}
        <Suspense fallback={<aside className="right" />}>
          <RightPanel
            projectId={projectId}
            chapters={tree.chapters ?? []}
            characters={characters}
            counts={{
              canon: facts.length,
              decisions: decisions.length,
              threads: threads.length,
              styles: styles.length,
              continuity: continuity.count ?? 0,
            }}
          />
        </Suspense>
      </div>
      <div id="toast" className="toast" />
      <AppBehaviors projectId={projectId} />
    </div>
  );
}
