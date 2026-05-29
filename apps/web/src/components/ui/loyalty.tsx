"use client";

// ── CoinBalance pill (gold $ disc + amount) ──
export function CoinBalance({ coins, label }: { coins: number; label?: string }) {
  return (
    <span className="ui-coin" title={label ?? "Coins"}>
      <span className="ui-coin__disc">$</span>
      {coins.toLocaleString()}
    </span>
  );
}

// ── Tier progress bar ──
export function TierProgress({
  pct,
  fromLabel,
  toLabel,
}: {
  pct: number; // 0..100
  fromLabel?: string;
  toLabel?: string;
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));
  return (
    <div>
      {(fromLabel || toLabel) && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "var(--text-sm)",
            color: "var(--color-text-muted)",
            marginBottom: "var(--space-1)",
          }}
        >
          <span>{fromLabel}</span>
          <span>{toLabel}</span>
        </div>
      )}
      <div className="ui-tier__track">
        <div className="ui-tier__fill" style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}
