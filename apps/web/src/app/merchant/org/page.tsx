"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  orgBrands,
  createBrand,
  orgOutlets,
  createOutlet,
  orgTables,
  createTable,
  deleteTable,
  getApiBase,
} from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import MerchantSidebar from "@/components/MerchantSidebar";
import type { OrgBrand, OrgOutlet, OrgTable } from "@fbgroup/api-client";

export default function OrgPage() {
  const router = useRouter();
  const base = getApiBase();
  const mid = () => getOperatorMerchant()?.id;

  const [brands, setBrands] = useState<OrgBrand[]>([]);
  const [outlets, setOutlets] = useState<OrgOutlet[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // brand form
  const [brandName, setBrandName] = useState("");
  const [brandCuisine, setBrandCuisine] = useState("");

  // outlet form
  const [outletBrand, setOutletBrand] = useState("");
  const [outletName, setOutletName] = useState("");
  const [outletAddress, setOutletAddress] = useState("");

  // tables (per expanded outlet)
  const [expanded, setExpanded] = useState<string | null>(null);
  const [tables, setTables] = useState<OrgTable[]>([]);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tableLabel, setTableLabel] = useState("");
  const [tableSeats, setTableSeats] = useState("");
  const [tableError, setTableError] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const loadOrg = useCallback(
    async (tok: string) => {
      const [b, o] = await Promise.all([orgBrands(base, tok, mid()), orgOutlets(base, tok, mid())]);
      setBrands(b);
      setOutlets(o);
      if (b.length > 0 && !outletBrand) setOutletBrand(b[0].id);
    },
    [base, outletBrand]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    loadOrg(tok)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(msg || "Failed to load org structure");
          setLoading(false);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function reloadOrg() {
    const tok = getStaffToken();
    if (tok) await loadOrg(tok);
  }

  async function run(fn: () => Promise<unknown>, after?: () => void) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await reloadOrg();
      after?.();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  function addBrand() {
    const tok = getStaffToken();
    if (!tok || !brandName.trim()) return;
    run(
      () => createBrand(base, tok, { name: brandName.trim(), cuisine_type: brandCuisine.trim() || undefined }, mid()),
      () => {
        setBrandName("");
        setBrandCuisine("");
      }
    );
  }

  function addOutlet() {
    const tok = getStaffToken();
    if (!tok || !outletBrand || !outletName.trim()) return;
    run(
      () =>
        createOutlet(
          base,
          tok,
          { brand_id: outletBrand, name: outletName.trim(), address: outletAddress.trim() || undefined },
          mid()
        ),
      () => {
        setOutletName("");
        setOutletAddress("");
      }
    );
  }

  async function toggleTables(outletId: string) {
    if (expanded === outletId) {
      setExpanded(null);
      setTables([]);
      return;
    }
    const tok = getStaffToken();
    if (!tok) return;
    setExpanded(outletId);
    setTables([]);
    setTableError(null);
    setTablesLoading(true);
    try {
      const t = await orgTables(base, tok, outletId, mid());
      setTables(t);
    } catch (err: unknown) {
      setTableError(err instanceof Error ? err.message : "Failed to load tables");
    } finally {
      setTablesLoading(false);
    }
  }

  async function reloadTables(outletId: string) {
    const tok = getStaffToken();
    if (!tok) return;
    const t = await orgTables(base, tok, outletId, mid());
    setTables(t);
  }

  async function addTable(outletId: string) {
    const tok = getStaffToken();
    if (!tok || !tableLabel.trim()) return;
    setBusy(true);
    setTableError(null);
    try {
      await createTable(
        base,
        tok,
        outletId,
        { label: tableLabel.trim(), seats: parseInt(tableSeats, 10) || undefined },
        mid()
      );
      setTableLabel("");
      setTableSeats("");
      await reloadTables(outletId);
      await reloadOrg();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add table";
      const status =
        err && typeof err === "object" && "status" in err
          ? (err as { status?: number }).status
          : undefined;
      if (status === 409 || msg.includes("409") || msg.toLowerCase().includes("exist") || msg.toLowerCase().includes("duplicate")) {
        setTableError("A table with that label already exists in this outlet.");
      } else {
        setTableError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  async function removeTable(outletId: string, tableId: string) {
    const tok = getStaffToken();
    if (!tok || !window.confirm("Delete this table?")) return;
    setBusy(true);
    setTableError(null);
    try {
      await deleteTable(base, tok, tableId, mid());
      await reloadTables(outletId);
      await reloadOrg();
    } catch (err: unknown) {
      setTableError(err instanceof Error ? err.message : "Failed to delete table");
    } finally {
      setBusy(false);
    }
  }

  function copyToken(token: string) {
    navigator.clipboard?.writeText(token).then(
      () => {
        setCopiedToken(token);
        setTimeout(() => setCopiedToken(null), 1500);
      },
      () => {}
    );
  }

  function brandName_(brandId: string): string {
    return brands.find((b) => b.id === brandId)?.name ?? "—";
  }

  return (
    <MerchantSidebar active="org">
      <div className="page-header">
        <h1 className="page-title">Outlets &amp; Brands</h1>
        <p className="page-subtitle">Manage your brands, outlets, and table QR codes</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading org structure…
        </div>
      ) : (
        <>
          {/* Brands */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title" style={{ marginBottom: 12 }}>
              Brands
            </div>
            {brands.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)" }}>No brands yet.</p>
            ) : (
              <div className="table-wrapper" style={{ border: "none", marginBottom: 12 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Cuisine</th>
                      <th>Outlets</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {brands.map((b) => (
                      <tr key={b.id}>
                        <td style={{ fontWeight: 600 }}>{b.name}</td>
                        <td>{b.cuisine_type ?? "—"}</td>
                        <td>{b.outlets}</td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              background: b.is_active ? "#dcfce7" : "#fee2e2",
                              color: b.is_active ? "#166534" : "#991b1b",
                            }}
                          >
                            {b.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <input
                type="text"
                placeholder="Brand name"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                style={{ flex: 1, minWidth: 160 }}
              />
              <input
                type="text"
                placeholder="Cuisine (optional)"
                value={brandCuisine}
                onChange={(e) => setBrandCuisine(e.target.value)}
                style={{ flex: 1, minWidth: 140 }}
              />
              <button className="btn btn-primary btn-sm" disabled={busy} onClick={addBrand}>
                Add brand
              </button>
            </div>
          </div>

          {/* Outlets */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title" style={{ marginBottom: 12 }}>
              Outlets
            </div>
            {outlets.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)" }}>No outlets yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                {outlets.map((o) => (
                  <div
                    key={o.id}
                    style={{ border: "1px solid var(--color-border, #e5e7eb)", borderRadius: 8 }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 12px",
                        gap: 10,
                        flexWrap: "wrap",
                      }}
                    >
                      <div>
                        <span style={{ fontWeight: 600 }}>{o.name}</span>
                        <span style={{ fontSize: 12, color: "var(--color-text-muted)", marginLeft: 8 }}>
                          {o.brand_name ?? brandName_(o.brand_id)}
                          {o.address ? ` · ${o.address}` : ""}
                          {` · ${o.tables} table${o.tables === 1 ? "" : "s"}`}
                        </span>
                        {!o.is_active && (
                          <span className="badge" style={{ background: "#fee2e2", color: "#991b1b", marginLeft: 8 }}>
                            Inactive
                          </span>
                        )}
                      </div>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => toggleTables(o.id)}
                      >
                        {expanded === o.id ? "Hide tables" : "Tables & QR"}
                      </button>
                    </div>

                    {expanded === o.id && (
                      <div style={{ borderTop: "1px solid var(--color-border, #e5e7eb)", padding: 12, background: "#fafafa" }}>
                        {tableError && <div className="alert alert-error">{tableError}</div>}
                        {tablesLoading ? (
                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <span className="spinner" /> Loading tables…
                          </div>
                        ) : (
                          <>
                            {tables.length === 0 ? (
                              <p style={{ color: "var(--color-text-muted)", marginTop: 0 }}>No tables yet.</p>
                            ) : (
                              <div className="table-wrapper" style={{ border: "none", marginBottom: 10 }}>
                                <table>
                                  <thead>
                                    <tr>
                                      <th>Label</th>
                                      <th>Seats</th>
                                      <th>QR Token / Link</th>
                                      <th></th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {tables.map((t) => (
                                      <tr key={t.id}>
                                        <td style={{ fontWeight: 600 }}>{t.label}</td>
                                        <td>{t.seats}</td>
                                        <td>
                                          {t.qr_token ? (
                                            <span style={{ display: "inline-flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                                              <a
                                                href={`/t/${t.qr_token}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{ fontFamily: "monospace", fontSize: 12 }}
                                              >
                                                {t.qr_token}
                                              </a>
                                              <button
                                                className="btn btn-secondary btn-sm"
                                                style={{ padding: "1px 8px", fontSize: 11 }}
                                                onClick={() => copyToken(t.qr_token!)}
                                              >
                                                {copiedToken === t.qr_token ? "Copied" : "Copy"}
                                              </button>
                                            </span>
                                          ) : (
                                            "—"
                                          )}
                                        </td>
                                        <td>
                                          <button
                                            className="btn btn-secondary btn-sm"
                                            style={{ padding: "2px 8px" }}
                                            disabled={busy}
                                            onClick={() => removeTable(o.id, t.id)}
                                          >
                                            Delete
                                          </button>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            )}
                            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                              <input
                                type="text"
                                placeholder="Table label (e.g. T1)"
                                value={tableLabel}
                                onChange={(e) => setTableLabel(e.target.value)}
                                style={{ width: 160 }}
                              />
                              <input
                                type="number"
                                min="1"
                                placeholder="Seats"
                                value={tableSeats}
                                onChange={(e) => setTableSeats(e.target.value)}
                                style={{ width: 90 }}
                              />
                              <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => addTable(o.id)}>
                                Add table
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Add outlet form */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <select
                value={outletBrand}
                onChange={(e) => setOutletBrand(e.target.value)}
                style={{ minWidth: 150 }}
                disabled={brands.length === 0}
              >
                {brands.length === 0 && <option value="">No brands</option>}
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Outlet name"
                value={outletName}
                onChange={(e) => setOutletName(e.target.value)}
                style={{ flex: 1, minWidth: 140 }}
              />
              <input
                type="text"
                placeholder="Address (optional)"
                value={outletAddress}
                onChange={(e) => setOutletAddress(e.target.value)}
                style={{ flex: 1, minWidth: 160 }}
              />
              <button
                className="btn btn-primary btn-sm"
                disabled={busy || brands.length === 0}
                onClick={addOutlet}
              >
                Add outlet
              </button>
            </div>
            <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 0 }}>
              New outlets get an empty menu automatically — set it up in the <strong>Menu Editor</strong>.
            </p>
          </div>
        </>
      )}
    </MerchantSidebar>
  );
}
