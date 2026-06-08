import { describe, it, expect } from "vitest";
import { NAV, isNavItemVisible, type NavModuleSet, type NavVisCtx } from "./merchantNav";

const ALL_ON: NavModuleSet = { engagement: true, table_qr: true, pos: true };
// isSuper bypasses the permission gate so these tests isolate the MODULE gate.
const ctx = (modules: NavModuleSet): NavVisCtx => ({ modules, pipelineEnabled: true, perms: null, isSuper: true });
const item = (key: string) => NAV.find((n) => n.key === key)!;

describe("merchant nav — menu reacts to module toggles", () => {
  it("all modules on → engagement + ordering items visible", () => {
    expect(isNavItemVisible(item("crm"), ctx(ALL_ON))).toBe(true);
    expect(isNavItemVisible(item("orders"), ctx(ALL_ON))).toBe(true);
  });

  it("Engagement off → CRM/campaigns/rfm hidden; ordering still shows", () => {
    const m = { ...ALL_ON, engagement: false };
    expect(isNavItemVisible(item("crm"), ctx(m))).toBe(false);
    expect(isNavItemVisible(item("campaigns"), ctx(m))).toBe(false);
    expect(isNavItemVisible(item("rfm"), ctx(m))).toBe(false);
    expect(isNavItemVisible(item("orders"), ctx(m))).toBe(true);
  });

  it("Table QR off → orders/menu/tables hidden; CRM still shows", () => {
    const m = { ...ALL_ON, table_qr: false };
    expect(isNavItemVisible(item("orders"), ctx(m))).toBe(false);
    expect(isNavItemVisible(item("menu"), ctx(m))).toBe(false);
    expect(isNavItemVisible(item("tables"), ctx(m))).toBe(false);
    expect(isNavItemVisible(item("crm"), ctx(m))).toBe(true);
  });

  it("core (Settings/Team) always visible regardless of modules", () => {
    const off: NavModuleSet = { engagement: false, table_qr: false, pos: false };
    expect(isNavItemVisible(item("settings"), ctx(off))).toBe(true);
    expect(isNavItemVisible(item("team"), ctx(off))).toBe(true);
  });

  it("Reports hidden only when ALL modules are off", () => {
    expect(isNavItemVisible(item("reports"), ctx({ engagement: false, table_qr: true, pos: false }))).toBe(true);
    expect(isNavItemVisible(item("reports"), ctx({ engagement: false, table_qr: false, pos: false }))).toBe(false);
  });

  it("permission gate still applies within an enabled module", () => {
    const noPerms: NavVisCtx = { modules: ALL_ON, pipelineEnabled: true, perms: new Set<string>(), isSuper: false };
    expect(isNavItemVisible(item("crm"), noPerms)).toBe(false);          // engagement on, but lacks crm.view
  });
});
