import { describe, it, expect } from "vitest";
import type { OrgTreeNode } from "@fbgroup/api-client";
import {
  deriveScope,
  indexTree,
  ancestorChain,
  subtreeIds,
  childrenAt,
  tenantsUnder,
} from "./scope";

// A test tree exercising every shape the walker must handle:
//   g  (cross-tenant GROUP — chain, NOT a boundary)
//   ├─ pl  (Pepper Lunch — TENANT boundary)
//   │   ├─ smw  (storefront leaf, outlet o1)
//   │   └─ rg   (sub-chain WITHIN the tenant — not a boundary)
//   │       └─ ion (storefront leaf, outlet o2)
//   └─ tb  (standalone storefront merchant — sells AND a boundary, outlet o3)
function node(p: Partial<OrgTreeNode> & { id: string; depth: number }): OrgTreeNode {
  return {
    parent_id: null,
    role: "CHAIN",
    name: p.id.toUpperCase(),
    sells: false,
    chain_stopped: false,
    is_settlement_boundary: false,
    subscription_fee: null,
    is_active: true,
    can_manage: true,
    qr_path: null,
    outlet_id: null,
    ...p,
  };
}

const TREE: OrgTreeNode[] = [
  node({ id: "g", depth: 0 }),
  node({ id: "pl", parent_id: "g", depth: 1, is_settlement_boundary: true }),
  node({ id: "smw", parent_id: "pl", depth: 2, role: "STOREFRONT", sells: true, outlet_id: "o1" }),
  node({ id: "rg", parent_id: "pl", depth: 2 }),
  node({ id: "ion", parent_id: "rg", depth: 3, role: "STOREFRONT", sells: true, outlet_id: "o2" }),
  node({ id: "tb", parent_id: "g", depth: 1, role: "STOREFRONT", sells: true, is_settlement_boundary: true, outlet_id: "o3" }),
];

describe("deriveScope — the tree-walker", () => {
  it("null current node → platform root, no tenant", () => {
    const s = deriveScope(TREE, null);
    expect(s.kind).toBe("platform");
    expect(s.tenantId).toBeNull();
    expect(s.node).toBeNull();
    expect(s.breadcrumb).toEqual([]);
  });

  it("unknown current node → falls back to platform root", () => {
    expect(deriveScope(TREE, "nope").kind).toBe("platform");
  });

  it("cross-tenant group (chain above all boundaries) → chain, tenantId null", () => {
    const s = deriveScope(TREE, "g");
    expect(s.kind).toBe("chain");
    expect(s.tenantId).toBeNull(); // above all tenants → per-tenant pages show a directory
  });

  it("a settlement-boundary node → tenant, tenantId = self", () => {
    const s = deriveScope(TREE, "pl");
    expect(s.kind).toBe("tenant");
    expect(s.tenantId).toBe("pl");
    expect(s.tenantName).toBe("PL");
  });

  it("storefront leaf → storefront, tenantId = enclosing boundary, outletId set", () => {
    const s = deriveScope(TREE, "smw");
    expect(s.kind).toBe("storefront");
    expect(s.tenantId).toBe("pl");
    expect(s.outletId).toBe("o1");
  });

  it("sub-chain WITHIN a tenant → chain, tenantId = the ancestor boundary (not null)", () => {
    const s = deriveScope(TREE, "rg");
    expect(s.kind).toBe("chain");
    expect(s.tenantId).toBe("pl"); // boundary is ABOVE → still operable, tenant-wide
    expect(s.outletId).toBeNull();
  });

  it("deep storefront resolves to the nearest boundary above it", () => {
    const s = deriveScope(TREE, "ion");
    expect(s.tenantId).toBe("pl");
    expect(s.outletId).toBe("o2");
  });

  it("standalone storefront merchant (sells AND boundary) → tenantId = self", () => {
    const s = deriveScope(TREE, "tb");
    expect(s.kind).toBe("storefront");
    expect(s.tenantId).toBe("tb"); // its own tenant — operable
    expect(s.outletId).toBe("o3");
  });
});

describe("tree helpers", () => {
  const idx = indexTree(TREE);

  it("breadcrumb is the full root→current chain", () => {
    expect(ancestorChain(idx, "ion").map((n) => n.id)).toEqual(["g", "pl", "rg", "ion"]);
  });

  it("ancestorChain stops at the visible-slice root when parent is absent", () => {
    const slice = indexTree(TREE.filter((n) => n.id !== "g")); // pl's parent 'g' not visible
    expect(ancestorChain(slice, "smw").map((n) => n.id)).toEqual(["pl", "smw"]);
  });

  it("subtreeIds is inclusive and covers all descendants", () => {
    expect(subtreeIds(idx, "pl").sort()).toEqual(["ion", "pl", "rg", "smw"]);
  });

  it("childrenAt(null) returns the visible roots", () => {
    expect(childrenAt(idx, null).map((n) => n.id)).toEqual(["g"]); // tb's parent g is visible → not a root
  });

  it("tenantsUnder lists every settlement boundary in scope", () => {
    expect(tenantsUnder(idx, null).map((n) => n.id).sort()).toEqual(["pl", "tb"]);
    expect(tenantsUnder(idx, "pl").map((n) => n.id)).toEqual(["pl"]);
  });
});
