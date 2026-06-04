// Reporting timezones for the markets we operate in: Singapore · Malaysia · Thailand · Indonesia.
// [IANA zone, display label]. The backend still accepts any valid IANA zone via ?tz= (e.g. for tests),
// but the UI dropdowns offer only these.
export const REPORT_TIMEZONES: [string, string][] = [
  ["Asia/Singapore", "Singapore (GMT+8)"],
  ["Asia/Kuala_Lumpur", "Malaysia (GMT+8)"],
  ["Asia/Bangkok", "Thailand (GMT+7)"],
  ["Asia/Jakarta", "Indonesia · WIB (GMT+7)"],
];
