"use client";

// Shown by a per-tenant page when the caller sits ABOVE a tenant boundary (operator at Platform scope,
// or focused on a cross-tenant group). The page's data is meaningless without a merchant, so instead of
// calling the API with a null merchant_id (→ 500 "missing merchant id") we let them pick one to manage.
// Picking = "Enter" that merchant. See docs/architecture-unified-console.md (Stage 1).

import { useMemo } from "react";
import type { OrgTreeNode } from "@fbgroup/api-client";
import { indexTree, tenantsUnder } from "@/lib/scope";

export default function NodeDirectory({
  feature,
  nodes,
  currentNodeId,
  onEnter,
}: {
  feature: string;
  nodes: OrgTreeNode[];
  currentNodeId: string | null;
  onEnter: (n: { id: string; name: string | null }) => void;
}) {
  const tenants = useMemo(
    () => tenantsUnder(indexTree(nodes), currentNodeId),
    [nodes, currentNodeId],
  );

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 4px" }}>{feature}</h1>
      <p style={{ color: "#6b7280", margin: "0 0 20px", fontSize: 15 }}>
        You&apos;re at <strong>Platform</strong> scope. {feature} is managed per merchant — pick one to continue.
      </p>

      {tenants.length === 0 ? (
        <div
          style={{
            border: "1px dashed #d1d5db",
            borderRadius: 10,
            padding: "28px 20px",
            textAlign: "center",
            color: "#6b7280",
            maxWidth: 560,
          }}
        >
          No merchants yet. Onboard one from the Platform directory, then come back here.
        </div>
      ) : (
        <div style={{ display: "grid", gap: 10, maxWidth: 560 }}>
          {tenants.map((t) => (
            <button
              key={t.id}
              onClick={() => onEnter({ id: t.id, name: t.name })}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: 10,
                padding: "14px 16px",
                cursor: "pointer",
                textAlign: "left",
                fontSize: 15,
                minHeight: 44,
              }}
            >
              <span style={{ fontWeight: 600, color: "#111827" }}>{t.name ?? t.id}</span>
              <span style={{ color: "#9ca3af", fontWeight: 600 }}>Manage →</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
