// React hook over the tree-walker (lib/scope.ts): loads the caller's visible tree + permissions,
// figures out the "current node" from the operator drill-in context, and derives the Scope.
// Per-tenant pages use `scope.tenantId == null && isOperator` to know they must show a directory
// instead of calling the API with a null merchant_id. See docs/architecture-unified-console.md.

import { useCallback, useEffect, useState } from "react";
import { orgTree, getMyPermissions, getApiBase } from "@/lib/api";
import { getStaffToken, getOperatorMerchant, setOperatorMerchant } from "@/lib/auth";
import type { OrgTreeNode } from "@fbgroup/api-client";
import { deriveScope, type Scope } from "@/lib/scope";

export interface UseScope {
  /** True once the first load has resolved (success or error) — gate guards on this to avoid a flash. */
  ready: boolean;
  loading: boolean;
  error: string | null;
  isOperator: boolean;
  nodes: OrgTreeNode[];
  scope: Scope | null;
  /** Enter a node (sets the operator drill-in context + re-derives). Mirrors the platform "Enter". */
  enter: (n: { id: string; name?: string | null; nodeId?: string; nodeName?: string | null; outletId?: string | null }) => void;
  reload: () => void;
}

export function useScope(): UseScope {
  const [nodes, setNodes] = useState<OrgTreeNode[]>([]);
  const [isOperator, setIsOperator] = useState(false);
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentNodeId, setCurrentNodeId] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    const t = getStaffToken();
    if (!t) { setLoading(false); setReady(true); return; }
    let cancelled = false;
    setLoading(true);
    const op = getOperatorMerchant();
    Promise.all([orgTree(getApiBase(), t), getMyPermissions(getApiBase(), t, op?.id)])
      .then(([tree, caps]) => {
        if (cancelled) return;
        const ns = tree.nodes ?? [];
        const operator = !!caps.is_super_admin || caps.permissions.includes("platform.merchants.view");
        // Current node: an entered sub-chain → nodeId; an entered merchant → id; operator with nothing
        // entered → null (platform root); merchant-staff → the shallowest node in their visible slice.
        let cur: string | null = null;
        if (op) cur = op.nodeId ?? op.id;
        else if (!operator && ns.length) cur = [...ns].sort((a, b) => a.depth - b.depth)[0].id;
        if (cur && !ns.some((n) => n.id === cur)) cur = null; // stale context → fall back to root
        setNodes(ns);
        setIsOperator(operator);
        setCurrentNodeId(cur);
        setError(null);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load scope");
      })
      .finally(() => { if (!cancelled) { setLoading(false); setReady(true); } });
    return () => { cancelled = true; };
  }, [tick]);

  const enter: UseScope["enter"] = useCallback((n) => {
    setOperatorMerchant({
      id: n.id,
      name: n.name ?? n.id,
      nodeId: n.nodeId,
      nodeName: n.nodeName ?? undefined,
      outletId: n.outletId ?? undefined,
    });
    // Tell the shell (sidebar banner + "← Platform Console") the operator context changed.
    if (typeof window !== "undefined") window.dispatchEvent(new Event("fbgroup:operator-changed"));
    reload();
  }, [reload]);

  const scope = ready ? deriveScope(nodes, currentNodeId) : null;
  return { ready, loading, error, isOperator, nodes, scope, enter, reload };
}
