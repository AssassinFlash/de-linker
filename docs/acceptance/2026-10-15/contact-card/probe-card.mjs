// The card's render probe for docs/acceptance/2026-10-15/contact-card/README.md:
// screenshots the card at 1440x900 and 390x844 (EN / DE) and prints the geometry
// the card's stylesheet is supposed to produce, plus a control for the class
// probes in the README's last section.
//
// Usage: node probe-card.mjs <base-url> <out-dir>
//   e.g. node probe-card.mjs http://127.0.0.1:9005 /tmp/contact-shots
// Playwright resolves from plugins/linker-tools (npm ci there first).
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '..', '..', '..', '..');
const { chromium } = createRequire(path.join(repo, 'plugins', 'linker-tools', 'package.json'))('playwright');

const base = (process.argv[2] ?? 'http://127.0.0.1:9005').replace(/\/$/, '');
const out = process.argv[3] ?? '/tmp/contact-shots';
fs.mkdirSync(out, { recursive: true });

const shots = [
	['en-1440', '/contact/', 1440, 900],
	['de-1440', '/de/kontakt/', 1440, 900],
	['en-390', '/contact/', 390, 844],
	['de-390', '/de/kontakt/', 390, 844],
];

for (const [name, route, width, height] of shots) {
	const browser = await chromium.launch({ channel: 'chromium' });
	try {
		const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
		await page.goto(`${base}${route}?cbq=${Date.now()}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
		await page.addStyleTag({ content: '*, *::before, *::after { animation: none !important; transition: none !important; }' });
		await page.evaluate(async () => { if (document.fonts?.ready) await document.fonts.ready; });
		await page.evaluate(() => document.querySelector('.linker-contact-card')?.scrollIntoView({ block: 'start' }));
		await page.waitForTimeout(700);
		const file = path.join(out, `${name}.png`);
		await page.screenshot({ path: file });
		const metrics = await page.evaluate(() => {
			const box = (selector) => {
				const node = document.querySelector(selector);
				if (!node) return null;
				const style = getComputedStyle(node);
				return {
					width: Math.round(node.getBoundingClientRect().width),
					display: style.display,
					padding: style.padding,
					gap: style.gap,
					radius: style.borderRadius,
					columns: style.gridTemplateColumns,
					background: style.backgroundColor,
				};
			};
			// The control: the same classes in the two places that matter. The
			// unlayered `:where(… #theme-main) :where(*) { all: revert }` rule of
			// the compiled cache reaches every descendant of #theme-main, so the
			// utilities only hold outside it (see README).
			const read = (el) => { const s = getComputedStyle(el); return { display: s.display, fontSize: s.fontSize, color: s.color, marginTop: s.marginTop }; };
			const make = () => { const d = document.createElement('div'); d.className = 'grid text-xs text-neutral-600 mt-1'; return d; };
			const outside = make();
			document.body.appendChild(outside);
			const inside = make();
			(document.querySelector('#theme-main') || document.body).appendChild(inside);
			const controlProbe = { outsideThemeMain: read(outside), insideThemeMain: read(inside) };
			outside.remove();
			inside.remove();

			const consent = document.querySelector('.linker-form-consent');
			const consentBox = consent && consent.querySelector('input[type="checkbox"]');
			const consentLink = consent && consent.querySelector('a');
			const styleOf = (node) => { const s = getComputedStyle(node); return { color: s.color, decoration: s.textDecorationLine, offset: s.textUnderlineOffset }; };
			return {
				card: box('.linker-contact-card'),
				form: box('.linker-contact-form'),
				submitRow: box('.linker-form-submit'),
				submit: box('.linker-contact-card .linker-form-primary'),
				rail: box('.linker-contact-rail'),
				fields: box('.linker-form-fields'),
				topic: (() => { const select = document.querySelector('select[name="intent"]'); return select ? select.value : null; })(),
				consent: consent ? {
					display: getComputedStyle(consent).display,
					width: Math.round(consent.getBoundingClientRect().width),
					fontSize: getComputedStyle(consent).fontSize,
					lineHeight: getComputedStyle(consent).lineHeight,
					color: getComputedStyle(consent).color,
					gap: getComputedStyle(consent).gap,
					checkbox: consentBox ? { width: getComputedStyle(consentBox).width, height: getComputedStyle(consentBox).height, marginTop: getComputedStyle(consentBox).marginTop, accent: getComputedStyle(consentBox).accentColor } : null,
					link: consentLink ? styleOf(consentLink) : null,
				} : null,
				controlProbe,
			};
		});
		console.log(JSON.stringify({ name, file, metrics }));
	} catch (error) {
		console.log(JSON.stringify({ name, error: String(error).split('\n')[0] }));
	} finally {
		await browser.close();
	}
}
