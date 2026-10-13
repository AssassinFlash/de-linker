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
