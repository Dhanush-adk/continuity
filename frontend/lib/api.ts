import type { Agent, AgentVersion, AuthorizationDecision, CapabilityTrust, Mandate, Organization, Review, VersionDiff } from "./types";

export class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }

function baseUrl(server = false): string {
  if (server) return process.env.CONTINUITY_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return "/api/continuity";
}

export function createApi(server = false) {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl(server)}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers }, cache: "no-store" });
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new ApiError(body.detail ?? `Request failed (${response.status})`, response.status); }
    return response.json() as Promise<T>;
  }
  return {
    organizations: () => request<Organization[]>("/organizations"),
    agents: (organizationId: string) => request<Agent[]>(`/organizations/${organizationId}/agents`),
    versions: (agentId: string) => request<AgentVersion[]>(`/agents/${agentId}/versions`),
    trusts: (agentId: string, versionId: string) => request<CapabilityTrust[]>(`/agents/${agentId}/versions/${versionId}/capabilities`),
    diff: (agentId: string, fromId: string, toId: string) => request<VersionDiff>(`/agents/${agentId}/versions/${fromId}/diff/${toId}`),
    authorizations: (organizationId?: string) => request<AuthorizationDecision[]>(`/authorizations${organizationId ? `?organization_id=${organizationId}` : ""}`),
    authorization: (id: string) => request<AuthorizationDecision>(`/authorizations/${id}`),
    review: (id: string, body: { decision: "APPROVE" | "DENY"; reviewer_id: string; reviewer_name?: string; reason: string }) => request<Review>(`/authorizations/${id}/review`, { method: "POST", body: JSON.stringify(body) }),
    extractMandate: (body: Record<string, unknown>) => request<Mandate>("/mandates/extract", { method: "POST", body: JSON.stringify(body) }),
    activateMandate: (id: string) => request<Mandate>(`/mandates/${id}/activate`, { method: "POST" })
  };
}
