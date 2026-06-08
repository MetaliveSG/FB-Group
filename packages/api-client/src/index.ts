// ============================================================
// FB Group F&B Platform — Typed API Client
// ============================================================

// ─── Types ───────────────────────────────────────────────────

export interface Modifier {
  id: string;
  name: string;
  price_delta: number;
}

export interface MenuItem {
  id: string;
  name: string;
  description: string;
  price: number;
  image_url: string | null;
  is_available: boolean;
  modifiers: Modifier[];
}

export interface MenuCategory {
  id: string;
  name: string;
  sort_order: number;
  items: MenuItem[];
}

export interface Menu {
  id: string;
  name: string;
  categories: MenuCategory[];
}

export interface Merchant {
  id: string;
  name: string;
}

export interface Brand {
  id: string;
  name: string;
}

export interface Outlet {
  id: string;
  name: string;
  address: string;
}

export interface Table {
  id: string;
  label: string;
}

export interface StallRef {
  menu_id: string;
  stall_name: string;
  cuisine: string | null;
  logo: string | null;
  is_open: boolean;
  item_count: number;
  /** Full-ordering page for this stall when it's a dedicated storefront venue; null for a
   *  shared-outlet foodcourt stall (the group browse opens its read-only sheet instead). */
  order_path?: string | null;
}

export interface QrResolution {
  qr_token: string;
  merchant: Merchant;
  brand: Brand;
  outlet: Outlet;
  table: Table;
  // Foodcourt: an outlet may host many stalls. `stalls` always lists them; `is_foodcourt`
  // = stalls.length > 1. `menu` is the inline single menu (restaurant/single stall —
  // backward compat); null for a foodcourt — fetch one via resolveStallMenu().
  is_foodcourt: boolean;
  stalls: StallRef[];
  menu: Menu | null;
  // Module flags (Phase 2): ordering_enabled off (rewards on) → rewards-only landing.
  ordering_enabled: boolean;
  rewards_enabled: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  actor: string;
  customer?: {
    id: string;
    email: string | null;
    phone: string | null;
    full_name: string | null;
    birthday: string | null;
    marketing_consent?: boolean;
  };
  user?: {
    id: string;
    email: string;
    full_name: string;
  };
}

export interface OtpRequestResponse {
  message: string;
  debug_code?: string;
}

export interface OrderItemModifier {
  name: string;
  price_delta: number;
}

export interface OrderItem {
  name_snapshot: string;
  unit_price: number;
  quantity: number;
  line_total: number;
  modifiers: OrderItemModifier[];
}

export interface OrderOut {
  id: string;
  subtotal: number;
  service_charge: number;
  tax: number;
  total: number;
  status: string;
  items: OrderItem[];
}

export interface MerchantOrder {
  id: string;
  status: string;
  channel: string;
  created_at: string;
  subtotal: number;
  service_charge: number;
  tax: number;
  total: number;
  outlet_name: string;
  customer_name: string | null;
  table_label: string | null;
  items: OrderItem[];
}

export interface CheckoutResponse {
  payment: {
    id: string;
    method: string;
    amount: number;
    status: string;
    reference: string;
  };
  transaction_id: string;
  points_earned: number;
  order_id: string;
}

export interface CustomerSummary {
  id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  tier: string;
  lifecycle_stage: string;
  total_spend: number;
  avg_spend: number;
  visit_count: number;
  points_balance: number;
  last_visit_at: string | null;
  days_since_last_visit: number | null;
  churn_risk: number;
  churn_label: string;
  segments: string[];
  tags: string[];
  owner_user_id: string | null;
  owner_name: string | null;
  open_tasks: number;
}

export interface SegmentSummary {
  total: number;
  vip: number;
  frequent: number;
  high_spender: number;
  inactive: number;
  new: number;
  low_frequency: number;
  birthday_month: number;
  [key: string]: number;
}

export interface CustomerMetrics {
  total_spend: number;
  avg_spend: number;
  visit_count: number;
  points_balance: number;
  last_visit_at: string | null;
  days_since_last_visit: number | null;
  churn_risk: number;
  churn_label: string;
  first_visit_at: string | null;
  lifetime_points: number;
  visits_per_month: number;
  tier: string;
  lifecycle_stage: string;
  segments: string[];
}

export interface CustomerTransaction {
  id: string;
  amount: number;
  method: string;
  status: string;
  created_at: string;
}

export interface CustomerReward {
  txn_type: string;
  points: number;
  reason: string | null;
  rule_code: string | null;
  created_at: string;
}

export interface CustomerNote {
  id: string;
  body: string;
  created_at: string;
}

export interface CustomerProfile {
  customer: {
    id: string;
    full_name: string | null;
    email: string | null;
    phone: string | null;
    birthday: string | null;
  };
  metrics: CustomerMetrics;
  orders: OrderOut[];
  transactions: CustomerTransaction[];
  rewards: CustomerReward[];
  tags: string[];
  notes: CustomerNote[];
  owner_user_id: string | null;
  owner_name: string | null;
  tasks: TaskOut[];
}

export interface ReportSummary {
  revenue: number;
  orders: number;
  unique_customers: number;
  avg_order_value: number;
  new_customer_revenue: number;
  repeat_customer_revenue: number;
}

export interface SalesPeriod {
  period: string;
  revenue: number;
  orders: number;
}

export interface TopItem {
  name: string;
  quantity: number;
  revenue: number;
}

export interface ForecastPeriod {
  date: string;
  projected_revenue: number;
}

export interface ForecastResponse {
  method: string;
  moving_average: number;
  history: SalesPeriod[];
  forecast: ForecastPeriod[];
  limitations: string;
}

export type PaymentMethod = "cash" | "card" | "nets" | "paywave" | "paynow";

// ─── Round 2: Loyalty / Rewards / Wheel ──────────────────────

export interface LoyaltyRecentTxn {
  txn_type: string;
  points: number;
  reason: string;
  created_at: string;
}

export interface LoyaltySummary {
  points_balance: number;
  lifetime_points: number;
  tier: string;
  next_tier: string | null;
  points_to_next_tier: number;
  visit_count: number;
  recent: LoyaltyRecentTxn[];
}

export interface CatalogItem {
  id: string;
  name: string;
  description: string;
  cost_points: number;
  kind: string;
  value: number;
  can_afford: boolean | null;
}

export interface MyOrder {
  id: string;
  status: string;
  total: number;
  items_count: number;
  summary: string;
  outlet_name: string | null;
  created_at: string;
}

export interface MyVoucher {
  voucher_code: string;
  reward_name: string;
  status: string;          // issued | redeemed | expired | void
  value?: number;          // $ off (0 = free item)
  valid_until?: string | null;
  created_at: string;
}

export interface VoucherRedeemResult {
  voucher_code: string;
  reward_name: string;
  value: number;
  status: string;
  order_id?: string | null;
  discount_amount?: number | null;
  order_total?: number | null;
}

export interface MyProfile {
  full_name: string;
  phone: string | null;
  email: string | null;
  birthday: string | null; // ISO date "YYYY-MM-DD"
  gender: string | null;
}

export interface ProfileUpdate {
  phone?: string;
  region?: string;
  birthday?: string | null;
  gender?: string | null;
  full_name?: string;
}

export interface RedeemResponse {
  voucher_code: string;
  reward_name: string;
  points_balance: number;
}

export interface WheelSegment {
  label: string;
  color: string;
}

export interface WheelConfig {
  spin_cost: number;
  segments: WheelSegment[];
}

export interface SpinPrize {
  kind: string;
  label: string;
  points: number;
  voucher_code: string | null;
}

export interface SpinResponse {
  winning_index: number;
  prize: SpinPrize;
  points_balance: number;
  spin_cost: number;
}

// ─── Round 2: Tasks / Timeline / Owner ───────────────────────

export type TaskPriority = "low" | "normal" | "high";
export type TaskStatus = "open" | "done";

