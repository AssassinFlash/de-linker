/**
 * A full computed-style dump of a face's region, for the old/new comparison:
 * every element under the face's root, every computed property, plus the
 * geometric box. Written as JSON so the two states can be diffed.
 *
 *   node .scratch/175/style-dump.mjs <out.json> <url> <root-id>
 */

import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-blogs/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const [out, url, rootId] = process.argv.slice(2);

const dump = (id) => {
	const root = document.getElementById(id);
	if (!root) {
		return { elements: [], missing: true };
	}
	const elements = [];
	const walk = (element) => {
		const computed = getComputedStyle(element);
		const style = {};
		for (const name of computed) {
			style[name] = computed.getPropertyValue(name);
		}
		const rect = element.getBoundingClientRect();
		elements.push({
			tag: element.tagName,
			cls: element.className.toString(),
			box: [
				Math.round(rect.x),
				Math.round(rect.y + window.scrollY),
				Math.round(rect.width),
				Math.round(rect.height),
			].join(','),
			style,
		});
		for (const child of element.children) {
			walk(child);
		}
	};
	walk(root);
	return { elements };
};

const browser = await chromium.launch();
const context = await browser.newContext({
	viewport: { width: 1440, height: 1000 },
	deviceScaleFactor: 1,
	reducedMotion: 'reduce',
});
const page = await context.newPage();
await page.goto(url, { waitUntil: 'load', timeout: 90_000 });
await page.waitForTimeout(800);
const data = await page.evaluate(dump, rootId);
writeFileSync(out, `${JSON.stringify(data)}\n`);
console.log(`wrote ${out}: ${data.elements.length} elements`);
await context.close();
await browser.close();
