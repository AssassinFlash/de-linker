import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {test} from 'node:test';
const require=createRequire(import.meta.url);
const {JSDOM}=require('../../../linker-tools/node_modules/jsdom');
function fixture(){
 const dom=new JSDOM(`<div id="tv-storefront-pdp"><button data-pdp-image data-pdp-main data-src="a"><img class="pdp-gallery-main" src="a"></button><button data-pdp-thumb data-src="a" aria-pressed="true"></button><button data-pdp-thumb data-src="b" aria-pressed="false"></button><dialog id="pdp-image-viewer"><img><button data-pdp-close-image></button></dialog></div>`,{runScripts:'outside-only'});
 const {window}=dom;window.matchMedia=()=>({matches:true});
 const viewer=window.document.querySelector('dialog');viewer.showModal=()=>{viewer.open=true;};
 window.eval(readFileSync(new URL('../../assets/pdp-ui.js',import.meta.url),'utf8'));
 return {window,main:window.document.querySelector('[data-pdp-main]'),thumbs:window.document.querySelectorAll('[data-pdp-thumb]'),viewer};
}
test('thumbnail and keyboard keep main image and viewer in sync',()=>{
 const {window,main,thumbs,viewer}=fixture();thumbs[1].click();
 assert.equal(main.dataset.src,'b'); assert.equal(thumbs[1].getAttribute('aria-pressed'),'true');
 main.click();assert.equal(viewer.querySelector('img').getAttribute('src'),'b');
 main.dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));
 assert.equal(main.dataset.src,'a');
});
test('horizontal swipe selects without opening viewer, vertical scroll does not select',()=>{
 const {window,main,viewer}=fixture();
 function touch(type,x,y){const e=new window.Event(type,{bubbles:true});Object.defineProperty(e,type==='touchstart'?'touches':'changedTouches',{value:[{clientX:x,clientY:y}]});main.dispatchEvent(e);}
 touch('touchstart',250,100);touch('touchend',100,110);main.click();
 assert.equal(main.dataset.src,'b');assert.equal(viewer.open,false);
 touch('touchstart',200,100);touch('touchend',180,250);
 assert.equal(main.dataset.src,'b');
});

test('swipe without a synthetic click does not swallow a later activation',()=>{
 const {window,main,viewer}=fixture(); let now=1000;window.Date.now=()=>now;
 function touch(type,x){const e=new window.Event(type,{bubbles:true});Object.defineProperty(e,type==='touchstart'?'touches':'changedTouches',{value:[{clientX:x,clientY:100}]});main.dispatchEvent(e);}
 touch('touchstart',250);touch('touchend',100);now+=400;main.click();
 assert.equal(viewer.open,true);
});

test('the viewer closes on a backdrop click and hands focus back to the picture',()=>{
 const loaded=new JSDOM(`<div id="tv-storefront-pdp"><button data-pdp-image data-pdp-main data-src="a"><img class="pdp-gallery-main" src="a"></button><dialog id="pdp-image-viewer"><img><button data-pdp-close-image></button></dialog></div>`,{runScripts:'outside-only'});
 const {window}=loaded;window.matchMedia=()=>({matches:true});
 const viewer=window.document.querySelector('dialog');
 let closed=0;
 viewer.showModal=()=>{viewer.open=true;};
 viewer.close=()=>{viewer.open=false;closed+=1;};
 window.eval(readFileSync(new URL('../../assets/pdp-ui.js',import.meta.url),'utf8'));
 const trigger=window.document.querySelector('[data-pdp-main]');
 trigger.focus=()=>{trigger.dataset.focused='1';};
 trigger.click();
 assert.equal(viewer.open,true);
 viewer.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));
 assert.equal(viewer.open,false);
 assert.equal(closed,1);
 viewer.dispatchEvent(new window.Event('close'));
 assert.equal(trigger.dataset.focused,'1');
});

test('the section nav marks the section in view and measures the chrome',()=>{
 const dom=new JSDOM(`<header id="lc-header"></header><div id="tv-storefront-pdp"><nav class="pdp-section-nav"><div class="sf-container"><a class="pdp-section-link" href="#description"></a><a class="pdp-section-link" href="#stats"></a></div></nav><section id="description"></section><section id="stats"></section></div>`,{runScripts:'outside-only'});
 const {window}=dom;window.matchMedia=()=>({matches:false});
 const doc=window.document;
 // jsdom lays nothing out: the heights the page reports are the test's own.
 Object.defineProperty(doc.querySelector('#lc-header'),'offsetHeight',{value:96});
 Object.defineProperty(doc.querySelector('.pdp-section-nav'),'offsetHeight',{value:54});
 ['#description','#stats'].forEach((id)=>{
  Object.defineProperty(doc.querySelector(id),'getBoundingClientRect',{value:()=>({top:id==='#stats'?-30:600})});
 });
 window.eval(readFileSync(new URL('../../assets/pdp-ui.js',import.meta.url),'utf8'));
 const style=doc.documentElement.style;
 assert.equal(style.getPropertyValue('--lk-header-h'),'96px');
 assert.equal(style.getPropertyValue('--pdp-snav-h'),'54px');
 const links=doc.querySelectorAll('.pdp-section-link');
 assert.equal(links[0].getAttribute('aria-current'),'false');
 assert.equal(links[1].getAttribute('aria-current'),'true');
});

test('the project choices ask Genie and the retired nameplate entry is gone',()=>{
 const dom=new JSDOM(`<div id="tv-storefront-pdp"><button data-project-message="New system with X">New system</button><button data-linker-assistant-open="nameplate">Identify a device from a nameplate photo</button></div>`,{runScripts:'outside-only'});
 const {window}=dom;window.matchMedia=()=>({matches:false});
 const seen=[];
 ['linker-genie-ask','lia:open'].forEach((name)=>window.addEventListener(name,(event)=>seen.push([name,event.detail.message||event.detail.view])));
 window.eval(readFileSync(new URL('../../assets/pdp-ui.js',import.meta.url),'utf8'));
 window.document.querySelector('[data-project-message]').click();
 // The nameplate chip had no listener left anywhere (owner 2026-10-13: not
 // delivered); a button that still carried the attribute must stay inert.
 window.document.querySelector('[data-linker-assistant-open]').click();
 assert.deepEqual(seen,[['linker-genie-ask','New system with X']]);
 const source=readFileSync(new URL('../../assets/pdp-ui.js',import.meta.url),'utf8');
 assert.doesNotMatch(source,/lia:open|data-linker-assistant-open/);
});
