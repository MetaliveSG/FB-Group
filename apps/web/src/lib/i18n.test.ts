import { describe, it, expect } from "vitest";
import {
  normalizeLocale,
  SUPPORTED_LOCALES,
  DEFAULT_LOCALE,
  formatMoney,
  formatTime,
} from "@fbgroup/i18n";

describe("normalizeLocale", () => {
  it("clamps case + region to a supported locale", () => {
    expect(normalizeLocale("EN")).toBe("en");
    expect(normalizeLocale("en-US")).toBe("en");
    expect(normalizeLocale("zh-CN")).toBe("zh");
    expect(normalizeLocale("ms_MY")).toBe("ms");
  });
  it("preserves Singlish (exact supported tag)", () => {
    expect(normalizeLocale("en-SG")).toBe("en-SG");
  });
  it("falls unknown/empty back to the default", () => {
    expect(normalizeLocale("fr")).toBe(DEFAULT_LOCALE);
    expect(normalizeLocale(null)).toBe(DEFAULT_LOCALE);
    expect(normalizeLocale("")).toBe(DEFAULT_LOCALE);
  });
  it("every supported locale normalises to itself", () => {
    for (const l of SUPPORTED_LOCALES) expect(normalizeLocale(l)).toBe(l);
  });
});

describe("formatMoney — currency is a settlement fact, decoupled from language", () => {
  it("formats 2-decimal currencies", () => {
    // non-breaking spaces vary by runtime; assert the parts instead of exact spacing
    const out = formatMoney(12.5, { locale: "en", currency: "SGD" });
    expect(out).toContain("12.50");
    expect(out).toMatch(/\$|SGD/);
  });
  it("renders 0-decimal currencies (IDR/VND) with no decimal places", () => {
    const out = formatMoney(15000, { locale: "en", currency: "IDR" });
    expect(out).not.toContain(".00");
    expect(out.replace(/[^0-9]/g, "")).toBe("15000");
  });
  it("same amount + locale, different currency → different symbol (no FX, just display)", () => {
    const sgd = formatMoney(10, { locale: "en", currency: "SGD" });
    const myr = formatMoney(10, { locale: "en", currency: "MYR" });
    expect(sgd).not.toBe(myr);
  });
});

describe("formatTime — timezone is a place fact, decoupled from language", () => {
  it("same instant renders different wall-clock in different zones", () => {
    const instant = "2026-06-11T04:00:00Z";
    const sg = formatTime(instant, { locale: "en", timeZone: "Asia/Singapore", dateStyle: undefined, timeStyle: "short" });
    const kl = formatTime(instant, { locale: "en", timeZone: "Asia/Bangkok", timeStyle: "short" });
    // SG is UTC+8 → 12:00; Bangkok UTC+7 → 11:00 — must differ
    expect(sg).not.toBe(kl);
  });
});
