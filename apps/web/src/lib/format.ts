// Utility helpers for formatting and cart calculations

/**
 * Format a number as SGD currency string.
 * e.g. 12.5 → "S$12.50"
 */
export function formatSGD(amount: number): string {
  return `S$${amount.toFixed(2)}`;
}

/**
 * Calculate cart subtotal from line items.
 */
export interface CartItem {
  unit_price: number;
  quantity: number;
  modifier_price_delta: number; // sum of selected modifier deltas
}

export function calcCartSubtotal(items: CartItem[]): number {
  return items.reduce((sum, item) => {
    const linePrice = (item.unit_price + item.modifier_price_delta) * item.quantity;
    return sum + linePrice;
  }, 0);
}

/**
 * Round to 2 decimal places (handles float drift).
 */
export function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

/**
 * Format a date string to a human-readable local date.
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("en-SG", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

/**
 * Tier badge color mapping.
 */
export function tierColor(tier: string): string {
  switch (tier?.toLowerCase()) {
    case "gold": return "#f59e0b";
    case "silver": return "#9ca3af";
    case "bronze": return "#b45309";
    default: return "#6b7280";
  }
}

/**
 * Churn label color mapping.
 */
export function churnColor(label: string): string {
  switch (label?.toLowerCase()) {
    case "high risk": return "#ef4444";
    case "medium risk": return "#f97316";
    case "low risk": return "#22c55e";
    default: return "#6b7280";
  }
}

/**
 * Relative time string from a date (e.g. "3h ago", "2d ago", "just now").
 * `now` is injectable for testing.
 */
export function relativeTime(dateStr: string | null | undefined, now: Date = new Date()): string {
  if (!dateStr) return "—";
  const then = new Date(dateStr).getTime();
  if (Number.isNaN(then)) return "—";
  const diffSec = Math.round((now.getTime() - then) / 1000);
  if (diffSec < 0) return "soon";
  if (diffSec < 45) return "just now";
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  const diffMon = Math.round(diffDay / 30);
  if (diffMon < 12) return `${diffMon}mo ago`;
  return `${Math.round(diffMon / 12)}y ago`;
}

/**
 * Compute the wheel rotation (in degrees) so the given winning segment lands
 * under the pointer at the top (12 o'clock / 0deg).
 *
 * Segments are drawn clockwise starting at the top. The center of segment
 * `index` sits at angle `(index + 0.5) * segmentAngle` clockwise from the top.
 * To bring that center under the top pointer we rotate the wheel by the
 * negative of that angle (normalized to [0,360)), plus full spins for drama.
 *
 * Returns a total rotation that is always >= the starting rotation so CSS
 * transitions spin forward.
 */
export function wheelTargetRotation(
  winningIndex: number,
  segmentCount: number,
  fullSpins = 5,
  currentRotation = 0
): number {
  if (segmentCount <= 0) return currentRotation;
  const segAngle = 360 / segmentCount;
  const centerAngle = (winningIndex + 0.5) * segAngle; // clockwise from top
  // Rotation needed (mod 360) so the segment center aligns to the top pointer.
  const targetMod = (360 - (centerAngle % 360)) % 360;
  // Advance from current rotation to the next occurrence of targetMod, then add full spins.
  const currentMod = ((currentRotation % 360) + 360) % 360;
  let delta = targetMod - currentMod;
  if (delta < 0) delta += 360;
  return currentRotation + delta + fullSpins * 360;
}

/**
 * Prettify a snake_case stage/key into Title Case words.
 * e.g. "offer_sent" → "Offer Sent", "at_risk" → "At Risk".
 */
export function prettyStage(key: string): string {
  return key
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
