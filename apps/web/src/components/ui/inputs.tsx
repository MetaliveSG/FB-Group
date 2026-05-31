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

// ── Toggle (left/right switch) — replaces Yes/No · Enable/Disable · On/Off ──
export function Toggle({
  on,
  onChange,
  disabled = false,
  label,
}: {
  on: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={() => onChange(!on)}
      style={{
        position: "relative",
        width: 44,
        height: 24,
        flex: "0 0 auto",
        borderRadius: 999,
        border: "none",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        background: on ? "var(--color-primary, #16a34a)" : "var(--color-border, #cbd5e1)",
        transition: "background .15s",
        padding: 0,
      }}
    >
      <span
        aria-hidden
        style={{
          position: "absolute",
          top: 2,
          left: on ? 22 : 2,
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: "#fff",
          boxShadow: "0 1px 2px rgba(0,0,0,0.25)",
          transition: "left .15s",
        }}
      />
    </button>
  );
}
