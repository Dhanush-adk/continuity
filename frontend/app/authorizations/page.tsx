import Link from "next/link";
import { EmptyDemo } from "../../components/empty-demo";
import { Shell } from "../../components/shell";
import { StatusBadge } from "../../components/status-badge";
import { loadDemo } from "../../lib/demo";
import { timestamp } from "../../lib/format";

export default async function AuthorizationsPage() {
  let demo = null; try { demo = await loadDemo(); } catch { demo = null; }
  return <Shell>{!demo ? <EmptyDemo /> : <><div className="eyebrow">Immutable audit log</div><h1>Authorization feed</h1><p>Every record uses the policy, mandate, and capability-trust snapshots available at decision time.</p><table><thead><tr><th>Timestamp</th><th>Agent</th><th>Version</th><th>Capability</th><th>Vendor</th><th>Amount</th><th>Decision</th></tr></thead><tbody>{demo.decisions.map((item) => <tr key={item.id}><td><Link href={`/authorizations/${item.id}`}>{timestamp(item.created_at)}</Link></td><td>{demo.agent.external_agent_id}</td><td>{demo.current.version}</td><td>{item.capability_name}</td><td>{String(item.proposed_action.vendor)}</td><td>${Number(item.proposed_action.amount).toLocaleString()}</td><td><StatusBadge value={item.decision} />{item.review ? <span className="small"> · {item.review.decision}</span> : null}</td></tr>)}</tbody></table></>}</Shell>;
}
