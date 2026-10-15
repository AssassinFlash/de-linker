import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
const require = createRequire(import.meta.url);
const {JSDOM} = require('../../../linker-tools/node_modules/jsdom');
const library = require('../../assets/library-ui.js');
const source = readFileSync(new URL('../../assets/library-ui.js', import.meta.url), 'utf8');

test('search matches fold case and accents, and require every word', () => {
 assert.equal(library.matches('GoodWe inverter 10 kW', 'GOODWE 10'), true);
 assert.equal(library.matches('Lösungsentwurf hinzufügen', 'losungsentwurf'), true);
 assert.equal(library.matches('Gleichstrom-Anschluss', 'gleichstrom anschluss'), true);
 assert.equal(library.matches('GoodWe inverter', 'GoodWe battery'), false);
 assert.equal(library.matches('Anything', '   '), true);
});

test('ranking prefers a title match over a body match', () => {
 const title = library.score('Chint DTSU666 datasheet', 'meter, EN', 'dtsu666');
 const body = library.score('Chint manual', 'the DTSU666 meter', 'dtsu666');
 assert.ok(title > body, `${title} should beat ${body}`);
 assert.equal(library.score('Anything', 'body', ''), 0);
});

test('highlight ranges cover every term once and merge overlaps', () => {
 assert.deepEqual(library.highlightRanges('Chint DTSU666 catalog', 'dtsu'), [[6, 10]]);
 assert.deepEqual(library.highlightRanges('GoodWe GoodWe', 'goodwe'), [[0, 6], [7, 13]]);
 assert.deepEqual(library.highlightRanges('Lösungsentwurf', 'losung'), [[0, 6]]);
 assert.deepEqual(library.highlightRanges('nothing here', 'zzz'), []);
 assert.deepEqual(library.highlightRanges('anything', '  '), []);
});

test('pagination windows the first page, the last and the current one', () => {
 assert.deepEqual(library.pageWindow(1, 1), [1]);
 assert.deepEqual(library.pageWindow(1, 3), [1, 2, 3]);
 assert.deepEqual(library.pageWindow(5, 12), [1, 4, 5, 6, 12]);
 assert.deepEqual(library.pageWindow(12, 12), [1, 11, 12]);
});

test('a page slice clamps out-of-range pages and keeps 20 rows a page', () => {
 const rows = Array.from({length: 45}, (_, i) => i + 1);
 assert.deepEqual(library.paginate(rows, 1, 20).items.length, 20);
 assert.equal(library.paginate(rows, 1, 20).pages, 3);
 assert.deepEqual(library.paginate(rows, 3, 20).items, [41, 42, 43, 44, 45]);
 assert.equal(library.paginate(rows, 99, 20).page, 3);
 assert.equal(library.paginate(rows, 0, 20).page, 1);
 assert.equal(library.PAGE_SIZE, 20);
});

test('the tab round-trips through the URL, documents named and faq the default', () => {
 assert.equal(library.tabFromSearch(''), 'faq');
 assert.equal(library.tabFromSearch('?tab=faq'), 'faq');
 assert.equal(library.tabFromSearch('?tab=documents'), 'documents');
 assert.equal(library.tabFromSearch('?lang=de&tab=documents&page=2'), 'documents');
 assert.equal(library.tabFromSearch('?tabs=documents'), 'faq');
 assert.equal(library.tabUrl('/faq-download/', '', '', 'documents'), '/faq-download/?tab=documents');
 assert.equal(library.tabUrl('/faq-download/', '?tab=documents', '', 'faq'), '/faq-download/');
 assert.equal(library.tabUrl('/faq-download/', '?kind=2', '#x', 'faq'), '/faq-download/?kind=2#x');
 assert.equal(library.tabUrl('/de/faq-download/', '?tab=documents', '#linker-library-zone-documents', 'documents'), '/de/faq-download/?tab=documents#linker-library-zone-documents');
});

test('a spy target names its zone', () => {
 assert.equal(library.zoneOf('linker-library-zone-trade'), 'linker-library-zone-trade');
 assert.equal(library.zoneOf('linker-library-trade-2'), 'linker-library-zone-trade');
 assert.equal(library.zoneOf('linker-library-answers-goodwe'), 'linker-library-zone-answers');
 assert.equal(library.zoneOf('linker-library-docs-goodwe'), 'linker-library-zone-documents');
 assert.equal(library.zoneOf(''), '');
});

