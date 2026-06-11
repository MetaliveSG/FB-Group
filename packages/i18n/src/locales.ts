// The locales the ecosystem recognises. MUST stay in sync with the backend
// app/services/i18n.py::SUPPORTED_LOCALES (same tags, same default).
//   en      — canonical / default (source of truth for the catalog)
//   en-SG   — Singlish; an OVERLAY on en (only overrides the fun strings, inherits the rest)
//   zh ms ta — SG official languages · id th vi — SEA expansion
export const DEFAULT_LOCALE = "en" as const;

export type Locale = "en" | "en-SG" | "zh" | "ms" | "ta" | "id" | "th" | "vi";

export const SUPPORTED_LOCALES: Locale[] = ["en", "en-SG", "zh", "ms", "ta", "id", "th", "vi"];

// The subset shown in the language switcher (UI). SUPPORTED_LOCALES stays the full RECOGNISED set (the
// resolver still honours a saved zh/ms etc.), but we only OFFER locales whose catalogs are ready — English
// + Singlish for now. Add zh/ms/… here as their catalogs reach usable coverage (see check-catalogs.mjs).
export const ENABLED_LOCALES: Locale[] = ["en", "en-SG"];

// Display name shown in the language switcher (in the language's own script — endonym).
export const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  "en-SG": "Singlish",
  zh: "中文",
  ms: "Bahasa Melayu",
  ta: "தமிழ்",
  id: "Bahasa Indonesia",
  th: "ไทย",
  vi: "Tiếng Việt",
};

// A locale → its fallback chain (most-specific first). en-SG inherits en; everything inherits en last.
export function fallbackChain(locale: string): Locale[] {
  const chain: Locale[] = [];
  const push = (l: Locale) => { if (!chain.includes(l)) chain.push(l); };
  if (SUPPORTED_LOCALES.includes(locale as Locale)) push(locale as Locale);
  if (locale === "en-SG") push("en");
  push(DEFAULT_LOCALE);
  return chain;
}

// Clamp an arbitrary tag (navigator.language, a saved value) to a supported locale. Tolerant of
// case + region: "EN" → en, "zh-CN" → zh, "en-SG" preserved. Unknown → default. Mirrors the backend.
export function normalizeLocale(tag: string | null | undefined): Locale {
  if (!tag) return DEFAULT_LOCALE;
  const t = tag.trim().replace("_", "-");
  if (!t) return DEFAULT_LOCALE;
  const exact = SUPPORTED_LOCALES.find((l) => l.toLowerCase() === t.toLowerCase());
  if (exact) return exact;
  const primary = t.split("-")[0].toLowerCase();
  const byPrimary = SUPPORTED_LOCALES.find((l) => l.toLowerCase() === primary);
  return byPrimary ?? DEFAULT_LOCALE;
}
