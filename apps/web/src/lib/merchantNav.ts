// Merchant sidebar nav manifest + visibility logic — extracted so the "menu reacts to the module
// toggle" rule is pure + unit-testable (merchantNav.test.ts). The component (MerchantSidebar) only
// renders; what shows is decided here by: module enabled × RBAC permission × (pipeline flag).
import {
  Users, BarChart3, Sparkles, ReceiptText, Filter, Megaphone, PieChart,
  BookOpen, QrCode, UserCog, ListChecks, CreditCard, Printer, Settings as SettingsIcon,
  type LucideIcon,
} from "lucide-react";

export type ActiveKey =
  | "crm" | "reports" | "insights" | "orders" | "pipeline" | "campaigns"
  | "menu" | "tables" | "team" | "rfm" | "settings" | "tasks" | "pos_staff" | "pos_settings";

// Which of the 3 modules an item belongs to (drives show/hide on the toggle). "reports" = analytics,
// shown if ANY module is on; "core" = always (Admin).
export type NavModule = "engagement" | "table_qr" | "pos" | "reports" | "core";

export type NavItem = {
  key: ActiveKey;
  label: string;
  href: string;
  icon: LucideIcon;
  module: NavModule;
  perm?: string;             // permission the page's API requires (server still enforces)
  flag?: "pipeline_enabled"; // a sub-feature toggle
  sensitive?: boolean;       // owner-only; stays hidden until permissions load
  scope?: "group" | "storefront" | "both";
};

export const NAV: NavItem[] = [
  { key: "crm", label: "CRM & Analytics", href: "/merchant/crm", icon: Users, module: "engagement", perm: "crm.view", scope: "group" },
  { key: "rfm", label: "RFM Analytics", href: "/merchant/rfm", icon: PieChart, module: "engagement", perm: "report.view", scope: "group" },
  { key: "campaigns", label: "Campaigns", href: "/merchant/campaigns", icon: Megaphone, module: "engagement", perm: "campaign.manage", scope: "group" },
  { key: "pipeline", label: "Pipeline", href: "/merchant/pipeline", icon: Filter, module: "engagement", perm: "crm.view", flag: "pipeline_enabled", scope: "group" },
  { key: "insights", label: "AI Insights", href: "/merchant/insights", icon: Sparkles, module: "engagement", perm: "report.view", scope: "group" },
  { key: "tasks", label: "My Tasks", href: "/merchant/tasks", icon: ListChecks, module: "engagement", perm: "crm.view", scope: "group" },
  { key: "orders", label: "Orders", href: "/merchant/orders", icon: ReceiptText, module: "table_qr", perm: "order.view", scope: "group" },
  { key: "menu", label: "Menu Editor", href: "/merchant/menu", icon: BookOpen, module: "table_qr", perm: "menu.manage", scope: "both" },
  { key: "tables", label: "Tables & QR", href: "/merchant/tables", icon: QrCode, module: "table_qr", perm: "outlet.manage", scope: "storefront" },
  { key: "pos_staff", label: "Staff & PINs", href: "/merchant/pos-staff", icon: CreditCard, module: "pos", perm: "user.manage", sensitive: true, scope: "both" },
  { key: "pos_settings", label: "POS Settings", href: "/merchant/pos-settings", icon: Printer, module: "pos", perm: "merchant.manage", sensitive: true, scope: "both" },
  { key: "reports", label: "Reports", href: "/merchant/reports", icon: BarChart3, module: "reports", perm: "report.view", scope: "both" },
  { key: "team", label: "Team", href: "/merchant/team", icon: UserCog, module: "core", perm: "user.manage", sensitive: true, scope: "group" },
  { key: "settings", label: "Settings", href: "/merchant/settings", icon: SettingsIcon, module: "core", perm: "merchant.manage", sensitive: true, scope: "group" },
];

// Sections grouped BY MODULE — a whole section disappears when its module is off (empty → hidden).
export const NAV_SECTIONS: { title: string; keys: ActiveKey[] }[] = [
  { title: "Intelligence", keys: ["crm", "rfm", "campaigns", "pipeline", "insights", "tasks"] },
  { title: "Ordering", keys: ["orders", "menu", "tables"] },
  { title: "Point of Sale", keys: ["pos_staff", "pos_settings"] },
  { title: "Reports", keys: ["reports"] },
  { title: "Admin", keys: ["team", "settings"] },
];

export interface NavModuleSet {
  engagement: boolean;
  table_qr: boolean;
  pos: boolean;
}

export interface NavVisCtx {
  modules: NavModuleSet;
  pipelineEnabled: boolean;
  perms: Set<string> | null;   // null = permissions not yet loaded
  isSuper: boolean;
}

export function moduleOn(m: NavModule, modules: NavModuleSet): boolean {
  switch (m) {
    case "core": return true;
    case "engagement": return modules.engagement;
    case "table_qr": return modules.table_qr;
    case "pos": return modules.pos;
    case "reports": return modules.engagement || modules.table_qr || modules.pos;
    default: return true;
  }
}

/** The single rule the sidebar renders by: module ON × permission × (pipeline flag). */
export function isNavItemVisible(item: NavItem, ctx: NavVisCtx): boolean {
  if (!moduleOn(item.module, ctx.modules)) return false;                 // module toggled off → hide
  if (item.flag === "pipeline_enabled" && !ctx.pipelineEnabled) return false;
  if (!item.perm) return true;
  if (ctx.isSuper) return true;
  if (ctx.perms === null) return !item.sensitive;                        // pre-load: broad optimistic, owner-only hidden
  return ctx.perms.has(item.perm);
}
