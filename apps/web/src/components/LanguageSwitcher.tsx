"use client";
// Diner-facing language picker. Sets the locale (persisted to localStorage by the provider) — UI strings
// re-render immediately; menu CONTENT re-localises on the next fetch (callers pass useLocale().locale as
// ?lang=). Language only — never touches the outlet's currency or timezone.
import { useLocale, useT, SUPPORTED_LOCALES, LOCALE_LABELS, type Locale } from "@fbgroup/i18n";

export default function LanguageSwitcher() {
  const { locale, setLocale } = useLocale();
  const t = useT();
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: "var(--text-sm)", fontWeight: 700 }}>
      <span aria-hidden style={{ fontSize: 18 }}>🌐</span>
      <span style={{ whiteSpace: "nowrap" }}>{t("common.language")}</span>
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        style={{ flex: 1, minWidth: 0, padding: "8px 10px", borderRadius: "var(--radius-md, 10px)", border: "1px solid var(--color-border, #e5e7eb)", fontWeight: 700, fontSize: "var(--text-sm)", background: "var(--color-surface, #fff)" }}
      >
        {SUPPORTED_LOCALES.map((l) => (
          <option key={l} value={l}>{LOCALE_LABELS[l]}</option>
        ))}
      </select>
    </label>
  );
}
