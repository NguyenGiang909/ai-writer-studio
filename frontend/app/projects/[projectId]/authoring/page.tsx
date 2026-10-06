import AuthoringRoom from "../../../../components/AuthoringRoom";
import { getLang } from "../../../../lib/lang-server";

export default async function AuthoringPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const lang = await getLang();
  return (
    <main className="page">
      <AuthoringRoom projectId={projectId} lang={lang} />
    </main>
  );
}
