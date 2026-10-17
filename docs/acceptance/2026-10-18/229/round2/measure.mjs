import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(
	new URL('../../../../../tests/e2e/package.json', import.meta.url)
);
const { chromium, webkit, firefox } = require('playwright-core');
// Run: node docs/acceptance/2026-10-18/229/round2/measure.mjs <local-base> <output-dir>
const base = process.argv[2];
const out = process.argv[3] || fileURLToPath(new URL('.', import.meta.url));
if (!base) throw new Error('Pass the local instance URL.');
await fs.mkdir(out, { recursive: true });
const widths = [
	...Array.from({ length: 21 }, (_, i) => 1280 + i),
	...Array.from({ length: 64 }, (_, i) => 1310 + i * 10),
	1366,
];
const all = [];
for (const [engine, type] of Object.entries({ chromium, webkit, firefox })) {
	const browser = await type.launch();
	const page = await browser.newPage({
		viewport: { width: 1440, height: 900 },
	});
	await page.goto(`${base}/de/`);
	await page.evaluate(() => document.fonts.ready);
	for (const width of widths) {
		await page.setViewportSize({ width, height: 900 });
		await page.evaluate(
			() =>
				new Promise((r) =>
					requestAnimationFrame(() => requestAnimationFrame(r))
				)
		);
		const row = await page.evaluate(() => {
			const h = document.querySelector('#tv-header-v2'),
				f = h.querySelector('.tv-nav-frame'),
				link = h.querySelector('.tv-nav-link');
			const originalPadding = getComputedStyle(link).paddingLeft;
			const originalFolded = h.dataset.tvNavFolded === 'true';
			const old = h.getAttribute('data-tv-actions-compact'),
				fold = h.getAttribute('data-tv-nav-folded');
			h.dataset.tvActionsCompact = 'true';
			h.removeAttribute('data-tv-nav-folded');
			const probe = document.createElement('style');
			probe.textContent =
				'html[lang^="de"] #tv-header-v2 .tv-nav-link{padding-inline:0!important}';
			document.head.append(probe);
			const st = getComputedStyle(f);
			const parts = [...f.children]
				.filter((c) => getComputedStyle(c).display !== 'none')
				.map((c) => ({
					class: c.className,
					width: c.getBoundingClientRect().width,
					marginRight:
						parseFloat(getComputedStyle(c).marginRight) || 0,
				}));
			const gap = parseFloat(st.columnGap);
			const zeroPaddingParts = parts.reduce(
				(s, p) => s + p.width + p.marginRight,
				0
			);
			const available = Math.floor(
				f.clientWidth -
					parseFloat(st.paddingLeft) -
					parseFloat(st.paddingRight)
			);
			const result = {
				width: innerWidth,
				available,
				gap,
				parts,
				zeroPaddingParts,
				zeroPaddingRequired:
					zeroPaddingParts + (parts.length - 1) * gap,
				originalPadding,
				originalFolded,
				font: getComputedStyle(link).font,
			};
			probe.remove();
			if (old === null) h.removeAttribute('data-tv-actions-compact');
			else h.setAttribute('data-tv-actions-compact', old);
			if (fold === null) h.removeAttribute('data-tv-nav-folded');
			else h.setAttribute('data-tv-nav-folded', fold);
			return result;
		});
		all.push({ engine, ...row });
	}
	console.log(
		engine,
		browser.version(),
		Math.min(
			...all
				.filter((r) => r.engine === engine)
				.map((r) => r.zeroPaddingParts)
		),
		Math.max(
			...all
				.filter((r) => r.engine === engine)
				.map((r) => r.zeroPaddingParts)
		)
	);
	await browser.close();
}
await fs.writeFile(
	`${out}/layout-metrics.json`,
	JSON.stringify(all, null, 2) + '\n'
);
