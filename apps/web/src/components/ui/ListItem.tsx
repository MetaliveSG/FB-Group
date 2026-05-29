"use client";

import type { ReactNode } from "react";
import { ChevronRight, type LucideIcon } from "./icons";

interface ListItemProps {
  icon?: LucideIcon;
  title: ReactNode;
  meta?: ReactNode;
  right?: ReactNode;
  chevron?: boolean;
  onClick?: () => void;
}

export default function ListItem({ icon: Icon, title, meta, right, chevron, onClick }: ListItemProps) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag className="ui-list-item" onClick={onClick} type={onClick ? "button" : undefined}>
      {Icon && <Icon className="ui-list-item__icon" size={22} aria-hidden />}
      <span className="ui-list-item__body">
        <span className="ui-list-item__title">{title}</span>
        {meta != null && <span className="ui-list-item__meta">{meta}</span>}
      </span>
      {right}
      {chevron && <ChevronRight className="ui-list-item__chevron" size={20} aria-hidden />}
    </Tag>
  );
}
