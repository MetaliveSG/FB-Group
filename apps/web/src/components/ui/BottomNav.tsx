"use client";

import type { LucideIcon } from "./icons";

export interface TabItem {
  key: string;
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
  badge?: boolean; // show a notification dot on this tab
}

export default function BottomNav({ items, active }: { items: TabItem[]; active: string }) {
  return (
    <nav className="ui-tabbar" aria-label="Primary">
      {items.map((t) => {
        const Icon = t.icon;
        const isActive = t.key === active;
        return (
          <button
            key={t.key}
            className={`ui-tabbar__item${isActive ? " ui-tabbar__item--active" : ""}`}
            onClick={t.onClick}
            aria-current={isActive ? "page" : undefined}
          >
            <span className="ui-tabbar__icon">
              <Icon size={22} aria-hidden />
              {t.badge && <span className="ui-tabbar__dot" aria-label="available" />}
            </span>
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}
