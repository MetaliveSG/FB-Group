#!/usr/bin/env node
// i18n catalog hygiene — run in CI (informational; FAILS only on orphan keys).
//   1. ORPHANS (fail): a t("key") used in apps/web with no entry in en.json (the master).
//   2. COVERAGE (report): % of en keys each other locale translates (missing → falls back to en).
// Keeps i18n from rotting: you always KNOW zh is 60% done instead of guessing.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const LOCALES_DIR = join(HERE, "..", "src", "locales");
const WEB_SRC = join(HERE, "..", "..", "..", "apps", "web", "src");

const load = (f) => {
  const o = JSON.parse(readFileSync(join(LOCALES_DIR, f), "utf8"));
  delete o._comment;
  return o;
};
const en = load("en.json");
const enKeys = new Set(Object.keys(en));

// Collect t("…")/t('…') keys used across the web app.
const used = new Set();
const T_CALL = /\bt\(\s*["'`]([\w.]+)["'`]/g;
function walk(dir) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".next") continue;
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p);
    else if (/\.(tsx?|jsx?)$/.test(name)) {
      const src = readFileSync(p, "utf8");
      let m;
      while ((m = T_CALL.exec(src))) used.add(m[1]);
    }
  }
}
try { walk(WEB_SRC); } catch { /* web not present — skip orphan scan */ }

// Orphans: used in code, allow `_plural` siblings of a real key.
const orphans = [...used].filter((k) => !enKeys.has(k) && !enKeys.has(k.replace(/_plural$/, "")));

// Coverage per locale.
const locales = readdirSync(LOCALES_DIR).filter((f) => f.endsWith(".json") && f !== "en.json");
console.log(`i18n catalogs — ${enKeys.size} keys in en (master)\n`);
for (const f of locales.sort()) {
  const cat = load(f);
  const have = Object.keys(cat).filter((k) => enKeys.has(k)).length;
  const pct = enKeys.size ? Math.round((have / enKeys.size) * 100) : 0;
  const extra = Object.keys(cat).filter((k) => !enKeys.has(k));
  const bar = "█".repeat(Math.round(pct / 5)).padEnd(20, "░");
  console.log(`  ${f.replace(".json", "").padEnd(8)} ${bar} ${pct}%  (${have}/${enKeys.size})${extra.length ? `  ⚠ ${extra.length} key(s) not in en` : ""}`);
}

if (orphans.length) {
  console.error(`\n✗ ${orphans.length} orphan key(s) — used in code but missing from en.json:`);
  for (const k of orphans.sort()) console.error(`    ${k}`);
  console.error("  Add them to packages/i18n/src/locales/en.json.");
  process.exit(1);
}
console.log("\n✓ no orphan keys");
