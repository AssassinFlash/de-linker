/**
 * The native readback behind native-matrix.json (2026-11-11 identity recheck).
 *
 * One saved project per language, read at 1440 × 1000 and 390 × 844 through
 * the shipped bundle on the review instance: the same shape as the 10-22
 * matrix (`docs/acceptance/2026-10-22/548/map-display/system-identity/`), so
 * the two records compare field by field.
 *
 * Run from tests/e2e after `node probe`'s dependency:
 *   node ../../../docs/acceptance/2026-11-11/548-identity-recheck/capture.mjs
 *
 * It writes the PNG/JSON pairs beside itself and prints the matrix row set.
 * This is evidence capture, not a gate: the gate is specs/planner-identity.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
// Playwright belongs to the regression suite, not to this record; resolve it
// from tests/e2e so the capture needs no second install.
const require = createRequire(join(HERE, '../../../../tests/e2e/package.json'));
const { chromium } = require('playwright');
const NATIVE = join(HERE, 'native');
mkdirSync(NATIVE, { recursive: true });

const BASE = 'http://127.0.0.1:8889';
const CONSENT = [
	{
		name: 'cookieyes-consent',
		value: 'consentid:e2e,consent:no,action:yes,necessary:yes,analytics:no,advertisement:no',
		domain: '127.0.0.1',
		path: '/',
	},
];

const WORDS = {
	en: {
		path: '/solution-configurator/',
		newProject: 'New project',
		create: 'Create project',
		title: 'Identity recheck EN',
		save: 'Save project',
		unsaved: 'Unsaved changes',
	},
	de: {
		path: '/de/loesungskonfigurator/',
		newProject: 'Neues Projekt',
		create: 'Projekt anlegen',
		title: 'Identitätsprüfung DE',
		save: 'Projekt speichern',
		unsaved: 'Ungespeicherte Änderungen',
	},
};

const READ = () => {
	const footer = document.querySelector('.lp-tool-identity');
	const details = document.querySelector('.lp-tool-about');
	const box = footer?.getBoundingClientRect();
	const lines = [...document.querySelectorAll('.lp-save-state')].map((n) =>
		n.textContent?.trim()
	);
	return {
		details: details ? details.open : null,
		identity: footer?.innerText ?? null,
		identityBox: box
			? {
					x: box.x,
					y: box.y,
					width: box.width,
					height: box.height,
					top: box.top,
					right: box.right,
					bottom: box.bottom,
					left: box.left,
				}
			: null,
		links: [...(footer?.querySelectorAll('a') ?? [])].map((a) => ({
			label: a.textContent?.trim() ?? '',
			href: a.getAttribute('href'),
			rel: a.getAttribute('rel'),
			target: a.getAttribute('target'),
		})),
		fonts: document.fonts?.status ?? null,
		revision: lines[0] ?? null,
		viewport: [innerWidth, innerHeight],
		widths: [document.documentElement.clientWidth, innerWidth],
		scroll: [scrollY, document.documentElement.scrollHeight],
		overflow:
			document.documentElement.scrollWidth -
			document.documentElement.clientWidth,
		url: location.href,
	};
};

function pngSize(path) {
	const bytes = readFileSync(path);
	return [
		bytes.readUInt32BE(16),
		bytes.readUInt32BE(20),
		bytes.length,
	];
}

const browser = await chromium.launch();
const accepted = [];
const frames = [];

for (const lang of ['en', 'de']) {
	const words = WORDS[lang];
	const context = await browser.newContext({
		viewport: { width: 1440, height: 1000 },
		deviceScaleFactor: 1,
	});
	await context.addCookies(CONSENT);
	const page = await context.newPage();

	await page.goto(BASE + words.path, { waitUntil: 'networkidle' });
	await page
		.getByRole('button', { name: words.newProject })
		.first()
		.click();
	await page.locator('input[maxlength="256"]').first().fill(words.title);
	await page.getByRole('button', { name: words.create }).click();
	await page.waitForFunction(
		() => /project=[a-f0-9]{32}/.test(location.href),
		null,
		{ timeout: 180_000 }
	);
	await page.locator('.lp-save-state').waitFor({ timeout: 60_000 });
	await page.waitForTimeout(3000);

	// Two real edits through the site section, each one saved with the editor's
	// own Save project button: the record then carries revision 3, the same
	// revision the 10-22 matrix framed, and the identity is read from a project
	// that has survived saves rather than from a first frame. The hash is what
	// makes the site section the live one.
	const projectPath =
		new URL(page.url()).pathname + new URL(page.url()).search;
	await page.goto(`${BASE}${projectPath}#lp-site`, {
		waitUntil: 'domcontentloaded',
	});
	await page.locator('.lp-save-state').waitFor({ timeout: 60_000 });
	for (const [index, note] of [
		[2, `${words.title} site`],
		[3, `${words.title} site edit`],
	]) {
		const field = page.locator('#lp-site input[maxlength="4096"]').first();
		await field.fill(note);
		await field.blur();
		await page.waitForFunction(
			(expected) =>
				document.querySelector('.lp-save-state')?.textContent?.trim() ===
				expected,
			words.unsaved,
			{ timeout: 20_000 }
		);
		// Saving is explicit: the editor writes a revision only when its own
		// Save project button is pressed.
		await page.getByRole('button', { name: words.save }).click();
		await page.waitForFunction(
			(expected) =>
				new RegExp(`\\b${expected}$`).test(
					document.querySelector('.lp-save-state')?.textContent?.trim() ?? ''
				),
			index,
			{ timeout: 90_000 }
		);
	}
	await page.waitForTimeout(1500);

	for (const [width, height, suffix] of [
		[1440, 1000, 'desktop'],
		[390, 844, 'phone'],
	]) {
		await page.setViewportSize({ width, height });
		await page.goto(BASE + projectPath, { waitUntil: 'domcontentloaded' });
		await page.locator('.lp-tool-identity').waitFor({ timeout: 120_000 });
		await page.locator('.lp-tool-about summary').click();
		await page.waitForFunction(
			() => document.querySelector('.lp-tool-about')?.open === true,
			null,
			{ timeout: 20_000 }
		);
		await page.waitForTimeout(600);
		const before = await page.evaluate(READ);

		const name = `${lang}-${suffix}-system-about-framed`;
		// The block itself, at CSS size: the frame the record indexes.
		await page.locator('.lp-tool-identity').scrollIntoViewIfNeeded();
		await page.waitForTimeout(200);
		const shot = join(NATIVE, `${name}.png`);
		await page.locator('.lp-tool-identity').screenshot({ path: shot });
		const after = await page.evaluate(READ);

		writeFileSync(
			join(NATIVE, `${name}.json`),
			`${JSON.stringify({ before, after, captureBeyondViewport: false }, null, 1)}\n`
		);
		const [pngWidth, pngHeight, bytes] = pngSize(shot);
		frames.push({
			name,
			size: [width, height],
			png: [pngWidth, pngHeight, bytes],
		});
		accepted.push({
			name,
			size: [width, height],
			revision: before.revision,
			links: before.links.length,
			identity_fully_framed:
				before.details === true &&
				before.identityBox !== null &&
				before.overflow === 0 &&
				before.fonts === 'loaded' &&
				before.links.length === 10,
			link_labels: before.links.map((link) => link.label),
			overflow: before.overflow,
		});
		console.log(
			`${name}: revision=${JSON.stringify(before.revision)} links=${before.links.length} overflow=${before.overflow} png=${pngWidth}x${pngHeight}`
		);
	}

	await context.close();
}

// The project list: the same identity, no editor and therefore no revision.
{
	const context = await browser.newContext({
		viewport: { width: 1440, height: 1000 },
		deviceScaleFactor: 1,
	});
	await context.addCookies(CONSENT);
	const page = await context.newPage();
	await page.goto(BASE + '/solution-configurator/', {
		waitUntil: 'networkidle',
	});
	await page.locator('.lp-tool-identity').waitFor({ timeout: 120_000 });
	await page.locator('.lp-tool-about summary').click();
	await page.waitForFunction(
		() => document.querySelector('.lp-tool-about')?.open === true,
		null,
		{ timeout: 20_000 }
	);
	await page.waitForTimeout(600);
	const before = await page.evaluate(READ);
	const name = 'en-desktop-list-system-about-framed';
	await page.locator('.lp-tool-identity').scrollIntoViewIfNeeded();
	await page.waitForTimeout(200);
	const shot = join(NATIVE, `${name}.png`);
	await page.locator('.lp-tool-identity').screenshot({ path: shot });
	const after = await page.evaluate(READ);
	writeFileSync(
		join(NATIVE, `${name}.json`),
		`${JSON.stringify({ before, after, captureBeyondViewport: false }, null, 1)}\n`
	);
	const [pngWidth, pngHeight, bytes] = pngSize(shot);
	frames.push({ name, size: [1440, 1000], png: [pngWidth, pngHeight, bytes] });
	accepted.push({
		name,
		size: [1440, 1000],
		revision: before.revision,
		links: before.links.length,
		identity_fully_framed:
			before.details === true &&
			before.identityBox !== null &&
			before.overflow === 0 &&
			before.fonts === 'loaded' &&
			before.links.length === 10,
		link_labels: before.links.map((link) => link.label),
		overflow: before.overflow,
	});
	console.log(
		`${name}: revision=${JSON.stringify(before.revision)} links=${before.links.length} overflow=${before.overflow} png=${pngWidth}x${pngHeight}`
	);
	await context.close();
}

await browser.close();

const matrix = {
	accepted,
	frames,
	new_instances_created: 0,
	new_projects_created: 2,
	production_changed: false,
	png_dimensions: 'PNG IHDR read with node:fs; no image dependency installed',
};
writeFileSync(
	join(HERE, 'native-matrix.json'),
	`${JSON.stringify(matrix, null, 1)}\n`
);
console.log(JSON.stringify(matrix.accepted, null, 1));
