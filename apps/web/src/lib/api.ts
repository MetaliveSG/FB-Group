// Instantiate the API client with the correct base URL and token

import {
  FbGroupApiClient,
  resolveQr,
  resolveStallMenu,
  resolveNodeBrowse,
  resolveNodeMenu,
  otpRequest,
  otpVerify,
  customerLogin,
  staffLogin,
  pinLogin,
  createManualOrder,
  cashierCheckout,
  getReceipt,
  voidOrder,
  setStaffPin,
  dinerVouchers,
  createOrder,
  checkout,
  crmCustomers,
  crmSegments,
  crmCustomerProfile,
  addTag,
  addNote,
  reportSummary,
  reportSales,
  reportTopItems,
  reportForecast,
  reportsSummary,
  reportsSales,
  reportsTopItems,
  reportsPeakHours,
  reportsPayments,
  reportsRollup,
  getLoyalty,
  getMyOrders,
  getOrder,
  getMerchantOrders,
  listKitchenOrders,
  advanceFulfilment,
  kdsQueue,
  kdsAdvance,
  kdsContext,
  getNodeKdsStation,
  issueNodeKdsStation,
  revokeNodeKdsStation,
  getMyVouchers,
  redeemVoucher,
  previewVoucher,
  getMyProfile,
  updateMyProfile,
  getRewardsCatalog,
  redeemReward,
  getWheel,
  spinWheel,
  getJackpot,
  playJackpot,
  crmTimeline,
  crmCustomerTasks,
  crmCreateTask,
  crmUpdateTask,
  crmMyTasks,
  crmAssignOwner,
  platformOverview,
  platformMerchants,
  platformCoalitions,
  platformCreateMerchant,
  platformSetMerchantActive,
  platformUpdateMerchant,
  platformOperators,
  platformMyPermissions,
  platformInviteOperator,
  platformRevokeOperator,
  platformCreateCoalition,
  platformUpdateCoalition,
  platformAddCoalitionMember,
  platformRemoveCoalitionMember,
  pipeline,
  listOpportunities,
  customerOpportunities,
  createOpportunity,
  updateOpportunity,
  listActivities,
  logActivity,
  bulkTag,
  bulkOwner,
  bulkTask,
  listCampaigns,
  createCampaign,
  issueCampaignVouchers,
  campaignDetail,
  buildAudience,
  sendCampaign,
  campaignMetrics,
  recordRedemption,
  menuOutlets,
  outletMenu,
  createCategory,
  updateCategory,
  deleteCategory,
  createMenuItem,
  updateMenuItem,
  deleteMenuItem,
  createModifier,
  deleteModifier,
  rfm,
  aiInsights,
  orgBrands,
  createBrand,
  updateBrand,
  orgOutlets,
  createOutlet,
  updateOutlet,
  orgTables,
  createTable,
  deleteTable,
  orgTree,
  createOrgNode,
  updateOrgNode,
  listNodeAccounts,
  createNodeAccount,
  revokeNodeAccount,
  getNodeModules,
  setNodeModules,
  getNodeServiceOptions,
  setNodeServiceOptions,
  getNodeTheme,
  setNodeTheme,
  listPosStaff,
  createPosStaff,
  resetPosStaffPin,
  deletePosStaff,
  listVenueLeases,
  createLease,
  updateLease,
  deleteLease,
  launchWinback,
  getSettings,
  getNavFlags,
  getMyPermissions,
  updateSettings,
  getLoyaltyProgram,
  updateLoyaltyProgram,
  listPromotions,
  createPromotion,
  deactivatePromotion,
  refresh,
  setAuthHandler,
} from "@fbgroup/api-client";
import {
  getCustomerToken,
  setCustomerToken,
  getCustomerRefreshToken,
  setCustomerRefreshToken,
  clearCustomerToken,
  getStaffToken,
  setStaffToken,
  getStaffRefreshToken,
  setStaffRefreshToken,
  clearStaffToken,
} from "@/lib/auth";

