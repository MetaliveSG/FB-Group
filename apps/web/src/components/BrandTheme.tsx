"use client";
// Injects a brand's theme as CSS-variable overrides on :root (the whole design system is token-driven,
// so this rebrands the customer app without touching any component). Render anywhere on the page.
import type { BrandTheme as Theme } from "@fbgroup/api-client";

function darken(hex: string, f = 0.82): string {
  const m = hex.replace("#", "");
  if (m.length !== 6) return hex;
  const n = parseInt(m, 16);
  if (Number.isNaN(n)) return hex;
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((x) => Math.round(x * f));
  return "#" + c.map((x) => x.toString(16).padStart(2, "0")).join("");
}

export default function BrandTheme({ theme }: { theme?: Theme | null }) {
  if (!theme || (!theme.primary && !theme.accent)) return null;
  const css: string[] = [];
  if (theme.primary) {
    css.push(
      `--color-primary:${theme.primary}`,
      `--brand-500:${theme.primary}`,
      `--brand-600:${theme.primary}`,
      `--brand-700:${darken(theme.primary)}`,
    );
  }
  if (theme.accent) css.push(`--color-accent:${theme.accent}`);
  return <style>{`:root{${css.join(";")}}`}</style>;
}
