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
 assert.equal(win.document.body.classList.contains('product-filter-open'),true);
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
 assert.equal(win.document.body.classList.contains('product-filter-open'),false);
 open.click();
 win.document.dispatchEvent(new win.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
 assert.equal(win.document.getElementById('sidebar-filters').classList.contains('is-mobile-open'),false);
});

test('the first tap on Filters works while the catalog page is still arriving', () => {
 const dom = new JSDOM('', { runScripts: 'outside-only' });
 const {window} = dom;
 const {document} = window;
 window.eval(readFileSync(new URL('../../assets/catalog-ui.js', import.meta.url), 'utf8'));
 document.body.innerHTML = '<button id="product-filter-open" aria-expanded="false"><span>Filters</span></button>';
 const label = document.querySelector('#product-filter-open span');
 label.click();
 assert.equal(document.body.classList.contains('product-filter-open'), false);
 document.body.insertAdjacentHTML('beforeend', '<aside id="sidebar-filters"></aside>');
 label.click();
 assert.equal(document.getElementById('product-filter-open').getAttribute('aria-expanded'), 'false');
 document.querySelector('aside').innerHTML = '<button id="product-filter-close">Close</button><button id="product-filter-apply">Show products</button>';
 label.click();
 assert.equal(document.getElementById('product-filter-open').getAttribute('aria-expanded'), 'true');
 assert.equal(document.getElementById('sidebar-filters').classList.contains('is-mobile-open'), true);
 assert.equal(document.activeElement.id, 'product-filter-close');
 document.dispatchEvent(new window.KeyboardEvent('keydown', {key: 'Escape'}));
 assert.equal(document.activeElement.id, 'product-filter-open');
 dom.window.close();
});

test('typing a model replaces the catalogue with the matching archive, including its empty state', async () => {
 const dom = new JSDOM('<form class="wb-search" action="/de/produkte/"><input id="search-box" name="q"><input type="hidden" name="brand" value="goodwe"><span role="status"></span></form><aside id="sidebar-filters">Old facets</aside><div data-catalog-listing>Old cards</div>', {url:'https://linker.test/de/produkte/', runScripts:'outside-only'});
 const {window}=dom;
 let requested;
 window.fetch=async (url, options)=>{
  requested=new URL(url);
  assert.equal(options.credentials,'same-origin');
  return {ok:true,text:async()=>'<aside id="sidebar-filters">0</aside><div data-catalog-listing><p role="status">Keine Produkte gefunden</p><a href="/de/produkte/">Alle Produkte</a></div>'};
 };
 window.eval(readFileSync(new URL('../../assets/catalog-ui.js',import.meta.url),'utf8'));
 const input=window.document.querySelector('input');
 input.value='ZZ9117';
 input.dispatchEvent(new window.Event('input',{bubbles:true}));
 await new Promise(resolve=>setTimeout(resolve,400));
 assert.equal(requested?.searchParams.get('q'),'ZZ9117');
 assert.equal(window.location.search,'');
 assert.equal(requested.searchParams.get('brand'),'goodwe');
 assert.equal(window.document.querySelector('[data-catalog-listing] a').pathname,'/de/produkte/');
 assert.equal(window.document.querySelector('[data-catalog-listing]').textContent.includes('Old cards'),false);
 assert.equal(window.document.querySelector('#sidebar-filters').textContent,'0');
 dom.window.close();
});

test('a pending catalogue search keeps an open filter drawer focused and usable', async () => {
 const window=fixture();
 const doc=window.document;
 doc.body.insertAdjacentHTML('beforeend','<form action="https://linker.test/products/"><input id="search-box" name="q"></form><div data-catalog-listing></div>');
 let resolveResponse, requestStarted;
 const started=new Promise(resolve=>{ requestStarted=resolve; });
 window.fetch=()=>new Promise(resolve=>{ resolveResponse=resolve; requestStarted(); });
 const input=doc.querySelector('#search-box');
 input.value='SAJ';
 input.dispatchEvent(new window.Event('input',{bubbles:true}));
 await started;
 doc.querySelector('#product-filter-open').click();
 const html='<aside id="sidebar-filters"><button id="product-filter-close">Close</button><button id="product-filter-apply">Show products</button></aside><div data-catalog-listing>SAJ</div>';
 resolveResponse({ok:true,text:async()=>html});
 await new Promise(resolve=>setTimeout(resolve,0));
 assert.equal(doc.querySelector('[data-catalog-listing]').textContent,'SAJ');
 assert.equal(doc.querySelector('#sidebar-filters').classList.contains('is-mobile-open'),true);
 assert.equal(doc.activeElement.id,'product-filter-close');
 doc.querySelector('#product-filter-apply').click();
 assert.equal(doc.body.classList.contains('product-filter-open'),false);
 assert.equal(doc.activeElement.id,'product-filter-open');
 window.close();
});
