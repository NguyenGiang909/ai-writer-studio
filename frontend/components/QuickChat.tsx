"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getJSON, postJSON } from "../lib/api";
import { t } from "../lib/i18n";
import { useLang } from "../lib/use-lang";
import ChatThread from "./ChatThread";

const QUICK_TITLE = "Trợ lý nhanh";

export default function QuickChat({
  projectId,
  context,
  sceneId,
}: {
  projectId: string;
  context: string;
  sceneId?: string;
}) {
  const lang = useLang();
  const [threadId, setThreadId] = useState<string | null>(null);

  useEffect(() => {
    let dead = false;
    (async () => {
      try {
        const threads: any[] = await getJSON(`/api/v1/projects/${projectId}/discussions`);
        let t = threads.find((x) => x.title === QUICK_TITLE);
        if (!t) t = await postJSON(`/api/v1/projects/${projectId}/discussions`, {
          title: QUICK_TITLE, role: "assistant",
        });
        if (!dead) setThreadId(t.id);
      } catch { /* panel optional */ }
    })();
    return () => { dead = true; };
  }, [projectId]);

  return (
    <>
      <div className="context-chip">{t(lang, "Đang gắn:")} {context}</div>
      {threadId ? (
        <ChatThread projectId={projectId} threadId={threadId} context={context} sceneId={sceneId} />
      ) : (
        <p className="hint">{t(lang, "Đang mở phòng chat…")}</p>
      )}
      {threadId && (
        <Link href={`/projects/${projectId}/discussions/${threadId}`}
          className="hint" style={{ display: "block", marginTop: 8, color: "var(--teal)", textDecoration: "none" }}>
          {t(lang, "Mở phòng thảo luận đầy đủ →")}
        </Link>
      )}
    </>
  );
}
