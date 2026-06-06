// POS web/PIN segregation proof. Run from repo root after api+web are up.
//   node artifacts/pos-proof/segregation_proof.mjs
import { chromium } from "playwright";

const WEB = "http://localhost:3001", API = "http://localhost:8000/api/v1";
const log = (...a) => process.stdout.write(a.join(" ") + "\n");
const post = (p, b, t) => fetch(API + p, { method: "POST", headers: { "Content-Type": "application/json", ...(t ? { Authorization: "Bearer " + t } : {}) }, body: JSON.stringify(b) }).then(async r => ({ s: r.status, j: await r.json().catch(() => ({})) }));

const admin = (await post("/auth/staff/login", { email: "superadmin@platform.sg", password: "Password123!" })).j.access_token;
// find Pepper Lunch Group to parent a fresh storefront under
const tree = await (await fetch(API + "/org/tree", { headers: { Authorization: "Bearer " + admin } })).json();
const parent = tree.nodes.find(n => n.name === "Pepper Lunch Group") || tree.nodes.find(n => n.role === "CHAIN" && n.can_manage);
log("parent chain:", parent.name, parent.id.slice(0, 8));

// 1) Create storefront → auto-provisions a 5-person POS team with one-time PINs
const created = await post("/org/nodes", { parent_id: parent.id, role: "STOREFRONT", name: "Proof SF" }, admin);
const node = created.j;
log("\n[1] storefront created:", created.s, "| outlet_id:", node.outlet_id?.slice(0, 8), "| qr_path:", node.qr_path);
log("    POS team:", node.pos_team.map(m => `${m.role}:${m.pin}`).join("  "));
log("    team size:", node.pos_team.length, "| unique pins:", new Set(node.pos_team.map(m => m.pin)).size);
const cashier = node.pos_team.find(m => m.role === "cashier");
const merchant_id = parent.id;  // SF inherits the tenant (Pepper Lunch Group == m... tenant root)

// 2) PIN-login works at THIS storefront's outlet
const ok = await post("/auth/staff/pin-login", { merchant_id, outlet_id: node.outlet_id, pin: cashier.pin });
log("\n[2] PIN-login at bound outlet:", ok.s, "| user:", ok.j.user?.full_name, "| actor:", ok.j.actor);

// 3) Same PIN must NOT work at a different storefront
const other = tree.nodes.find(n => n.sells && n.outlet_id && n.id !== node.id);
let crossStatus = "n/a";
if (other) {
  const oOutlet = (await (await fetch(API + "/org/tree", { headers: { Authorization: "Bearer " + admin } })).json()).nodes.find(n => n.id === other.id)?.outlet_id;
  if (oOutlet) crossStatus = (await post("/auth/staff/pin-login", { merchant_id: other.settlement_account_id || merchant_id, outlet_id: oOutlet, pin: cashier.pin })).s;
}
log("\n[3] same PIN at a DIFFERENT storefront →", crossStatus, "(expect 401 — per-storefront scope)");

// 4) POS user cannot web-login (synthetic @pos.local id rejected at the web login)
const web = await post("/auth/staff/login", { email: "pos-deadbeef-aaaaaa@pos.local", password: "whatever" });
log("\n[4] POS-style id at web login →", web.s, "(blocked: 401/422)");

// 4b) PINs are READABLE in the list (owner reveals via eye) + owner can SET a chosen PIN
const rows = await (await fetch(API + `/org/nodes/${node.id}/pos-staff`, { headers: { Authorization: "Bearer " + admin } })).json();
log("\n[4b] list returns readable PINs:", rows.every(r => r.pin && r.pin_set), "| e.g.", rows[0].full_name, "→", rows[0].pin);
const setRes = await post(`/org/nodes/${node.id}/pos-staff/${cashier.user_id}/reset-pin`, { pin: "246813" }, admin);
const chosenLogin = await post("/auth/staff/pin-login", { merchant_id, outlet_id: node.outlet_id, pin: "246813" });
log("     set chosen PIN 246813 →", setRes.s, "| login with chosen PIN →", chosenLogin.s, "(expect 200)");

// 5) Browser: bind the new storefront POS, PIN in (the chosen 246813), see the order screen
const livePin = "246813";  // the cashier's PIN after [4b]
const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1280, height: 850 } });
const errs = []; pg.on("pageerror", e => errs.push(e.message.split("\n")[0]));
let qrPath = node.qr_path;
if (!qrPath) {  // older image: create response may omit qr_path → read it from the tree
  const t2 = await (await fetch(API + "/org/tree", { headers: { Authorization: "Bearer " + admin } })).json();
  qrPath = t2.nodes.find(n => n.id === node.id)?.qr_path;
}
const bindTok = qrPath.replace("/t/", "");
await pg.goto(`${WEB}/pos`, { waitUntil: "networkidle" });
await pg.evaluate(() => localStorage.clear());
await pg.goto(`${WEB}/pos?bind=${bindTok}`, { waitUntil: "networkidle" }); await pg.waitForTimeout(1500);
for (const d of livePin.split("")) await pg.locator(`button:text-is("${d}")`).first().click();
await pg.locator("button:has-text('OK')").click(); await pg.waitForTimeout(1500);
const onOrder = /Ticket|POS/i.test(await pg.locator("body").innerText());
log("\n[5] browser POS PIN-login → order screen:", onOrder, "| errors:", errs.length ? errs.join("|") : "none");
await pg.screenshot({ path: "artifacts/pos-proof/screens/seg_01_pos_after_pin.png" });

await b.close();
log("\nDONE");
