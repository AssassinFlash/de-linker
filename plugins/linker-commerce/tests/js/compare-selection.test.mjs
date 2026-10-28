import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {test} from 'node:test';

const require=createRequire(import.meta.url);
const {JSDOM}=require('../../../linker-tools/node_modules/jsdom');
const script=readFileSync(new URL('../../assets/compare-selection.js',import.meta.url),'utf8');
const familyScript=readFileSync(new URL('../../assets/product-family.js',import.meta.url),'utf8');
const map={101:101,201:101,102:102,202:102,103:103,203:103,104:104,204:104,105:105,205:105};

function fixture(ids,{language='en',page=null,family=false}={}){
 const label=language==='de'?'Vergleichen':'Compare';
 const rows=[{id:201,compareId:101,name:'Modell A',compareLabel:'Vergleichen: Modell A'},{id:202,compareId:102,name:'Modell B',compareLabel:'Vergleichen: Modell B'}];
 const markup=family?`<article data-linker-family-card data-compare-identities='${JSON.stringify(map)}'>
  <script type="application/json" data-linker-products>${JSON.stringify(rows)}</script>
  <button data-compare-product="101" aria-pressed="false" aria-label="Vergleichen: Modell A">${label}</button>
  <details class="card-product-picker" open><button data-linker-select-product="202">Modell B</button></details></article>`:
  `<section data-compare-identities='${JSON.stringify(map)}'>${[101,102,103,104,105].map(id=>`<button data-compare-product="${id}" aria-pressed="false">${label}</button>`).join('')}</section>`;
 const dom=new JSDOM(`${markup}<a data-compare-chip data-compare-page="/${language}/compare/" data-compare-max="4" hidden><span data-compare-count></span></a>${page===null?'':`<div id="linker-compare" data-compare-ids="${page}"></div>`}`,{url:'https://linker.test/',runScripts:'outside-only'});
 const {window}=dom;
 window.sessionStorage.setItem('linkerCompareIds',JSON.stringify(ids));
 window.eval(script);
 if(family)window.eval(familyScript);
 return window;
}
const stored=win=>JSON.parse(win.sessionStorage.getItem('linkerCompareIds'));
const control=(win,id)=>win.document.querySelector(`[data-compare-product="${id}"]`);

test('a list language change keeps the same selected physical products',()=>{
 const en=fixture([]);control(en,101).click();control(en,102).click();
 const de=fixture(stored(en),{language:'de'});
 assert.equal(control(de,101).getAttribute('aria-pressed'),'true');
 assert.equal(control(de,102).getAttribute('aria-pressed'),'true');
 control(de,101).click();
 const back=fixture(stored(de));
 assert.deepEqual(stored(back),['102']);
 assert.equal(control(back,101).getAttribute('aria-pressed'),'false');
 assert.equal(control(back,102).getAttribute('aria-pressed'),'true');
});

test('legacy locale aliases deduplicate before the four-product limit and toggle once',()=>{
 const win=fixture(['201','101','202','203','204']);
 assert.deepEqual(stored(win),['101','102','103','104']);
 assert.equal(control(win,105).disabled,true);
 assert.equal(win.document.querySelector('[data-compare-count]').textContent,'4/4');
 control(win,101).click();
 assert.deepEqual(stored(win),['102','103','104']);
 assert.equal(control(win,105).disabled,false);
});

test('an opened comparison replaces stale tab selection with normalized server identities',()=>{
 const win=fixture(['205'],{language:'de',page:'201,101,202'});
 assert.deepEqual(stored(win),['101','102']);
 assert.equal(win.document.querySelector('[data-compare-chip]').getAttribute('href'),'/de/compare/?ids=101,102');
});

test('choosing a family model immediately repaints its selection and localized accessible name',()=>{
 const win=fixture(['202'],{language:'de',family:true});
 assert.equal(control(win,101).getAttribute('aria-pressed'),'false');
 win.document.querySelector('[data-linker-select-product]').click();
 const selected=control(win,102);
 assert.equal(selected.getAttribute('aria-pressed'),'true');
 assert.equal(selected.getAttribute('aria-label'),'Vergleichen: Modell B');
 assert.equal(win.document.querySelector('details').open,false);
 selected.click();
 assert.deepEqual(stored(win),[]);
});

test('the visible mobile comparison row follows the header through scroll and resize',()=>{
 const dom=new JSDOM('<header id="lc-header"></header><button data-compare-product="101"></button><a data-compare-chip data-compare-max="4" hidden><span data-compare-count></span></a>',{url:'https://linker.test/',runScripts:'outside-only'});
 const {window}=dom;
 const frames=new Map();
 let frameId=0;
 let headerBottom=127;
 window.matchMedia=()=>({matches:true});
 window.requestAnimationFrame=callback=>{frames.set(++frameId,callback);return frameId;};
 window.cancelAnimationFrame=id=>frames.delete(id);
 const nextFrame=()=>{const [id,callback]=frames.entries().next().value;frames.delete(id);callback();};
 window.document.getElementById('lc-header').getBoundingClientRect=()=>({bottom:headerBottom});
 window.eval(script);
 const row=window.document.querySelector('[data-compare-chip]');
 const selection=control(window,101);
 selection.click();
 assert.equal(row.hidden,false);
 assert.equal(row.style.getPropertyValue('--compare-chip-top'),'127px');
 headerBottom=102;
 window.dispatchEvent(new window.Event('scroll'));
 window.dispatchEvent(new window.Event('scroll'));
 assert.equal(frames.size,1);
 nextFrame();
 assert.equal(row.style.getPropertyValue('--compare-chip-top'),'102px');
 headerBottom=81;
 window.dispatchEvent(new window.Event('scroll'));
 nextFrame();
 assert.equal(row.style.getPropertyValue('--compare-chip-top'),'81px');
 window.dispatchEvent(new window.Event('scroll'));
 assert.equal(frames.size,1);
 selection.click();
 assert.equal(row.hidden,true);
 assert.equal(frames.size,0);
 window.dispatchEvent(new window.Event('scroll'));
 assert.equal(frames.size,0);
 headerBottom=113;
 selection.click();
 assert.equal(row.style.getPropertyValue('--compare-chip-top'),'113px');
 headerBottom=127;
 window.dispatchEvent(new window.Event('resize'));
 nextFrame();
 assert.equal(row.style.getPropertyValue('--compare-chip-top'),'127px');
});
