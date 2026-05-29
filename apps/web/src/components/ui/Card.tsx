import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  pad?: boolean;
  flush?: boolean;
  children?: ReactNode;
}

export default function Card({ pad = true, flush, children, className = "", ...rest }: CardProps) {
  const cls = ["ui-card", pad && !flush ? "ui-card--pad" : "", flush ? "ui-card--flush" : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
