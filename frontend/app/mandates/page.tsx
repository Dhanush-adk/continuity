import { EmptyDemo } from "../../components/empty-demo";
import { MandateWorkbench } from "../../components/mandate-workbench";
import { Shell } from "../../components/shell";
import { loadDemo } from "../../lib/demo";

export default async function MandatesPage() { let demo = null; try { demo = await loadDemo(); } catch { demo = null; } return <Shell>{!demo ? <EmptyDemo /> : <><div className="eyebrow">Optional demo workflow</div><h1>Create mandate</h1><p>Extraction produces a candidate. Explicit activation—not the LLM—is what makes it a valid authorization input.</p><MandateWorkbench organization={demo.organization} agent={demo.agent} /></>}</Shell>; }
