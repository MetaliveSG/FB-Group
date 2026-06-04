// Tree-walker core for the unified tree-scoped console (see docs/architecture-unified-console.md).
//
// Pure functions over the flat OrgTreeNode list returned by GET /org/tree (the client assembles the
// tree via `parent_id`). Given a "current node" the user has navigated to, derive their Scope: where
// they sit, the enclosing tenant boundary, and the breadcrumb. NO React, NO fetch here — this is the
// testable concept (lib/scope.test.ts). The hook (lib/useScope.ts) and UI build on top.
//
// Tenant boundary = the nearest `is_settlement_boundary` ancestor-or-self. That node is "the merchant"
// — the loyalty/CRM/settlement ring (CLAUDE.md: CRM/Orders/Settings stay tenant-wide). `tenantId == null`
// means the current node is ABOVE all tenant boundaries (operator at root, or a cross-tenant group) →
// per-tenant pages must show a directory ("pick a merchant"), never call the API with a null merchant_id.

import type { OrgTreeNode } from "@fbgroup/api-client";

export type ScopeKind = "platform" | "chain" | "tenant" | "storefront";

export interface Scope {
  /** The node the user is focused on; null = platform root (operator, nothing entered). */
  currentNodeId: string | null;
  /** Derived from the current node's flags. */
  kind: ScopeKind;
  /** Nearest is_settlement_boundary ancestor-or-self; null = above all tenants. The "merchant". */
  tenantId: string | null;
  tenantName: string | null;
  /** The current node's typed Outlet, iff it's a Storefront leaf (for Tables/QR scoping). */
  outletId: string | null;
  /** The current node object (null at platform root). */
  node: OrgTreeNode | null;
  /** Root→current ancestor chain (within the caller's visible slice) — the breadcrumb. */
  breadcrumb: OrgTreeNode[];
}

export interface TreeIndex {
  byId: Map<string, OrgTreeNode>;
  /** parent_id → its visible children. */
  childrenOf: Map<string, OrgTreeNode[]>;
  /** Nodes whose parent is not in the visible set — the roots of the caller's slice. */
  roots: OrgTreeNode[];
}

function byNameThenId(a: OrgTreeNode, b: OrgTreeNode): number {
  const an = (a.name ?? a.id).toLowerCase();
  const bn = (b.name ?? b.id).toLowerCase();
  return an < bn ? -1 : an > bn ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

/** Index a flat node list into id/children/roots maps (children + roots sorted by name). */
export function indexTree(nodes: OrgTreeNode[]): TreeIndex {
  const byId = new Map<string, OrgTreeNode>(nodes.map((n) => [n.id, n]));
  const childrenOf = new Map<string, OrgTreeNode[]>();
  const roots: OrgTreeNode[] = [];
  for (const n of nodes) {
    if (n.parent_id && byId.has(n.parent_id)) {
      const arr = childrenOf.get(n.parent_id) ?? [];
      arr.push(n);
      childrenOf.set(n.parent_id, arr);
    } else {
      roots.push(n); // parent not visible (or null) → a root of the caller's visible slice
    }
  }
  childrenOf.forEach((arr) => arr.sort(byNameThenId));
  roots.sort(byNameThenId);
  return { byId, childrenOf, roots };
}

/** Root→node ancestor chain, stopping at the visible-slice boundary. Cycle-safe. */
export function ancestorChain(idx: TreeIndex, nodeId: string): OrgTreeNode[] {
  const chain: OrgTreeNode[] = [];
  const seen = new Set<string>();
  let cur: OrgTreeNode | null = idx.byId.get(nodeId) ?? null;
  while (cur && !seen.has(cur.id)) {
    seen.add(cur.id);
    chain.push(cur);
    cur = cur.parent_id ? idx.byId.get(cur.parent_id) ?? null : null;
  }
  return chain.reverse(); // root → current
}

/** The nearest tenant boundary in a root→current chain (i.e. closest to current). */
function nearestTenant(rootToCurrent: OrgTreeNode[]): OrgTreeNode | null {
  for (let i = rootToCurrent.length - 1; i >= 0; i--) {
    if (rootToCurrent[i].is_settlement_boundary) return rootToCurrent[i];
  }
  return null;
}

/** All node ids in the subtree rooted at `rootId` (inclusive). For rollup/structural scope-down. */
export function subtreeIds(idx: TreeIndex, rootId: string): string[] {
  const out: string[] = [];
  const stack = [rootId];
  const seen = new Set<string>();
  while (stack.length) {
    const id = stack.pop()!;
    if (seen.has(id)) continue;
    seen.add(id);
    out.push(id);
    for (const c of idx.childrenOf.get(id) ?? []) stack.push(c.id);
  }
  return out;
}

/** Immediate children to show in a directory at `currentNodeId` (roots when null). */
export function childrenAt(idx: TreeIndex, currentNodeId: string | null): OrgTreeNode[] {
  if (!currentNodeId) return idx.roots;
  return idx.childrenOf.get(currentNodeId) ?? [];
}

/** Every tenant-boundary node in the subtree at/below `currentNodeId` (roots when null) — the
 *  selectable "merchants" for a per-tenant page's directory when the caller sits above a boundary. */
export function tenantsUnder(idx: TreeIndex, currentNodeId: string | null): OrgTreeNode[] {
  const ids = currentNodeId
    ? subtreeIds(idx, currentNodeId)
    : idx.roots.flatMap((r) => subtreeIds(idx, r.id));
  return ids
    .map((id) => idx.byId.get(id)!)
    .filter((n) => n.is_settlement_boundary)
    .sort(byNameThenId);
}

/** THE tree-walker: derive the Scope at `currentNodeId` (null = platform root). Pure. */
export function deriveScope(nodes: OrgTreeNode[], currentNodeId: string | null): Scope {
  const idx = indexTree(nodes);
  if (!currentNodeId || !idx.byId.has(currentNodeId)) {
    return {
      currentNodeId: null,
      kind: "platform",
      tenantId: null,
      tenantName: null,
      outletId: null,
      node: null,
      breadcrumb: [],
    };
  }
  const node = idx.byId.get(currentNodeId)!;
  const breadcrumb = ancestorChain(idx, currentNodeId);
  const tenant = nearestTenant(breadcrumb);
  const kind: ScopeKind = node.sells
    ? "storefront"
    : node.is_settlement_boundary
    ? "tenant"
    : "chain";
  return {
    currentNodeId,
    kind,
    tenantId: tenant?.id ?? null,
    tenantName: tenant?.name ?? null,
    outletId: node.sells ? node.outlet_id ?? null : null,
    node,
    breadcrumb,
  };
}
