import type { Decision, TrustStatus } from "../lib/types";

export function StatusBadge({ value }: { value: Decision | TrustStatus | "PASS" | "FAIL" | "INHERIT" | "RESTRICT" | "REAUTHORIZE" }) {
  const tone = value === "ALLOW" || value === "TRUSTED" || value === "PASS" ? "allow" : value === "DENY" || value === "UNTRUSTED" || value === "FAIL" ? "deny" : value === "REVIEW" || value === "LIMITED" || value === "RESTRICT" || value === "REAUTHORIZE" ? "review" : "inherit";
  return <span className={`badge ${tone}`}>{value}</span>;
}
