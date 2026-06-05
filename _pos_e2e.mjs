import { chromium } from "playwright";
const API="http://localhost:8000/api/v1", WEB="http://localhost:3001";
const PEPPER="9a05bb10711a47bbb1712302b23a33a5", TOK="pepper-lunch-tpy-0ab5b283", PIN="2580";
const SH="artifacts/pos-proof/screens";
const api=async(m,p,b,t)=>{const r=await fetch(API+p,{method:m,headers:{"Content-Type":"application/json",...(t?{Authorization:"Bearer "+t}:{})},body:b?JSON.stringify(b):undefined});return [r.status,await r.json().catch(()=>null)];};
const log=(...a)=>process.stdout.write(a.join(" ")+"\n");
// setup: owner sets own PIN + receipt header
const [,lg]=await api("POST","/auth/staff/login",{email:"owner@pepperlunch.sg",password:"Password123!"});
const t=lg.access_token, uid=lg.user.id;
log("set PIN:", (await api("POST",`/org/nodes/${PEPPER}/accounts/${uid}/pin`,{pin:PIN},t))[0]);
await api("PATCH","/org/settings",{receipt:{company_name:"Pepper Lunch Pte Ltd",uen:"201900111A",address:"1 Orchard Rd",phone:"61112222",footer:"Thank you, see you again!"}},t);
// browser POS
const b=await chromium.launch(); const pg=await b.newPage({viewport:{width:1280,height:800}});
const errs=[]; pg.on("pageerror",e=>errs.push(e.message.split("\n")[0]));
try {
  await pg.goto(`${WEB}/pos`,{waitUntil:"networkidle"});
  await pg.evaluate(()=>localStorage.clear());
  await pg.reload({waitUntil:"networkidle"}); await pg.waitForTimeout(400);
  await pg.locator("input").first().fill(TOK);
  await pg.locator("button:has-text('Connect outlet')").click(); await pg.waitForTimeout(1500);
  log("lock screen:", /Enter PIN/i.test(await pg.locator("body").innerText()));
  for (const d of PIN.split("")) await pg.locator(`button:text-is("${d}")`).first().click();
  await pg.locator("button:has-text('OK')").click(); await pg.waitForTimeout(1500);
  const items = pg.locator("[data-testid=pos-item]");
  log("menu items:", await items.count());
  await items.nth(0).click(); await items.nth(0).click(); // 2× first item
  if (await items.count()>1) await items.nth(1).click();
  await pg.screenshot({path:`${SH}/01_order.png`});
  await pg.locator("[data-testid=pos-charge]").click(); await pg.waitForTimeout(300);
  await pg.locator("[data-testid=pos-pay-cash]").click(); await pg.waitForTimeout(2500);
  const body=await pg.locator("body").innerText();
  log("receipt shown:", /TOTAL/i.test(body), "| company:", /Pepper Lunch Pte Ltd/i.test(body), "| paid CASH:", /Paid: CASH/i.test(body), "| footer:", /see you again/i.test(body));
  await pg.screenshot({path:`${SH}/02_receipt.png`});
  log("page errors:", errs.length?errs.join("|"):"(none)");
} catch(e){ log("ERROR:", e.message.split("\n")[0]); }
await b.close();
