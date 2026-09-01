"use client";

import { useState } from "react";
import { ReviewForm } from "./review-form";
import { StatusBadge } from "./status-badge";
import { timestamp } from "../lib/format";
import type { AuthorizationDecision } from "../lib/types";

const value = (input: unknown) => input === null || input === undefined ? "—" : String(input);
const money = (input: unknown) => typeof input === "number" ? `$${input.toLocaleString("en-US")}` : "—";

export function AuthorizationDetail({ decision }: { decision: AuthorizationDecision }) {
  const [review, setReview] = useState(decision.review);
  const action = decision.proposed_action;
  const intent = (decision.mandate_snapshot.structured_intent ?? {}) as Record<string, unknown>;
  const envelope = (decision.capability_trust_snapshot.autonomy_constraints ?? {}) as Record<string, unknown>;
  const policy = decision.policy_snapshot;
  const checkRows: Array<[string, string]> = [
    ["Deployment", "PASS"], ["Capability", String(decision.capability_trust_snapshot.status ?? "—")],
    ["Trusted envelope", Number(action.amount) > Number(envelope.max_amount ?? Infinity) ? "REVIEW" : "PASS"],
    ["Mandate quantity", Number(action.quantity) > Number(intent.quantity_max ?? -1) ? "FAIL" : "PASS"],
    ["Mandate amount", Number(action.amount) > Number(intent.max_amount ?? -1) ? "FAIL" : "PASS"],
    ["Vendor policy", Array.isArray(policy.approved_vendors) && !policy.approved_vendors.includes(action.vendor) ? "FAIL" : "PASS"],
    ["Organization policy", decision.decision === "REVIEW" ? "REVIEW" : "PASS"]
  ];
  const mandateRows: Array<[string, unknown]> = [["Category", intent.item_category], ["Quantity max", intent.quantity_max], ["Amount max", money(intent.max_amount)], ["Vendor policy", intent.vendor_policy], ["Purpose", intent.purpose]];
  const actionRows: Array<[string, unknown]> = [["Vendor", action.vendor], ["Category", action.item_category], ["Quantity", action.quantity], ["Amount", money(action.amount)], ["Purpose", action.purpose]];
  return <><div className="grid two"><div className="card"><h3>Authorization #{decision.id.slice(0, 8)}</h3><p>Capability: <strong>{decision.capability_name}</strong></p><p>Capability trust: <StatusBadge value={String(decision.capability_trust_snapshot.status) as "TRUSTED" | "LIMITED" | "UNTRUSTED"} /></p><p>Trusted envelope: ≤ {money(envelope.max_amount)}</p></div><div className="card"><h3>Decision</h3><StatusBadge value={decision.decision} /><p className="small">Recorded {timestamp(decision.created_at)}</p>{review && <p>Human review: <StatusBadge value={review.decision === "APPROVE" ? "PASS" : "FAIL"} /> by {review.reviewer_name ?? review.reviewer_id}</p>}</div></div>
    <div className="split"><div className="card"><h2>User mandate</h2><p className="mono small">{String(decision.mandate_snapshot.raw_intent ?? "Raw intent retained in mandate record")}</p><div className="list">{mandateRows.map(([name, item]) => <div className="row" key={name}><span>{name}</span><strong>{value(item)}</strong></div>)}</div></div><div className="card"><h2>Proposed action</h2><div className="list">{actionRows.map(([name, item]) => <div className="row" key={name}><span>{name}</span><strong>{value(item)}</strong></div>)}</div></div></div>
    <h2>Checks at decision time</h2><div className="card">{checkRows.map(([name, status]) => <div className="check" key={String(name)}><span>{name}</span><StatusBadge value={status as "PASS" | "REVIEW" | "FAIL" | "TRUSTED" | "LIMITED" | "UNTRUSTED"} /></div>)}</div>
    {decision.reason_codes.length > 0 && <><h2>Reason codes</h2><div className="card">{decision.reason_codes.map((reason) => <p className="reason" key={reason.code}>{reason.code} — expected {value(reason.expected)}, actual {value(reason.actual)}</p>)}</div></>}
    <h2>Final decision</h2><StatusBadge value={decision.decision} />
    {decision.decision === "REVIEW" && !review && <ReviewForm authorizationId={decision.id} onReviewed={setReview} />}
  </>;
}
