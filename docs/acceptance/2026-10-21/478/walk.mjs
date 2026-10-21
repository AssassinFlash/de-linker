/**
 * Local walk for #478: seven engine behaviours through the Solution
 * Configurator UI (C17, C18, C44, C53, C54, C55, C56).
 *
 * Every scenario is a real form submission on the local snapshot instance
 * (`just up w478` + `just pull load w478 latest` + `just serve w478`), not an
 * engine injection. The swap scenarios start from the base form and change the
 * inverter through the solution card's "Other inverter" select, the same
 * control a customer uses. Nothing is added to the draft and nothing is saved;
 * no mail, no inquiry, no registration.
 *
 * For each language the record keeps the request body and the full response
 * (json/) and element screenshots of the solution and the design report
 * (shots/), at 1440 and 390.
 *
 * Prerequisites: the instance at ORIGIN below (default `http://127.0.0.1:9255`,
 * override with `LINKER_SITE`) and Playwright from the main checkout's
 * tests/e2e install (the same borrow as docs/acceptance/2026-10-21/473).
 * Run: node walk.mjs
 */
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = join(here, 'shots');
const jsonDir = join(here, 'json');
mkdirSync(shotsDir, { recursive: true });
mkdirSync(jsonDir, { recursive: true });

const ORIGIN = process.env.LINKER_SITE || 'http://127.0.0.1:9255';
const PAGES = {
	en: '/solution-configurator/',
	de: '/de/loesungskonfigurator/',
};

const BASE = {
	plz: '80538',
	annual: '5000',
	kwp: '10',
	phase: '3',
	backup: 'none',
	load: '',
	hours: '',
	heat: false,
	ev: false,
};

const SCENARIOS = [
	{
		id: 'base',
		fields: BASE,
		covers: ['C44', 'C54 included meter', 'C55', 'C56 released'],
		reportShots: ['bom', 'releases', 'basis'],
	},
	{
		id: 'backup',
		fields: { ...BASE, backup: 'needed', load: '3', hours: '4' },
		covers: ['C17'],
		reportShots: [],
	},
	{
		id: 'hp-ev',
		fields: { ...BASE, heat: true, ev: true },
		covers: ['C18'],
		reportShots: ['storage', 'basis'],
	},
	{
		id: 'stack',
		fields: { ...BASE, annual: '12000' },
		covers: ['C53 largest within the cap'],
		reportShots: ['storage'],
	},
	{
		id: 'small',
		fields: { ...BASE, annual: '600', kwp: '4' },
		covers: ['C53 smallest above, marked', 'C54 meter line', 'C55 one string'],
		reportShots: ['bom', 'storage'],
	},
	{
		id: 'h2',
		fields: BASE,
		swap: 'SAJ H2-10K-T3',
		covers: ['C54 meter line', 'C56 released_with_accessory'],
		reportShots: ['bom', 'releases'],
	},
	{
		id: 'hs2',
		fields: BASE,
		swap: 'SAJ HS2-10K-T2-X',
		covers: ['C54 meter line', 'C56 unknown pair absent'],
		reportShots: ['bom', 'releases'],
	},
];

function writeJson(name, value) {
	writeFileSync(join(jsonDir, name), `${JSON.stringify(value, null, 2)}\n`);
}

function writeRecord(record) {
	writeFileSync(
		join(here, 'record.json'),
		`${JSON.stringify(record, null, 2)}\n`
	);
}

async function dismissConsent(page) {
	const accept = page.locator('[data-cky-tag="accept-button"]');
	try {
		await accept.waitFor({ state: 'visible', timeout: 3000 });
		await accept.evaluate((button) => button.click());
		await page
			.locator('.cky-consent-container')
			.waitFor({ state: 'hidden', timeout: 3000 });
	} catch {
		// Already chosen, or this page has no banner.
	}
}

async function quiet(page) {
	await page
		.addStyleTag({
			content:
				'*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}' +
				// Site chrome would be painted over an element screenshot: the
				// theme header is sticky, and under 48rem the step rail is
				// sticky and the mobile step bar is fixed. They are not part of
				// the result or the report, so take them out of the painted box.
				'#lc-header{display:none!important}' +
				'.linker-mobile-nav{display:none!important}' +
				'.linker-configurator .linker-steps{position:static!important}',
		})
		.catch(() => {});
}

function designResponse(page, timeout = 180000) {
	return page.waitForResponse(
		(response) =>
			response.url().includes('design/residential') &&
			response.request().method() === 'POST',
		{ timeout }
	);
}

