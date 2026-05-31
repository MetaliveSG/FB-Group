const { chromium } = require("/tmp/pw/node_modules/playwright");
const API = "http://localhost:8000/api/v1";
const WEB = "http://localhost:3001";
const ROLES = [
  ["Owner", "superadmin@platform.sg"],
  ["Admin", "admin@platform.sg"],
  ["Onboarding", "onboard@platform.sg"],
  ["Support", "support@platform.sg"],
];

async function token(email) {
  const r = await fetch(`${API}/auth/staff/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: "Password123!" }),
  });
  const j = await r.json();
  if (!j.access_token) throw new Error(`login failed for ${email}: ${JSON.stringify(j)}`);
  return j.access_token;
}

(async () => {
  const b = await chromium.launch();
  for (const [label, email] of ROLES) {
    const tok = await token(email);
    const ctx = await b.newContext({ viewport: { width: 1280, height: 1600 } });
    await ctx.addInitScript((t) => localStorage.setItem("fbgroup_staff_token", t), tok);
    const p = await ctx.newPage();
    await p.goto(`${WEB}/operator`, { waitUntil: "networkidle" });
    await p.waitForTimeout(1800);
    const count = (sel) => p.locator(sel).count();
    const signals = {
      label,
      url: p.url().replace(WEB, ""),
      onboardBtn: await count('button:has-text("Onboard Merchant")'),
      editPencils: await count('button[aria-label="Edit merchant"]'),
      enterBtns: await count('button:has-text("Enter")'),
      suspendOrCoalitionToggles: await count('[role="switch"]'),
      operatorsSection: await count('h2:has-text("Operators")'),
      addOperatorBtn: await count('button:has-text("Add Operator")'),
      newCoalitionBtn: await count('button:has-text("New Coalition")'),
      renameCoalitionPencils: await count('button[aria-label="Rename coalition"]'),
    };
    console.log(JSON.stringify(signals));
    await p.screenshot({ path: `/tmp/pw/operator-${label}.png`, fullPage: true });
    await ctx.close();
  }
  await b.close();
})().catch((e) => {
  console.error("DRIVER ERROR:", e.message);
  process.exit(1);
});
