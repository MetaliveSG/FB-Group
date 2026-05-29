// Token storage helpers — wraps localStorage with safe SSR fallback

const CUSTOMER_TOKEN_KEY = "fbgroup_customer_token";
const CUSTOMER_REFRESH_KEY = "fbgroup_customer_refresh";
const STAFF_TOKEN_KEY = "fbgroup_staff_token";
const STAFF_REFRESH_KEY = "fbgroup_staff_refresh";
const CUSTOMER_DATA_KEY = "fbgroup_customer_data";
const STAFF_USER_KEY = "fbgroup_staff_user";
const OPERATOR_MERCHANT_KEY = "fbgroup_operator_merchant";

export interface StaffUser {
  id: string;
  email: string;
  full_name: string;
}

/** A merchant an operator (super admin) has drilled into. */
export interface OperatorMerchant {
  id: string;
  name: string;
}

function isBrowser() {
  return typeof window !== "undefined";
}

// ─── Customer ────────────────────────────────────────────────

export function getCustomerToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(CUSTOMER_TOKEN_KEY);
}

export function setCustomerToken(token: string): void {
  if (!isBrowser()) return;
  localStorage.setItem(CUSTOMER_TOKEN_KEY, token);
}

export function getCustomerRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(CUSTOMER_REFRESH_KEY);
}

export function setCustomerRefreshToken(token: string): void {
  if (!isBrowser()) return;
  localStorage.setItem(CUSTOMER_REFRESH_KEY, token);
}

export function clearCustomerToken(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(CUSTOMER_TOKEN_KEY);
  localStorage.removeItem(CUSTOMER_REFRESH_KEY);
  localStorage.removeItem(CUSTOMER_DATA_KEY);
}

export function getCustomerData(): Record<string, unknown> | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(CUSTOMER_DATA_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setCustomerData(data: Record<string, unknown>): void {
  if (!isBrowser()) return;
  localStorage.setItem(CUSTOMER_DATA_KEY, JSON.stringify(data));
}

// ─── Staff ───────────────────────────────────────────────────

export function getStaffToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(STAFF_TOKEN_KEY);
}

export function setStaffToken(token: string): void {
  if (!isBrowser()) return;
  localStorage.setItem(STAFF_TOKEN_KEY, token);
}

export function getStaffRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(STAFF_REFRESH_KEY);
}

export function setStaffRefreshToken(token: string): void {
  if (!isBrowser()) return;
  localStorage.setItem(STAFF_REFRESH_KEY, token);
}

export function clearStaffToken(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(STAFF_TOKEN_KEY);
  localStorage.removeItem(STAFF_REFRESH_KEY);
  localStorage.removeItem(STAFF_USER_KEY);
  localStorage.removeItem(OPERATOR_MERCHANT_KEY);
}

export function getStaffUser(): StaffUser | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(STAFF_USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StaffUser;
  } catch {
    return null;
  }
}

export function setStaffUser(user: StaffUser): void {
  if (!isBrowser()) return;
  localStorage.setItem(STAFF_USER_KEY, JSON.stringify(user));
}

// ─── Operator drill-down (selected merchant) ─────────────────

export function getOperatorMerchant(): OperatorMerchant | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(OPERATOR_MERCHANT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as OperatorMerchant;
  } catch {
    return null;
  }
}

export function setOperatorMerchant(merchant: OperatorMerchant): void {
  if (!isBrowser()) return;
  localStorage.setItem(OPERATOR_MERCHANT_KEY, JSON.stringify(merchant));
}

export function clearOperatorMerchant(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(OPERATOR_MERCHANT_KEY);
}