async function fillForm(page, fields) {
	await page.locator('#linker-plz').fill(fields.plz);
	await page.locator('#linker-annual').fill(fields.annual);
	await page.locator('#linker-kwp').fill(fields.kwp);
	if (fields.phase === '1') {
		await page.locator('#linker-phase-1').check();
	} else {
		await page.locator('#linker-phase-3').check();
	}
	await page.locator('#linker-backup').selectOption(fields.backup);
	if (fields.backup !== 'none') {
		await page.locator('#linker-backup-load').fill(fields.load);
		await page.locator('#linker-backup-hours').fill(fields.hours);
	}
	if (fields.heat) {
		await page.locator('#linker-heat-pump').check();
	}
	if (fields.ev) {
		await page.locator('#linker-ev').check();
	}
}

async function shootSection(page, selector, name) {
	const target = page.locator(selector).first();
	if (!(await target.count())) {
		// A renamed or missing selector would otherwise leave the record
		// claiming screenshots that do not exist while the walk exits 0.
		throw new Error(`no element for ${selector}`);
	}
	const taken = [];
	for (const viewport of [
		{ width: 1440, height: 900, tag: '1440' },
		{ width: 390, height: 844, tag: '390' },
	]) {
		await page.setViewportSize({
			width: viewport.width,
			height: viewport.height,
		});
		await page.waitForTimeout(400);
		const file = `${name}-${viewport.tag}.png`;
		await target.screenshot({ path: join(shotsDir, file) });
		taken.push(`shots/${file}`);
	}
	await page.setViewportSize({ width: 1440, height: 900 });
	if (taken.length !== 2) {
		throw new Error(`${selector}: ${taken.length} screenshots, expected 2`);
	}
	return taken;
}

function reportSection(response, id) {
	const section = (response.report?.sections || []).find(
		(entry) => entry.id === id
	);
	if (!section) {
		return null;
	}
	return {
		title: section.title,
		rows: (section.rows || []).map((row) => ({
			label: row.label,
			value: row.value,
		})),
		table: section.table
			? {
					columns: section.table.columns,
					rows: section.table.rows,
			  }
			: null,
		paragraphs: section.paragraphs || [],
	};
}

function observed(response) {
	const selected = response.selected;
	return {
		status: response.status,
		storage: response.storage,
		warnings: response.warnings,
		relaxations: response.relaxations,
		metrics: response.metrics,
		selected: selected
			? {
					inverter: selected.inverter.model,
					battery: selected.battery
						? {
								model: selected.battery.product.model,
								quantity: selected.battery.quantity,
								stacks: selected.battery.stacks,
								usable_kwh: selected.battery.usable_kwh,
								above_upper_limit:
									selected.battery.above_upper_limit,
								release: selected.battery.release,
						  }
						: null,
					inverter_rules: selected.inverter_rules.map((rule) => ({
						id: rule.id,
						passed: rule.passed,
						value: rule.value,
						limit: rule.limit,
						text: rule.text,
					})),
					strings: selected.strings
						? {
								module: selected.strings.module,
								module_count: selected.strings.module_count,
								modules_per_string:
									selected.strings.modules_per_string,
								groups: selected.strings.groups,
								total_strings: selected.strings.groups.reduce(
									(sum, group) => sum + group.strings,
									0
								),
						  }
						: null,
					lines: selected.lines.map((line) => ({
						role: line.role,
						quantity: line.quantity,
						unit: line.unit,
						model: line.product ? line.product.model : null,
						label: line.label,
						basis: line.basis,
					})),
			  }
			: null,
		candidates: {
			inverters: response.candidates.inverters.map((candidate) => ({
				model: candidate.product.model,
				ac_power_kw: candidate.ac_power_kw,
				battery: candidate.battery
					? {
							model: candidate.battery.product.model,
							usable_kwh: candidate.battery.usable_kwh,
							above_upper_limit:
								candidate.battery.above_upper_limit,
							verdict: candidate.battery.release.verdict,
					  }
					: null,
			})),
			batteries: response.candidates.batteries.map((battery) => ({
				model: battery.product.model,
				quantity: battery.quantity,
				usable_kwh: battery.usable_kwh,
				above_upper_limit: battery.above_upper_limit,
				verdict: battery.release.verdict,
			})),
			excluded: response.candidates.excluded.map((excluded) => ({
				model: excluded.product.model,
				failed: excluded.failed.map((rule) => ({
					id: rule.id,
					passed: rule.passed,
					value: rule.value,
					limit: rule.limit,
				})),
			})),
			accessories: response.candidates.accessories.map(
				(accessory) => accessory.model
			),
		},
		report: response.report
			? {
					locale: response.report.locale,
					sections: response.report.sections.map((entry) => entry.id),
					storage: reportSection(response, 'storage'),
					basis: reportSection(response, 'basis'),
					releases: reportSection(response, 'releases'),
					bom: reportSection(response, 'bom'),
					assumptions: reportSection(response, 'assumptions'),
			  }
			: null,
	};
}

