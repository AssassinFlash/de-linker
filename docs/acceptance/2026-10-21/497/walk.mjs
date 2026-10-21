/**
 * Ticket #497: the Roof detail step's role and the cost of skipping it.
 *
 * Real local Genie, guest, EN and DE at 1440×900 and 390×844. The two
 * acceptance questions are asked in the Genie workspace, the answer is
 * scrolled into view and captured. Each turn is asserted twice: in the DOM the
 * customer sees, and in the service's own turn log (`route`, blocks, provider,
 * model, tool calls).
 *
 * Instance: `just up w497`, `just pull load w497 latest`,
 * `just windpress-compile w497`, `just present w497`, `just serve w497`.
 * Origin: http://127.0.0.1:9264 (Genie on :9266).
 *
 * No mail, no inquiry, no registration, no account. The walk writes only its
 * own guest conversations in this instance's Genie log.
 *
 * Run: node walk.mjs
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
	process.env.LINKER_E2E_PACKAGE ||
		'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = join(here, 'shots');
mkdirSync(shotsDir, { recursive: true });

const INSTANCE = 'w497';
const ORIGIN = 'http://127.0.0.1:9264';
const GENIE_LOG = join(
	process.env.HOME,
	'de-linker-local',
	INSTANCE,
	'genie',
	'turns.sqlite'
);
const PAGES = { en: '/genie/', de: '/de/genie/' };
const LOCALES = { en: 'en-GB', de: 'de-DE' };
const VIEWPORTS = [
	{ name: '1440', width: 1440, height: 900 },
	{ name: '390', width: 390, height: 844 },
];
const QUESTIONS = {
	en: {
		role: 'What does the Roof detail step do?',
		skip: 'What happens if I skip the roof?',
	},
	de: {
		role: 'Was macht der Schritt Dachdetails?',
		skip: 'Was passiert, wenn ich das Dach weglasse?',
	},
};
const ANSWER = {
	en:
		"The Roof detail step adds the building's layout. It is optional and " +
		'maps the roof surface and module placement. Without a roof plane, ' +
		'the yield assumes 35° tilt facing south (HTW Berlin calculator default).',
	de:
		'Der Schritt Dachdetails nimmt die Dachfläche auf. Er ist optional und ' +
		'zeichnet die Lage der Module ein. Ohne Dachfläche nimmt der Ertrag ' +
		'35° Neigung nach Süden an (Vorgabe des HTW-Rechners).',
};
const ORIENTATION = {
	en:
		'Without a roof plane, the yield assumes 35° tilt facing south ' +
		'(HTW Berlin calculator default).',
	de:
		'Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an ' +
		'(Vorgabe des HTW-Rechners).',
};
const ACTION_URL = `${ORIGIN}/solution-configurator/`;
const CONSENT = /^(Reject all|Alle ablehnen)$/;

const record = {
	ticket: 497,
	kind: 'local Genie guest walkthrough',
	instance: INSTANCE,
	origin: ORIGIN,
	genie: 'http://127.0.0.1:9266',
	startedAt: new Date().toISOString(),
	startedDb: new Date().toISOString().slice(0, 19).replace('T', ' '),
	mailSent: false,
	accountUsed: false,
	cases: [],
	turnLog: [],
	assertions: {},
};

function parse(row) {
	const parsed = {};
	for (const key of ['output', 'understanding', 'tool_calls', 'failures']) {
		parsed[key] = JSON.parse(row[key]);
	}
	return { ...row, ...parsed };
}

async function screenshotView(page, shot) {
	const assistant = page.locator('.linker-genie-app__message--assistant').last();
	await assistant.scrollIntoViewIfNeeded();
	await page.waitForTimeout(250);
	await page.screenshot({ path: join(shotsDir, shot) });
	return assistant;
}

async function ask(browser, locale, viewport, kind) {
	const question = QUESTIONS[locale][kind];
	const shot = `roof-${kind}-${locale}-${viewport.name}.png`;
	const context = await browser.newContext({
		viewport: { width: viewport.width, height: viewport.height },
		locale: LOCALES[locale],
		reducedMotion: 'reduce',
	});
	const page = await context.newPage();
	await page.goto(`${ORIGIN}${PAGES[locale]}`, {
		waitUntil: 'domcontentloaded',
		timeout: 60_000,
	});
	const consent = page.getByRole('button', { name: CONSENT }).first();
	if (await consent.isVisible().catch(() => false)) {
		await consent.click();
	}
	await page.locator('#linker-genie-input').waitFor({
		state: 'visible',
		timeout: 60_000,
	});
	await page.fill('#linker-genie-input', question);
	await page.locator('.linker-genie-app__send').click();
	await page.locator('.linker-genie-app__action').waitFor({
		state: 'visible',
		timeout: 90_000,
	});
	const show = page.locator('.linker-genie-reply__show');
	if (await show.count()) {
		await show.click();
	}
	const assistant = await screenshotView(page, shot);
	const text = (
		await assistant
			.locator('[data-testid="reply-reveal"] .linker-genie-message-body')
			.last()
			.innerText()
	).trim();
	const href = await page
		.locator('.linker-genie-app__action')
		.last()
		.getAttribute('href');
	const counts = {
		cards: await page.locator('.linker-card').count(),
		handoff: await page.locator('.linker-genie-app__handoff').count(),
		ask: await page.locator('.linker-genie-app__ask').count(),
	};
	const html = await page.locator('html').getAttribute('lang');
	const title = await page.title();
	await context.close();
	const passed =
		text === ANSWER[locale] &&
		text.includes(ORIENTATION[locale]) &&
		href === ACTION_URL &&
		counts.cards === 0 &&
		counts.handoff === 0 &&
		counts.ask === 0;
	record.cases.push({
		locale,
		viewport: `${viewport.width}x${viewport.height}`,
		kind,
		question,
		answer: text,
		orientationExact: text.includes(ORIENTATION[locale]),
		answerExact: text === ANSWER[locale],
		action: { name: 'open_configurator', href },
		actionUrlExact: href === ACTION_URL,
		counts,
		htmlLang: html,
		title,
		screenshot: `shots/${shot}`,
		pass: passed,
	});
	if (!passed) {
		throw new Error(`case failed: ${locale} ${viewport.name} ${kind}`);
	}
	return passed;
}

function readTurnLog() {
	const rows = execFileSync(
		'sqlite3',
		[
			'-json',
			GENIE_LOG,
			`select * from turns where created_at >= '${record.startedDb}' order by id`,
		],
		{ encoding: 'utf8' }
	);
	const turns = rows.trim() ? JSON.parse(rows).map(parse) : [];
	const asked = new Set(
		Object.values(QUESTIONS).flatMap((item) => [item.role, item.skip])
	);
	for (const turn of turns) {
		if (!asked.has(turn.question ?? '')) {
			continue;
		}
		const locale = turn.locale === 'de' ? 'de' : 'en';
		const blocks = turn.output.blocks ?? [];
		const text = blocks
			.filter((block) => block.type === 'text')
			.map((block) => block.text)
			.join(' ');
		const actions = blocks.filter((block) => block.type === 'action');
		const sizeHint = turn.tool_calls.find(
			(call) => call.name === 'linker/size-hint'
		);
		const entry = {
			id: turn.id,
			question: turn.question,
			locale: turn.locale,
			answeredIn: turn.output.language,
			route: turn.understanding.route,
			provider: turn.provider,
			model: turn.model,
			grounded: turn.grounded,
			fallback: turn.fallback,
			failures: turn.failures,
			blocks: blocks.map((block) => block.type),
			answer: text,
			answerExact: text === ANSWER[locale],
			orientationExact: text.includes(ORIENTATION[locale]),
			action: actions.length === 1 ? actions[0] : null,
			sizeHint: sizeHint
				? { arguments: sizeHint.arguments, ok: sizeHint.ok }
				: null,
			pass:
				turn.understanding.route === 'roof' &&
				turn.provider === 'service' &&
				turn.model === 'none' &&
				turn.grounded === 1 &&
				turn.fallback === 0 &&
				turn.failures.length === 0 &&
				blocks.length === 2 &&
				blocks[0].type === 'text' &&
				blocks[1].type === 'action' &&
				blocks[1].name === 'open_configurator' &&
				blocks[1].args.url === ACTION_URL &&
				text === ANSWER[locale] &&
				Boolean(sizeHint) &&
				sizeHint.ok === true &&
				JSON.stringify(sizeHint.arguments) === '{}',
		};
		record.turnLog.push(entry);
	}
}

let snapshot = null;
try {
	const meta = JSON.parse(
		readFileSync(join(process.env.HOME, 'de-linker-local', INSTANCE, 'snapshot.json'), 'utf8')
	);
	snapshot = { name: meta.name ?? null, taken: meta.taken ?? null };
} catch {
	snapshot = null;
}
record.snapshot = snapshot;

const browser = await chromium.launch();
try {
	for (const locale of ['en', 'de']) {
		for (const viewport of VIEWPORTS) {
			for (const kind of ['role', 'skip']) {
				await ask(browser, locale, viewport, kind);
			}
		}
	}
} finally {
	await browser.close();
}

readTurnLog();
record.assertions = {
	cases: record.cases.length,
	casesPass: record.cases.every((item) => item.pass),
	turnLogRows: record.turnLog.length,
	turnLogPass: record.turnLog.every((item) => item.pass),
	noCards: record.cases.every((item) => item.counts.cards === 0),
	noHandoff: record.cases.every((item) => item.counts.handoff === 0),
	noAsk: record.cases.every((item) => item.counts.ask === 0),
	actionUrl: record.cases.every((item) => item.actionUrlExact),
	orientationExact: record.cases.every((item) => item.orientationExact),
	serviceWroteEveryTurn: record.turnLog.every(
		(item) => item.provider === 'service' && item.model === 'none'
	),
};
record.finishedAt = new Date().toISOString();
writeFileSync(
	join(here, 'record.json'),
	`${JSON.stringify(record, null, 2)}\n`
);
console.log(JSON.stringify(record.assertions, null, 2));
