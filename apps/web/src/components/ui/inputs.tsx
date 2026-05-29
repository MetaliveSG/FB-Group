"use client";

import type { ReactNode } from "react";
import { Plus, Minus } from "./icons";

// ── Stepper (quantity) ──
export function Stepper({
  value,
  min = 1,
  max = 99,
  onChange,
}: {
  value: number;
  min?: number;
  max?: number;
  onChange: (next: number) => void;
}) {
  return (
    <div className="ui-stepper">
      <button
        className="ui-stepper__btn"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
        aria-label="Decrease quantity"
      >
        <Minus size={16} aria-hidden />
      </button>
      <span className="ui-stepper__val" aria-live="polite">{value}</span>
      <button
        className="ui-stepper__btn"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
        aria-label="Increase quantity"
      >
        <Plus size={16} aria-hidden />
      </button>
    </div>
  );
}

// ── Badge / Chip ──
type Tone = "default" | "success" | "danger" | "warning" | "gold";
export function Badge({ tone = "default", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`ui-badge${tone !== "default" ? ` ui-badge--${tone}` : ""}`}>{children}</span>;
}
