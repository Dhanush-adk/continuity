import { notFound } from "next/navigation";
import { AuthorizationDetail } from "../../../components/authorization-detail";
import { Shell } from "../../../components/shell";
import { ApiError, createApi } from "../../../lib/api";

export default async function AuthorizationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try { const decision = await createApi(true).authorization(id); return <Shell><div className="eyebrow">Decision audit</div><h1>Authorization detail</h1><p>Displayed from the immutable snapshots stored with this authorization.</p><AuthorizationDetail decision={decision} /></Shell>; }
  catch (error) { if (error instanceof ApiError && error.status === 404) notFound(); return <Shell><div className="empty">Could not load this authorization.</div></Shell>; }
}
