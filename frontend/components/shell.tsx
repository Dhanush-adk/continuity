import Link from "next/link";
import type { ReactNode } from "react";

export function Shell({ children }: { children: ReactNode }) {
  return <div className="shell"><aside className="nav"><div className="brand">Continuity</div><Link href="/">Dashboard</Link><Link href="/agents">Agent versions</Link><Link href="/authorizations">Authorization feed</Link><Link href="/mandates">Create mandate</Link></aside><main>{children}</main></div>;
}
