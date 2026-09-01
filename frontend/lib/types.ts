export type Decision = "ALLOW" | "REVIEW" | "DENY";
export type TrustStatus = "TRUSTED" | "LIMITED" | "UNTRUSTED";

export interface Organization { id: string; name: string; created_at: string }
export interface Agent { id: string; organization_id: string; external_agent_id: string; name: string; description?: string | null; created_at: string }
export interface AgentVersion { id: string; agent_id: string; version: string; model_name: string; deployment_fingerprint: string; capability_manifest: Record<string, unknown>; created_at: string }
export interface CapabilityTrust { capability_name: string; status: TrustStatus; autonomy_constraints: Record<string, unknown>; continuity_action: string; inherited_from_version_id?: string | null; reason_codes: string[]; explicitly_reauthorized: boolean }
export interface Reason { code: string; expected?: unknown; actual?: unknown }
export interface Review { id: string; decision: "APPROVE" | "DENY"; reviewer_id: string; reviewer_name?: string | null; reason: string; created_at: string }
export interface AuthorizationDecision { id: string; organization_id: string; agent_id: string; agent_version_id: string; mandate_id: string; capability_name: string; decision: Decision; reason_codes: Reason[]; proposed_action: Record<string, unknown>; capability_trust_snapshot: Record<string, unknown>; mandate_snapshot: Record<string, unknown>; policy_snapshot: Record<string, unknown>; created_at: string; review?: Review | null }
export interface VersionDiff { from_version: string; to_version: string; model: { changed: boolean; before?: string; after?: string }; tools: { added: string[]; removed: string[] }; capabilities: { added: string[]; removed: string[]; modified: Array<{name: string; before: Record<string, unknown>; after: Record<string, unknown>}> } }
export interface Mandate { id: string; status: string; raw_intent: string; structured_intent: Record<string, unknown>; created_at: string }