export {
  FbGroupApiClient,
  resolveQr,
  resolveStallMenu,
  resolveNodeBrowse,
  resolveNodeMenu,
  otpRequest,
  otpVerify,
  customerLogin,
  staffLogin,
  pinLogin,
  createManualOrder,
  cashierCheckout,
  getReceipt,
  voidOrder,
  setStaffPin,
  dinerVouchers,
  createOrder,
  checkout,
  crmCustomers,
  crmSegments,
  crmCustomerProfile,
  addTag,
  addNote,
  reportSummary,
  reportSales,
  reportTopItems,
  reportForecast,
  reportsSummary,
  reportsSales,
  reportsTopItems,
  reportsPeakHours,
  reportsPayments,
  reportsRollup,
  getLoyalty,
  getMyOrders,
  getOrder,
  getMerchantOrders,
  listKitchenOrders,
  advanceFulfilment,
  kdsQueue,
  kdsAdvance,
  kdsContext,
  getNodeKdsStation,
  issueNodeKdsStation,
  revokeNodeKdsStation,
  getMyVouchers,
  redeemVoucher,
  previewVoucher,
  getMyProfile,
  updateMyProfile,
  getRewardsCatalog,
  redeemReward,
  getWheel,
  spinWheel,
  getJackpot,
  playJackpot,
  crmTimeline,
  crmCustomerTasks,
  crmCreateTask,
  crmUpdateTask,
  crmMyTasks,
  crmAssignOwner,
  platformOverview,
  platformMerchants,
  platformCoalitions,
  platformCreateMerchant,
  platformSetMerchantActive,
  platformUpdateMerchant,
  platformOperators,
  platformMyPermissions,
  platformInviteOperator,
  platformRevokeOperator,
  platformCreateCoalition,
  platformUpdateCoalition,
  platformAddCoalitionMember,
  platformRemoveCoalitionMember,
  pipeline,
  listOpportunities,
  customerOpportunities,
  createOpportunity,
  updateOpportunity,
  listActivities,
  logActivity,
  bulkTag,
  bulkOwner,
  bulkTask,
  listCampaigns,
  createCampaign,
  issueCampaignVouchers,
  campaignDetail,
  buildAudience,
  sendCampaign,
  campaignMetrics,
  recordRedemption,
  menuOutlets,
  outletMenu,
  createCategory,
  updateCategory,
  deleteCategory,
  createMenuItem,
  updateMenuItem,
  deleteMenuItem,
  createModifier,
  deleteModifier,
  rfm,
  aiInsights,
  orgBrands,
  createBrand,
  updateBrand,
  orgOutlets,
  createOutlet,
  updateOutlet,
  orgTables,
  createTable,
  deleteTable,
  orgTree,
  createOrgNode,
  updateOrgNode,
  listNodeAccounts,
  createNodeAccount,
  revokeNodeAccount,
  getNodeModules,
  setNodeModules,
  getNodeServiceOptions,
  setNodeServiceOptions,
  getNodeTheme,
  setNodeTheme,
  listPosStaff,
  createPosStaff,
  resetPosStaffPin,
  deletePosStaff,
  listVenueLeases,
  createLease,
  updateLease,
  deleteLease,
  launchWinback,
  getSettings,
  getNavFlags,
  getMyPermissions,
  updateSettings,
  getLoyaltyProgram,
  updateLoyaltyProgram,
  listPromotions,
  createPromotion,
  deactivatePromotion,
  refresh,
};

export function getApiBase(): string {
  // Explicit override wins (e.g. a fixed API domain in prod).
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  // Otherwise call the API on the SAME host the page was loaded from, port 8000.
  // This is what lets a phone on the home wifi reach it via the Mac's LAN IP
  // (e.g. http://192.168.68.57:3001) — `localhost` would resolve to the phone itself.
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

export function getApiClient(token?: string): FbGroupApiClient {
  return new FbGroupApiClient(getApiBase(), token);
}

// ─── Auth resilience wiring ───────────────────────────────────

/** Actor whose session was logged out by a failed refresh. */
export type LoggedOutActor = "customer" | "staff";

export const AUTH_LOGOUT_EVENT = "fbgroup:auth-logout";

/**
 * Notify the app that a session was cleared after a failed refresh.
 * Pages listen for this to surface the login UI in place.
 */
function emitLogout(actor: LoggedOutActor): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT, { detail: { actor } }));
}

let authHandlerInstalled = false;

/**
 * Install the global 401 → refresh → retry handler. Idempotent; safe to call
 * from any client component on mount.
 */
export function installAuthHandler(): void {
  if (authHandlerInstalled || typeof window === "undefined") return;
  authHandlerInstalled = true;

  const base = getApiBase();

  setAuthHandler({
    async refresh(failedAccessToken: string): Promise<string | null> {
      // Match the failed access token to the correct actor so we use the
      // right refresh token (a page may hold both customer + staff tokens).
      const isStaff = failedAccessToken === getStaffToken();
      const isCustomer = failedAccessToken === getCustomerToken();
      const actor: LoggedOutActor | null = isStaff
        ? "staff"
        : isCustomer
          ? "customer"
          : null;
      if (!actor) return null;

      const refreshToken =
        actor === "staff" ? getStaffRefreshToken() : getCustomerRefreshToken();

      const logout = () => {
        if (actor === "staff") clearStaffToken();
        else clearCustomerToken();
        emitLogout(actor);
      };

      if (!refreshToken) {
        logout();
        return null;
      }

      try {
        const toks = await refresh(base, refreshToken);
        // /auth/refresh returns only tokens + actor (no profile); keep cached
        // customer/staff profile as-is.
        if (actor === "staff") {
          setStaffToken(toks.access_token);
          setStaffRefreshToken(toks.refresh_token);
        } else {
          setCustomerToken(toks.access_token);
          setCustomerRefreshToken(toks.refresh_token);
        }
        return toks.access_token;
      } catch {
        logout();
        return null;
      }
    },
  });
}
