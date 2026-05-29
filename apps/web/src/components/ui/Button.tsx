"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "./icons";

type Variant = "primary" | "secondary" | "ghost" | "accent" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  loading?: boolean;
  leftIcon?: LucideIcon;
  children?: ReactNode;
}

export default function Button({
  variant = "primary",
  size = "md",
  block,
  loading,
  leftIcon: Left,
  children,
  className = "",
  disabled,
  ...rest
}: ButtonProps) {
  const cls = [
    "ui-btn",
    `ui-btn--${variant}`,
    size !== "md" ? `ui-btn--${size}` : "",
    block ? "ui-btn--block" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const iconSize = size === "lg" ? 20 : size === "sm" ? 16 : 18;
  return (
    <button className={cls} disabled={disabled || loading} aria-busy={loading} {...rest}>
      {loading ? "…" : Left ? <Left size={iconSize} aria-hidden /> : null}
      {children}
    </button>
  );
}
