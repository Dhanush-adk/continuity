import { EmptyDemo } from "../../components/empty-demo";
import { Shell } from "../../components/shell";
import { StatusBadge } from "../../components/status-badge";
import { loadDemo } from "../../lib/demo";

export default async function AgentsPage() {
  let demo = null; try { demo = await loadDemo(); } catch { demo = null; }
  return <Shell>{!demo ? <EmptyDemo /> : <><div className="eyebrow">Deployment continuity</div><h1>{demo.agent.external_agent_id}</h1><p>What changed in the deployment, and what trust carried forward.</p>
    <div className="grid two">{demo.versions.map((version) => <div className="card" key={version.id}><h3>Version {version.version}</h3><p className="mono small">{version.deployment_fingerprint}</p></div>)}</div>
    {demo.diff && <><h2>What changed: {demo.diff.from_version} → {demo.diff.to_version}</h2><div className="grid two"><div className="card"><h3>Model</h3><p>{demo.diff.model.changed ? `${demo.diff.model.before} → ${demo.diff.model.after}` : "Unchanged"}</p><h3>Tools</h3><p>{demo.diff.tools.added.map((name) => `+ ${name}`).join(", ") || "No additions"}</p></div><div className="card"><h3>Capabilities</h3><p>{demo.diff.capabilities.added.map((name) => `+ ${name}`).join(", ") || "No additions"}</p>{demo.diff.capabilities.modified.map((item) => <p key={item.name}><strong>{item.name}</strong><br />max_amount {String((item.before.constraints as Record<string, unknown>)?.max_amount)} → {String((item.after.constraints as Record<string, unknown>)?.max_amount)}</p>)}</div></div></>}
    <h2>Continuity interpretation</h2><div className="card list">{demo.trusts.map((trust) => <div className="row" key={trust.capability_name}><div><strong>{trust.capability_name}</strong><p className="small">{trust.reason_codes.join(" · ")}</p></div><div><StatusBadge value={trust.continuity_action as "INHERIT" | "RESTRICT" | "REAUTHORIZE"} /><p className="small">{trust.autonomy_constraints.max_amount ? `Envelope ≤ $${Number(trust.autonomy_constraints.max_amount).toLocaleString()}` : ""}</p></div></div>)}</div>
  </>}</Shell>;
}
