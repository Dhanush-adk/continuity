"use client";

import { useState } from "react";
import { createApi } from "../lib/api";
import type { Review } from "../lib/types";

export function ReviewForm({ authorizationId, onReviewed }: { authorizationId: string; onReviewed: (review: Review) => void }) {
  const [reviewerId, setReviewerId] = useState("procurement-director");
  const [reason, setReason] = useState("Approved for ML expansion");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(decision: "APPROVE" | "DENY") {
    setBusy(true); setError(null);
    try { onReviewed(await createApi().review(authorizationId, { decision, reviewer_id: reviewerId, reason })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not record review"); }
    finally { setBusy(false); }
  }
  return <div className="card"><h3>Human review</h3><p className="small">This creates a separate audit record; the original REVIEW remains unchanged.</p><div className="form"><input aria-label="Reviewer ID" value={reviewerId} onChange={(event) => setReviewerId(event.target.value)} /><textarea aria-label="Review reason" value={reason} onChange={(event) => setReason(event.target.value)} /><div><button className="button" disabled={busy} onClick={() => submit("APPROVE")}>APPROVE</button>{" "}<button className="button danger" disabled={busy} onClick={() => submit("DENY")}>DENY</button></div>{error && <p className="reason">{error}</p>}</div></div>;
}
