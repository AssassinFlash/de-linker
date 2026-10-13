// Run from the lane root: node docs/acceptance/2026-10-13/pdp-faq-mobile/measure.mjs
// Only t109. No content/product writes; login uses the existing one-time-link tool.
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import assert from 'node:assert/strict';
const out=dirname(fileURLToPath(import.meta.url));
const root=resolve(out,'../../../..');
const require=createRequire(resolve(root,'tests/e2e/package.json'));
const {chromium}=require('playwright');
const browser=await chromium.launch({headless:true});
const base='http://127.0.0.1:8969';
const pages=[['pdp-en','/product/goodwe-gw60k-sts-g10/'],['faq-en','/faq-download/'],['faq-de','/de/faq-download/']];
const results=[]; const checks=[];
async function settle(page){await page.evaluate(async()=>{await Promise.race([Promise.all([document.fonts.ready,...Array.from(document.images).map(i=>i.decode().catch(()=>{}))]),new Promise(resolve=>setTimeout(resolve,3000))]);});}
async function metrics(page,name,width){return page.evaluate(({name,width})=>{
 const box=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
 const root=document.querySelector(name.startsWith('pdp')?'#tv-storefront-pdp':'#linker-faq-page');
 const controls=Array.from(root.querySelectorAll('a,button,summary,input')).filter(e=>e.checkVisibility());
 const relevant=controls.filter(e=>e.matches('.pdp-thumb,.pdp-section-link,.pdp-mobile-action a,.pdp-tool,.pdp-project-choice,.linker-faq-contact a,.linker-faq-contact button,.linker-faq-zone,summary,input,.linker-document-download a'));
 return {name,width,overflow:document.documentElement.scrollWidth>innerWidth,pageHeight:document.documentElement.scrollHeight,gallery:box('.pdp-gallery-main-wrap'),sticky:box('.pdp-mobile-action'),pills:box('.pdp-section-nav'),search:box('.linker-faq-search-field'),firstQuestion:box('.linker-trade-question summary'),margin:box('.sf-container')?.x??box('.linker-faq-help')?.x,targets:relevant.map(e=>({text:(e.textContent||e.getAttribute('aria-label')||'input').trim().slice(0,75),h:e.getBoundingClientRect().height,w:e.getBoundingClientRect().width})),answers:root.querySelectorAll('.linker-answer').length,trade:root.querySelectorAll('.linker-trade-question').length,documents:root.querySelectorAll('.linker-document').length,open:root.querySelectorAll('details[open]').length};
 },{name,width});}
