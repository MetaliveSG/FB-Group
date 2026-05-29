/**
 * FB Group design tokens — the single source of truth for the visual system.
 *
 * This is plain TypeScript with no web/React-Native-specific APIs, so the SAME
 * object powers the Next.js web app today AND a React Native / Expo app later.
 * Web consumes it via inline styles / the mirrored CSS variables in tokens.css;
 * React Native imports `theme` directly (it can't read CSS vars, but it can read
 * this object). Change a value here → it changes everywhere, on both platforms.
 *
 * Anchored on the existing brand: navy `#0f4c75` (primary) + amber `#e8960a`
 * (accent) + the jackpot gold for premium/game surfaces.
 */

// ─── Color ramps ────────────────────────────────────────────────────────────
const brand = {
  50: "#fff4ed", 100: "#ffe6d5", 200: "#fecdaa", 300: "#fda674",
  400: "#fb7a3c", 500: "#f4531d", 600: "#e23a0f", 700: "#bd2d0c",
  800: "#972711", 900: "#7c2410",
} as const; // 600 = primary — warm "flame" orange-red (appetising F&B energy)

const amber = {
  50: "#fff7ea", 100: "#fde9c2", 200: "#fbd488", 300: "#f6bb4d",
  400: "#f0a623", 500: "#e8960a", 600: "#c47908", 700: "#9c5f0a",
  800: "#7e4d0f", 900: "#6a4110",
} as const; // 500 = the existing --color-accent

const gold = {
  300: "#ffe680", 400: "#ffd84d", 500: "#f4c430", 600: "#c8961f",
  700: "#9c6a0c", 800: "#8b6508",
} as const; // premium / jackpot / wheel surfaces

const neutral = {
  // warm-tinted greys (stone) — pair with the flame brand for an appetising feel
  0: "#ffffff", 50: "#faf8f6", 100: "#f4f1ee", 200: "#e7e2dd",
  300: "#d6cfc8", 400: "#a89f97", 500: "#78706a", 600: "#574f4a",
  700: "#3d3833", 800: "#272320", 900: "#1a1714", 1000: "#000000",
} as const;

const semanticColor = {
  successFg: "#15803d", success: "#16a34a", successBg: "#dcfce7",
  dangerFg: "#b91c1c", danger: "#dc2626", dangerBg: "#fee2e2",
  warningFg: "#b45309", warning: "#d97706", warningBg: "#fef3c7",
  info: "#0ea5e9", infoBg: "#e0f2fe",
} as const;

// ─── Tokens ──────────────────────────────────────────────────────────────────
export const theme = {
  color: {
    brand,
    amber,
    gold,
    neutral,
    ...semanticColor,

    // semantic aliases — what components should actually reference
    primary: brand[600],
    primaryHover: brand[500],
    primaryActive: brand[700],
    accent: amber[500],
    accentHover: amber[400],

    bg: neutral[50],
    surface: neutral[0],
    surfaceAlt: neutral[100],
    text: neutral[900],
    textMuted: neutral[500],
    textInverse: neutral[0],
    border: neutral[200],
    borderStrong: neutral[300],
    overlay: "rgba(15, 23, 42, 0.55)",
  },

  // 4px base, 8pt rhythm — every padding/margin/gap snaps to one of these
  space: { 0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48, 8: 64, 9: 96 },

  radius: { none: 0, sm: 6, md: 8, lg: 12, xl: 16, "2xl": 24, pill: 9999 },

  font: {
    family: {
      sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
      // For a premium consumer feel later, swap to a webfont (e.g. Inter / Plus Jakarta Sans).
      display: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      mono: '"SF Mono", "Courier New", ui-monospace, monospace',
    },
    size: {
      xs: 12, sm: 14, base: 16, lg: 18, xl: 20,
      "2xl": 24, "3xl": 30, "4xl": 36, "5xl": 48,
    },
    weight: { regular: 400, medium: 500, semibold: 600, bold: 700, black: 900 },
    leading: { tight: 1.1, snug: 1.25, normal: 1.5, relaxed: 1.65 },
  },

  shadow: {
    sm: "0 1px 2px rgba(0,0,0,0.06)",
    md: "0 2px 8px rgba(0,0,0,0.08)",
    lg: "0 8px 24px rgba(0,0,0,0.12)",
    xl: "0 16px 40px rgba(0,0,0,0.18)",
    gold: "0 0 24px rgba(255,215,0,0.55)", // glow for win/premium moments
  },

  motion: {
    duration: { fast: 150, base: 250, slow: 400, slower: 600 }, // ms
    easing: {
      out: "cubic-bezier(0.2, 0.8, 0.2, 1)",
      inOut: "cubic-bezier(0.4, 0, 0.2, 1)",
      spring: "cubic-bezier(0.18, 0.9, 0.32, 1.15)", // slight overshoot (reel land, pops)
    },
  },

  zIndex: {
    base: 0, dropdown: 1000, sticky: 1100, overlay: 1200,
    modal: 1300, toast: 1400, max: 9999,
  },

  // mobile-first: design at `sm` (390) first, scale up
  breakpoint: { sm: 390, md: 768, lg: 1024, xl: 1280 },

  // touch ergonomics
  size: { touchMin: 44, tabBar: 64, headerH: 56 },
} as const;

export type Theme = typeof theme;
export default theme;
