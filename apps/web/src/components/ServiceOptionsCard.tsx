"use client";
// Per-storefront service options (fulfilment): Dine-in [Self-Service | Served] + Takeaway on/off.
// Maps to the node's `service_options` set (one dine-in variant + optional takeaway). Cascades to the
// subtree. Lives in the merchant Ordering setup hub (Tables & QR page).
import { useEffect, useState } from "react";
import { getNodeServiceOptions, setNodeServiceOptions, getApiBase } from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import type { NodeServiceOptions } from "@fbgroup/api-client";

export default function ServiceOptionsCard({ nodeId }: { nodeId: string }) {
  const base = getApiBase();
  const [svc, setSvc] = useState<NodeServiceOptions | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) return;
    getNodeServiceOptions(base, tok, nodeId).then(setSvc).catch(() => setSvc(null));
  }, [base, nodeId]);

  const save = (served: boolean, takeawayOn: boolean) => {
    const tok = getStaffToken();
    if (!tok) return;
    const list = [served ? "dine_in_served" : "dine_in_pickup", ...(takeawayOn ? ["takeaway"] : [])];
    setBusy(true);
    setNodeServiceOptions(base, tok, nodeId, list).then(setSvc).catch(() => {}).finally(() => setBusy(false));
  };

  if (!svc) return null;
  const eff = svc.own ?? svc.resolved;
  const served = eff.includes("dine_in_served");
  const takeawayOn = eff.includes("takeaway");

  return (
    <div className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ fontWeight: 800 }}>Service options</div>
      {/* Dine-in: Self-Service (collect) vs Served (waiter). */}
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>Dine-in</span>
        <div role="radiogroup" aria-label="Dine-in service" style={{ display: "flex", border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 8, overflow: "hidden", maxWidth: 320 }}>
          {([["Self-Service", false], ["Served", true]] as [string, boolean][]).map(([lbl, isServed], i) => {
            const sel = served === isServed;
            return (
              <button key={lbl} type="button" role="radio" aria-checked={sel} disabled={busy}
                onClick={() => save(isServed, takeawayOn)}
                style={{ flex: 1, padding: "8px 0", fontSize: 13, fontWeight: sel ? 700 : 500, border: "none",
                  borderLeft: i ? "1px solid var(--color-border,#e5e7eb)" : "none",
                  background: sel ? "var(--color-primary,#dc2626)" : "#fff", color: sel ? "#fff" : "var(--color-text,#334155)",
                  cursor: busy ? "default" : "pointer" }}>
                {lbl}
              </button>
            );
          })}
        </div>
        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
          {served ? "A waiter/runner brings it to the table (no diner alert)." : "Diner collects from the counter when ready (gets a “ready” alert)."}
        </span>
      </div>
      {/* Takeaway on/off. */}
      <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: busy ? "default" : "pointer" }}>
        <input type="checkbox" checked={takeawayOn} disabled={busy} onChange={() => save(served, !takeawayOn)} />
        <span style={{ fontSize: 13, fontWeight: 600 }}>Takeaway <span style={{ fontWeight: 400, color: "var(--color-text-muted)", fontSize: 12 }}>— packaged to go</span></span>
      </label>
      <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>The diner picks at checkout when more than one is offered.</span>
    </div>
  );
}
