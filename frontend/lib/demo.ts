import { createApi } from "./api";

export async function loadDemo() {
  const api = createApi(true);
  const organization = (await api.organizations()).find((item) => item.name === "Acme Corp");
  if (!organization) return null;
  const agent = (await api.agents(organization.id)).find((item) => item.external_agent_id === "procurement-agent");
  if (!agent) return null;
  const versions = await api.versions(agent.id);
  const current = versions.find((item) => item.version === "1.1.0") ?? versions.at(-1);
  const previous = versions.find((item) => item.version === "1.0.0");
  if (!current) return null;
  const [trusts, decisions, diff] = await Promise.all([
    api.trusts(agent.id, current.id), api.authorizations(organization.id), previous ? api.diff(agent.id, previous.id, current.id) : Promise.resolve(null)
  ]);
  return { organization, agent, versions, current, previous, trusts, decisions, diff };
}
