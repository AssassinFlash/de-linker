import {createRequire} from 'node:module';
import {writeFile,mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
const repo=resolve(dirname(fileURLToPath(import.meta.url)),'../../../..');
const {chromium}=createRequire(repo+'/plugins/linker-tools/package.json')('playwright');
const out=repo+'/docs/acceptance/2026-10-12/header-live-sync';
await mkdir(out+'/after',{recursive:true});
const browser=await chromium.launch({channel:'chromium'});
const results=[];
try {
 for(const user of ['guest','customer-3']) {
  const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(user!=='guest') {
   const link=execFileSync('just',['--justfile',repo+'/justfile','login','t110','--user='+user],{encoding:'utf8'}).trim().split('\n').at(-1);
   await page.goto(link,{waitUntil:'domcontentloaded'});
  }
  for(const lang of ['en','de']) for(const width of [1440,390]) {
   const key=`${user}-${lang}-${width}`;
   await page.setViewportSize({width,height:900});
   await page.goto('http://127.0.0.1:8975/'+(lang==='de'?'de/':'')+'?cbq='+Date.now(),{waitUntil:'domcontentloaded'});
   await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.querySelectorAll('#lc-header img[src]')].map(i=>i.decode().catch(()=>{})));});
   await page.locator('#tv-header-v2').waitFor();
   await page.screenshot({path:out+'/after/'+key+'-base.png'});
   const state=await page.evaluate(()=>{
    const sels={header:'#lc-header',logo:'.tv-brand img',nav:'.tv-desktop-nav',search:'[data-tv-header-search]',cart:'.tv-desktop-actions .tv-header-cart-link',account:'.tv-b2b-acct-btn',language:'.lnk-lang-toggle--desktop',mobileLanguage:'.lnk-lang-toggle--mobile',toggle:'#tv-mobile-toggle'};
    const boxes={};for(const [key,s] of Object.entries(sels)){const e=document.querySelector(s);if(e){const r=e.getBoundingClientRect();boxes[key]={x:r.x,y:r.y,w:r.width,h:r.height};}}
    return {boxes,folded:document.querySelector('#tv-header-v2').dataset.tvNavFolded,compact:document.querySelector('#tv-header-v2').dataset.tvActionsCompact,literal:/\[linker_/.test(document.querySelector('#lc-header').innerText),accountLinks:[...document.querySelectorAll('.tv-b2b-acct-menu a')].map(a=>({text:a.innerText,url:a.getAttribute('href')}))};
   });
   if(state.literal)throw new Error(key+' literal shortcode');
   if(width===1440) {
    const account=page.locator('.tv-b2b-acct-btn');await account.focus();await account.press('Enter');
    if(!(await page.locator('.tv-b2b-acct-menu').isVisible()))throw new Error(key+' account did not open');
    await page.screenshot({path:out+'/after/'+key+'-account.png'});
    await account.press('ArrowDown');await page.keyboard.press('Escape');
    if(await page.locator('.tv-b2b-acct-menu').isVisible())throw new Error(key+' Escape did not close account');
   }
   if(await page.locator('#tv-mobile-toggle').isVisible()) {
    await page.locator('#tv-mobile-toggle').click();
    if(!(await page.locator('#tv-mobile-panel').isVisible()))throw new Error(key+' drawer not open');
    await page.screenshot({path:out+'/after/'+key+'-drawer.png'});
    for(const name of ['products','solutions','ai','partners','about']){
     const summary=page.locator(`[data-tv-mobile-primary="${name}"] summary`);await summary.click();
     await page.screenshot({path:out+'/after/'+key+'-drawer-'+name+'.png'});
     await summary.click();
    }
    const portal=page.locator('.tv-mobile-utility-row .tv-b2b-mobile-portal-link');
    if(!(await portal.isVisible()))throw new Error(key+' mobile account absent');
    await page.keyboard.press('Escape');
   } else {
    for(const name of ['products','solutions','ai','partners','about']){
     const button=page.locator(`[data-tv-nav-primary="${name}"] .tv-nav-link`);await button.focus();await button.press('Enter');
     await page.locator(`[data-tv-nav-primary="${name}"] img`).evaluateAll(async imgs=>{await Promise.all(imgs.map(i=>i.decode().catch(()=>{})));});
     await page.screenshot({path:out+'/after/'+key+'-mega-'+name+'.png'});
     await page.keyboard.press('Escape');
    }
   }
   await page.evaluate(()=>scrollTo(0,650));
   await page.screenshot({path:out+'/after/'+key+'-sticky.png'});
   const top=await page.locator('#lc-header').evaluate(e=>e.getBoundingClientRect().top);
   if(top!==0)throw new Error(key+' sticky top='+top);
   results.push({key,...state,errors:[...errors],functional:'PASS'});console.log(key+' PASS');
  }
  await context.close();
 }
 await writeFile(out+'/measurement.json',JSON.stringify({browser:'isolated Chromium 1248; functional evidence only; official Computer Use gate pending',results},null,2));
}finally{await browser.close();}