/** The page's own markup, as the template and the fragments print it. */
function page(rows) {
 return `<!doctype html><html><body>
 <div id="linker-faq-page" class="linker-library">
  <div class="linker-library-searchbox"><div class="linker-library-search" hidden>
   <input class="linker-library-q" type="search" role="combobox" aria-expanded="false" aria-controls="linker-library-suggest">
   <button type="button" class="linker-library-clear" data-library-clear hidden>×</button>
   <span class="linker-library-count" id="linker-library-result-count">432 on file</span>
  </div><div id="linker-library-suggest" role="listbox" hidden></div></div>
  <div class="linker-library-tabbar"><div class="linker-library-tablist" role="tablist">
   <a id="linker-library-tab-faq" role="tab" href="#linker-library-panel-faq" data-library-tab="faq" aria-selected="true">FAQ <span class="linker-library-n">16</span></a>
   <a id="linker-library-tab-documents" role="tab" href="#linker-library-panel-documents" data-library-tab="documents" aria-selected="false">Documents <span class="linker-library-n">25</span></a>
  </div></div>
  <div class="linker-library-layout">
   <aside class="linker-library-rail"><div class="linker-library-rail-group" data-library-nav="faq"><nav class="linker-library-toc">
    <a href="#linker-library-trade-0" data-library-spy-link>Ordering <span class="linker-library-n">2</span></a>
    <a href="#linker-library-answers-chint" data-library-spy-link>Chint <span class="linker-library-n">1</span></a>
   </nav></div><div class="linker-library-rail-group" data-library-nav="documents"><nav class="linker-library-toc">
    <a href="#linker-library-docs-chint" data-library-spy-link>Chint <span class="linker-library-n">3</span></a>
   </nav></div></aside>
   <div class="linker-library-main">
    <nav class="linker-library-chips"><div class="linker-library-chips-scroll" data-library-nav="faq"><a class="linker-library-chip" href="#linker-library-zone-trade" data-library-spy-link data-library-zone="linker-library-zone-trade">Before you order</a></div><div class="linker-library-chips-scroll" data-library-nav="documents"><a class="linker-library-chip" href="#linker-library-docs-chint" data-library-spy-link>Chint <span class="linker-library-n">3</span></a></div></nav>
    <div class="linker-library-panel" id="linker-library-panel-faq" data-library-panel="faq">
     <section class="linker-library-zone" id="linker-library-zone-trade" data-library-spy>
      <h2 class="linker-library-zone-title">Before you order</h2><div class="linker-library-stack">
      <article class="linker-library-card" id="linker-library-trade-0" data-library-card data-library-kind="trade">
       <header class="linker-library-card-head"><h3 class="linker-library-card-title">Ordering</h3><span class="linker-library-n" data-library-card-count>2</span></header>
       <div class="linker-library-rows">${rows.trade}</div>
      </article></div></section>
     <section class="linker-library-zone" id="linker-library-zone-answers" data-library-spy>
      <h2 class="linker-library-zone-title">Product answers</h2><div class="linker-library-stack">
      <article class="linker-library-card" id="linker-library-answers-chint" data-library-card data-library-kind="answer">
       <header class="linker-library-card-head"><h3 class="linker-library-card-title">Chint</h3><span class="linker-library-n" data-library-card-count>1</span></header>
       <div class="linker-library-rows">${rows.answers}</div>
      </article></div></section>
    </div>
    <div class="linker-library-panel" id="linker-library-panel-documents" data-library-panel="documents" hidden>
     <div class="linker-library-filters" data-library-filters hidden><button type="button" data-library-type="all" aria-pressed="true">All</button><button type="button" data-library-type="datasheet" aria-pressed="false">Datasheet</button><button type="button" data-library-type="manual" aria-pressed="false">Manual</button></div>
     <section class="linker-library-zone" id="linker-library-zone-documents" data-library-spy>
      <h2 class="linker-library-zone-title">Brands</h2><div class="linker-library-stack">
      <article class="linker-library-card" id="linker-library-docs-chint" data-library-card data-library-kind="document">
       <header class="linker-library-card-head"><h3 class="linker-library-card-title">Chint</h3><span class="linker-library-n" data-library-card-count>3</span></header>
       <div class="linker-library-rows"><ul class="linker-library-doc-list">${rows.documents}</ul></div>
      </article></div></section>
    </div>
   </div>
  </div>
  <script type="application/json" id="linker-library-config">{"pageSize":20,"genieUrl":"/genie/","i18n":{"resultsOne":"%d result","resultsOther":"%d results","onFile":"%d on file","empty":"Nothing on file matches that search.","emptySoft":"No documents of this type.","askGenie":"Ask Genie","previous":"Previous","next":"Next","pages":"Pages","questions":"Questions","documents":"Documents","trade":"Trade rule","answer":"Answer","document":"Document","inAnswer":"In the answer","clear":"Clear search"}}</script>
 </div></body></html>`;
}

