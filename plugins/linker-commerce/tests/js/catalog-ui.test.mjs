import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {test} from 'node:test';
const require=createRequire(import.meta.url);
const {JSDOM}=require('../../../linker-tools/node_modules/jsdom');
function fixture(){
 const dom=new JSDOM(`<button type="button" id="product-filter-open" aria-controls="sidebar-filters" aria-expanded="false">Filters</button>
 <aside class="sidebar-filters" id="sidebar-filters"><button type="button" id="product-filter-close">×</button><a href="#f">facet</a><button type="button" id="product-filter-apply">Show products</button></aside>`,{runScripts:'outside-only'});
 const {window}=dom;
 window.eval(readFileSync(new URL('../../assets/catalog-ui.js',import.meta.url),'utf8'));
 return window;
}
test('the Filters button opens the drawer panel over the page',()=>{
 const win=fixture();
 win.document.getElementById('product-filter-open').click();
 assert.equal(win.document.getElementById('sidebar-filters').classList.contains('is-mobile-open'),true);
 assert.equal(win.document.body.classList.contains('tv-product-filter-open'),true);
 assert.equal(win.document.getElementById('product-filter-open').getAttribute('aria-expanded'),'true');
});
test('close, apply and Escape hide the drawer again',()=>{
 const win=fixture(); const open=win.document.getElementById('product-filter-open');
 open.click();
 win.document.getElementById('product-filter-close').click();
 assert.equal(win.document.getElementById('sidebar-filters').classList.contains('is-mobile-open'),false);
 assert.equal(win.document.getElementById('product-filter-open').getAttribute('aria-expanded'),'false');
 open.click();
 win.document.getElementById('product-filter-apply').click();
 assert.equal(win.document.body.classList.contains('tv-product-filter-open'),false);
 open.click();
 win.document.dispatchEvent(new win.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
 assert.equal(win.document.getElementById('sidebar-filters').classList.contains('is-mobile-open'),false);
});