export interface TaskOut {
  id: string;
  title: string;
  description: string;
  due_date: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assignee_user_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TaskCreate {
  title: string;
  description?: string;
  due_date?: string;
  priority?: TaskPriority;
  assignee_user_id?: string;
}

export type TimelineEventType =
  | "order"
  | "payment"
  | "reward_earn"
  | "reward_redeem"
  | "note"
  | "task"
  | "task_done";

export interface TimelineEvent {
  ts: string;
  type: TimelineEventType;
  title: string;
  detail: string;
}

// ─── Round 5: Operator console (platform super-admin) ────────

export interface PlatformOverview {
  gmv: number;
  orders: number;
  active_customers: number;
  merchants_total: number;
  merchants_active: number;
  brands: number;
  outlets: number;
  coalitions: number;
}

export interface MerchantKpi {
  id: string;
  name: string;
  is_active: boolean;
  brands: number;
  outlets: number;
  revenue: number;
  orders: number;
  customers: number;
  owner_email: string | null;
  owner_name: string | null;
  module_flags: Record<string, boolean>;
}

export interface MerchantUpdate {
  name?: string;
  module_flags?: Record<string, boolean>;
}

export interface Coalition {
  id: string;
  name: string;
  is_active: boolean;
  members: string[];
  member_ids: string[];
  member_count: number;
  points_issued: number;
}

export interface CoalitionUpdate {
  name?: string;
  is_active?: boolean;
}

export interface MerchantCreate {
  name: string;
  owner_email: string;
  owner_password: string;
  owner_name?: string;
  kind?: "chain" | "storefront";   // member-tree kind for the new top-level tenant
  subscription_fee?: string;       // per-node SaaS fee
}

export interface MerchantCreateResult {
  merchant_id: string;
  name: string;
  owner_email: string;
  owner_user_id: string;
}

/** The four operator (platform-tier) roles. */
export type OperatorRole = "super_admin" | "platform_admin" | "platform_onboarder" | "platform_support";

export const OPERATOR_ROLE_LABELS: Record<OperatorRole, string> = {
  super_admin: "Owner",
  platform_admin: "Admin",
  platform_onboarder: "Onboarding",
  platform_support: "Support",
};

export interface Operator {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  role: OperatorRole;
  is_self: boolean;
}

export interface OperatorCreate {
  email: string;
  password: string;
  full_name?: string;
  role?: OperatorRole;
}

/** The operator's own platform-tier capabilities — gates operator-console sections/actions. */
export interface PlatformCapabilities {
  permissions: string[];
  is_owner: boolean;
}

// ─── Round 6: Opportunities / pipeline / activities / bulk ───

export type PipelineType = "sales" | "winback";

// Stage names vary per pipeline type, so the stage field is an open string.
// Render columns from the Pipeline.stages array rather than hardcoding these.
export type OpportunityStage = string;

/** Sales-pipeline stages, in board order (used as a fallback / reference). */
export const OPPORTUNITY_STAGES: string[] = [
  "prospecting",
  "qualified",
  "proposal",
  "negotiation",
  "won",
  "lost",
];

export interface Opportunity {
  id: string;
  customer_id: string;
  name: string;
  pipeline_type: PipelineType;
  stage: OpportunityStage;
  amount: number;
  expected_close_date: string | null;
  owner_user_id: string | null;
  closed_at: string | null;
  created_at: string;
}

export interface OpportunityCreate {
  name: string;
  amount: number;
  pipeline_type?: PipelineType;
  stage?: OpportunityStage;
  expected_close_date?: string;
}

export interface PipelineStage {
  stage: OpportunityStage;
  count: number;
  value: number;
  is_open: boolean;
  is_won: boolean;
  is_lost: boolean;
}

export interface Pipeline {
  pipeline_type: PipelineType;
  stages: PipelineStage[];
  open_value: number;
  won_value: number;
  open_count: number;
}

export interface WinbackLaunch {
  customer_ids?: string[];
  rfm_segments?: string[];
  create_campaign?: boolean;
  message_template?: string;
}

export interface WinbackResult {
  targets: number;
  opportunities_created: number;
  campaign_id: string | null;
  campaign_delivered: number;
}

export interface WelcomeVoucherCfg {
  enabled: boolean;
  count: number;
  value: number;
  per_period: "day" | "week" | "month" | null;
  valid_days: number | null;
  name: string;
}

export interface ReceiptCfg {
  company_name: string;
  uen: string;
  address: string;
  phone: string;
  footer: string;
}

export interface MerchantSettings {
  pipeline_enabled: boolean;
  wheel_spin_cost: number;
  jackpot_spin_cost: number;
  rewards_enabled: boolean;
  qr_ordering_enabled: boolean;
  pos_enabled: boolean;
  timezone: string;   // the tenant's canonical reporting timezone (the "books")
  welcome_voucher: WelcomeVoucherCfg;
  receipt: ReceiptCfg;
}

/** Non-sensitive nav booleans any staff member may read (no spin costs / earn rates).
 *  Use this for navigation gating; full MerchantSettings is owner-only (`merchant.manage`). */
export interface NavFlags {
  pipeline_enabled: boolean;
  rewards_enabled: boolean;
  qr_ordering_enabled: boolean;
  pos_enabled: boolean;
  /** Caller holds `merchant.manage` (owner or operator) — gate owner-only nav (Settings/Team) on this. */
  can_manage_merchant: boolean;
}

/** The caller's effective permission codes in a merchant context — drives nav rendering.
 *  `permissions` is expanded (no '*'); `is_super_admin` means "can do everything". */
export interface MyPermissions {
  permissions: string[];
  is_super_admin: boolean;
}

export interface LoyaltyProgram {
  points_per_dollar: number;
  welcome_bonus: number;
  birthday_bonus: number;
}

export interface Promotion {
  id: string;
  label: string;
  multiplier: number;
  starts_on: string | null;
  ends_on: string | null;
  is_active: boolean;
}

export interface PromotionCreate {
  label: string;
  multiplier: number;
  starts_on?: string | null;
  ends_on?: string | null;
}

export type ActivityType = "call" | "email" | "meeting" | "whatsapp" | "note";

export interface Activity {
  id: string;
  activity_type: ActivityType;
  subject: string;
  body: string;
  occurred_at: string | null;
  logged_by_user_id: string | null;
  created_at: string;
}

export interface ActivityCreate {
  activity_type: ActivityType;
  subject: string;
  body?: string;
  occurred_at?: string;
}

export interface BulkResult {
  affected: number;
}

// ─── Round 7: Campaigns & retention ──────────────────────────

export type CampaignType =
  | "whatsapp_promo"
  | "birthday"
  | "winback"
  | "weekday_boost"
  | "new_customer_return"
  | "vip_reward"
  | "voucher";

export const CAMPAIGN_TYPES: CampaignType[] = [
  "whatsapp_promo",
  "birthday",
  "winback",
  "weekday_boost",
  "new_customer_return",
  "vip_reward",
  "voucher",
];

export interface VoucherConfig {
  value: number;
  count?: number;
  per_period?: "day" | "week" | "month" | null;
  valid_days?: number | null;
  name?: string | null;
}

export interface CampaignMetrics {
  audience: number;
  sent: number;
  delivered: number;
  failed: number;
  redeemed: number;
  revenue_generated: number;
  conversion_rate: number;
  cost: number;
  roi: number;
}

export interface CampaignListItem {
  id: string;
  name: string;
  campaign_type: CampaignType;
  segment_key: string | null;
  is_active: boolean;
  created_at: string;
  metrics: CampaignMetrics;
}

export interface Campaign {
  id: string;
  name: string;
  campaign_type: CampaignType;
  segment_key: string | null;
  message_template: string;
  reward_points: number;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
}

export interface CampaignMessage {
  id: string;
  customer_id: string;
  to_address: string;
  body: string;
  status: string;
  provider_ref: string | null;
  attempts: number;
  created_at: string;
}

export interface CampaignDetail {
  campaign: Campaign;
  metrics: CampaignMetrics;
  messages: CampaignMessage[];
}

export interface CampaignCreate {
  name: string;
  campaign_type: CampaignType;
  segment_key?: string;
  message_template?: string;
  reward_points?: number;
  scope_node_id?: string;     // member-tree node this campaign reaches (subtree); omit = tenant-wide
  voucher?: VoucherConfig;    // if set, the campaign can issue these vouchers to its audience
  starts_at?: string;
  ends_at?: string;
}

export interface AudienceResult {
  audience_size: number;
}

export interface SendResult {
  delivered: number;
  failed: number;
  audience: number;
}

// ─── Round 8: Menu admin / users / RFM ───────────────────────

export interface MenuAdminOutlet {
  outlet_id: string;
  name: string;
  menu_id: string;
}


export interface RfmCustomer {
  customer_id: string;
  name: string;
  recency_days: number;
  frequency: number;
  monetary: number;
  r: number;
  f: number;
  m: number;
  rfm: string;
  segment: string;
}

export interface RfmReport {
  count: number;
  distribution: Record<string, number>;
  customers: RfmCustomer[];
}

// ─── 3x3 Jackpot game ────────────────────────────────────────

export interface JackpotPrize {
  item_name: string;
  item_price: number;
  emoji: string;
  weight: number;
}

export interface JackpotConfig {
  spin_cost: number;
  grid_size: number;
  payline: string;          // "middle_row"
  grand_prize: number;      // progressive pot (persistent; resets to base on a win)
  prizes: JackpotPrize[];
}

export interface JackpotCell {
  item_name: string;
  item_price: number;
  emoji: string;
}

export interface JackpotWin {
  item_name: string;
  item_price: number;
  emoji: string;
  voucher_code: string;
}

export interface JackpotPlay {
  spin_cost: number;
  grid: JackpotCell[][];    // 3 rows × 3 cols; middle row is the payline
  won: boolean;
  prize: JackpotWin | null;
  points_balance: number;
}

// ─── AI Insights advisor ─────────────────────────────────────

export interface AIRecommendation {
  title: string;
  rationale: string;
  action: string;
  priority: "high" | "medium" | "low";
  metric: string | null;
}

export interface AIInsights {
  summary: string;
  highlights: string[];
  recommendations: AIRecommendation[];
  generated_by: "claude" | "heuristic";
  model: string | null;
  fallback_reason: string | null;
  context: Record<string, unknown>;
  generated_at: string;
}

// ─── Round 9: Org structure (brands / outlets / tables) ──────

export interface OrgBrand {
  id: string;
  name: string;
  cuisine_type: string | null;
  is_active: boolean;
  outlets: number;
}

export interface OrgOutlet {
  id: string;
  name: string;
  address: string | null;
  is_active: boolean;
  brand_id: string;
  brand_name: string | null;
  tables: number;
  menu_id: string | null;
}

export interface OrgTable {
  id: string;
  label: string;
  seats: number;
  is_active: boolean;
  qr_token: string | null;
}

// Member tree (org spine) — two node kinds: CHAIN (structural) | STOREFRONT (sells, leaf).
export interface OrgTreeNode {
  id: string;
  parent_id: string | null;
  role: string;            // CHAIN | STOREFRONT
  name: string | null;
  depth: number;
  sells: boolean;
  chain_stopped: boolean;          // a Chain whose children may only be Storefronts
  is_settlement_boundary: boolean; // this Chain is a tenant ("merchant")
  subscription_fee: string | null; // per-node SaaS fee (null = inherit)
  is_active: boolean;
  can_manage: boolean;     // may THIS caller grow the tree beneath this node?
  qr_path: string | null;  // customer-scan link: a Storefront → /t/{token}; a Chain → /t/node/{id}; null if unscannable
  outlet_id?: string | null; // a Storefront's typed Outlet — lets the console scope to it; null for a Chain
}

// A node-scoped customer browse (the "brand / group app" view): the orderable leaf stalls in a
// node's scope. is_group = it's a chain (many stalls) vs a single storefront.
export interface NodeBrowse {
  node_id: string;
  name: string;
  is_group: boolean;
  stalls: StallRef[];
}

export interface OrgTree {
  nodes: OrgTreeNode[];
  can_manage: boolean;
}

// A POS operator (kind="pos") — PIN-only, segregated from web logins, scoped to a storefront.
// `pin` is the readable PIN the owner reveals via the eye (owner choice for low-risk storefront PINs).
export interface PosStaffMember {
  user_id: string;
  full_name: string;
  role: string;            // manager | cashier | staff | finance
  is_active: boolean;
  pin: string | null;
  pin_set: boolean;
}

// A POS operator + its (readable) PIN — returned on create/reset.
export interface PosStaffSecret {
  user_id: string;
  full_name: string;
  role: string;
  pin: string;
}

// A staff login assigned at a member-tree node (role from the palette).
export interface OrgNodeAccount {
  assignment_id: string;
  user_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role: string;            // manager | viewer | finance (web node palette)
  pin_set?: boolean;       // has a POS quick-login PIN
  node_id?: string;        // the node this login is assigned at (subtree listings)
  node_name?: string;
}

export type ModuleState = "inherit" | "on" | "off";
export type ModuleKey = "rewards" | "qr_ordering" | "pos";
export interface OrgNodeModules {
  rewards: ModuleState;        // the node's OWN setting — Customer Engagement
  qr_ordering: ModuleState;    // Table QR
  pos: ModuleState;            // POS
  resolved: { rewards_enabled: boolean; qr_ordering_enabled: boolean; pos_enabled: boolean };
}

// A venue↔stall tenancy edge. rent_type is the foodcourt/coffeeshop switch:
// FIXED = flat $/mo (landlord blind) · GTO = % of turnover (landlord reads it). rate is $/mo for
// FIXED, a percentage for GTO.
export interface Lease {
  id: string;
  venue_id: string;
  tenant_node_id: string;
  tenant_name: string | null;
  rent_type: string;       // FIXED | GTO
  rate: string;
  is_active: boolean;
}

// ─── API Client ──────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Auth resilience (401 → refresh → retry) ──────────────────

/**
 * Auth-related error codes the backend may return on a 401. Includes
 * `not_found` because a stored token's subject id can disappear (e.g. after a
 * DB reseed), which the backend surfaces as 401 + `not_found`. This list is
 * informational only — the decision below treats ANY 401 as an auth failure.
 */
export const AUTH_ERROR_CODES = [
  "token_expired",
  "invalid_token",
  "missing_token",
  "wrong_actor",
  "not_found",
] as const;

/**
 * Pure decision helper: should a failed response trigger a token refresh?
 * ANY 401 on an authenticated request is treated as an auth failure (the
 * error code is not whitelisted), so cases like `not_found` are also handled.
 */
export function shouldAttemptRefresh(status: number, _code?: string): boolean {
  return status === 401;
}

/**
 * Handler the host app registers once to make 401s self-healing.
 * `refresh` is given the access token that just failed; it should locate the
 * matching refresh token, call the refresh endpoint, persist the new tokens,
 * and return the new access token (or null if refresh is impossible/failed,
 * in which case the host should also have cleared its stored tokens).
 */
export interface AuthHandler {
  refresh(failedAccessToken: string): Promise<string | null>;
}

let authHandler: AuthHandler | null = null;

export function setAuthHandler(handler: AuthHandler | null): void {
  authHandler = handler;
}

export function getAuthHandler(): AuthHandler | null {
  return authHandler;
}

/** Refresh tokens against the backend. Throws ApiError on failure. */
export function refresh(baseUrl: string, refreshToken: string): Promise<TokenResponse> {
  return request(baseUrl, "/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

async function request<T>(
  baseUrl: string,
  path: string,
  options: RequestInit = {},
  token?: string,
  // Internal flag: prevents infinite refresh loops (the retry and the
  // /auth/refresh call itself both pass `true`).
  isRetry = false
): Promise<T> {
  const url = `${baseUrl}/api/v1${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let code = "UNKNOWN";
    let message = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as {
        error?: { code?: string; message?: string };
        detail?: unknown;
      };
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
      } else if (body?.detail) {
        message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore parse errors
    }

    // Self-healing: on the first 401 for an authenticated request, try to
    // refresh the token and retry once. The host-registered handler persists
    // the new tokens (or clears them + surfaces login on failure).
    if (token && !isRetry && authHandler && shouldAttemptRefresh(res.status, code)) {
      let newToken: string | null = null;
      try {
        newToken = await authHandler.refresh(token);
      } catch {
        newToken = null;
      }
      if (newToken) {
        return request<T>(baseUrl, path, options, newToken, true);
      }
    }

    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/**
 * Build a `?merchant_id=` query suffix (operator drill-down). Returns "" when
 * no merchant id is provided — merchant owners omit it and default to their own.
 */
export function mq(merchantId?: string): string {
  return merchantId ? `?merchant_id=${encodeURIComponent(merchantId)}` : "";
}

// ─── Public API functions ─────────────────────────────────────

export function resolveQr(baseUrl: string, token: string): Promise<QrResolution> {
  return fetch(`${baseUrl}/api/v1/qr/${token}`).then(async (res) => {
    if (!res.ok) throw new ApiError(res.status, "QR_ERROR", "Failed to resolve QR token");
    return res.json() as Promise<QrResolution>;
  });
}

// Node-scoped browse — a Chain/group's leaf stalls (the "brand app" view).
export function resolveNodeBrowse(baseUrl: string, nodeId: string): Promise<NodeBrowse> {
  return fetch(`${baseUrl}/api/v1/qr/node/${nodeId}`).then(async (res) => {
    if (!res.ok) throw new ApiError(res.status, "NODE_ERROR", "Failed to resolve location");
    return res.json() as Promise<NodeBrowse>;
  });
}

export function resolveNodeMenu(baseUrl: string, nodeId: string, menuId: string): Promise<Menu> {
  return fetch(`${baseUrl}/api/v1/qr/node/${nodeId}/menu/${menuId}`).then(async (res) => {
    if (!res.ok) throw new ApiError(res.status, "MENU_ERROR", "Failed to resolve stall menu");
    return res.json() as Promise<Menu>;
  });
}

export function resolveStallMenu(baseUrl: string, token: string, menuId: string): Promise<Menu> {
  return fetch(`${baseUrl}/api/v1/qr/${token}/menu/${menuId}`).then(async (res) => {
    if (!res.ok) throw new ApiError(res.status, "MENU_ERROR", "Failed to resolve stall menu");
    return res.json() as Promise<Menu>;
  });
}

export function otpRequest(baseUrl: string, phone: string, region: string = "SG"): Promise<OtpRequestResponse> {
  return request(baseUrl, "/auth/customer/otp/request", {
    method: "POST",
    body: JSON.stringify({ phone, region }),
  });
}

export interface ConsentInput {
  accepted_terms?: boolean;     // notice acknowledgement — required to create a NEW account
  marketing_opt_in?: boolean;   // express opt-in to promotional messages
  consent_merchant_id?: string; // the data-controller (loyalty domain) from the QR context
}

export function otpVerify(
  baseUrl: string,
  phone: string,
  code: string,
  full_name?: string,
  region: string = "SG",
  consent?: ConsentInput
): Promise<TokenResponse> {
  return request(baseUrl, "/auth/customer/otp/verify", {
    method: "POST",
    body: JSON.stringify({ phone, code, full_name, region, ...consent }),
  });
}

/** Grant or withdraw marketing consent (PDPA withdrawal right). Returns the updated customer. */
export function updateCustomerConsent(
  baseUrl: string,
  token: string,
  marketing_opt_in: boolean,
  merchant_id?: string
): Promise<TokenResponse["customer"]> {
  return request(baseUrl, "/auth/customer/consent", {
    method: "POST",
    body: JSON.stringify({ marketing_opt_in, merchant_id }),
  }, token);
}

export function customerRegister(
  baseUrl: string,
  data: { email: string; password: string; full_name?: string; phone?: string; birthday?: string }
): Promise<TokenResponse> {
  return request(baseUrl, "/auth/customer/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function customerLogin(
  baseUrl: string,
  email: string,
  password: string
): Promise<TokenResponse> {
  return request(baseUrl, "/auth/customer/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function staffLogin(
  baseUrl: string,
  email: string,
  password: string
): Promise<TokenResponse> {
  return request(baseUrl, "/auth/staff/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function createOrder(
  baseUrl: string,
  token: string,
  data: {
    qr_token: string;
    items: { menu_item_id: string; quantity: number; modifier_ids?: string[] }[];
    order_type?: string;
  }
): Promise<OrderOut> {
  return request(baseUrl, "/orders", { method: "POST", body: JSON.stringify(data) }, token);
}

export function checkout(
  baseUrl: string,
  token: string,
  orderId: string,
  method: PaymentMethod,
  force_outcome?: string
): Promise<CheckoutResponse> {
  return request(
    baseUrl,
    `/orders/${orderId}/checkout`,
    { method: "POST", body: JSON.stringify({ method, force_outcome }) },
    token
  );
}

// ── POS (staff) ────────────────────────────────────────────────────
export interface ReceiptPayload {
  company: { name: string; uen: string; address: string; phone: string };
  outlet: { name: string; address: string };
  stall: string | null;
  order_id: string;
  table_label: string | null;
  created_at: string;
  items: { name: string; quantity: number; line_total: number; modifiers: string[] }[];
  subtotal: number; service_charge: number; tax: number; discount: number;
  voucher_code: string | null; total: number;
  payment: { method: string; status: string; reference: string | null } | null;
  points_earned: number | null;
  footer: string;
}

/** POS PIN quick-login → staff token. */
export function pinLogin(baseUrl: string, merchant_id: string, outlet_id: string, pin: string): Promise<TokenResponse> {
  return request(baseUrl, "/auth/staff/pin-login", { method: "POST", body: JSON.stringify({ merchant_id, outlet_id, pin }) });
}

/** Staff creates a walk-in order (POS). */
export function createManualOrder(
  baseUrl: string,
  token: string,
  data: {
    outlet_id: string;
    items: { menu_item_id: string; quantity: number; modifier_ids?: string[] }[];
    table_id?: string;
    customer_phone?: string;
    order_type?: string;
  }
): Promise<OrderOut> {
  return request(baseUrl, "/orders/manual", { method: "POST", body: JSON.stringify(data) }, token);
}

/** Staff takes payment for a walk-in order (mock). */
export function cashierCheckout(
  baseUrl: string,
  token: string,
  orderId: string,
  method: PaymentMethod,
  force_outcome?: string
): Promise<CheckoutResponse> {
  return request(baseUrl, `/orders/${orderId}/cashier-checkout`,
    { method: "POST", body: JSON.stringify({ method, force_outcome }) }, token);
}

export function getReceipt(baseUrl: string, token: string, orderId: string): Promise<ReceiptPayload> {
  return request(baseUrl, `/orders/${orderId}/receipt`, {}, token);
}

export interface VoidResult {
  order_id: string;
  status: string;
  amount: number;
  points_reversed: number;
  voucher_restored: string | null;
}

/** Void a paid sale. Requires an order.void-capable token (Supervisor+) — the POS passes a token
 *  from a momentary supervisor PIN-login so a cashier can get manager authorization. */
export function voidOrder(baseUrl: string, token: string, orderId: string, reason = ""): Promise<VoidResult> {
  return request(baseUrl, `/orders/${orderId}/void`, { method: "POST", body: JSON.stringify({ reason }) }, token);
}

/** Staff: set/reset a node account's POS PIN. */
export function setStaffPin(
  baseUrl: string, token: string, nodeId: string, userId: string, pin: string, merchantId?: string
): Promise<void> {
  return request(baseUrl, `/org/nodes/${nodeId}/accounts/${userId}/pin${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify({ pin }) }, token);
}

/** Staff: an attached diner's unused vouchers at this merchant. */
export function dinerVouchers(
  baseUrl: string, token: string, customerId: string, merchantId?: string
): Promise<MyVoucher[]> {
  const q = new URLSearchParams();
  if (merchantId) q.set("merchant_id", merchantId);
  return request(baseUrl, `/vouchers/diner/${customerId}?${q.toString()}`, {}, token);
}

export function crmCustomers(
  baseUrl: string,
  token: string,
  params?: { segment?: string; search?: string },
  merchantId?: string
): Promise<CustomerSummary[]> {
  const qs = new URLSearchParams();
  if (params?.segment) qs.set("segment", params.segment);
  if (params?.search) qs.set("search", params.search);
  if (merchantId) qs.set("merchant_id", merchantId);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request(baseUrl, `/crm/customers${query}`, {}, token);
}

export function crmSegments(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<SegmentSummary> {
  return request(baseUrl, `/crm/segments${mq(merchantId)}`, {}, token);
}

export function crmCustomerProfile(
  baseUrl: string,
  token: string,
  customerId: string,
  merchantId?: string
): Promise<CustomerProfile> {
  return request(baseUrl, `/crm/customers/${customerId}${mq(merchantId)}`, {}, token);
}

export function addTag(
  baseUrl: string,
  token: string,
  customerId: string,
  tag: string
): Promise<unknown> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/tags`,
    { method: "POST", body: JSON.stringify({ tag }) },
    token
  );
}

export function addNote(
  baseUrl: string,
  token: string,
  customerId: string,
  body: string
): Promise<unknown> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/notes`,
    { method: "POST", body: JSON.stringify({ body }) },
    token
  );
}

export function reportSummary(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<ReportSummary> {
  return request(baseUrl, `/reports/summary${mq(merchantId)}`, {}, token);
}

export function reportSales(
  baseUrl: string,
  token: string,
  params?: { granularity?: string; days?: number },
  merchantId?: string
): Promise<SalesPeriod[]> {
  const qs = new URLSearchParams();
  if (params?.granularity) qs.set("granularity", params.granularity);
  if (params?.days != null) qs.set("days", String(params.days));
  if (merchantId) qs.set("merchant_id", merchantId);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request(baseUrl, `/reports/sales${query}`, {}, token);
}

export function reportTopItems(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<TopItem[]> {
  return request(baseUrl, `/reports/top-items${mq(merchantId)}`, {}, token);
}

export function reportForecast(
  baseUrl: string,
  token: string,
  horizon?: number,
  merchantId?: string
): Promise<ForecastResponse> {
  const qs = new URLSearchParams();
  if (horizon != null) qs.set("horizon", String(horizon));
  if (merchantId) qs.set("merchant_id", merchantId);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request(baseUrl, `/reports/forecast${query}`, {}, token);
}

// ─── Node-scoped Reports dashboard ───────────────────────────
// SOURCE scope: Platform (operators only, all merchants) | a node (its subtree). A node account is
// confined to its node + downline by the server. Date range = inclusive YYYY-MM-DD start/end.
export interface ReportScope { merchantId?: string; nodeId?: string; platform?: boolean; start?: string; end?: string; tz?: string; }
export interface ReportTotals {
  revenue: number; orders: number; unique_customers: number; avg_order_value: number;
  new_customer_revenue: number; repeat_customer_revenue: number;
  timezone: string;   // the effective report timezone (the UI labels it + defaults the dropdown)
}
export interface PeakHour { hour: number; orders: number; revenue: number; }
export interface PaymentSplitRow { method: string; amount: number; count: number; }
export interface RollupRow {
  node_id: string; name: string; role: string; sells: boolean;
  revenue: number; orders: number; avg_order_value: number;
}

function reportQuery(scope?: ReportScope, extra?: Record<string, string | number | undefined>): string {
  const qs = new URLSearchParams();
  if (scope?.platform) qs.set("platform", "true");
  if (scope?.nodeId) qs.set("node_id", scope.nodeId);
  if (scope?.merchantId) qs.set("merchant_id", scope.merchantId);
  if (scope?.start) qs.set("start", scope.start);
  if (scope?.end) qs.set("end", scope.end);
  if (scope?.tz) qs.set("tz", scope.tz);
  for (const [k, v] of Object.entries(extra ?? {})) if (v != null) qs.set(k, String(v));
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export function reportsSummary(b: string, t: string, scope?: ReportScope): Promise<ReportTotals> {
  return request(b, `/reports/summary${reportQuery(scope)}`, {}, t);
}
export function reportsSales(b: string, t: string, scope?: ReportScope, granularity = "day"): Promise<SalesPeriod[]> {
  return request(b, `/reports/sales${reportQuery(scope, { granularity })}`, {}, t);
}
export function reportsTopItems(b: string, t: string, scope?: ReportScope, limit = 8): Promise<TopItem[]> {
  return request(b, `/reports/top-items${reportQuery(scope, { limit })}`, {}, t);
}
export function reportsPeakHours(b: string, t: string, scope?: ReportScope): Promise<PeakHour[]> {
  return request(b, `/reports/peak-hours${reportQuery(scope)}`, {}, t);
}
export function reportsPayments(b: string, t: string, scope?: ReportScope): Promise<PaymentSplitRow[]> {
  return request(b, `/reports/payments${reportQuery(scope)}`, {}, t);
}
export function reportsRollup(b: string, t: string, scope?: ReportScope): Promise<RollupRow[]> {
  return request(b, `/reports/rollup${reportQuery(scope)}`, {}, t);
}

// ─── Round 2: Customer loyalty / rewards / wheel ─────────────

export function getLoyalty(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<LoyaltySummary> {
  return request(baseUrl, `/me/loyalty?merchant_id=${encodeURIComponent(merchantId)}`, {}, token);
}

export function getMyOrders(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<MyOrder[]> {
  return request(baseUrl, `/me/orders?merchant_id=${encodeURIComponent(merchantId)}`, {}, token);
}

export function getOrder(baseUrl: string, token: string, orderId: string): Promise<OrderOut> {
  return request(baseUrl, `/orders/${encodeURIComponent(orderId)}`, {}, token);
}

export function getMerchantOrders(
  baseUrl: string,
  token: string,
  opts: { status?: string; outletId?: string; limit?: number } = {},
  merchantId?: string
): Promise<MerchantOrder[]> {
  const p = new URLSearchParams();
  if (merchantId) p.set("merchant_id", merchantId);
  if (opts.status) p.set("status", opts.status);
  if (opts.outletId) p.set("outlet_id", opts.outletId);
  if (opts.limit) p.set("limit", String(opts.limit));
  const qs = p.toString();
  return request(baseUrl, `/orders${qs ? `?${qs}` : ""}`, {}, token);
}

export function getMyProfile(baseUrl: string, token: string): Promise<MyProfile> {
  return request(baseUrl, `/me/profile`, {}, token);
}

export function updateMyProfile(
  baseUrl: string,
  token: string,
  body: ProfileUpdate
): Promise<MyProfile> {
  return request(baseUrl, `/me/profile`, { method: "PATCH", body: JSON.stringify(body) }, token);
}

export function getMyVouchers(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<MyVoucher[]> {
  return request(baseUrl, `/me/vouchers?merchant_id=${encodeURIComponent(merchantId)}`, {}, token);
}

/** Staff: dry-run validate a scanned/typed voucher (no mutation). */
export function previewVoucher(
  baseUrl: string,
  token: string,
  code: string,
  opts: { orderId?: string; merchantId?: string } = {}
): Promise<{ voucher_code: string; reward_name: string; value: number; min_spend: number; valid_until: string | null; valid: boolean }> {
  const q = new URLSearchParams();
  if (opts.orderId) q.set("order_id", opts.orderId);
  if (opts.merchantId) q.set("merchant_id", opts.merchantId);
  return request(baseUrl, `/vouchers/${encodeURIComponent(code)}?${q.toString()}`, {}, token);
}

/** Staff/cashier: redeem a voucher (scan QR / enter code) → marks used + applies to the order. */
export function redeemVoucher(
  baseUrl: string,
  token: string,
  code: string,
  body: { order_id?: string; merchant_id?: string }
): Promise<VoucherRedeemResult> {
  return request(baseUrl, `/vouchers/${encodeURIComponent(code)}/redeem`, {
    method: "POST",
    body: JSON.stringify(body),
  }, token);
}

export function getRewardsCatalog(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<CatalogItem[]> {
  return request(
    baseUrl,
    `/me/rewards/catalog?merchant_id=${encodeURIComponent(merchantId)}`,
    {},
    token
  );
}

export function redeemReward(
  baseUrl: string,
  token: string,
  merchantId: string,
  itemId: string
): Promise<RedeemResponse> {
  return request(
    baseUrl,
    "/me/rewards/redeem",
    { method: "POST", body: JSON.stringify({ merchant_id: merchantId, item_id: itemId }) },
    token
  );
}

export function getWheel(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<WheelConfig> {
  return request(baseUrl, `/me/wheel?merchant_id=${encodeURIComponent(merchantId)}`, {}, token);
}

export function spinWheel(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<SpinResponse> {
  return request(
    baseUrl,
    "/me/wheel/spin",
    { method: "POST", body: JSON.stringify({ merchant_id: merchantId }) },
    token
  );
}

// ─── Round 2: CRM timeline / tasks / owner ───────────────────

export function crmTimeline(
  baseUrl: string,
  token: string,
  customerId: string,
  merchantId?: string
): Promise<TimelineEvent[]> {
  return request(baseUrl, `/crm/customers/${customerId}/timeline${mq(merchantId)}`, {}, token);
}

export function crmCustomerTasks(
  baseUrl: string,
  token: string,
  customerId: string,
  merchantId?: string
): Promise<TaskOut[]> {
  return request(baseUrl, `/crm/customers/${customerId}/tasks${mq(merchantId)}`, {}, token);
}

export function crmCreateTask(
  baseUrl: string,
  token: string,
  customerId: string,
  data: TaskCreate,
  merchantId?: string
): Promise<TaskOut> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/tasks${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function crmUpdateTask(
  baseUrl: string,
  token: string,
  taskId: string,
  status: TaskStatus,
  merchantId?: string
): Promise<TaskOut> {
  return request(
    baseUrl,
    `/crm/tasks/${taskId}${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify({ status }) },
    token
  );
}

export function crmMyTasks(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<TaskOut[]> {
  return request(baseUrl, `/crm/tasks${mq(merchantId)}`, {}, token);
}

export function crmAssignOwner(
  baseUrl: string,
  token: string,
  customerId: string,
  ownerUserId: string | null,
  merchantId?: string
): Promise<unknown> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/owner${mq(merchantId)}`,
    { method: "PUT", body: JSON.stringify({ owner_user_id: ownerUserId }) },
    token
  );
}

// ─── Round 5: Operator console (platform super-admin) ────────

export function platformOverview(baseUrl: string, token: string): Promise<PlatformOverview> {
  return request(baseUrl, "/platform/overview", {}, token);
}

export function platformMerchants(baseUrl: string, token: string): Promise<MerchantKpi[]> {
  return request(baseUrl, "/platform/merchants", {}, token);
}

export function platformCoalitions(baseUrl: string, token: string): Promise<Coalition[]> {
  return request(baseUrl, "/platform/coalitions", {}, token);
}

export function platformCreateMerchant(
  baseUrl: string,
  token: string,
  data: MerchantCreate
): Promise<MerchantCreateResult> {
  return request(
    baseUrl,
    "/platform/merchants",
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function platformSetMerchantActive(
  baseUrl: string,
  token: string,
  merchantId: string,
  isActive: boolean
): Promise<MerchantKpi> {
  return request(
    baseUrl,
    `/platform/merchants/${merchantId}`,
    { method: "PATCH", body: JSON.stringify({ is_active: isActive }) },
    token
  );
}

export function platformUpdateMerchant(
  baseUrl: string,
  token: string,
  merchantId: string,
  data: MerchantUpdate
): Promise<MerchantKpi> {
  return request(
    baseUrl,
    `/platform/merchants/${merchantId}`,
    { method: "PUT", body: JSON.stringify(data) },
    token
  );
}

export function platformOperators(baseUrl: string, token: string): Promise<Operator[]> {
  return request(baseUrl, "/platform/operators", {}, token);
}

/** The calling operator's own platform capabilities (for console section/action gating). */
export function platformMyPermissions(baseUrl: string, token: string): Promise<PlatformCapabilities> {
  return request(baseUrl, "/platform/permissions", {}, token);
}

export function platformInviteOperator(
  baseUrl: string,
  token: string,
  data: OperatorCreate
): Promise<Operator> {
  return request(
    baseUrl,
    "/platform/operators",
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function platformRevokeOperator(
  baseUrl: string,
  token: string,
  operatorId: string
): Promise<void> {
  return request(
    baseUrl,
    `/platform/operators/${operatorId}`,
    { method: "DELETE" },
    token
  );
}

export function platformCreateCoalition(
  baseUrl: string,
  token: string,
  name: string
): Promise<Coalition> {
  return request(
    baseUrl,
    "/platform/coalitions",
    { method: "POST", body: JSON.stringify({ name }) },
    token
  );
}

export function platformUpdateCoalition(
  baseUrl: string,
  token: string,
  coalitionId: string,
  data: CoalitionUpdate
): Promise<Coalition> {
  return request(
    baseUrl,
    `/platform/coalitions/${coalitionId}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
}

export function platformAddCoalitionMember(
  baseUrl: string,
  token: string,
  coalitionId: string,
  merchantId: string
): Promise<Coalition> {
  return request(
    baseUrl,
    `/platform/coalitions/${coalitionId}/members`,
    { method: "POST", body: JSON.stringify({ merchant_id: merchantId }) },
    token
  );
}

export function platformRemoveCoalitionMember(
  baseUrl: string,
  token: string,
  coalitionId: string,
  merchantId: string
): Promise<Coalition> {
  return request(
    baseUrl,
    `/platform/coalitions/${coalitionId}/members/${merchantId}`,
    { method: "DELETE" },
    token
  );
}

// ─── Round 6: Opportunities / pipeline / activities / bulk ───

export function pipeline(
  baseUrl: string,
  token: string,
  pipelineType?: PipelineType,
  merchantId?: string
): Promise<Pipeline> {
  const qs = new URLSearchParams();
  if (pipelineType) qs.set("pipeline_type", pipelineType);
  if (merchantId) qs.set("merchant_id", merchantId);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request(baseUrl, `/crm/pipeline${query}`, {}, token);
}

export function listOpportunities(
  baseUrl: string,
  token: string,
  pipelineType?: PipelineType,
  merchantId?: string
): Promise<Opportunity[]> {
  const qs = new URLSearchParams();
  if (pipelineType) qs.set("pipeline_type", pipelineType);
  if (merchantId) qs.set("merchant_id", merchantId);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request(baseUrl, `/crm/opportunities${query}`, {}, token);
}

export function customerOpportunities(
  baseUrl: string,
  token: string,
  customerId: string,
  merchantId?: string
): Promise<Opportunity[]> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/opportunities${mq(merchantId)}`,
    {},
    token
  );
}

export function createOpportunity(
  baseUrl: string,
  token: string,
  customerId: string,
  data: OpportunityCreate,
  merchantId?: string
): Promise<Opportunity> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/opportunities${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function updateOpportunity(
  baseUrl: string,
  token: string,
  oppId: string,
  data: { stage?: OpportunityStage; amount?: number },
  merchantId?: string
): Promise<Opportunity> {
  return request(
    baseUrl,
    `/crm/opportunities/${oppId}${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
}

export function listActivities(
  baseUrl: string,
  token: string,
  customerId: string,
  merchantId?: string
): Promise<Activity[]> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/activities${mq(merchantId)}`,
    {},
    token
  );
}

export function logActivity(
  baseUrl: string,
  token: string,
  customerId: string,
  data: ActivityCreate,
  merchantId?: string
): Promise<Activity> {
  return request(
    baseUrl,
    `/crm/customers/${customerId}/activities${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function bulkTag(
  baseUrl: string,
  token: string,
  data: { tag: string; customer_ids?: string[]; segment?: string },
  merchantId?: string
): Promise<BulkResult> {
  return request(
    baseUrl,
    `/crm/bulk/tag${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function bulkOwner(
  baseUrl: string,
  token: string,
  data: { owner_user_id?: string | null; customer_ids?: string[]; segment?: string },
  merchantId?: string
): Promise<BulkResult> {
  return request(
    baseUrl,
    `/crm/bulk/owner${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function bulkTask(
  baseUrl: string,
  token: string,
  data: { title: string; priority?: TaskPriority; customer_ids?: string[]; segment?: string },
  merchantId?: string
): Promise<BulkResult> {
  return request(
    baseUrl,
    `/crm/bulk/task${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

// ─── Round 10: Win-back launcher + merchant settings ─────────

export function launchWinback(
  baseUrl: string,
  token: string,
  data: WinbackLaunch,
  merchantId?: string
): Promise<WinbackResult> {
  return request(
    baseUrl,
    `/crm/winback${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function getSettings(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<MerchantSettings> {
  return request(baseUrl, `/org/settings${mq(merchantId)}`, {}, token);
}

/** Nav-only flags — readable by any staff member (owner-only `getSettings` 403s for downline). */
export function getNavFlags(
  baseUrl: string,
  token: string,
  merchantId?: string,
  nodeId?: string
): Promise<NavFlags> {
  const q = new URLSearchParams();
  if (merchantId) q.set("merchant_id", merchantId);
  if (nodeId) q.set("node_id", nodeId);
  const qs = q.toString();
  return request(baseUrl, `/org/nav-flags${qs ? `?${qs}` : ""}`, {}, token);
}

/** Capabilities: the caller's effective permissions in a merchant context (for nav-gating). */
export function getMyPermissions(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<MyPermissions> {
  return request(baseUrl, `/org/permissions${mq(merchantId)}`, {}, token);
}

export function updateSettings(
  baseUrl: string,
  token: string,
  data: {
    pipeline_enabled?: boolean;
    wheel_spin_cost?: number;
    jackpot_spin_cost?: number;
    rewards_enabled?: boolean;
    qr_ordering_enabled?: boolean;
    pos_enabled?: boolean;
    timezone?: string;
    welcome_voucher?: WelcomeVoucherCfg;
    receipt?: ReceiptCfg;
  },
  merchantId?: string
): Promise<MerchantSettings> {
  return request(
    baseUrl,
    `/org/settings${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
}

export function getLoyaltyProgram(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<LoyaltyProgram> {
  return request(baseUrl, `/org/loyalty${mq(merchantId)}`, {}, token);
}

export function updateLoyaltyProgram(
  baseUrl: string,
  token: string,
  data: LoyaltyProgram,
  merchantId?: string
): Promise<LoyaltyProgram> {
  return request(
    baseUrl,
    `/org/loyalty${mq(merchantId)}`,
    { method: "PUT", body: JSON.stringify(data) },
    token
  );
}

export function listPromotions(baseUrl: string, token: string, merchantId?: string): Promise<Promotion[]> {
  return request(baseUrl, `/promotions${mq(merchantId)}`, {}, token);
}

export function createPromotion(
  baseUrl: string,
  token: string,
  data: PromotionCreate,
  merchantId?: string
): Promise<Promotion> {
  return request(baseUrl, `/promotions${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) }, token);
}

export function deactivatePromotion(baseUrl: string, token: string, promoId: string, merchantId?: string): Promise<void> {
  return request(baseUrl, `/promotions/${encodeURIComponent(promoId)}${mq(merchantId)}`,
    { method: "DELETE" }, token);
}

// ─── Round 7: Campaigns & retention ──────────────────────────

export function listCampaigns(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<CampaignListItem[]> {
  return request(baseUrl, `/campaigns${mq(merchantId)}`, {}, token);
}

export function createCampaign(
  baseUrl: string,
  token: string,
  data: CampaignCreate,
  merchantId?: string
): Promise<Campaign> {
  return request(
    baseUrl,
    `/campaigns${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function campaignDetail(
  baseUrl: string,
  token: string,
  campaignId: string,
  merchantId?: string
): Promise<CampaignDetail> {
  return request(baseUrl, `/campaigns/${campaignId}${mq(merchantId)}`, {}, token);
}

export function buildAudience(
  baseUrl: string,
  token: string,
  campaignId: string,
  merchantId?: string
): Promise<AudienceResult> {
  return request(
    baseUrl,
    `/campaigns/${campaignId}/audience${mq(merchantId)}`,
    { method: "POST" },
    token
  );
}

export function issueCampaignVouchers(
  baseUrl: string,
  token: string,
  campaignId: string,
  merchantId?: string
): Promise<{ issued: number }> {
  return request(
    baseUrl,
    `/campaigns/${campaignId}/issue-vouchers${mq(merchantId)}`,
    { method: "POST" },
    token
  );
}

export function sendCampaign(
  baseUrl: string,
  token: string,
  campaignId: string,
  merchantId?: string
): Promise<SendResult> {
  return request(
    baseUrl,
    `/campaigns/${campaignId}/send${mq(merchantId)}`,
    { method: "POST" },
    token
  );
}

export function campaignMetrics(
  baseUrl: string,
  token: string,
  campaignId: string,
  merchantId?: string
): Promise<CampaignMetrics> {
  return request(baseUrl, `/campaigns/${campaignId}/metrics${mq(merchantId)}`, {}, token);
}

export function recordRedemption(
  baseUrl: string,
  token: string,
  campaignId: string,
  data: { customer_id: string; revenue: number; order_id?: string },
  merchantId?: string
): Promise<unknown> {
  return request(
    baseUrl,
    `/campaigns/${campaignId}/redemptions${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

// ─── Round 8: Menu admin ─────────────────────────────────────

export function menuOutlets(
  baseUrl: string,
  token: string,
  merchantId?: string,
  nodeId?: string
): Promise<MenuAdminOutlet[]> {
  const qs = new URLSearchParams();
  if (merchantId) qs.set("merchant_id", merchantId);
  if (nodeId) qs.set("node_id", nodeId);
  const q = qs.toString();
  return request(baseUrl, `/menu-admin/outlets${q ? `?${q}` : ""}`, {}, token);
}

export function outletMenu(
  baseUrl: string,
  token: string,
  outletId: string
): Promise<Menu> {
  return request(baseUrl, `/outlets/${outletId}/menu`, {}, token);
}

export function createCategory(
  baseUrl: string,
  token: string,
  data: { menu_id: string; name: string; sort_order?: number },
  merchantId?: string
): Promise<MenuCategory> {
  return request(
    baseUrl,
    `/menu-admin/categories${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function updateCategory(
  baseUrl: string,
  token: string,
  categoryId: string,
  data: { name?: string; sort_order?: number },
  merchantId?: string
): Promise<MenuCategory> {
  return request(
    baseUrl,
    `/menu-admin/categories/${categoryId}${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
}

export function deleteCategory(
  baseUrl: string,
  token: string,
  categoryId: string,
  merchantId?: string
): Promise<void> {
  return request(
    baseUrl,
    `/menu-admin/categories/${categoryId}${mq(merchantId)}`,
    { method: "DELETE" },
    token
  );
}

export function createMenuItem(
  baseUrl: string,
  token: string,
  data: { category_id: string; name: string; price: number; description?: string; sort_order?: number },
  merchantId?: string
): Promise<MenuItem> {
  return request(
    baseUrl,
    `/menu-admin/items${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function updateMenuItem(
  baseUrl: string,
  token: string,
  itemId: string,
  data: { name?: string; price?: number; description?: string; is_available?: boolean; sort_order?: number },
  merchantId?: string
): Promise<MenuItem> {
  return request(
    baseUrl,
    `/menu-admin/items/${itemId}${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
}

export function deleteMenuItem(
  baseUrl: string,
  token: string,
  itemId: string,
  merchantId?: string
): Promise<void> {
  return request(
    baseUrl,
    `/menu-admin/items/${itemId}${mq(merchantId)}`,
    { method: "DELETE" },
    token
  );
}

export function createModifier(
  baseUrl: string,
  token: string,
  data: { item_id: string; name: string; price_delta?: number },
  merchantId?: string
): Promise<Modifier> {
  return request(
    baseUrl,
    `/menu-admin/modifiers${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function deleteModifier(
  baseUrl: string,
  token: string,
  modifierId: string,
  merchantId?: string
): Promise<void> {
  return request(
    baseUrl,
    `/menu-admin/modifiers/${modifierId}${mq(merchantId)}`,
    { method: "DELETE" },
    token
  );
}


// ─── Round 8: RFM analytics ──────────────────────────────────

export function rfm(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<RfmReport> {
  return request(baseUrl, `/reports/rfm${mq(merchantId)}`, {}, token);
}

export function aiInsights(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<AIInsights> {
  return request(baseUrl, `/reports/ai-insights${mq(merchantId)}`, {}, token);
}

// ─── 3x3 Jackpot — customer-facing -----------------------------

export function getJackpot(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<JackpotConfig> {
  return request(baseUrl, `/me/jackpot?merchant_id=${encodeURIComponent(merchantId)}`, {}, token);
}

export function playJackpot(
  baseUrl: string,
  token: string,
  merchantId: string
): Promise<JackpotPlay> {
  return request(baseUrl, "/me/jackpot/play",
    { method: "POST", body: JSON.stringify({ merchant_id: merchantId }) }, token);
}

// ─── Round 9: Org structure (brands / outlets / tables) ──────

export function orgBrands(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<OrgBrand[]> {
  return request(baseUrl, `/org/brands${mq(merchantId)}`, {}, token);
}

export function createBrand(
  baseUrl: string,
  token: string,
  data: { name: string; cuisine_type?: string },
  merchantId?: string
): Promise<OrgBrand> {
  return request(
    baseUrl,
    `/org/brands${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function updateBrand(
  baseUrl: string,
  token: string,
  brandId: string,
  data: { name?: string; cuisine_type?: string; is_active?: boolean },
  merchantId?: string
): Promise<OrgBrand> {
  return request(
    baseUrl,
    `/org/brands/${brandId}${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
}

export function orgOutlets(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<OrgOutlet[]> {
  return request(baseUrl, `/org/outlets${mq(merchantId)}`, {}, token);
}

export function createOutlet(
  baseUrl: string,
  token: string,
  data: { brand_id: string; name: string; address?: string },
  merchantId?: string
): Promise<OrgOutlet> {
  return request(
    baseUrl,
    `/org/outlets${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function updateOutlet(
  baseUrl: string,
  token: string,
  outletId: string,
  data: { name?: string; address?: string; is_active?: boolean },
  merchantId?: string
): Promise<OrgOutlet> {
  return request(
    baseUrl,
    `/org/outlets/${outletId}${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
}

export function orgTables(
  baseUrl: string,
  token: string,
  outletId: string,
  merchantId?: string
): Promise<OrgTable[]> {
  return request(baseUrl, `/org/outlets/${outletId}/tables${mq(merchantId)}`, {}, token);
}

export function createTable(
  baseUrl: string,
  token: string,
  outletId: string,
  data: { label: string; seats?: number },
  merchantId?: string
): Promise<OrgTable> {
  return request(
    baseUrl,
    `/org/outlets/${outletId}/tables${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function deleteTable(
  baseUrl: string,
  token: string,
  tableId: string,
  merchantId?: string
): Promise<void> {
  return request(
    baseUrl,
    `/org/tables/${tableId}${mq(merchantId)}`,
    { method: "DELETE" },
    token
  );
}

// Org tree (member-tree) — scope-aware, no merchant_id: keyed off the caller's node assignments.
export function orgTree(baseUrl: string, token: string): Promise<OrgTree> {
  return request(baseUrl, `/org/tree`, {}, token);
}

// A freshly-created node + (for a Storefront) its auto-provisioned starter POS team with one-time PINs.
export interface OrgNodeCreated extends OrgTreeNode {
  pos_team: PosStaffSecret[];
}

export function createOrgNode(
  baseUrl: string,
  token: string,
  data: { parent_id: string; role: string; name: string; chain_stopped?: boolean; subscription_fee?: string }
): Promise<OrgNodeCreated> {
  return request(baseUrl, `/org/nodes`, { method: "POST", body: JSON.stringify(data) }, token);
}

// --- POS staff (POS operators) — PIN-only, per storefront -------------------
export function listPosStaff(baseUrl: string, token: string, nodeId: string): Promise<PosStaffMember[]> {
  return request(baseUrl, `/org/nodes/${nodeId}/pos-staff`, {}, token);
}

export function createPosStaff(
  baseUrl: string, token: string, nodeId: string, data: { full_name: string; role: string; pin?: string }
): Promise<PosStaffSecret> {
  return request(baseUrl, `/org/nodes/${nodeId}/pos-staff`, { method: "POST", body: JSON.stringify(data) }, token);
}

// pin omitted/undefined → server auto-generates a fresh storefront-unique PIN.
export function resetPosStaffPin(baseUrl: string, token: string, nodeId: string, userId: string, pin?: string): Promise<PosStaffSecret> {
  return request(baseUrl, `/org/nodes/${nodeId}/pos-staff/${userId}/reset-pin`,
    { method: "POST", body: JSON.stringify({ pin: pin ?? null }) }, token);
}

export function deletePosStaff(baseUrl: string, token: string, nodeId: string, userId: string): Promise<void> {
  return request(baseUrl, `/org/nodes/${nodeId}/pos-staff/${userId}`, { method: "DELETE" }, token);
}

export function updateOrgNode(
  baseUrl: string,
  token: string,
  nodeId: string,
  data: { name?: string; is_active?: boolean; chain_stopped?: boolean; subscription_fee?: string }
): Promise<OrgTreeNode> {
  return request(baseUrl, `/org/nodes/${nodeId}`, { method: "PATCH", body: JSON.stringify(data) }, token);
}

// Node logins (staff at a member-tree node) — scope-aware, no merchant_id.
export function listNodeAccounts(baseUrl: string, token: string, nodeId: string, subtree = false): Promise<OrgNodeAccount[]> {
  return request(baseUrl, `/org/nodes/${nodeId}/accounts${subtree ? "?subtree=true" : ""}`, {}, token);
}

export function createNodeAccount(
  baseUrl: string,
  token: string,
  nodeId: string,
  data: { email: string; password: string; full_name?: string; role: string }
): Promise<OrgNodeAccount> {
  return request(baseUrl, `/org/nodes/${nodeId}/accounts`, { method: "POST", body: JSON.stringify(data) }, token);
}

export function revokeNodeAccount(baseUrl: string, token: string, nodeId: string, assignmentId: string): Promise<void> {
  return request(baseUrl, `/org/nodes/${nodeId}/accounts/${assignmentId}`, { method: "DELETE" }, token);
}

export function getNodeModules(baseUrl: string, token: string, nodeId: string): Promise<OrgNodeModules> {
  return request(baseUrl, `/org/nodes/${nodeId}/modules`, {}, token);
}

export function setNodeModules(
  baseUrl: string, token: string, nodeId: string,
  body: Partial<Record<ModuleKey, ModuleState>>
): Promise<OrgNodeModules> {
  return request(baseUrl, `/org/nodes/${nodeId}/modules`, { method: "PUT", body: JSON.stringify(body) }, token);
}

// Leases — stalls leased INTO a venue node (foodcourt GTO vs coffeeshop FIXED).
export function listVenueLeases(baseUrl: string, token: string, venueId: string): Promise<Lease[]> {
  return request(baseUrl, `/org/nodes/${venueId}/leases`, {}, token);
}

export function createLease(
  baseUrl: string,
  token: string,
  venueId: string,
  data: { tenant_node_id: string; rent_type: string; rate: string }
): Promise<Lease> {
  return request(baseUrl, `/org/nodes/${venueId}/leases`, { method: "POST", body: JSON.stringify(data) }, token);
}

export function updateLease(
  baseUrl: string,
  token: string,
  venueId: string,
  leaseId: string,
  data: { rent_type?: string; rate?: string; is_active?: boolean }
): Promise<Lease> {
  return request(baseUrl, `/org/nodes/${venueId}/leases/${leaseId}`, { method: "PATCH", body: JSON.stringify(data) }, token);
}

export function deleteLease(baseUrl: string, token: string, venueId: string, leaseId: string): Promise<void> {
  return request(baseUrl, `/org/nodes/${venueId}/leases/${leaseId}`, { method: "DELETE" }, token);
}

// ─── Client class (optional OOP interface) ───────────────────

export class FbGroupApiClient {
  constructor(
    private baseUrl: string,
    private token?: string
  ) {}

  withToken(token: string): FbGroupApiClient {
    return new FbGroupApiClient(this.baseUrl, token);
  }

  resolveQr(token: string) { return resolveQr(this.baseUrl, token); }
  resolveStallMenu(token: string, menuId: string) { return resolveStallMenu(this.baseUrl, token, menuId); }
  refresh(refreshToken: string) { return refresh(this.baseUrl, refreshToken); }
  otpRequest(phone: string) { return otpRequest(this.baseUrl, phone); }
  otpVerify(phone: string, code: string, full_name?: string) { return otpVerify(this.baseUrl, phone, code, full_name); }
  customerRegister(data: Parameters<typeof customerRegister>[1]) { return customerRegister(this.baseUrl, data); }
  customerLogin(email: string, password: string) { return customerLogin(this.baseUrl, email, password); }
  staffLogin(email: string, password: string) { return staffLogin(this.baseUrl, email, password); }
  createOrder(data: Parameters<typeof createOrder>[2]) { return createOrder(this.baseUrl, this.token!, data); }
  checkout(orderId: string, method: PaymentMethod, force_outcome?: string) { return checkout(this.baseUrl, this.token!, orderId, method, force_outcome); }
  crmCustomers(params?: Parameters<typeof crmCustomers>[2], merchantId?: string) { return crmCustomers(this.baseUrl, this.token!, params, merchantId); }
  crmSegments(merchantId?: string) { return crmSegments(this.baseUrl, this.token!, merchantId); }
  crmCustomerProfile(customerId: string, merchantId?: string) { return crmCustomerProfile(this.baseUrl, this.token!, customerId, merchantId); }
  addTag(customerId: string, tag: string) { return addTag(this.baseUrl, this.token!, customerId, tag); }
  addNote(customerId: string, body: string) { return addNote(this.baseUrl, this.token!, customerId, body); }
  reportSummary(merchantId?: string) { return reportSummary(this.baseUrl, this.token!, merchantId); }
  reportSales(params?: Parameters<typeof reportSales>[2], merchantId?: string) { return reportSales(this.baseUrl, this.token!, params, merchantId); }
  reportTopItems(merchantId?: string) { return reportTopItems(this.baseUrl, this.token!, merchantId); }
  reportForecast(horizon?: number, merchantId?: string) { return reportForecast(this.baseUrl, this.token!, horizon, merchantId); }

  // Round 2 — customer loyalty / rewards / wheel
  getLoyalty(merchantId: string) { return getLoyalty(this.baseUrl, this.token!, merchantId); }
  getRewardsCatalog(merchantId: string) { return getRewardsCatalog(this.baseUrl, this.token!, merchantId); }
  redeemReward(merchantId: string, itemId: string) { return redeemReward(this.baseUrl, this.token!, merchantId, itemId); }
  getWheel(merchantId: string) { return getWheel(this.baseUrl, this.token!, merchantId); }
  spinWheel(merchantId: string) { return spinWheel(this.baseUrl, this.token!, merchantId); }
  getJackpot(merchantId: string) { return getJackpot(this.baseUrl, this.token!, merchantId); }
  playJackpot(merchantId: string) { return playJackpot(this.baseUrl, this.token!, merchantId); }

  // Round 2 — CRM timeline / tasks / owner
  crmTimeline(customerId: string, merchantId?: string) { return crmTimeline(this.baseUrl, this.token!, customerId, merchantId); }
  crmCustomerTasks(customerId: string, merchantId?: string) { return crmCustomerTasks(this.baseUrl, this.token!, customerId, merchantId); }
  crmCreateTask(customerId: string, data: TaskCreate, merchantId?: string) { return crmCreateTask(this.baseUrl, this.token!, customerId, data, merchantId); }
  crmUpdateTask(taskId: string, status: TaskStatus, merchantId?: string) { return crmUpdateTask(this.baseUrl, this.token!, taskId, status, merchantId); }
  crmMyTasks(merchantId?: string) { return crmMyTasks(this.baseUrl, this.token!, merchantId); }
  crmAssignOwner(customerId: string, ownerUserId: string | null, merchantId?: string) { return crmAssignOwner(this.baseUrl, this.token!, customerId, ownerUserId, merchantId); }

  // Round 5 — operator console
  platformOverview() { return platformOverview(this.baseUrl, this.token!); }
  platformMerchants() { return platformMerchants(this.baseUrl, this.token!); }
  platformCoalitions() { return platformCoalitions(this.baseUrl, this.token!); }
  platformCreateMerchant(data: MerchantCreate) { return platformCreateMerchant(this.baseUrl, this.token!, data); }
  platformSetMerchantActive(merchantId: string, isActive: boolean) { return platformSetMerchantActive(this.baseUrl, this.token!, merchantId, isActive); }
  platformUpdateMerchant(merchantId: string, data: MerchantUpdate) { return platformUpdateMerchant(this.baseUrl, this.token!, merchantId, data); }
  platformOperators() { return platformOperators(this.baseUrl, this.token!); }
  platformMyPermissions() { return platformMyPermissions(this.baseUrl, this.token!); }
  platformInviteOperator(data: OperatorCreate) { return platformInviteOperator(this.baseUrl, this.token!, data); }
  platformRevokeOperator(operatorId: string) { return platformRevokeOperator(this.baseUrl, this.token!, operatorId); }
  platformCreateCoalition(name: string) { return platformCreateCoalition(this.baseUrl, this.token!, name); }
  platformUpdateCoalition(coalitionId: string, data: CoalitionUpdate) { return platformUpdateCoalition(this.baseUrl, this.token!, coalitionId, data); }
  platformAddCoalitionMember(coalitionId: string, merchantId: string) { return platformAddCoalitionMember(this.baseUrl, this.token!, coalitionId, merchantId); }
  platformRemoveCoalitionMember(coalitionId: string, merchantId: string) { return platformRemoveCoalitionMember(this.baseUrl, this.token!, coalitionId, merchantId); }

  // Round 6 — opportunities / pipeline / activities / bulk
  pipeline(pipelineType?: PipelineType, merchantId?: string) { return pipeline(this.baseUrl, this.token!, pipelineType, merchantId); }
  listOpportunities(pipelineType?: PipelineType, merchantId?: string) { return listOpportunities(this.baseUrl, this.token!, pipelineType, merchantId); }
  customerOpportunities(customerId: string, merchantId?: string) { return customerOpportunities(this.baseUrl, this.token!, customerId, merchantId); }
  createOpportunity(customerId: string, data: OpportunityCreate, merchantId?: string) { return createOpportunity(this.baseUrl, this.token!, customerId, data, merchantId); }
  updateOpportunity(oppId: string, data: { stage?: OpportunityStage; amount?: number }, merchantId?: string) { return updateOpportunity(this.baseUrl, this.token!, oppId, data, merchantId); }
  listActivities(customerId: string, merchantId?: string) { return listActivities(this.baseUrl, this.token!, customerId, merchantId); }
  logActivity(customerId: string, data: ActivityCreate, merchantId?: string) { return logActivity(this.baseUrl, this.token!, customerId, data, merchantId); }
  bulkTag(data: { tag: string; customer_ids?: string[]; segment?: string }, merchantId?: string) { return bulkTag(this.baseUrl, this.token!, data, merchantId); }
  bulkOwner(data: { owner_user_id?: string | null; customer_ids?: string[]; segment?: string }, merchantId?: string) { return bulkOwner(this.baseUrl, this.token!, data, merchantId); }
  bulkTask(data: { title: string; priority?: TaskPriority; customer_ids?: string[]; segment?: string }, merchantId?: string) { return bulkTask(this.baseUrl, this.token!, data, merchantId); }

  // Round 7 — campaigns & retention
  listCampaigns(merchantId?: string) { return listCampaigns(this.baseUrl, this.token!, merchantId); }
  createCampaign(data: CampaignCreate, merchantId?: string) { return createCampaign(this.baseUrl, this.token!, data, merchantId); }
  campaignDetail(campaignId: string, merchantId?: string) { return campaignDetail(this.baseUrl, this.token!, campaignId, merchantId); }
  buildAudience(campaignId: string, merchantId?: string) { return buildAudience(this.baseUrl, this.token!, campaignId, merchantId); }
  sendCampaign(campaignId: string, merchantId?: string) { return sendCampaign(this.baseUrl, this.token!, campaignId, merchantId); }
  campaignMetrics(campaignId: string, merchantId?: string) { return campaignMetrics(this.baseUrl, this.token!, campaignId, merchantId); }
  recordRedemption(campaignId: string, data: { customer_id: string; revenue: number; order_id?: string }, merchantId?: string) { return recordRedemption(this.baseUrl, this.token!, campaignId, data, merchantId); }

  // Round 8 — menu admin / users / RFM
  menuOutlets(merchantId?: string) { return menuOutlets(this.baseUrl, this.token!, merchantId); }
  outletMenu(outletId: string) { return outletMenu(this.baseUrl, this.token!, outletId); }
  createCategory(data: { menu_id: string; name: string; sort_order?: number }, merchantId?: string) { return createCategory(this.baseUrl, this.token!, data, merchantId); }
  updateCategory(categoryId: string, data: { name?: string; sort_order?: number }, merchantId?: string) { return updateCategory(this.baseUrl, this.token!, categoryId, data, merchantId); }
  deleteCategory(categoryId: string, merchantId?: string) { return deleteCategory(this.baseUrl, this.token!, categoryId, merchantId); }
  createMenuItem(data: { category_id: string; name: string; price: number; description?: string; sort_order?: number }, merchantId?: string) { return createMenuItem(this.baseUrl, this.token!, data, merchantId); }
  updateMenuItem(itemId: string, data: { name?: string; price?: number; description?: string; is_available?: boolean; sort_order?: number }, merchantId?: string) { return updateMenuItem(this.baseUrl, this.token!, itemId, data, merchantId); }
  deleteMenuItem(itemId: string, merchantId?: string) { return deleteMenuItem(this.baseUrl, this.token!, itemId, merchantId); }
  createModifier(data: { item_id: string; name: string; price_delta?: number }, merchantId?: string) { return createModifier(this.baseUrl, this.token!, data, merchantId); }
  deleteModifier(modifierId: string, merchantId?: string) { return deleteModifier(this.baseUrl, this.token!, modifierId, merchantId); }
  rfm(merchantId?: string) { return rfm(this.baseUrl, this.token!, merchantId); }
  aiInsights(merchantId?: string) { return aiInsights(this.baseUrl, this.token!, merchantId); }

  // Round 9 — org structure (brands / outlets / tables)
  orgBrands(merchantId?: string) { return orgBrands(this.baseUrl, this.token!, merchantId); }
  createBrand(data: { name: string; cuisine_type?: string }, merchantId?: string) { return createBrand(this.baseUrl, this.token!, data, merchantId); }
  updateBrand(brandId: string, data: { name?: string; cuisine_type?: string; is_active?: boolean }, merchantId?: string) { return updateBrand(this.baseUrl, this.token!, brandId, data, merchantId); }
  orgOutlets(merchantId?: string) { return orgOutlets(this.baseUrl, this.token!, merchantId); }
  createOutlet(data: { brand_id: string; name: string; address?: string }, merchantId?: string) { return createOutlet(this.baseUrl, this.token!, data, merchantId); }
  updateOutlet(outletId: string, data: { name?: string; address?: string; is_active?: boolean }, merchantId?: string) { return updateOutlet(this.baseUrl, this.token!, outletId, data, merchantId); }
  orgTables(outletId: string, merchantId?: string) { return orgTables(this.baseUrl, this.token!, outletId, merchantId); }
  createTable(outletId: string, data: { label: string; seats?: number }, merchantId?: string) { return createTable(this.baseUrl, this.token!, outletId, data, merchantId); }
  deleteTable(tableId: string, merchantId?: string) { return deleteTable(this.baseUrl, this.token!, tableId, merchantId); }
  orgTree() { return orgTree(this.baseUrl, this.token!); }
  createOrgNode(data: { parent_id: string; role: string; name: string; chain_stopped?: boolean; subscription_fee?: string }) { return createOrgNode(this.baseUrl, this.token!, data); }
  updateOrgNode(nodeId: string, data: { name?: string; is_active?: boolean; chain_stopped?: boolean; subscription_fee?: string }) { return updateOrgNode(this.baseUrl, this.token!, nodeId, data); }
  listNodeAccounts(nodeId: string, subtree = false) { return listNodeAccounts(this.baseUrl, this.token!, nodeId, subtree); }
  createNodeAccount(nodeId: string, data: { email: string; password: string; full_name?: string; role: string }) { return createNodeAccount(this.baseUrl, this.token!, nodeId, data); }
  revokeNodeAccount(nodeId: string, assignmentId: string) { return revokeNodeAccount(this.baseUrl, this.token!, nodeId, assignmentId); }
  getNodeModules(nodeId: string) { return getNodeModules(this.baseUrl, this.token!, nodeId); }
  setNodeModules(nodeId: string, body: Partial<Record<ModuleKey, ModuleState>>) { return setNodeModules(this.baseUrl, this.token!, nodeId, body); }
  listVenueLeases(venueId: string) { return listVenueLeases(this.baseUrl, this.token!, venueId); }
  createLease(venueId: string, data: { tenant_node_id: string; rent_type: string; rate: string }) { return createLease(this.baseUrl, this.token!, venueId, data); }
  updateLease(venueId: string, leaseId: string, data: { rent_type?: string; rate?: string; is_active?: boolean }) { return updateLease(this.baseUrl, this.token!, venueId, leaseId, data); }
  deleteLease(venueId: string, leaseId: string) { return deleteLease(this.baseUrl, this.token!, venueId, leaseId); }

  // Round 10 — win-back launcher + merchant settings
  launchWinback(data: WinbackLaunch, merchantId?: string) { return launchWinback(this.baseUrl, this.token!, data, merchantId); }
  getSettings(merchantId?: string) { return getSettings(this.baseUrl, this.token!, merchantId); }
  getNavFlags(merchantId?: string, nodeId?: string) { return getNavFlags(this.baseUrl, this.token!, merchantId, nodeId); }
  getMyPermissions(merchantId?: string) { return getMyPermissions(this.baseUrl, this.token!, merchantId); }
  updateSettings(data: Partial<MerchantSettings>, merchantId?: string) { return updateSettings(this.baseUrl, this.token!, data, merchantId); }
  getLoyaltyProgram(merchantId?: string) { return getLoyaltyProgram(this.baseUrl, this.token!, merchantId); }
  updateLoyaltyProgram(data: LoyaltyProgram, merchantId?: string) { return updateLoyaltyProgram(this.baseUrl, this.token!, data, merchantId); }
  listPromotions(merchantId?: string) { return listPromotions(this.baseUrl, this.token!, merchantId); }
  createPromotion(data: PromotionCreate, merchantId?: string) { return createPromotion(this.baseUrl, this.token!, data, merchantId); }
  deactivatePromotion(promoId: string, merchantId?: string) { return deactivatePromotion(this.baseUrl, this.token!, promoId, merchantId); }
}