const QA = (question, answer) => `<details class="linker-library-qa" data-library-item data-library-group="Ordering"><summary class="linker-library-qa-head"><span class="linker-library-qa-text"><span class="linker-library-qa-q">${question}</span><span class="linker-library-qa-where" hidden>In the answer</span></span></summary><div class="linker-library-qa-a"><p>${answer}</p></div></details>`;
const DOC = (title, type) => `<li class="linker-library-doc" data-library-item data-library-type="${type}"><span class="linker-library-thumb is-type"></span><span class="linker-library-doc-lead"><span class="linker-library-badge is-${type}">${type}</span><span class="linker-library-doc-title">${title}</span></span><p class="linker-library-doc-meta"><span class="linker-library-doc-covers">covers 2 products</span><span class="linker-library-lang">EN</span></p><a class="linker-library-dl" href="https://de-linker.test/a.pdf">Download</a></li>`;

/** The page with rows: 25 documents so the pager has two pages. */
function fixture() {
 const many = Array.from({length: 25}, (_, i) => DOC(`Chint DTSU666 document ${i + 1}`, i % 2 ? 'manual' : 'datasheet')).join('');
 return new JSDOM(page({
  trade: QA('What is the minimum order quantity?', 'There is no pallet minimum.') + QA('How are quotations processed?', 'Net pricing and a bill of materials.'),
  answers: QA('Is the Chint module stackable?', 'Yes, up to four modules.'),
  documents: many
 }), {runScripts: 'outside-only', pretendToBeVisual: true, url: 'https://de-linker.test/faq-download/'});
}

function boot(dom) {
 dom.window.eval(source);
 // jsdom has no layout: the sticky measurement would read zeros and scroll
 // nothing, which is all the assertions below need.
 dom.window.scrollTo = () => {};
 return dom.window.document;
}

test('the script reveals the search field and the filters, and hides the inactive tab', () => {
 const dom = fixture();
 const doc = boot(dom);
 assert.equal(doc.querySelector('#linker-faq-page').classList.contains('is-enhanced'), true);
 assert.equal(doc.querySelector('.linker-library-search').hidden, false);
 assert.equal(doc.querySelector('[data-library-filters]').hidden, false);
 assert.equal(doc.querySelector('[data-library-panel="faq"]').hidden, false);
 assert.equal(doc.querySelector('[data-library-panel="documents"]').hidden, true);
 assert.equal(doc.querySelector('[data-library-nav="faq"]').hidden, false);
 assert.equal(doc.querySelector('[data-library-nav="documents"]').hidden, true);
 assert.equal(doc.querySelector('#linker-library-docs-chint [data-library-card-count]').textContent, '25');
 assert.equal(doc.querySelector('#linker-library-result-count').textContent, '28 on file');
});

test('the documents tab is named in the URL and the panels follow it', () => {
 const dom = fixture();
 const doc = boot(dom);
 const tab = doc.querySelector('#linker-library-tab-documents');
 tab.dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true, cancelable: true}));
 assert.equal(doc.querySelector('[data-library-panel="documents"]').hidden, false);
 assert.equal(doc.querySelector('[data-library-panel="faq"]').hidden, true);
 assert.equal(doc.querySelector('#linker-library-tab-documents').getAttribute('aria-selected'), 'true');
 assert.equal(doc.querySelector('#linker-library-tab-faq').getAttribute('aria-selected'), 'false');
 assert.match(dom.window.location.search, /tab=documents/);
 assert.equal(doc.querySelector('[data-library-nav="documents"]').hidden, false);
});

