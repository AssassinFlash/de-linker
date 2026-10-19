/**
 * The in-browser battery of campaign #331: reload/reopen, cross-device keys,
 * same-conversation concurrency from two tabs, and conversation-list
 * switching — against the local instance's real Genie, driving the same DOM
 * the e2e suite drives (tests/e2e/specs/genie-sessions.spec.ts's selectors
 * and ask()/titles() patterns, reused).
 *
 * A thrown expect still leaves a JSONL verdict: the row is written in
 * `finally`, and the catch marks the case defect before rethrowing. The
 * two-tab race does not expect its outcome, so the suite can finish and
 * the defect stays in the evidence.
 *
 * Run: LINKER_E2E_INSTANCE=c331 npx playwright test --config playwright.config.ts
 * (from this directory; evidence lands in ~/de-linker-data/campaign-331/).
 */

/**
 * External dependencies
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { expect, test, type Browser, type BrowserContext, type Page } from '@playwright/test';

/**
 * Internal dependencies.
 *
 * The suite's own helper (tests/e2e/lib/instance.ts) cannot be imported from
 * outside its package root under Playwright's loader, so the two pieces this
 * battery needs — the instance registry reader and WP-CLI through `just` —
 * are inlined here in the helper's own shape (parseRegistry, instance(), wp()).
 * Evidence goes through evidence.mjs so a header cannot skip redaction.
 */
import { record, selectedHeaders, verdict as verdictRow } from './evidence.mjs';
import {
	DOUBLE_SUBMIT_DWELL_MS,
	PROXY_SETTLE_MS,
	RACE_REREAD_MS,
	TURN_TIMEOUT_MS,
} from './timing.mjs';

// harness/ -> campaign-331 -> research -> docs -> repo root.
const REPO_ROOT = fileURLToPath(new URL('../../../../', import.meta.url));

interface InstanceRow {
	name: string;
	url: string;
	dir: string;
}

interface WireHit {
	finalUrl: string;
	status: number;
	headers: ReturnType<typeof selectedHeaders>;
}

function parseRegistry(text: string): Record<string, { port: number; genie_port: number }> {
	const rows: Record<string, { port: number; genie_port: number }> = {};
	let current = '';
	for (const line of text.split('\n')) {
		const table = /^\[([^\]]+)\]\s*$/.exec(line);
		if (table) {
			current = table[1] ?? '';
			rows[current] = { port: 0, genie_port: 0 };
			continue;
		}
		const value = /^(\w+)\s*=\s*(\d+)\s*$/.exec(line);
		const row = rows[current];
		if (!row || !value) {
			continue;
		}
		if (value[1] === 'port' || value[1] === 'genie_port') {
			row[value[1]] = Number(value[2]);
		}
	}
	return rows;
}

function instance(): InstanceRow {
	const name = process.env.LINKER_E2E_INSTANCE ?? 'c331';
	const registry = `${process.env.HOME}/de-linker-local/instances.toml`;
	if (!existsSync(registry)) {
		throw new Error(`${registry} does not exist`);
	}
	const row = parseRegistry(readFileSync(registry, 'utf8'))[name];
	if (!row || !row.port) {
		throw new Error(`${name} is not in ${registry}`);
	}
	return {
		name,
		url: `http://127.0.0.1:${row.port}`,
		dir: `${process.env.HOME}/de-linker-local/${name}`,
	};
}

/** WP-CLI against the instance, as the suite's wp() runs it. */
function wp(args: string[]): string {
	return execFileSync('just', ['wp', instance().name, ...args], {
		cwd: REPO_ROOT,
		encoding: 'utf8',
		maxBuffer: 64 * 1024 * 1024,
	});
}

const target = instance();
const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);

const WORKSPACE = { en: '/genie/', de: '/de/genie/' };
const CATEGORY = { en: '/product-category/inverters/', de: '/de/produkt-kategorie/wechselrichter/' };
const ACCOUNT = { en: '/my-account/', de: '/de/mein-konto/' };

/** Every /genie/ response: final URL and the same header selection as the probes. */
function watchGenie(context: BrowserContext, hits: WireHit[]): void {
	context.on('response', (response) => {
		const url = response.url();
		if (!url.includes('/genie/')) {
			return;
		}
		hits.push({
			finalUrl: url,
			status: response.status(),
			headers: selectedHeaders(response.headers()),
		});
	});
}

