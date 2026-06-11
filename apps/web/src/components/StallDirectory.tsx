"use client";

import { Icons } from "./ui";
import type { StallRef } from "@fbgroup/api-client";

// Foodcourt landing: a directory of stalls (each a menu). Tapping an open stall drills
// into its menu (the Phase-1 menu view). Closed stalls are shown but not selectable.
export default function StallDirectory({
  stalls,
  onSelect,
}: {
  stalls: StallRef[];
  onSelect: (stall: StallRef) => void;
}) {
  return (
    <div className="stall-grid">
      {stalls.map((s) => (
        <button
          key={s.menu_id}
          type="button"
          className={`stall-card${s.is_open ? "" : " stall-card--closed"}`}
          disabled={!s.is_open}
          onClick={() => s.is_open && onSelect(s)}
        >
          {s.signboard_url
            ? <img src={s.signboard_url} alt={s.stall_name} loading="lazy"
                   style={{ width: 56, height: 56, flexShrink: 0, objectFit: "contain", borderRadius: 12, background: "#fff", padding: 4, border: "1px solid var(--color-border, #e5e7eb)" }} />
            : <div className="stall-card__logo" aria-hidden>{s.logo || "🍽️"}</div>}
          <div className="stall-card__body">
            <div className="stall-card__name">{s.stall_name}</div>
            <div className="stall-card__meta">
              {s.cuisine ? `${s.cuisine} · ` : ""}{s.item_count} item{s.item_count === 1 ? "" : "s"}
            </div>
          </div>
          {s.is_open
            ? <Icons.ChevronRight size={20} className="stall-card__chev" />
            : <span className="stall-card__closed-tag">Closed</span>}
        </button>
      ))}
    </div>
  );
}
