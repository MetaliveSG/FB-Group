"use client";

import { useState } from "react";
import { Sheet, Button, Stepper } from "./ui";
import { formatSGD } from "@/lib/format";
import type { MenuItem } from "@fbgroup/api-client";

// Item customisation in a bottom sheet (industry-standard pattern). Phase 1 renders
// the existing FLAT modifier list as toggle chips (no group_name/group_type yet);
// live price updates with selections + qty, then "Add · $total". Mounted fresh per
// item (keyed by the page) so selection state resets each open.
export default function CustomiseSheet({
  item,
  onClose,
  onAdd,
}: {
  item: MenuItem;
  onClose: () => void;
  onAdd: (item: MenuItem, modifierIds: string[], qty: number) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [qty, setQty] = useState(1);

  const toggle = (id: string) =>
    setSelected((p) => (p.includes(id) ? p.filter((m) => m !== id) : [...p, id]));

  const modDelta = item.modifiers
    .filter((m) => selected.includes(m.id))
    .reduce((s, m) => s + m.price_delta, 0);
  const total = (item.price + modDelta) * qty;
  const available = item.is_available;

  return (
    <Sheet open onClose={onClose}>
      {item.image_url && (
        <img src={item.image_url} alt={item.name} className="customise__img" loading="lazy" />
      )}
      <div className="customise__title">{item.name}</div>
      {item.description && item.description !== item.name && (
        <div className="customise__desc">{item.description}</div>
      )}
      <div className="customise__base">{formatSGD(item.price)}</div>

      {item.modifiers.length > 0 && (
        <div className="customise__group">
          <div className="customise__group-label">Options</div>
          <div className="modifier-list">
            {item.modifiers.map((mod) => (
              <button
                key={mod.id}
                type="button"
                className={`modifier-chip ${selected.includes(mod.id) ? "selected" : ""}`}
                onClick={() => toggle(mod.id)}
                disabled={!available}
              >
                {mod.name}
                {mod.price_delta !== 0 && (
                  <span style={{ opacity: 0.7 }}>
                    {" "}({mod.price_delta > 0 ? "+" : ""}{formatSGD(mod.price_delta)})
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="customise__actions">
        <Stepper value={qty} onChange={setQty} />
        <Button
          variant="primary"
          size="lg"
          style={{ flex: 1 }}
          disabled={!available}
          onClick={() => {
            onAdd(item, selected, qty);
            onClose();
          }}
        >
          {available ? `Add · ${formatSGD(total)}` : "Unavailable"}
        </Button>
      </div>
    </Sheet>
  );
}