async function openContext(browser: Browser, hits: WireHit[]): Promise<BrowserContext> {
	const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	watchGenie(context, hits);
	return context;
}

async function closeAll(contexts: BrowserContext[]): Promise<void> {
	for (const context of contexts) {
		await context.close().catch(() => undefined);
	}
}

function writeVerdict(
	scenario: string,
	file: string,
	passed: boolean,
	notes: string,
	hits: WireHit[],
	criterion: string,
	extra: Record<string, unknown> = {}
): void {
	const last = hits.at(-1);
	record(
		scenario,
		file,
		verdictRow(file, passed, criterion, notes, {
			stamp,
			finalUrl: last?.finalUrl ?? null,
			headers: last?.headers ?? null,
			genieResponses: hits,
			...extra,
		})
	);
}

function thrown(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

/** Asks one question and returns once the answer has landed (votes count). */
async function ask(page: Page, question: string): Promise<string> {
	const votes = page.locator('.linker-genie-app__votes');
	const before = await votes.count();
	await page.fill('#linker-genie-input', question);
	await page.locator('.linker-genie-app__send').click();
	await expect
		.poll(async () => votes.count(), { timeout: TURN_TIMEOUT_MS })
		.toBeGreaterThan(before);
	return (await page.locator('.linker-genie-app__panel').innerText()).trim();
}

/** Starts asking and returns immediately, with the send already clicked. */
async function sendAndDetach(page: Page, question: string): Promise<void> {
	await page.fill('#linker-genie-input', question);
	await page.locator('.linker-genie-app__send').click();
}

/** The user messages on screen, in order. */
async function userMessages(page: Page): Promise<string[]> {
	return page
		.locator('.linker-genie-app__message--user')
		.allInnerTexts();
}

/** The rail's titles, top to bottom. */
async function titles(page: Page): Promise<string[]> {
	await expect(page.locator('.linker-genie-rail__item').first()).toBeVisible({
		timeout: 20_000,
	});
	return page.locator('.linker-genie-rail__item').allInnerTexts();
}

/** Opens the rail if it is closed (the workspace keeps it open ≥768px). */
async function openRail(page: Page, conversationsLabel: string): Promise<void> {
	const rail = page.locator('.linker-genie-rail');
	if (await rail.evaluate((n) => n.classList.contains('is-open'))) {
		return;
	}
	await page
		.locator('.linker-genie-app__rail-toggle')
		.filter({ hasText: conversationsLabel })
		.click();
	await expect(rail).toHaveClass(/is-open/);
}

/** New conversation, and the first question that names it. */
async function newConversation(
	page: Page,
	conversationsLabel: string,
	question: string
): Promise<void> {
	await openRail(page, conversationsLabel);
	await page.locator('.linker-genie-rail__new').click();
	await expect(page.locator('.linker-genie-app__message')).toHaveCount(0);
	await ask(page, question);
}

/** Signs in through the account page's own form (sessions spec's helper). */
async function signIn(
	page: Page,
	lang: 'en' | 'de',
	login: string,
	password: string
): Promise<void> {
	await page.goto(`${target.url}${ACCOUNT[lang]}`);
	await page.fill('#username', login);
	await page.fill('#password', password);
	await page.locator('button[name="login"]').click();
	await expect(page.locator('#username')).toHaveCount(0, { timeout: 30_000 });
}

test.describe('campaign #331 — conversation state in the browser', () => {
	test('s6-en: reload restores the thread, on the workspace and in the dock', async ({ browser }) => {
		test.setTimeout(600_000);
		const file = `s6-en-reload-${stamp}`;
		const scenario = 's6-reload';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const questions = [
			'Show me the SAJ H2-10K-T3.',
			'What batteries pair with it?',
		];
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, questions[0]);
			const panel = await ask(page, questions[1]);
			record(scenario, file, {
				type: 'turns',
				questions,
				answerHead: panel.slice(0, 300),
			});

			await page.reload();
			const afterReload = page.locator('.linker-genie-app__panel');
			await expect(afterReload).toContainText(questions[0], { timeout: 30_000 });
			await expect(afterReload).toContainText(questions[1]);
			record(scenario, file, {
				type: 'check',
				name: 'reload restores both turns',
				passed: true,
			});

			await page.goto(`${target.url}${CATEGORY.en}`);
			await page.locator('.linker-genie-open').first().click();
			await expect(page.locator('.linker-genie-app__panel')).toContainText(
				questions[0],
				{ timeout: 30_000 }
			);
			record(scenario, file, {
				type: 'check',
				name: 'the dock on another page reads the same thread',
				passed: true,
			});
			passed = true;
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'thread intact after reload and across surfaces (#235/#232)'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s6-en: a reload in the middle of a turn', async ({ browser }) => {
		test.setTimeout(600_000);
		const file = `s6-en-reload-mid-turn-${stamp}`;
		const scenario = 's6-reload';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const q1 = 'Which hybrid inverters do you carry for homes?';
		const q2 = 'Which home storage batteries do you carry?';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, q1);
			await sendAndDetach(page, q2);
			await page.reload();
			// The mount restore races the still-running server turn: what the
			// customer first sees may or may not include q2 yet.
			const early = await page
				.locator('.linker-genie-app__panel')
				.innerText({ timeout: 10_000 })
				.catch(() => '');
			const sawQ2Early = early.includes(q2);
			record(scenario, file, {
				type: 'observation',
				name: 'first view after mid-turn reload',
				sawQ2Early,
				earlyHead: early.slice(0, 200),
			});
			// The proxy finishes the turn server-side within its 60 s budget
			// (timing.mjs PROXY_SETTLE_MS).
			await page.waitForTimeout(PROXY_SETTLE_MS);
			await page.reload();
			const panel = page.locator('.linker-genie-app__panel');
			await expect(panel).toContainText(q1, { timeout: 30_000 });
			const late = await panel.innerText();
			const q2Present = late.includes(q2);
			// A restored thread renders its votes once (last stored turn); the
			// answer is judged by the assistant messages rendered.
			const answered =
				(await page.locator('.linker-genie-app__message--assistant').count()) >= 2;
			record(scenario, file, {
				type: 'check',
				name: 'after the turn completes, a second reload shows it',
				q2Present,
				answered,
			});
			passed = q2Present && answered;
			expect(q2Present, `thread after settle: ${late.slice(0, 400)}`).toBe(true);
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'the in-flight turn is recorded server-side and survives the reload (data); the first post-reload view can be one turn behind (noted as UI timing, not data loss)'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s6-en: closing the dock and opening it again keeps the thread', async ({ browser }) => {
		test.setTimeout(600_000);
		const file = `s6-en-dock-reopen-${stamp}`;
		const scenario = 's6-reload';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const q = 'Which EV chargers do you carry?';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			await page.goto(`${target.url}${CATEGORY.en}`);
			await page.locator('.linker-genie-open').first().click();
			await expect(page.locator('.linker-genie-app__composer')).toBeVisible({
				timeout: 30_000,
			});
			await ask(page, q);
			// Close (the open dock's head icon) and open it again.
			await page
				.locator('.linker-genie-app__bar-actions')
				.getByRole('button', { name: 'Close' })
				.click();
			await expect(page.locator('.linker-genie-app__panel')).toHaveCount(0);
			await page.locator('.linker-genie-open').first().click();
			await expect(page.locator('.linker-genie-app__panel')).toContainText(q, {
				timeout: 60_000,
			});
			passed = true;
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'dock close + reopen reads the same stored thread (#232/#235)'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s6-de: reload stellt den Faden wieder her', async ({ browser }) => {
		test.setTimeout(600_000);
		const file = `s6-de-reload-${stamp}`;
		const scenario = 's6-reload';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const q = 'Welche Hybridwechselrichter führen Sie für Wohngebäude?';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			await page.goto(`${target.url}${WORKSPACE.de}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, q);
			await page.reload();
			await expect(page.locator('.linker-genie-app__panel')).toContainText(q, {
				timeout: 30_000,
			});
			passed = true;
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'DE: Frage und Antwort sind nach dem Neuladen da'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s7-en: the guest key carries the history into a second browser', async ({ browser }) => {
		test.setTimeout(600_000);
		const file = `s7-en-guest-key-${stamp}`;
		const scenario = 's7-cross-device';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const q1 = 'Show me the SAJ H2-10K-T3.';
		let passed = false;
		let notes = '';
		try {
			const first = await openContext(browser, hits);
			contexts.push(first);
			const page = await first.newPage();
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, q1);
			const cookies = await first.cookies();
			record(scenario, file, {
				type: 'state',
				name: 'cookies carried',
				names: cookies.map((c) => c.name),
			});
			const second = await openContext(browser, hits);
			contexts.push(second);
			await second.addCookies(cookies);
			const other = await second.newPage();
			await other.goto(`${target.url}${WORKSPACE.en}`);
			await expect(other.locator('.linker-genie-app__panel')).toContainText(q1, {
				timeout: 30_000,
			});
			const list = await titles(other);
			record(scenario, file, {
				type: 'check',
				name: 'second browser with the same key reads the same thread and list',
				passed: list.length >= 1,
				list,
			});
			passed = list.length >= 1;
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'history follows the browser key, not the browser (spec 13 目标 7)'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s7-en: signing in claims the conversations for the account, on every device, and other guests see nothing', async ({ browser }) => {
		test.setTimeout(900_000);
		const file = `s7-en-login-claim-${stamp}`;
		const scenario = 's7-cross-device';
		const login = `c331-${stamp}-${Date.now()}`;
		const password = `Pw-${Date.now()}`;
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const questions = [
			'Show me the SAJ H2-10K-T3.',
			'Which EV chargers do you carry?',
		];
		let user = '';
		let passed = false;
		let notes = '';
		try {
			const guest = await openContext(browser, hits);
			contexts.push(guest);
			const otherDevice = await openContext(browser, hits);
			contexts.push(otherDevice);
			const stranger = await openContext(browser, hits);
			contexts.push(stranger);
			const page = await guest.newPage();
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, questions[0]);
			await newConversation(page, 'Conversations', questions[1]);

			user = wp(['user', 'create', login, `${login}@example.test`, '--role=customer', `--user_pass=${password}`, '--porcelain']).trim();
			await signIn(page, 'en', login, password);
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await openRail(page, 'Conversations');
			await expect
				.poll(() => titles(page))
				.toEqual([...questions].reverse());

			const other = await otherDevice.newPage();
			await signIn(other, 'en', login, password);
			await other.goto(`${target.url}${WORKSPACE.en}`);
			await openRail(other, 'Conversations');
			await expect
				.poll(() => titles(other))
				.toEqual([...questions].reverse());
			record(scenario, file, {
				type: 'check',
				name: 'the second device, signed in, lists both conversations',
				passed: true,
			});

			const noKey = await stranger.newPage();
			await noKey.goto(`${target.url}${WORKSPACE.en}`);
			await expect(noKey.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			const strangerList = await titles(noKey).catch(() => [] as string[]);
			const leak = strangerList.some((t) =>
				questions.some((q) => t.includes(q.slice(0, 20)))
			);
			record(scenario, file, {
				type: 'check',
				name: 'a guest without the key sees none of them',
				passed: !leak,
				strangerList,
			});
			expect(leak).toBe(false);
			passed = !leak;
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'claim on sign-in; cross-device through the account; no leak to keyless guests'
				);
			} finally {
				await closeAll(contexts);
				if (user) {
					wp([
						'eval',
						`foreach ( get_posts( array( 'post_type' => 'linker_conversation', 'post_status' => 'any', 'author' => ${Number(user)}, 'posts_per_page' => -1, 'fields' => 'ids' ) ) as $id ) { wp_delete_post( $id, true ); }`,
					]);
					wp(['user', 'delete', user, '--yes']);
				}
			}
		}
	});

	test('s8-en: two tabs, one conversation, two turns at once', async ({ browser }) => {
		test.setTimeout(900_000);
		const file = `s8-en-two-tabs-${stamp}`;
		const scenario = 's8-concurrency';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const q1 = 'Which hybrid inverters do you carry for homes?';
		const qa = 'Which EV chargers do you carry?';
		const qb = 'Which home storage batteries do you carry?';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page1 = await context.newPage();
			await page1.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page1.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page1, q1);

			const page2 = await context.newPage();
			await page2.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page2.locator('.linker-genie-app__panel')).toContainText(q1, {
				timeout: 30_000,
			});

			// Both tabs hold the same stored thread; each appends its own
			// question and sends at the same time.
			await Promise.all([
				(async () => {
					await page1.fill('#linker-genie-input', qa);
					await page1.locator('.linker-genie-app__send').click();
				})(),
				(async () => {
					await page2.fill('#linker-genie-input', qb);
					await page2.locator('.linker-genie-app__send').click();
				})(),
			]);
			await expect
				.poll(async () => page1.locator('.linker-genie-app__votes').count(), { timeout: TURN_TIMEOUT_MS })
				.toBeGreaterThanOrEqual(2);
			await expect
				.poll(async () => page2.locator('.linker-genie-app__votes').count(), { timeout: TURN_TIMEOUT_MS })
				.toBeGreaterThanOrEqual(2);
			const ownViews = {
				tab1: await page1.locator('.linker-genie-app__panel').innerText(),
				tab2: await page2.locator('.linker-genie-app__panel').innerText(),
			};
			record(scenario, file, {
				type: 'observation',
				name: 'each tab saw its own answer arrive',
				tab1SawOwn: ownViews.tab1.includes(qa),
				tab2SawOwn: ownViews.tab2.includes(qb),
				tab1SawOther: ownViews.tab1.includes(qb),
				tab2SawOther: ownViews.tab2.includes(qa),
			});

			// What the conversation actually kept: a fresh view of the same
			// conversation. The mount restore is one fetch; wait for content.
			const page3 = await context.newPage();
			await page3.goto(`${target.url}${WORKSPACE.en}`);
			const panel3 = page3.locator('.linker-genie-app__panel');
			await expect(panel3).toContainText(q1, { timeout: 60_000 });
			// One reread after the proxy can finish a write that landed during
			// navigation (timing.mjs RACE_REREAD_MS). The race itself is not
			// expected: a lost turn is a defect in the JSONL, and the suite
			// continues.
			await page3.waitForTimeout(RACE_REREAD_MS);
			await page3.reload();
			await expect(panel3).toContainText(q1, { timeout: 60_000 });
			const stored = await panel3.innerText();
			const keptA = stored.includes(qa);
			const keptB = stored.includes(qb);
			record(scenario, file, {
				type: 'check',
				name: 'the stored thread after the race',
				keptA,
				keptB,
				lost: [!keptA && qa, !keptB && qb].filter(Boolean),
				storedHead: stored.slice(0, 400),
			});
			passed = keptA && keptB;
			await page3.close();
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'both turns of the race survive in the conversation; a lost turn is the last-write-wins overwrite of dossier §1.16'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s8-en: a rapid double submit sends one turn', async ({ browser }) => {
		test.setTimeout(600_000);
		const file = `s8-en-double-submit-${stamp}`;
		const scenario = 's8-concurrency';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const q = 'Which EV chargers do you carry?';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, 'Which hybrid inverters do you carry for homes?');
			// A user's rapid double activation: type the question, press Enter,
			// and immediately type it again and press Enter while the first
			// turn is still in flight. The second send must be refused by the
			// in-flight guard (sending.current), not queued.
			await page.fill('#linker-genie-input', q);
			await page.focus('#linker-genie-input');
			await page.keyboard.press('Enter');
			await page.fill('#linker-genie-input', q);
			await page.focus('#linker-genie-input');
			await page.keyboard.press('Enter');
			await expect
				.poll(async () => page.locator('.linker-genie-app__votes').count(), { timeout: TURN_TIMEOUT_MS })
				.toBeGreaterThanOrEqual(2);
			// Let a wrongly queued second turn paint its user bubble, if the
			// guard accepted it (timing.mjs DOUBLE_SUBMIT_DWELL_MS).
			await page.waitForTimeout(DOUBLE_SUBMIT_DWELL_MS);
			const messages = await userMessages(page);
			const copies = messages.filter((m) => m.includes(q)).length;
			record(scenario, file, {
				type: 'check',
				name: 'exactly one copy of the question after a double submit',
				copies,
				messages,
			});
			passed = copies === 1;
			expect(copies).toBe(1);
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'the per-view single-flight guard holds (Race.test.tsx)'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s9-en: three conversations, switching always shows the right thread', async ({ browser }) => {
		test.setTimeout(900_000);
		const file = `s9-en-switch-abc-${stamp}`;
		const scenario = 's9-switching';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const qA1 = 'Show me the SAJ H2-10K-T3.';
		const qB1 = 'Which home storage batteries do you carry?';
		const qC1 = 'Which EV chargers do you carry?';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, qA1);
			await newConversation(page, 'Conversations', qB1);
			await newConversation(page, 'Conversations', qC1);
			await openRail(page, 'Conversations');
			await expect
				.poll(() => titles(page))
				.toEqual([qC1, qB1, qA1]);

			const switches: Array<[string, string]> = [
				[qA1, 'A'],
				[qB1, 'B'],
				[qC1, 'C'],
				[qA1, 'A again'],
			];
			let allRight = true;
			for (const [question, label] of switches) {
				await page
					.locator('.linker-genie-rail__item', { hasText: question })
					.click();
				// The switch is one lane job (select POST, then the thread
				// read); wait for the panel to show the switched-to thread.
				let shown = '';
				const waited = await expect
					.poll(
						async () => {
							shown = (await userMessages(page))[0] ?? '';
							return shown;
						},
						{ timeout: 60_000 }
					)
					.toContain(question.slice(0, 25))
					.then(() => true)
					.catch(() => false);
				const right = waited && shown.includes(question.slice(0, 25));
				allRight = allRight && right;
				record(scenario, file, {
					type: 'check',
					name: `switch to ${label} shows its own first message`,
					passed: right,
					shownHead: shown.slice(0, 60),
				});
			}

			// The follow-up must carry A's context (the inverter), not B's or C's.
			const answer = await ask(page, 'What batteries pair with it?');
			// The panel's text: A's history plus this turn. B/C's topics must
			// not appear (other than in the rail list, which is outside the
			// panel).
			const carriesA = !/wallbox|EV charger|home storage batteries do you carry/i.test(
				answer
			);
			const namesBatteries = /batter|Batterie/i.test(answer);
			record(scenario, file, {
				type: 'check',
				name: "follow-up in A resolves 'it' to A's inverter and answers batteries",
				passed: carriesA && namesBatteries,
				answerHead: answer.slice(0, 300),
			});
			passed = allRight && carriesA && namesBatteries;
			expect(passed).toBe(true);
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					"every switch shows the right thread; a follow-up after switching back carries that conversation's own context"
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s9-en: switching while a turn is in flight', async ({ browser }) => {
		test.setTimeout(900_000);
		const file = `s9-en-switch-mid-flight-${stamp}`;
		const scenario = 's9-switching';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const qA1 = 'Show me the SAJ H2-10K-T3.';
		const qA2 = 'What batteries pair with it?';
		const qB1 = 'Which EV chargers do you carry?';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			// Everything that crosses the wire, so a lost or misrouted turn is
			// attributed, not guessed.
			const wire: Array<Record<string, unknown>> = [];
			page.on('request', (request) => {
				if (request.url().includes('/genie/')) {
					let body: { messages?: Array<{ role: string; content: string }>; id?: number } = {};
					try {
						body = request.postDataJSON() ?? {};
					} catch {
						body = {};
					}
					wire.push({
						at: Date.now(),
						method: request.method(),
						path: request.url().replace(target.url, ''),
						id: body.id,
						last:
							body.messages?.filter((m) => m.role === 'user').at(-1)?.content?.slice(0, 40) ??
							null,
						messages: body.messages?.length ?? null,
					});
				}
			});
			page.on('response', (response) => {
				if (response.url().includes('/genie/conversations')) {
					void response
						.json()
						.then((json: { conversation_id?: number }) =>
							wire.push({
								at: Date.now(),
								method: 'RESPONSE',
								path: response.url().replace(target.url, ''),
								conversation_id: json.conversation_id,
							})
						)
						.catch(() => undefined);
				}
			});
			await page.goto(`${target.url}${WORKSPACE.en}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, qA1);
			await newConversation(page, 'Conversations', qB1);
			// Back to A, ask, and switch away before the answer can land.
			await page.locator('.linker-genie-rail__item', { hasText: qA1 }).click();
			await expect(page.locator('.linker-genie-app__panel')).toContainText(qA1);
			await sendAndDetach(page, qA2);
			await page.locator('.linker-genie-rail__item', { hasText: qB1 }).click();
			// The lane lets the in-flight ask finish on A, then applies the
			// switch; the view settles on B.
			await expect(page.locator('.linker-genie-app__panel')).toContainText(qB1, {
				timeout: 120_000,
			});
			const viewIsB = !((await page.locator('.linker-genie-app__panel').innerText()).includes(qA2));
			record(scenario, file, {
				type: 'observation',
				name: 'the view settles on B while A’s ask was in flight',
				viewIsB,
			});
			// And A kept the turn: switch back and read.
			await page.locator('.linker-genie-rail__item', { hasText: qA1 }).click();
			await expect(page.locator('.linker-genie-app__panel')).toContainText(qA1, {
				timeout: 120_000,
			});
			let aThread = '';
			await expect
				.poll(async () => {
					aThread = await page.locator('.linker-genie-app__panel').innerText();
					return aThread.includes(qA2);
				}, { timeout: TURN_TIMEOUT_MS })
				.toBe(true);
			// A restored thread renders votes only for the last stored turn, so
			// the answer is judged by its words, not the vote count.
			const answeredInA =
				aThread.includes(qA2) && /batter|Batterie/i.test(aThread);
			record(scenario, file, {
				type: 'check',
				name: 'the in-flight question landed in A, with its answer',
				passed: answeredInA,
				aThreadHead: aThread.slice(0, 300),
				wire,
			});
			passed = viewIsB && aThread.includes(qA2) && answeredInA;
			expect(passed).toBe(true);
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'the ask completes on the conversation it was asked in; the switch is applied after it; no lost or misrouted turn'
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});

	test('s9-de: Wechsel zwischen zwei Gesprächen zeigt jeweils den richtigen Faden', async ({ browser }) => {
		test.setTimeout(600_000);
		const file = `s9-de-switch-${stamp}`;
		const scenario = 's9-switching';
		const hits: WireHit[] = [];
		const contexts: BrowserContext[] = [];
		const qA = 'Zeigen Sie mir den SAJ H2-10K-T3.';
		const qB = 'Welche Wallboxen führen Sie?';
		let shownA = '';
		let shownB = '';
		let passed = false;
		let notes = '';
		try {
			const context = await openContext(browser, hits);
			contexts.push(context);
			const page = await context.newPage();
			await page.goto(`${target.url}${WORKSPACE.de}`);
			await expect(page.locator('#linker-genie-input')).toBeVisible({ timeout: 30_000 });
			await ask(page, qA);
			await newConversation(page, 'Gespräche', qB);
			await openRail(page, 'Gespräche');
			await page.locator('.linker-genie-rail__item', { hasText: qA }).click();
			await expect
				.poll(async () => {
					shownA = (await userMessages(page))[0] ?? '';
					return shownA;
				}, { timeout: 60_000 })
				.toContain('SAJ H2-10K-T3');
			await page.locator('.linker-genie-rail__item', { hasText: qB }).click();
			await expect
				.poll(async () => {
					shownB = (await userMessages(page))[0] ?? '';
					return shownB;
				}, { timeout: 60_000 })
				.toContain('Wallboxen');
			passed =
				shownA.includes('SAJ H2-10K-T3') && shownB.includes('Wallboxen');
			expect(passed).toBe(true);
		} catch (error: unknown) {
			passed = false;
			notes = thrown(error);
			throw error;
		} finally {
			try {
				writeVerdict(
					scenario,
					file,
					passed,
					notes,
					hits,
					'DE: jeder Wechsel zeigt den eigenen ersten Satz',
					{
						shownA: shownA.slice(0, 60),
						shownB: shownB.slice(0, 60),
					}
				);
			} finally {
				await closeAll(contexts);
			}
		}
	});
});