try{
 for(const [name,path] of pages){
  for(const [width,height] of [[390,844],[430,932],[1440,1000]]){
   const context=await browser.newContext({viewport:{width,height}});const page=await context.newPage();
   const response=await page.goto(base+path+'?cbq=pdpfaq-measure-'+Date.now());assert.equal(response.status(),200);await settle(page);
   const m=await metrics(page,name,width);results.push(m);assert.equal(m.overflow,false,`${name} ${width} overflow`);
   await page.screenshot({path:resolve(out,`${name}-ours-${width}.png`)});
   await page.screenshot({path:resolve(out,`${name}-ours-${width}-full.png`),fullPage:true});
   if(width===390){mkdirSync(resolve(out,name+'-ours-390'),{recursive:true});let n=0;for(let y=0;y<m.pageHeight;y+=height-124){await page.evaluate(y=>scrollTo(0,y),y);await page.screenshot({path:resolve(out,name+'-ours-390',String(++n).padStart(2,'0')+'.png')});}await page.evaluate(()=>scrollTo(0,0));}
   if(name.startsWith('faq')&&width===390){
    assert.equal(m.open,0,'default collapsed');if(name==='faq-en'){assert.equal(m.answers,272);assert.equal(m.documents,159);}assert.equal(m.trade,16);
    const query=page.locator('#linker-faq-query');await query.fill('zzzz-no-such-term');assert.equal(await page.locator('.linker-answer:not([hidden]),.linker-trade-question:not([hidden])').count(),0);
    await query.fill('GoodWe');if(m.answers>0)assert.ok(await page.locator('.linker-answer:not([hidden])').count()>0);await page.screenshot({path:resolve(out,name+'-search-ours-390.png')});
    await query.fill('');assert.equal(await page.locator('.linker-answer:not([hidden])').count(),m.answers);
    await page.locator('.linker-trade-question summary').first().focus();await page.keyboard.press('Enter');assert.equal(await page.locator('.linker-trade-question[open]').count(),1);await page.screenshot({path:resolve(out,name+'-expanded-ours-390.png')});
    checks.push(`${name}: ${m.answers} product answers / 16 trade questions / ${m.documents} documents; default 0 open; search match/empty/reset + keyboard Enter PASS`);
   }
   await context.close();console.log(name+' '+width+' measured');
  }
  if(name.startsWith('faq')){const expected=results.find(x=>x.name===name);const c=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});const page=await c.newPage();await page.goto(base+path+'?cbq=nojs-'+Date.now());assert.equal(await page.locator('.linker-answer').count(),expected.answers);assert.equal(await page.locator('.linker-trade-question').count(),16);assert.equal(await page.locator('.linker-document').count(),expected.documents);assert.equal(await page.locator('[data-faq-search]').isVisible(),false);await page.locator('.linker-trade-question summary').first().click();assert.equal(await page.locator('.linker-trade-question[open]').count(),1);checks.push(`${name} no JS: same ${expected.answers}/16/${expected.documents}; search hidden; native accordion PASS`);await c.close();}
 }
 for(const status of ['pending','restricted','approved']){
  const url=execFileSync('just',['login','t109','--user=pdp-faq-'+status],{cwd:root,encoding:'utf8'}).trim().split('\n').pop();
  const c=await browser.newContext({viewport:{width:390,height:844}});const page=await c.newPage();await page.goto(url);await page.goto(base+'/product/saj-h2-10k-t3/?cbq=state-'+Date.now());await settle(page);
  const text=await page.locator('.pdp-mobile-action').innerText();
  if(status!=='approved')assert.equal(/€|EUR/.test(text),false);else if(!/€|EUR/.test(text))checks.push('GAP: approved PDP amount is intercepted by the active snapshot plugin price hook (tv_b2b_filter_price_html); Woo edit price is present.');
  if(status==='pending')assert.match(text,/Prices after approval/);if(status==='restricted')assert.match(text,/Not available for your account/);if(status==='approved')assert.match(text,/Add to solution draft/);
  await page.screenshot({path:resolve(out,'pdp-'+status+'-ours-390.png')});checks.push(`PDP ${status}: ${text.replace(/\n/g,' | ')} UI-state PASS (amount/add operation separate)`);
  if(status==='approved'){await page.locator('.pdp-mobile-action .pdp-btn-dark').click();const items=await page.locator('.cart_item').count();checks.push('PDP approved action: existing Woo add-to-cart -> draft items '+items+(items?' PASS':' GAP: snapshot price/cart gate conflicts with new approval state'));}
  await c.close();
 }
 // The data migration left German products as drafts; report their public response, never publish them here.
 const c=await browser.newContext();const p=await c.newPage();const de=await p.goto(base+'/de/produkt/goodwe-gw60k-sts-g10/?cbq=de-'+Date.now());checks.push(`DE PDP public response: ${de.status()} (instance product twin is draft; not edited)`);await c.close();
 writeFileSync(resolve(out,'metrics.json'),JSON.stringify({results,checks},null,2)+'\n');
 const table=['# 实测数值（t109）','','来自 `measure.mjs` 的浏览器 DOM 几何；单位 CSS px。390×844、430×932、1440×1000。','','| 面 | 宽 | 头图高 | sticky高 | pill高 | 问题行高 | 侧边距 | 溢出 |','|---|---:|---:|---:|---:|---:|---:|---|'];
 for(const m of results)table.push(`| ${m.name} | ${m.width} | ${m.gallery?.h??'—'} | ${m.sticky?.h??'—'} | ${m.pills?.h??'—'} | ${m.firstQuestion?.h??'—'} | ${m.margin} | ${m.overflow} |`);
 table.push('','## 触控目标（390）');for(const m of results.filter(x=>x.width===390)){const small=m.targets.filter(x=>x.h<44||x.w<44);table.push(`- ${m.name}: ${m.targets.length} 个目标；小于44px：${small.length}。`);for(const x of small)table.push(`  - ${x.text}: ${x.w} × ${x.h}`);}
 table.push('','## 实际行为',...checks.map(x=>'- '+x),'','## sticky 遮挡','移动条本身有意固定覆盖视口底部；每屏拍摄步长为视口高−124，保留上下屏重叠。PDP 底部 padding=实际行动条高度+52px，body scroll-padding-bottom=实际高度+36px（当前88px分别得140/124），为最后内容留出空间。需要展开 Genie 的浮层按其既有覆盖行为处理；PDP 仅上移现有关闭态坞，不改其实现。');
 writeFileSync(resolve(out,'metrics.md'),table.join('\n')+'\n');console.log(table.join('\n'));
}finally{await browser.close();}