test('a card paginates its rows 20 at a time and the pager clamps', () => {
 const dom = fixture();
 const doc = boot(dom);
 const rows = [...doc.querySelectorAll('#linker-library-docs-chint [data-library-item]')];
 assert.equal(rows.filter((row) => !row.hidden).length, 20);
 const pager = doc.querySelector('#linker-library-docs-chint .linker-library-pager');
 assert.ok(pager, 'the card has a pager');
 const pages = [...pager.querySelectorAll('[data-library-page]')].map((button) => button.textContent);
 assert.deepEqual(pages, ['Previous', '1', '2', 'Next']);
 assert.equal(pager.querySelector('[data-library-page="prev"]').disabled, true);
 pager.querySelector('[data-library-page="2"]').dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true, cancelable: true}));
 assert.equal(rows.filter((row) => !row.hidden).length, 5);
 assert.equal(doc.querySelector('#linker-library-docs-chint [data-library-card-count]').textContent, '25');
 assert.equal(doc.querySelector('#linker-library-docs-chint .linker-library-pager [aria-current="page"]').textContent, '2');
});

test('a type chip filters the rows, the card count and the rail link together', () => {
 const dom = fixture();
 const doc = boot(dom);
 const chip = doc.querySelector('[data-library-type="datasheet"]');
 chip.dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true, cancelable: true}));
 assert.equal(chip.getAttribute('aria-pressed'), 'true');
 const rows = [...doc.querySelectorAll('#linker-library-docs-chint [data-library-item]')];
 assert.equal(rows.filter((row) => !row.hidden).length, 13);
 assert.equal(doc.querySelector('#linker-library-docs-chint [data-library-card-count]').textContent, '13');
 assert.equal(doc.querySelector('[data-library-spy-link][href="#linker-library-docs-chint"] .linker-library-n').textContent, '13');
 const empty = doc.querySelector('#linker-library-docs-chint .linker-library-empty-soft');
 assert.ok(empty && empty.hidden, 'the soft empty stays hidden while rows match');
});

test('the search lists hits from both kinds, marked, paginated, with the tab counts split', () => {
 const dom = fixture();
 const doc = boot(dom);
 const input = doc.querySelector('.linker-library-q');
 input.value = 'dtsu666';
 input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
 const host = doc.querySelector('[data-library-results]');
 assert.equal(host.hidden, false);
 assert.equal(doc.querySelector('[data-library-panel="faq"]').hidden, true);
 assert.equal(doc.querySelector('#linker-faq-page').classList.contains('is-searching'), true);
 assert.equal(host.querySelectorAll('.linker-library-hit').length, 20);
 assert.equal(host.querySelectorAll('.linker-library-hit-eye').length, 20);
 assert.equal(host.querySelector('.linker-library-hit .linker-library-hit-eye').textContent, 'Chint · Document');
 assert.ok(host.querySelector('mark').textContent.toLowerCase() === 'dtsu666');
 assert.equal(doc.querySelector('#linker-library-result-count').textContent, '25 results');
 assert.equal(doc.querySelector('#linker-library-tab-faq .linker-library-n').textContent, '0');
 assert.equal(doc.querySelector('#linker-library-tab-documents .linker-library-n').textContent, '25');
});

test('a question searched in the answer shows where it matched', () => {
 const dom = fixture();
 const doc = boot(dom);
 const input = doc.querySelector('.linker-library-q');
 input.value = 'modules';
 input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
 const hit = doc.querySelector('[data-library-results] .linker-library-qa');
 assert.ok(hit, 'the answer row matched');
 const where = hit.querySelector('.linker-library-qa-where');
 assert.equal(where.hidden, false);
});

