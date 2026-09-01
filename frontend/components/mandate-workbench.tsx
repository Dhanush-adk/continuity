"use client";

import { useState } from "react";
import { ApiError, createApi } from "../lib/api";
import type { Agent, Mandate, Organization } from "../lib/types";

export function MandateWorkbench({ organization, agent }: { organization: Organization; agent: Agent }) {
  const [text, setText] = useState("Purchase 10 GPUs for the ML team from an approved vendor. Maximum $15,000.");
  const [mandate, setMandate] = useState<Mandate | null>(null); const [error, setError] = useState<string | null>(null);
  async function extract() { setError(null); try { setMandate(await createApi().extractMandate({ organization_id: organization.id, requester_id: "demo-requester", agent_id: agent.id, text })); } catch (cause) { setError(cause instanceof ApiError ? cause.message : "Extraction failed"); } }
  async function activate() { if (!mandate) return; setError(null); try { setMandate(await createApi().activateMandate(mandate.id)); } catch (cause) { setError(cause instanceof Error ? cause.message : "Activation failed"); } }
  return <div className="card"><p className="small">Uses the configured extractor. In local demo mode this is explicitly the deterministic MockIntentExtractor.</p><div className="form"><textarea aria-label="Natural language mandate" rows={5} value={text} onChange={(event) => setText(event.target.value)} /><div><button className="button" onClick={extract}>Extract intent</button>{mandate?.status === "DRAFT" && <> <button className="button" onClick={activate}>Activate mandate</button></>}</div>{error && <p className="reason">{error}</p>}{mandate && <><StatusLine label="Status" value={mandate.status} /><pre className="mono small">{JSON.stringify(mandate.structured_intent, null, 2)}</pre></>}</div></div>;
}
function StatusLine({ label, value }: { label: string; value: string }) { return <p><strong>{label}:</strong> {value}</p>; }
