// POS void flow proof — supervisor-authorized. Run from repo root after api+web are up.
//   node artifacts/pos-proof/void_proof.mjs
import { chromium } from "playwright";

const WEB = "http://localhost:3001", API = "http://localhost:8000/api/v1";
const log = (...a) => process.stdout.write(a.join(" ") + "\n");
const auth = (t) => ({ Authorization: "Bearer " + t });
const post = (p, b, t) => fetch(API + p, { method: "POST", headers: { "Content-Type": "application/json", ...(t ? auth(t) : {}) }, body: JSON.stringify(b) }).then(async r => ({ s: r.status, j: await r.json().catch(() => ({})) }));
const get = (p, t) => fetch(API + p, { headers: t ? auth(t) : {} }).then(r => r.json());

const admin = (await post("/auth/staff/login", { email: "superadmin@platform.sg", password: "Password123!" })).j.access_token;
const tree = await get("/org/tree", admin);
const sf = tree.nodes.find(n => n.name === "Pepper Lunch @ TPY");
const token = sf.qr_path.replace("/t/", "");
const qr = await get(`/qr/${token}`);
const merchant_id = qr.merchant.id;
const item = qr.menu.categories.flatMap(c => c.items)[0];
const staff = await get(`/org/nodes/${sf.id}/pos-staff`, admin);
const sup = staff.find(s => s.role === "supervisor"), cash = staff.find(s => s.role === "cashier");
log("storefront:", sf.name, "| supervisor PIN", sup.pin, "| cashier PIN", cash.pin, "| item:", item.name);

// ── A) API: cashier can't void, supervisor can ───────────────────────────
const tc = (await post("/auth/staff/pin-login", { merchant_id, outlet_id: sf.outlet_id, pin: cash.pin })).j.access_token;
const order = (await post("/orders/manual", { outlet_id: sf.outlet_id, items: [{ menu_item_id: item.id, quantity: 1 }] }, tc)).j;
await post(`/orders/${order.id}/cashier-checkout`, { method: "cash" }, tc);
log("\n[A] cashier rang + paid order", order.id.slice(0, 8));
const vc = await post(`/orders/${order.id}/void`, { reason: "x" }, tc);
log("[A] void by CASHIER →", vc.s, "(expect 403 — no order.void)");
const ts = (await post("/auth/staff/pin-login", { merchant_id, outlet_id: sf.outlet_id, pin: sup.pin })).j.access_token;
const vs = await post(`/orders/${order.id}/void`, { reason: "wrong order" }, ts);
log("[A] void by SUPERVISOR →", vs.s, "| status:", vs.j.status, "| $reversed:", vs.j.amount, "(expect 200/voided)");

// ── B) Browser: ring → pay → Void sale → cashier PIN blocked → supervisor PIN voids ──
const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1280, height: 850 } });
const errs = []; pg.on("pageerror", e => errs.push(e.message.split("\n")[0]));
await pg.goto(`${WEB}/pos`, { waitUntil: "networkidle" });
await pg.evaluate(() => localStorage.clear());
await pg.goto(`${WEB}/pos?bind=${token}`, { waitUntil: "networkidle" }); await pg.waitForTimeout(1500);
for (const d of cash.pin.split("")) await pg.locator(`button:text-is("${d}")`).first().click();
await pg.locator("button:has-text('OK')").click(); await pg.waitForTimeout(1500);
await pg.locator('[data-testid="pos-item"]').first().click(); await pg.waitForTimeout(400);
await pg.locator('[data-testid="pos-charge"]').click(); await pg.waitForTimeout(700);
await pg.locator('[data-testid^="pos-pay-"]').first().click(); await pg.waitForTimeout(2200);
log("\n[B] on receipt screen:", /TOTAL/i.test(await pg.locator("body").innerText()));
await pg.locator('[data-testid="pos-void"]').click(); await pg.waitForTimeout(300);
await pg.locator('input[type=password]').fill(cash.pin);
await pg.locator("button:has-text('Void')").last().click(); await pg.waitForTimeout(1500);
log("[B] cashier PIN blocked:", /Supervisor PIN/i.test(await pg.locator("body").innerText()));
await pg.locator('input[type=password]').fill(sup.pin);
await pg.locator("button:has-text('Void')").last().click(); await pg.waitForTimeout(2000);
const body = await pg.locator("body").innerText();
log("[B] voided banner shown:", /Sale voided/i.test(body), "| errors:", errs.length ? errs.join("|") : "none");
await pg.screenshot({ path: "artifacts/pos-proof/screens/void_01_done.png" });
await b.close();
log("\nDONE");
