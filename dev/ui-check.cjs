const {chromium}=require('playwright');
const out=process.argv[2], tag=process.argv[3]||'x', fake=process.argv[4];
(async()=>{const b=await chromium.launch();const c=await b.newContext({viewport:{width:1180,height:820}});const p=await c.newPage();
if(fake) await p.clock.install({time:new Date(fake)});
const errs=[];p.on('pageerror',e=>errs.push('PAGEERR '+e.message));
p.on('console',m=>{if(m.type()==='error'&&!/ERR_TUNNEL|fonts|net::|Failed to load resource|open-meteo/.test(m.text()))errs.push('CONSOLE '+m.text().slice(0,200))});
await p.goto('http://localhost:3999/');await p.waitForTimeout(1500);
const lf=p.frameLocator('#loginfr');
await p.screenshot({path:`${out}/${tag}_login.png`});
await lf.locator('.bx[data-k=o]').click();await p.waitForTimeout(300);
await lf.locator('.bx.on .pin').fill('000000');await lf.locator('.bx.on .go').click();await p.waitForTimeout(800);
console.log('wrong pin msg:',await lf.locator('.bx.on .err').textContent());
await p.screenshot({path:`${out}/${tag}_pin.png`});
await lf.locator('.bx.on .pin').fill('123456');await lf.locator('.bx.on .go').click();
await p.waitForTimeout(4000);
console.log('login hidden:',await p.evaluate(()=>document.getElementById('loginfr').classList.contains('hide')));
for(const k of ['home','book','cust','hk','fin','rep','mkt','crmm','linechat']){await p.evaluate(k=>show(k),k);await p.waitForTimeout(1300);await p.screenshot({path:`${out}/${tag}_${k}.png`});}
for(const s of ['crm:crm','crmtool:main']){await p.evaluate(s=>goSub('crmm',s),s);await p.waitForTimeout(1200)}
console.log('errors',errs.length);errs.slice(0,15).forEach(e=>console.log(' ',e));
await b.close();})();
