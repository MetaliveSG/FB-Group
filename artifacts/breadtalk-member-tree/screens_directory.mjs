// Proof: the operator Merchant Directory is now a MEMBER-TREE drill-down.
// Top level shows "BreadTalk Group" (Enterprise); clicking it zooms DOWN to the two companies,
// then into a company's brands → outlets → stalls.
import { chromium } from "playwright";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { mkdirSync } from "fs";

const WEB = process.env.WEB || "http://localhost:3001";
const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "screens");
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1100 } });
const page = await ctx.newPage();

await page.goto(`${WEB}/platform/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "superadmin@platform.sg");
await page.fill('input[type="password"]', "Password123!");
await page.click('button[type="submit"]');
await page.waitForFunction(() => !!localStorage.getItem("fbgroup_staff_token"), { timeout: 15000 });
await page.goto(`${WEB}/platform`, { waitUntil: "networkidle" });
await page.waitForSelector("text=Merchant Directory", { timeout: 15000 });
await page.waitForTimeout(600);
await page.screenshot({ path: join(OUT, "9-directory-1-toplevel.png"), fullPage: true });
console.log("captured 9-directory-1-toplevel (shows BreadTalk Group at top)");

// Zoom into the Enterprise → reveals the two companies.
await page.getByRole("button", { name: /BreadTalk Group/ }).first().click();
await page.waitForSelector("text=BreadTalk (F&B) Pte Ltd", { timeout: 10000 });
await page.waitForTimeout(400);
await page.screenshot({ path: join(OUT, "9-directory-2-enterprise-zoom.png"), fullPage: true });
console.log("captured 9-directory-2-enterprise-zoom (BreadTalk F&B + Din Tai Fung)");

// Zoom into a company → reveals its brands.
await page.getByRole("button", { name: /BreadTalk \(F&B\) Pte Ltd/ }).first().click();
await page.waitForTimeout(600);
await page.screenshot({ path: join(OUT, "9-directory-3-merchant-zoom.png"), fullPage: true });
console.log("captured 9-directory-3-merchant-zoom (brands under the company)");

await browser.close();
console.log(`\nScreenshots in ${OUT}`);