test('an empty result offers Genie, and clearing restores the tabs', () => {
 const dom = fixture();
 const doc = boot(dom);
 const input = doc.querySelector('.linker-library-q');
 input.value = 'zzzz';
 input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
 const empty = doc.querySelector('[data-library-results] .linker-library-empty');
 assert.ok(empty);
 assert.equal(empty.querySelector('.linker-library-genie').textContent, 'Ask Genie');
 doc.querySelector('[data-library-clear]').dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true, cancelable: true}));
 assert.equal(doc.querySelector('[data-library-results]').hidden, true);
 assert.equal(doc.querySelector('[data-library-panel="faq"]').hidden, false);
 assert.equal(doc.querySelector('#linker-library-result-count').textContent, '28 on file');
 assert.equal(doc.querySelector('#linker-library-tab-documents .linker-library-n').textContent, '25');
});

test('the suggestions list questions and documents, and a click outside closes them', () => {
 const dom = fixture();
 const doc = boot(dom);
 const input = doc.querySelector('.linker-library-q');
 input.value = 'chint';
 input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
 const box = doc.querySelector('#linker-library-suggest');
 assert.equal(box.hidden, false);
 assert.equal(input.getAttribute('aria-expanded'), 'true');
 const labels = [...box.querySelectorAll('.linker-library-sug-label')].map((node) => node.textContent);
 assert.deepEqual(labels, ['Questions', 'Documents']);
 assert.ok(box.querySelectorAll('[data-library-suggest]').length <= 12);
 doc.body.dispatchEvent(new dom.window.Event('pointerdown', {bubbles: true}));
 assert.equal(box.hidden, true);
 assert.equal(input.getAttribute('aria-expanded'), 'false');
 // The render path does not reopen what the reader closed.
 input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
 assert.equal(box.hidden, false);
 dom.window.document.querySelector('.linker-library-clear').dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true, cancelable: true}));
 assert.equal(box.hidden, true);
});

test('arrow keys walk the suggestions and Enter opens a question in its card', () => {
 const dom = fixture();
 const doc = boot(dom);
 const input = doc.querySelector('.linker-library-q');
 input.value = 'minimum';
 input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
 input.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true, cancelable: true}));
 assert.equal(doc.querySelector('#linker-library-suggest [data-library-suggest="0"]').classList.contains('is-active'), true);
 assert.equal(input.getAttribute('aria-activedescendant'), 'linker-library-sug-0');
 input.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
 assert.equal(doc.querySelector('#linker-library-suggest').hidden, true);
 assert.equal(input.value, '');
 assert.equal(doc.querySelector('[data-library-panel="faq"]').hidden, false);
 const question = doc.querySelector('#linker-library-trade-0 .linker-library-qa');
 assert.equal(question.open, true, 'the question the suggestion named is open');
});

test('a document suggestion opens the file, not the page', () => {
 const dom = fixture();
 const doc = boot(dom);
 const opened = [];
 dom.window.open = (url) => { opened.push(url); return null; };
 const input = doc.querySelector('.linker-library-q');
 input.value = 'document 1';
 input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
 const triggers = [...doc.querySelectorAll('#linker-library-suggest [data-library-suggest]')];
 const match = triggers.find((node) => node.querySelector('.linker-library-sug-meta').textContent.indexOf('Document') !== -1);
 assert.ok(match, 'the dropdown lists documents');
 match.dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true, cancelable: true}));
 assert.deepEqual(opened, ['https://de-linker.test/a.pdf']);
});

test('a question the reader opened keeps its state, and a zone link scrolls to its zone', () => {
 const dom = fixture();
 const doc = boot(dom);
 const details = doc.querySelectorAll('#linker-library-trade-0 .linker-library-qa')[1];
 details.open = true;
 details.dispatchEvent(new dom.window.Event('toggle', {bubbles: false}));
 assert.equal(details.open, true);
 const link = doc.querySelector('a[href="#linker-library-zone-trade"]');
 link.dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true, cancelable: true}));
 assert.equal(dom.window.location.hash, '#linker-library-zone-trade');
});

test('the enhancement never writes customer-visible words of its own', () => {
 const words = ['Nothing on file', 'No documents of this type', 'Ask Genie', 'Previous', 'Next', 'In the answer'];
 words.forEach((word) => assert.equal(source.includes(word), false, `the script must not carry "${word}"`));
});
