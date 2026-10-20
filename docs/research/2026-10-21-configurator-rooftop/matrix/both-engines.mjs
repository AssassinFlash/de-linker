/**
 * Read-only both-engine probe for #445 classification.
 * Production: GET and DOM read only. No turn, no add-to-draft, no account, no mail.
 * Local roof-button click is the established UI path, local instance only.
 */
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, 'shots');

const engines = [
	{ id: 'local', origin: 'http://127.0.0.1:9231' },
	{ id: 'prod', origin: 'https://de-linker.com' },
];

const cases = [
	{
		id: 'step-roof',
		path: '/solution-configurator/?step=roof',
	},
	{
		id: 'step-roof-de',
		path: '/de/loesungskonfigurator/?step=roof',
	},
	{
		id: 'prefill',
		path: '/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538',
	},
	{
		id: 'prefill-de',
		path: '/de/loesungskonfigurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538',
	},
	{
		id: 'retired-en',
		path: '/design-canvas/',
	},
	{
		id: 'retired-de',
		path: '/de/design-canvas/',
	},
	{
		id: 'retired-alias',
		path: '/de/entwurfsflache/',
	},
];

async function readState(page) {
	await page.locator('#linker-plz').waitFor({ state: 'visible', timeout: 25000 });
	return page.evaluate(() => {
		const value = (id) => document.getElementById(id)?.value ?? null;
		const mount = document.querySelector('[data-linker-app="configurator"]');
		const roof = document.querySelector('.linker-roof');
		const roofButton = [...document.querySelectorAll('button')].find((node) =>
			/roof|Dach/i.test(node.textContent || '')
		);
		return {
			htmlLang: document.documentElement.lang,
			title: document.title,
			finalPath: location.pathname + location.search,
			dataStep: mount ? mount.getAttribute('data-step') : null,
			mountAttrs: mount
				? [...mount.attributes].map((attr) => attr.name).sort()
				: [],
			roofPresent: Boolean(roof),
			roofVisible: Boolean(roof && roof.getClientRects().length),
			roofText: roof ? roof.textContent.replace(/\s+/g, ' ').trim().slice(0, 180) : '',
			loadingMap: /Loading the map|Karte wird geladen/i.test(document.body.innerText),
			plz: value('linker-plz'),
			annual: value('linker-annual'),
			kwp: value('linker-kwp'),
			phase: document.querySelector('input[name="phase"]:checked')?.value ?? null,
			backup: value('linker-backup'),
			steps: [...document.querySelectorAll('.linker-steps__item')].map((node) =>
				node.textContent.replace(/\s+/g, ' ').trim()
			),
			roofButton: roofButton
				? roofButton.textContent.replace(/\s+/g, ' ').trim()
				: '',
			scripts: [...document.scripts]
				.map((node) => node.src)
				.filter((src) => /configurator|linker-tools/i.test(src)),
		};
	});
}

async function assetFingerprint(page, scriptUrls) {
	const out = [];
	for (const url of scriptUrls) {
		const response = await page.request.get(url);
		const body = await response.body();
		const text = body.toString('utf8');
		out.push({
			url,
			status: response.status(),
			bytes: body.length,
			sha256: createHash('sha256').update(body).digest('hex'),
			hasUrlSearchParams: text.includes('URLSearchParams'),
			hasOpenRoof: text.includes('openRoof'),
			hasDataStep: text.includes('data-step') || text.includes('dataset.step') || text.includes('.step==="roof"') || text.includes(".step==='roof'"),
			stepRoofHits: (text.match(/step==="roof"|step==='roof'|data-step/g) || []).slice(0, 8),
		});
	}
	return out;
}

const rows = [];
const browser = await chromium.launch({ headless: true });

try {
	for (const engine of engines) {
		const context = await browser.newContext({
			viewport: { width: 1440, height: 900 },
			userAgent: 'de-linker-matrix-445/1.0',
		});
		const page = await context.newPage();
		let fingerprinted = false;
		for (const item of cases) {
			for (const viewport of [1440, 390]) {
				await page.setViewportSize({ width: viewport, height: viewport === 1440 ? 900 : 844 });
				const url = engine.origin + item.path;
				const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
				const state = await readState(page);
				const shot = `both-${engine.id}-${item.id}-${viewport}.png`;
				await page.screenshot({ path: join(shots, shot), fullPage: false });
				const row = {
					engine: engine.id,
					case: item.id,
					requested: url,
					status: response ? response.status() : null,
					viewport,
					shot: `shots/${shot}`,
					...state,
				};
				if (!fingerprinted && state.scripts.length) {
					row.assets = await assetFingerprint(page, state.scripts);
					fingerprinted = true;
				}
				rows.push(row);
				console.log(
					`${engine.id} ${item.id} ${viewport} roof=${state.roofPresent} data-step=${state.dataStep} kwp=${state.kwp || 'empty'} lang=${state.htmlLang} path=${state.finalPath}`
				);
			}
		}
		if (engine.id === 'local') {
			await page.setViewportSize({ width: 1440, height: 900 });
			await page.goto(engine.origin + '/solution-configurator/', {
				waitUntil: 'domcontentloaded',
				timeout: 45000,
			});
			await page.locator('#linker-plz').waitFor({ state: 'visible', timeout: 25000 });
			await page.locator('#linker-plz').fill('80538');
			const button = page.getByRole('button', {
				name: /Estimate from the roof|Dach/i,
			});
			await button.click();
			await page.locator('.linker-roof, .linker-empty').first().waitFor({
				state: 'visible',
				timeout: 20000,
			});
			await page.waitForTimeout(800);
			const opened = await readState(page);
			const shot = 'both-local-roof-button-1440.png';
			await page.screenshot({ path: join(shots, shot), fullPage: false });
			rows.push({
				engine: 'local',
				case: 'roof-button',
				requested: engine.origin + '/solution-configurator/',
				viewport: 1440,
				shot: `shots/${shot}`,
				note: 'Established UI path only. Not repeated on production.',
				...opened,
			});
			console.log(
				`local roof-button roof=${opened.roofPresent} visible=${opened.roofVisible} text=${opened.roofText.slice(0, 80)}`
			);
		}
		await context.close();
	}
} finally {
	await browser.close();
}

writeFileSync(join(here, 'both-engines.json'), JSON.stringify(rows, null, 2));
console.log(`wrote ${rows.length} rows`);
