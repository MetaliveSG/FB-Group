"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  menuOutlets,
  outletMenu,
  createCategory,
  deleteCategory,
  createMenuItem,
  updateMenuItem,
  deleteMenuItem,
  createModifier,
  deleteModifier,
  getApiBase,
} from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import type { MenuAdminOutlet, Menu } from "@fbgroup/api-client";

export default function MenuEditorPage() {
  const router = useRouter();
  const base = getApiBase();
  const mid = () => getOperatorMerchant()?.id;

  const [outlets, setOutlets] = useState<MenuAdminOutlet[]>([]);
  const [selectedOutlet, setSelectedOutlet] = useState<MenuAdminOutlet | null>(null);
  const [menu, setMenu] = useState<Menu | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // forms
  const [newCategory, setNewCategory] = useState("");
  const [newItem, setNewItem] = useState<Record<string, { name: string; price: string; description: string }>>({});
  const [newModifier, setNewModifier] = useState<Record<string, { name: string; delta: string }>>({});

  const loadMenu = useCallback(
    async (tok: string, outletId: string) => {
      const m = await outletMenu(base, tok, outletId);
      setMenu(m);
    },
    [base]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    menuOutlets(base, tok, mid())
      .then(async (ots) => {
        setOutlets(ots);
        if (ots.length > 0) {
          setSelectedOutlet(ots[0]);
          await loadMenu(tok, ots[0].outlet_id);
        }
        setLoading(false);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(msg || "Failed to load outlets");
          setLoading(false);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function reload() {
    const tok = getStaffToken();
    if (!tok || !selectedOutlet) return;
    await loadMenu(tok, selectedOutlet.outlet_id);
  }

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await reload();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSelectOutlet(outletId: string) {
    const tok = getStaffToken();
    if (!tok) return;
    const o = outlets.find((x) => x.outlet_id === outletId) ?? null;
    setSelectedOutlet(o);
    setMenu(null);
    if (o) {
      setLoading(true);
      await loadMenu(tok, o.outlet_id).catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load menu")
      );
      setLoading(false);
    }
  }

  function addCategory() {
    const tok = getStaffToken();
    if (!tok || !selectedOutlet || !newCategory.trim()) return;
    run(() =>
      createCategory(base, tok, { menu_id: selectedOutlet.menu_id, name: newCategory.trim() }, mid())
    ).then(() => setNewCategory(""));
  }

  function addItem(categoryId: string) {
    const tok = getStaffToken();
    const draft = newItem[categoryId];
    if (!tok || !draft?.name.trim()) return;
    run(() =>
      createMenuItem(
        base,
        tok,
        {
          category_id: categoryId,
          name: draft.name.trim(),
          price: parseFloat(draft.price) || 0,
          description: draft.description.trim() || undefined,
        },
        mid()
      )
    ).then(() => setNewItem((p) => ({ ...p, [categoryId]: { name: "", price: "", description: "" } })));
  }

  function addModifier(itemId: string) {
    const tok = getStaffToken();
    const draft = newModifier[itemId];
    if (!tok || !draft?.name.trim()) return;
    run(() =>
      createModifier(
        base,
        tok,
        { item_id: itemId, name: draft.name.trim(), price_delta: parseFloat(draft.delta) || 0 },
        mid()
      )
    ).then(() => setNewModifier((p) => ({ ...p, [itemId]: { name: "", delta: "" } })));
  }

  function toggleAvail(itemId: string, current: boolean) {
    const tok = getStaffToken();
    if (!tok) return;
    run(() => updateMenuItem(base, tok, itemId, { is_available: !current }, mid()));
  }

  function editPrice(itemId: string, current: number) {
    const tok = getStaffToken();
    if (!tok) return;
    const input = window.prompt("New price (SGD):", String(current));
    if (input === null) return;
    const price = parseFloat(input);
    if (Number.isNaN(price) || price < 0) {
      setError("Invalid price.");
      return;
    }
    run(() => updateMenuItem(base, tok, itemId, { price }, mid()));
  }

  function removeItem(itemId: string) {
    const tok = getStaffToken();
    if (!tok || !window.confirm("Delete this item?")) return;
    run(() => deleteMenuItem(base, tok, itemId, mid()));
  }

  function removeCategory(categoryId: string) {
    const tok = getStaffToken();
    if (!tok || !window.confirm("Delete this category and its items?")) return;
    run(() => deleteCategory(base, tok, categoryId, mid()));
  }

  function removeModifier(modifierId: string) {
    const tok = getStaffToken();
    if (!tok) return;
    run(() => deleteModifier(base, tok, modifierId, mid()));
  }

  return (
    <MerchantSidebar active="menu">
      <div className="page-header">
        <h1 className="page-title">Menu Editor</h1>
        <p className="page-subtitle">Manage categories, items &amp; modifiers per outlet</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ fontWeight: 600, fontSize: 14 }}>Outlet</label>
          <select
            value={selectedOutlet?.outlet_id ?? ""}
            onChange={(e) => onSelectOutlet(e.target.value)}
            style={{ minWidth: 220 }}
            disabled={loading || outlets.length === 0}
          >
            {outlets.length === 0 && <option value="">No outlets</option>}
            {outlets.map((o) => (
              <option key={o.outlet_id} value={o.outlet_id}>
                {o.name}
              </option>
            ))}
          </select>
          {busy && <span className="spinner" />}
        </div>
      </div>

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading menu…
        </div>
      ) : !menu ? (
        <p style={{ color: "var(--color-text-muted)" }}>No menu to display.</p>
      ) : (
        <>
          {/* Add category */}
          {selectedOutlet && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="New category name"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button className="btn btn-primary btn-sm" disabled={busy} onClick={addCategory}>
                  Add category
                </button>
              </div>
            </div>
          )}

          {menu.categories.length === 0 ? (
            <p style={{ color: "var(--color-text-muted)" }}>No categories yet.</p>
          ) : (
            menu.categories.map((cat) => (
              <div className="card" key={cat.id} style={{ marginBottom: 16 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 12,
                  }}
                >
                  <div className="card-title" style={{ margin: 0 }}>
                    {cat.name}
                  </div>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: "2px 10px" }}
                    disabled={busy}
                    onClick={() => removeCategory(cat.id)}
                  >
                    Delete category
                  </button>
                </div>

                {/* Items */}
                {cat.items.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      borderTop: "1px solid var(--color-border, #e5e7eb)",
                      padding: "10px 0",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                      <div style={{ flex: 1, minWidth: 180 }}>
                        <span style={{ fontWeight: 600 }}>{item.name}</span>
                        {!item.is_available && (
                          <span className="badge" style={{ background: "#fee2e2", color: "#991b1b", marginLeft: 8 }}>
                            Unavailable
                          </span>
                        )}
                        {item.description && (
                          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{item.description}</div>
                        )}
                      </div>
                      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                        <span style={{ fontWeight: 600 }}>{formatSGD(item.price)}</span>
                        <button className="btn btn-secondary btn-sm" style={{ padding: "2px 8px" }} disabled={busy} onClick={() => editPrice(item.id, item.price)}>
                          Edit price
                        </button>
                        <button className="btn btn-secondary btn-sm" style={{ padding: "2px 8px" }} disabled={busy} onClick={() => toggleAvail(item.id, item.is_available)}>
                          {item.is_available ? "Mark unavailable" : "Mark available"}
                        </button>
                        <button className="btn btn-secondary btn-sm" style={{ padding: "2px 8px" }} disabled={busy} onClick={() => removeItem(item.id)}>
                          Delete
                        </button>
                      </div>
                    </div>

                    {/* Modifiers */}
                    <div style={{ marginTop: 6, paddingLeft: 12 }}>
                      {item.modifiers.map((mod) => (
                        <span
                          key={mod.id}
                          className="badge"
                          style={{ background: "#f3f4f6", color: "#374151", marginRight: 6 }}
                        >
                          {mod.name} {mod.price_delta ? `(${formatSGD(mod.price_delta)})` : ""}
                          <button
                            onClick={() => removeModifier(mod.id)}
                            disabled={busy}
                            style={{ marginLeft: 6, border: "none", background: "none", cursor: "pointer", color: "#991b1b" }}
                            title="Remove modifier"
                          >
                            ×
                          </button>
                        </span>
                      ))}
                      <span style={{ display: "inline-flex", gap: 4, alignItems: "center", marginTop: 4 }}>
                        <input
                          type="text"
                          placeholder="Modifier"
                          value={newModifier[item.id]?.name ?? ""}
                          onChange={(e) =>
                            setNewModifier((p) => ({
                              ...p,
                              [item.id]: { name: e.target.value, delta: p[item.id]?.delta ?? "" },
                            }))
                          }
                          style={{ width: 110, padding: "2px 6px", fontSize: 12 }}
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="±$"
                          value={newModifier[item.id]?.delta ?? ""}
                          onChange={(e) =>
                            setNewModifier((p) => ({
                              ...p,
                              [item.id]: { name: p[item.id]?.name ?? "", delta: e.target.value },
                            }))
                          }
                          style={{ width: 70, padding: "2px 6px", fontSize: 12 }}
                        />
                        <button className="btn btn-secondary btn-sm" style={{ padding: "2px 8px" }} disabled={busy} onClick={() => addModifier(item.id)}>
                          + Mod
                        </button>
                      </span>
                    </div>
                  </div>
                ))}

                {/* Add item */}
                <div
                  style={{
                    borderTop: "1px solid var(--color-border, #e5e7eb)",
                    paddingTop: 10,
                    marginTop: 6,
                    display: "flex",
                    gap: 6,
                    flexWrap: "wrap",
                    alignItems: "center",
                  }}
                >
                  <input
                    type="text"
                    placeholder="Item name"
                    value={newItem[cat.id]?.name ?? ""}
                    onChange={(e) =>
                      setNewItem((p) => ({
                        ...p,
                        [cat.id]: { ...(p[cat.id] ?? { price: "", description: "" }), name: e.target.value },
                      }))
                    }
                    style={{ flex: 1, minWidth: 130 }}
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Price"
                    value={newItem[cat.id]?.price ?? ""}
                    onChange={(e) =>
                      setNewItem((p) => ({
                        ...p,
                        [cat.id]: { ...(p[cat.id] ?? { name: "", description: "" }), price: e.target.value },
                      }))
                    }
                    style={{ width: 90 }}
                  />
                  <input
                    type="text"
                    placeholder="Description"
                    value={newItem[cat.id]?.description ?? ""}
                    onChange={(e) =>
                      setNewItem((p) => ({
                        ...p,
                        [cat.id]: { ...(p[cat.id] ?? { name: "", price: "" }), description: e.target.value },
                      }))
                    }
                    style={{ flex: 1, minWidth: 130 }}
                  />
                  <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => addItem(cat.id)}>
                    Add item
                  </button>
                </div>
              </div>
            ))
          )}
        </>
      )}
    </MerchantSidebar>
  );
}
