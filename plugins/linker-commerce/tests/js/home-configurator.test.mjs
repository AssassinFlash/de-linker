import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { JSDOM } from 'jsdom';

const script = new URL('../../assets/home-configurator.js', import.meta.url);

for (const [lang, base] of [
	['en', '/solution-configurator/'],
	['de', '/de/loesungskonfigurator/'],
]) {
	test(lang + ': changing the showcase view updates its picture, direct entry and keyboard focus', () => {
		const source = new URL('../../content/livecanvas/home-configurator/showcase-' + lang + '.html', import.meta.url);
		const dom = new JSDOM(readFileSync(source, 'utf8'), { url: 'https://de-linker.com/', runScripts: 'outside-only' });
		const { document, KeyboardEvent } = dom.window;
		const root = document.getElementById('configurator-showcase');
		dom.window.eval(readFileSync(script, 'utf8'));
		const tabs = [...root.querySelectorAll('[role=tab]')];
		const active = () => root.querySelector('[role=tabpanel]:not([hidden])');
		assert.equal(tabs.length, 5);
		assert.equal(active().id, tabs[0].getAttribute('aria-controls'));
		tabs[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
		assert.equal(document.activeElement, tabs[1]);
		assert.equal(tabs[1].getAttribute('aria-selected'), 'true');
		assert.equal(active().querySelector('figcaption a').getAttribute('href'), base + '?view=equipment');
		assert.match(active().querySelector('picture img').src, new RegExp('equipment-' + lang + '-1440.webp$'));
		assert.match(active().querySelector('picture source').srcset, new RegExp('equipment-' + lang + '-390.webp$'));
		assert.match(root.querySelector('[data-showcase-address]').textContent, /view=equipment$/);
		tabs[1].dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
		assert.equal(active().querySelector('figcaption a').getAttribute('href'), base + '?view=inquiry');
		tabs[2].click();
		assert.equal(active().querySelector('figcaption a').getAttribute('href'), base + '?step=roof');
		assert.equal(root.querySelectorAll('[role=tab][tabindex="0"]').length, 1);
		dom.window.close();
	});
}
