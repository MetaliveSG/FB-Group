// Browser proof: log in as each BreadTalk level and screenshot the live Org-Tree console,
// showing a parent sees ALL its children (stalls/outlets/brands) with the right manage rights.
//   node screens.mjs            (defaults to http://localhost:3001)
import { chromium } from "playwright";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { mkdirSync } from "fs";

const WEB = process.env.WEB || "http://localhost:3001";
const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "screens");
mkdirSync(OUT, { recursive: true });
const PW = "Password123!";

// Representative levels: top Chain (Manager) → Storefront, plus finance read-only + isolation.
const LEVELS = [
  ["ceo@breadtalk.sg", "1-group-chain-manager"],
  ["cfo@breadtalk.sg", "2-group-finance-readonly"],
  ["owner.m1@breadtalk.sg", "3-tenant-chain-manager"],
  ["mgr.toastbox@breadtalk.sg", "4-chain-toastbox"],
  ["mgr.foodrepublic@breadtalk.sg", "5-chain-foodrepublic-foodcourt"],
  ["mgr.ion@breadtalk.sg", "6-storefront-ion"],
  ["staff.chicken@breadtalk.sg", "7-storefront-staff-chickenrice"],
  ["mgr.dtf@breadtalk.sg", "8-chain-dintaifung-tenant2"],
];

const browser = await chromium.launch();
for (const [email, slug] of LEVELS) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1100 } });
  const page = await ctx.newPage();
  await page.goto(`${WEB}/merchant/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', PW);
  await page.click('button[type="submit"]');
  // Wait until the login actually persisted a staff token before navigating (avoid the race).
  await page.waitForFunction(() => !!localStorage.getItem("fbgroup_staff_token"), { timeout: 15000 });
  // Land straight on the Org-Tree console (works for multi-merchant enterprise accounts too).
  await page.goto(`${WEB}/merchant/org-tree`, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Org Tree", { timeout: 15000 });
  await page.waitForTimeout(700); // let the tree fetch + render
  await page.screenshot({ path: join(OUT, `${slug}.png`), fullPage: true });
  console.log(`captured ${slug}  (${email})`);
  await ctx.close();
}
await browser.close();
console.log(`\nScreenshots in ${OUT}`);
