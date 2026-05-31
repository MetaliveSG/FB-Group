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
  status: string;
  created_at: string;
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
}

export interface Coalition {
  id: string;
  name: string;
  is_active: boolean;
  members: string[];
  member_count: number;
  points_issued: number;
}

export interface MerchantCreate {
  name: string;
  owner_email: string;
  owner_password: string;
  owner_name?: string;
}

export interface MerchantCreateResult {
  merchant_id: string;
  name: string;
  owner_email: string;
  owner_user_id: string;
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

export interface MerchantSettings {
  pipeline_enabled: boolean;
  wheel_spin_cost: number;
  jackpot_spin_cost: number;
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
  | "vip_reward";

export const CAMPAIGN_TYPES: CampaignType[] = [
  "whatsapp_promo",
  "birthday",
  "winback",
  "weekday_boost",
  "new_customer_return",
  "vip_reward",
];

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

export type StaffRole =
  | "merchant_owner"
  | "brand_manager"
  | "outlet_manager"
  | "staff";

export type ScopeType = "merchant" | "brand" | "outlet";

export const STAFF_ROLES: StaffRole[] = [
  "merchant_owner",
  "brand_manager",
  "outlet_manager",
  "staff",
];

export interface RoleAssignment {
  assignment_id: string;
  role: string;
  scope_type: string;
  scope_id: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: RoleAssignment[];
}

export interface InviteUser {
  email: string;
  password: string;
  full_name: string;
  role: StaffRole;
  scope_type: ScopeType;
  scope_id?: string;
}

export interface InviteUserResult {
  id: string;
  email: string;
  full_name: string;
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

export function otpVerify(
  baseUrl: string,
  phone: string,
  code: string,
  full_name?: string,
  region: string = "SG"
): Promise<TokenResponse> {
  return request(baseUrl, "/auth/customer/otp/verify", {
    method: "POST",
    body: JSON.stringify({ phone, code, full_name, region }),
  });
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

export function updateSettings(
  baseUrl: string,
  token: string,
  data: { pipeline_enabled?: boolean; wheel_spin_cost?: number; jackpot_spin_cost?: number },
  merchantId?: string
): Promise<MerchantSettings> {
  return request(
    baseUrl,
    `/org/settings${mq(merchantId)}`,
    { method: "PATCH", body: JSON.stringify(data) },
    token
  );
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
  merchantId?: string
): Promise<MenuAdminOutlet[]> {
  return request(baseUrl, `/menu-admin/outlets${mq(merchantId)}`, {}, token);
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

// ─── Round 8: User management ────────────────────────────────

export function listUsers(
  baseUrl: string,
  token: string,
  merchantId?: string
): Promise<AdminUser[]> {
  return request(baseUrl, `/admin/users${mq(merchantId)}`, {}, token);
}

export function inviteUser(
  baseUrl: string,
  token: string,
  data: InviteUser,
  merchantId?: string
): Promise<InviteUserResult> {
  return request(
    baseUrl,
    `/admin/users${mq(merchantId)}`,
    { method: "POST", body: JSON.stringify(data) },
    token
  );
}

export function revokeAssignment(
  baseUrl: string,
  token: string,
  assignmentId: string,
  merchantId?: string
): Promise<void> {
  return request(
    baseUrl,
    `/admin/users/assignments/${assignmentId}${mq(merchantId)}`,
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
  listUsers(merchantId?: string) { return listUsers(this.baseUrl, this.token!, merchantId); }
  inviteUser(data: InviteUser, merchantId?: string) { return inviteUser(this.baseUrl, this.token!, data, merchantId); }
  revokeAssignment(assignmentId: string, merchantId?: string) { return revokeAssignment(this.baseUrl, this.token!, assignmentId, merchantId); }
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

  // Round 10 — win-back launcher + merchant settings
  launchWinback(data: WinbackLaunch, merchantId?: string) { return launchWinback(this.baseUrl, this.token!, data, merchantId); }
  getSettings(merchantId?: string) { return getSettings(this.baseUrl, this.token!, merchantId); }
  updateSettings(data: { pipeline_enabled?: boolean; wheel_spin_cost?: number; jackpot_spin_cost?: number }, merchantId?: string) { return updateSettings(this.baseUrl, this.token!, data, merchantId); }
}
