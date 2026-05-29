"use client";

import { useEffect, type ReactNode } from "react";
import type { LucideIcon } from "./icons";

// ── Skeleton ──
export function Skeleton({
  width = "100%",
  height = 16,
  radius,
  style,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  style?: React.CSSProperties;
}) {
  return <div className="ui-skel" style={{ width, height, borderRadius: radius, ...style }} aria-hidden />;
}

// ── EmptyState ──
export function EmptyState({
  icon: Icon,
  title,
  children,
}: {
  icon?: LucideIcon;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="ui-empty">
      {Icon && <Icon className="ui-empty__icon" size={44} aria-hidden />}
      <div className="ui-empty__title">{title}</div>
      {children && <div>{children}</div>}
    </div>
  );
}

// ── Bottom Sheet ──
export function Sheet({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="ui-sheet__overlay" onClick={onClose} role="dialog" aria-modal>
      <div className="ui-sheet__panel" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="ui-sheet__grip-btn" onClick={onClose} aria-label="Close">
          <span className="ui-sheet__grip" />
        </button>
        {children}
      </div>
    </div>
  );
}