async function runScenario(page, lang, scenario) {
	const config = PAGES[lang];
	await page.goto(ORIGIN + config, {
		waitUntil: 'domcontentloaded',
		timeout: 45000,
	});
	await dismissConsent(page);
	await quiet(page);
	await page.locator('#linker-plz').waitFor({
		state: 'visible',
		timeout: 30000,
	});
	await fillForm(page, scenario.fields);

	const pending = designResponse(page);
	await page
		.locator('#linker-inputs-section form button[type="submit"]')
		.click();
	const response = await pending;
	const body = await response.json();
	let final = body;
	let finalUrl = response.url();
	let request = JSON.parse(response.request().postData() || '{}');
	if (scenario.swap) {
		// Keep the form request that the swap started from: the swap request
		// replaces the same file name below.
		writeJson(`${lang}-${scenario.id}-base-request.json`, request);
		writeJson(`${lang}-${scenario.id}-base-response.json`, body);
		await page.locator('#linker-swap-inverter').waitFor({
			state: 'visible',
			timeout: 60000,
		});
		const swapped = designResponse(page);
		await page
			.locator('#linker-swap-inverter')
			.selectOption({ label: scenario.swap });
		const swapResponse = await swapped;
		final = await swapResponse.json();
		finalUrl = swapResponse.url();
		request = JSON.parse(swapResponse.request().postData() || '{}');
	}
	writeJson(`${lang}-${scenario.id}-request.json`, request);

	await page
		.locator('.linker-solution, .linker-empty--none, .linker-empty--error')
		.first()
		.waitFor({ state: 'visible', timeout: 60000 });

	writeJson(`${lang}-${scenario.id}-response.json`, final);

	const shots = {
		solution: await shootSection(
			page,
			'#linker-solution-section',
			`${lang}-${scenario.id}-solution`
		),
		report: [],
		sections: {},
	};
	const hasReport = (await page.locator('#linker-report-section').count()) > 0;
	if (hasReport !== scenario.reportShots.length > 0) {
		throw new Error(
			`${lang} ${scenario.id}: report=${hasReport}, reportShots=` +
				`${scenario.reportShots.length}`
		);
	}
	if (hasReport) {
		shots.report = await shootSection(
			page,
			'#linker-report-section',
			`${lang}-${scenario.id}-report`
		);
		for (const section of scenario.reportShots) {
			shots.sections[section] = await shootSection(
				page,
				`section[aria-labelledby="linker-report-${section}"]`,
				`${lang}-${scenario.id}-report-${section}`
			);
		}
	}

	const htmlLang = await page.getAttribute('html', 'lang');
	const build = await page.evaluate(
		() =>
			Array.from(document.querySelectorAll('script[src]'))
				.map((script) => script.src)
				.find((src) => src.includes('configurator.js')) || null
	);
	return {
		lang,
		scenario: scenario.id,
		covers: scenario.covers,
		url: ORIGIN + config,
		htmlLang,
		build,
		swappedTo: scenario.swap || null,
		requestStatus: response.status(),
		finalStatus: final.status,
		requestUrl: response.url(),
		finalUrl,
		shots,
		observed: observed(final),
	};
}

async function main() {
	const record = {
		ticket: 478,
		instance: 'w478',
		origin: ORIGIN,
		snapshot: '20261019-1715',
		browser: 'playwright chromium',
		startedAt: new Date().toISOString(),
		mailSent: false,
		inquirySent: false,
		registered: false,
		draftWrites: false,
		browserRequests: [],
		runs: [],
	};
	const browserRequests = [];
	const browser = await chromium.launch();
	try {
		for (const lang of ['en', 'de']) {
			const context = await browser.newContext({
				viewport: { width: 1440, height: 900 },
				locale: lang === 'de' ? 'de-DE' : 'en-GB',
			});
			const page = await context.newPage();
			page.on('request', (request) => {
				if (request.method() !== 'GET') {
					browserRequests.push({
						method: request.method(),
						url: request.url(),
					});
				}
			});
			for (const scenario of SCENARIOS) {
				const run = await runScenario(page, lang, scenario);
				if (!record.build && run.build) {
					record.build = run.build;
				}
				record.runs.push(run);
				record.browserRequests = browserRequests;
				// A write is any non-GET request that is not the design call
				// the form and the swap make. The list above is the observation.
				record.draftWrites = browserRequests.some(
					(request) => !request.url.includes('/design/residential')
				);
				console.log(
					`${lang} ${scenario.id}: ${run.finalStatus} ` +
						`${run.observed.selected?.inverter || '-'} ` +
						`${run.observed.selected?.battery?.model || '-'}`
				);
				writeRecord(record);
			}
			await context.close();
		}
	} finally {
		await browser.close();
	}
	record.finishedAt = new Date().toISOString();
	writeRecord(record);
}

main().catch((error) => {
	console.error(error);
	process.exit(1);
});
