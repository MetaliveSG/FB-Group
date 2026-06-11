"use client";
// i18n runtime for the customer app — a lightweight typed-catalog seam (no heavy framework, keeps the
// "own design system" spirit). THREE INDEPENDENT axes, never coupled:
//   • language  = a PERSON fact  → useLocale()/useT()        (this provider)
//   • currency  = a SETTLEMENT fact → formatMoney(amt, {currency})  (passed in, from the merchant)
//   • timezone  = a PLACE fact   → formatTime(ts, {timeZone})       (passed in, from the outlet)
// A diner can switch to Singlish and the prices/times DON'T move — only the words do.
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { DEFAULT_LOCALE, type Locale, fallbackChain, normalizeLocale } from "./locales";
import en from "./locales/en.json";
import enSG from "./locales/en-SG.json";
import zh from "./locales/zh.json";
import ms from "./locales/ms.json";

export {
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  ENABLED_LOCALES,
  LOCALE_LABELS,
  normalizeLocale,
  type Locale,
} from "./locales";

type Catalog = Record<string, string>;
const CATALOGS: Partial<Record<Locale, Catalog>> = {
  en: en as Catalog,
  "en-SG": enSG as Catalog,
  zh: zh as Catalog,
  ms: ms as Catalog,
};

const STORAGE_KEY = "cip.locale";

// Resolve one key through the locale's fallback chain (e.g. en-SG → en), else the key itself
// (never blank — a raw key surfaces a missing string in dev without breaking the UI).
function lookup(locale: Locale, key: string): string {
  for (const loc of fallbackChain(locale)) {
    const hit = CATALOGS[loc]?.[key];
    if (typeof hit === "string") return hit;
  }
  return key;
}

// {var} interpolation. `count` also drives a simple plural: when count !== 1 and a `${key}_plural`
// exists, that variant is used (ICU MessageFormat is the upgrade path — swap lookup() for an ICU
// formatter and this signature is unchanged).
function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`));
}

export type TFunc = (key: string, vars?: Record<string, string | number>) => string;

interface Ctx {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: TFunc;
}
const LocaleContext = createContext<Ctx | null>(null);

export function LocaleProvider({
  children,
  initialLocale,
}: {
  children: React.ReactNode;
  initialLocale?: string | null;
}) {
  const [locale, setLocaleState] = useState<Locale>(() => normalizeLocale(initialLocale ?? DEFAULT_LOCALE));

  // On mount, prefer a previously-chosen locale, else the device language (clamped). Runs client-only
  // so SSR stays deterministic on the server-resolved initialLocale.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) { setLocaleState(normalizeLocale(saved)); return; }
      if (!initialLocale && typeof navigator !== "undefined") {
        setLocaleState(normalizeLocale(navigator.language));
      }
    } catch { /* localStorage blocked — keep initial */ }
  }, [initialLocale]);

  const setLocale = useCallback((l: Locale) => {
    const norm = normalizeLocale(l);
    setLocaleState(norm);
    try { window.localStorage.setItem(STORAGE_KEY, norm); } catch { /* ignore */ }
    try { document.documentElement.lang = norm; } catch { /* ignore */ }
  }, []);

  const t = useCallback<TFunc>((key, vars) => {
    let resolvedKey = key;
    if (vars && typeof vars.count === "number" && vars.count !== 1 && lookup(locale, `${key}_plural`) !== `${key}_plural`) {
      resolvedKey = `${key}_plural`;
    }
    return interpolate(lookup(locale, resolvedKey), vars);
  }, [locale]);

  const value = useMemo<Ctx>(() => ({ locale, setLocale, t }), [locale, setLocale, t]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): { locale: Locale; setLocale: (l: Locale) => void } {
  const ctx = useContext(LocaleContext);
  if (!ctx) return { locale: DEFAULT_LOCALE, setLocale: () => {} };  // tolerate use outside a provider
  return { locale: ctx.locale, setLocale: ctx.setLocale };
}

export function useT(): TFunc {
  const ctx = useContext(LocaleContext);
  // Fallback t still localises to the default catalog — a component used outside the provider degrades
  // to English rather than throwing.
  return ctx?.t ?? ((key, vars) => interpolate(lookup(DEFAULT_LOCALE, key), vars));
}

// --- Formatters — the ONE place language meets currency/timezone (everything else keeps them apart) ---

// ISO 4217 currencies with ZERO minor units (no decimals). We pin fraction digits explicitly rather than
// trust the runtime's ICU data — a Node build with small-icu would otherwise render "IDR 15,000.00".
// (Grab's lesson: don't assume Western i18n defaults / runtime locale data cover SEA.) Extend as needed.
const ZERO_DECIMAL = new Set(["IDR", "VND", "JPY", "KRW", "KHR", "LAK", "MMK", "CLP", "ISK", "HUF"]);

// Money: `currency` is the merchant's settlement currency (a SETTLEMENT fact, NOT derived from `locale`).
// Per-locale grouping/symbol comes from Intl; the decimal count is pinned so 0-decimal currencies (IDR/VND)
// are correct on every runtime. We never hardcode "$" or 2 dp. The numeric token is passed through untouched
// (Grab's no-mutate rule).
export function formatMoney(amount: number, opts: { locale: string; currency: string }): string {
  const digits = ZERO_DECIMAL.has(opts.currency.toUpperCase()) ? 0 : 2;
  try {
    return new Intl.NumberFormat(opts.locale, {
      style: "currency",
      currency: opts.currency,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(amount);
  } catch {
    return `${opts.currency} ${amount.toFixed(digits)}`;
  }
}

// Wall-clock time: `timeZone` is the outlet's tz (a PLACE fact). Pass an IANA zone (e.g. "Asia/Bangkok")
// so a KL order shows KL time regardless of the diner's language or device.
export function formatTime(
  date: Date | string | number,
  opts: { locale: string; timeZone?: string; dateStyle?: "full" | "long" | "medium" | "short"; timeStyle?: "full" | "long" | "medium" | "short" },
): string {
  const d = date instanceof Date ? date : new Date(date);
  try {
    return new Intl.DateTimeFormat(opts.locale, {
      timeZone: opts.timeZone,
      dateStyle: opts.dateStyle ?? "medium",
      timeStyle: opts.timeStyle ?? "short",
    }).format(d);
  } catch {
    return d.toISOString();
  }
}
