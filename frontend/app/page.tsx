import Link from "next/link";
import { EmptyDemo } from "../components/empty-demo";
import { Shell } from "../components/shell";
import { StatusBadge } from "../components/status-badge";
import { loadDemo } from "../lib/demo";

const money = (value: unknown) => typeof value === "number" ? `$${value.toLocaleString("en-US")}` : "—";

export default async function Dashboard() {
  let demo = null;
  try { demo = await loadDemo(); } catch { demo = null; }
  return <Shell>{!demo ? <EmptyDemo /> : <>
    <div className="eyebrow">Authorization control plane</div><h1>{demo.organization.name}</h1><p>Verified runtime evidence for <strong>{demo.agent.external_agent_id}</strong>.</p>
    <div className="grid four"><div className="card"><p>Current deployment</p><div className="value">v{demo.current.version}</div><StatusBadge value="PASS" /></div><div className="card"><p>Deployment identity</p><div className="value">VERIFIED</div><p className="small mono">{demo.current.deployment_fingerprint.slice(0, 18)}…</p></div><div className="card"><p>Capabilities</p><div className="value">{demo.trusts.length}</div><p className="small">Capability-specific trust</p></div><div className="card"><p>Recent decisions</p><div className="value">{demo.decisions.length}</div><p className="small">Stored immutable snapshots</p></div></div>
    <h2>Capability trust</h2><div className="grid two">{demo.trusts.map((trust) => <div className="card" key={trust.capability_name}><div className="row"><strong>{trust.capability_name}</strong><StatusBadge value={trust.status} /></div><p>{Object.keys(trust.autonomy_constraints).length ? `Trusted envelope ≤ ${money(trust.autonomy_constraints.max_amount)}` : "No monetary envelope"}</p><p className="small">Continuity: {trust.continuity_action}</p></div>)}</div>
    <h2>Recent authorization decisions</h2><table><thead><tr><th>Vendor</th><th>Amount</th><th>Decision</th><th>Details</th></tr></thead><tbody>{["ALLOW", "DENY", "REVIEW"].flatMap((outcome) => demo.decisions.filter((item) => item.decision === outcome).slice(0, 1)).map((item) => <tr key={item.id}><td>{String(item.proposed_action.vendor)}</td><td>{money(item.proposed_action.amount)}</td><td><StatusBadge value={item.decision} /></td><td><Link href={`/authorizations/${item.id}`}>View audit →</Link></td></tr>)}</tbody></table>
  </>}</Shell>;
}
