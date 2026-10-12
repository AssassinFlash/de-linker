// Measures the computed styles and geometry of every element under a root
// selector, so the same dump can be taken on the live page and the local page
// and diffed property by property. Usage:
//
//   node measure.mjs <url> <root-selector> <out.json> [viewportWidth]
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const [, , url, root, out, widthArg] = process.argv;
const width = Number(widthArg || 1440);

const PROPS = [
	'display', 'position', 'float', 'clear',
	'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height',
	'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
	'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
	'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
	'border-top-style', 'border-bottom-style', 'border-left-style', 'border-right-style',
	'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
	'border-top-left-radius', 'border-top-right-radius', 'border-bottom-right-radius', 'border-bottom-left-radius',
	'box-shadow', 'background-color', 'background-image', 'color', 'opacity',
	'font-family', 'font-size', 'font-weight', 'font-style', 'line-height', 'letter-spacing', 'text-transform', 'text-decoration-line', 'text-align', 'white-space',
	'flex-direction', 'flex-wrap', 'justify-content', 'align-items', 'align-content', 'flex-grow', 'flex-shrink', 'flex-basis', 'order',
	'gap', 'row-gap', 'column-gap', 'grid-template-columns', 'grid-template-rows', 'grid-auto-flow', 'grid-column', 'grid-row',
	'overflow-x', 'overflow-y', 'z-index', 'transform', 'transition-property',
	'list-style-type', 'object-fit', 'aspect-ratio', 'box-sizing', 'cursor', 'visibility',
];

const browser = await chromium.launch({ channel: 'chromium' });
try {
	const context = await browser.newContext({ viewport: { width, height: 900 } });
	const page = await context.newPage();
	await page.goto(url, { waitUntil: 'networkidle', timeout: 90_000 }).catch(() => page.waitForTimeout(4000));
	await page.waitForTimeout(1200);
	// Load lazy images so geometry is final.
	await page.evaluate(async () => {
		await new Promise((resolve) => {
			let total = 0;
			const step = () => {
				window.scrollTo(0, total);
				total += 800;
				if (total < document.body.scrollHeight + 800) setTimeout(step, 60);
				else resolve();
			};
			step();
		});
		window.scrollTo(0, 0);
	});
	await page.waitForTimeout(1500);

	const dump = await page.evaluate(({ rootSel, props }) => {
		const rootEl = document.querySelector(rootSel);
		if (!rootEl) return { error: 'root not found: ' + rootSel, items: [] };
		const items = [];
		const keyOf = (el) => {
			const parts = [];
			let node = el;
			while (node && node !== rootEl.parentElement) {
				const tag = node.tagName.toLowerCase();
				let n = 1;
				let sib = node;
				while ((sib = sib.previousElementSibling)) if (sib.tagName === node.tagName) n++;
				parts.unshift(`${tag}:${n}`);
				node = node.parentElement;
			}
			return parts.join('/');
		};
		const walk = (el) => {
			const cs = getComputedStyle(el);
			const rect = el.getBoundingClientRect();
			const scrollX = window.scrollX;
			const scrollY = window.scrollY;
			const row = {
				key: keyOf(el),
				tag: el.tagName.toLowerCase(),
				classes: (el.getAttribute('class') || '').split(/\s+/).filter(Boolean).join(' '),
				id: el.id || '',
				rect: {
					x: Math.round((rect.x + scrollX) * 100) / 100,
					y: Math.round((rect.y + scrollY) * 100) / 100,
					w: Math.round(rect.width * 100) / 100,
					h: Math.round(rect.height * 100) / 100,
				},
				text: (el.children.length === 0 ? el.textContent.trim().slice(0, 80) : ''),
				style: {},
			};
			for (const p of props) row.style[p] = cs.getPropertyValue(p);
			items.push(row);
			for (const child of el.children) walk(child);
		};
		walk(rootEl);
		return { items };
	}, { rootSel: root, props: PROPS });

	fs.writeFileSync(out, JSON.stringify(dump, null, 1));
	console.log(`wrote ${out}: ${dump.items.length} elements`);
} finally {
	await browser.close();
}
