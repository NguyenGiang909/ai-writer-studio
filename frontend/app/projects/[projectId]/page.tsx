import { redirect } from "next/navigation";
import { getJSON } from "../../../lib/api";
import SceneEditor from "../../../components/SceneEditor";
import { getLang } from "../../../lib/lang-server";
import { t } from "../../../lib/i18n";

async function safe(path: string, fallback: any = []) {
  try {
    return await getJSON(path);
  } catch {
    return fallback;
  }
}

export default async function Workspace({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ scene?: string }>;
}) {
  const { projectId } = await params;
  const lang = await getLang();
  const { scene: sceneId } = await searchParams;
  const base = `/api/v1/projects/${projectId}`;
  const [tree, characters, locations] = await Promise.all([
    safe(`${base}/manuscript`, { chapters: [] }),
    safe(`${base}/characters`),
    safe(`${base}/locations`),
  ]);

  const scenes = tree.chapters.flatMap((c: any) => c.scenes.map((s: any) => ({ ...s, chapter: c })));
  if (!sceneId && scenes.length) redirect(`/projects/${projectId}?scene=${scenes[0].id}`);
  const selected = scenes.find((s: any) => s.id === sceneId) ?? scenes[0] ?? null;
  const selIdx = scenes.findIndex((s: any) => s.id === selected?.id);
  const nav = (s: any) =>
    s && {
      href: `/projects/${projectId}?scene=${s.id}`,
      label: `${s.chapter.title} · ${s.title ?? t(lang, "Cảnh {n}", { n: (s.order_index ?? 0) + 1 })}`,
    };
  const prev = selIdx > 0 ? nav(scenes[selIdx - 1]) : null;
  const next = selIdx >= 0 && selIdx < scenes.length - 1 ? nav(scenes[selIdx + 1]) : null;

  return (
    <main className="main">
      {selected ? (
        <SceneEditor
          key={selected.id}
          projectId={projectId}
          scene={selected}
          chapterTitle={selected.chapter.title}
          sceneIndex={selected.chapter.scenes.findIndex((s: any) => s.id === selected.id) + 1}
          sceneTotal={selected.chapter.scenes.length}
          characters={characters}
          locations={locations}
          reviewHref={`/projects/${projectId}/review`}
          memoryHref={`/projects/${projectId}/memory`}
          prevScene={prev}
          nextScene={next}
        />
      ) : (
        <div style={{ padding: 60, color: "var(--muted)" }}>
          {t(lang, "Chưa có cảnh nào. Tạo chương và cảnh đầu tiên ở cây bên trái.")}
        </div>
      )}
    </main>
  );
}
