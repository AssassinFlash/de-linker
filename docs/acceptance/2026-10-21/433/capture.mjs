/**
 * One failure state, one viewport, one language (#433).
 *
 * The turn goes through the real dock and the real turn route. The fault is
 * outside this script: capture.py points the instance at the campaign #332
 * cut proxy (SSE-CUT), stops Genie before the turn (VPS-DOWN), or kills it
 * while the turn is in flight (VPS-KILL). Nothing here mocks a response.
 *
 * A live shot is taken only after the failure sentence is visible. With
 * `--shots live,reload`, the page is reloaded afterwards and the same
 * sentence must come back from the failure record (#411). Both states are
 * recorded in `runs/<name>-<width>-<lang>.json` next to the images.
 *
 *   node capture.mjs --wp URL --path /de/ --width 390 --height 844 \
 *     --lang de --name sse-cut --out DIR --shots live,reload \
 *     [--hook FILE] [--live-done FILE] [--resume FILE]
 *
 * `--hook` is written when the turn request starts (capture.py kills Genie
 * three seconds later). `--live-done` is written after the live screenshot.
 * `--resume` is waited on before the reload, so the service is healthy again
 * when the reload reads the thread.
 */
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

const COPY = {
	en: {
		failure: 'Genie did not answer. Please try again.',
		retry: 'Try again',
		// `stock` is the #332 question and is answered by the service alone
		// (simple stock status). `doc` and `model` take the model; the
		// document and recommendation turns measured 12-21s here, past the
		// 3s kill plus the 8s SIGTERM grace, so VPS-KILL lands inside the turn.
		stock: 'Do you stock the SAJ H2-10K-T2?',
		doc: 'What is the maximum PV input power of the SAJ H2-10K-T2? Use the datasheet.',
		model: 'Which three-phase hybrid inverters do you list for a home?',
	},
	de: {
		failure: 'Genie hat nicht geantwortet. Bitte versuchen Sie es erneut.',
		retry: 'Erneut versuchen',
		stock: 'Haben Sie den SAJ H2-10K-T2 auf Lager?',
		doc: 'Wie hoch ist die maximale PV-Eingangsleistung des SAJ H2-10K-T2? Nutzen Sie das Datenblatt.',
		model: 'Welche dreiphasigen Hybrid-Wechselrichter bieten Sie für ein Einfamilienhaus an?',
	},
};

function parseArgs(argv) {
	const out = {
		wp: 'http://127.0.0.1:9187',
		path: '/',
		width: 1440,
		height: 900,
		lang: 'en',
		name: 'state',
		questionKey: 'stock',
		shots: ['live', 'reload'],
		out: here,
		hook: '',
		liveDone: '',
		resume: '',
	};
	for (let i = 2; i < argv.length; i += 1) {
		const arg = argv[i];
		const value = argv[i + 1];
		switch (arg) {
			case '--wp':
				out.wp = value;
				i += 1;
				break;
			case '--path':
				out.path = value;
				i += 1;
				break;
			case '--width':
				out.width = Number(value);
				i += 1;
				break;
			case '--height':
				out.height = Number(value);
				i += 1;
				break;
			case '--lang':
				out.lang = value;
				i += 1;
				break;
			case '--question-key':
				out.questionKey = value;
				i += 1;
				break;
			case '--name':
				out.name = value;
				i += 1;
				break;
			case '--out':
				out.out = value;
				i += 1;
				break;
			case '--shots':
				out.shots = String(value)
					.split(',')
					.map((item) => item.trim())
					.filter(Boolean);
				i += 1;
				break;
			case '--hook':
				out.hook = value;
				i += 1;
				break;
			case '--live-done':
				out.liveDone = value;
				i += 1;
				break;
			case '--resume':
				out.resume = value;
				i += 1;
				break;
			default:
				throw new Error(`unknown argument ${arg}`);
		}
	}
	if (!COPY[out.lang]) {
		throw new Error(`no copy for language ${out.lang}`);
	}
	if (!COPY[out.lang][out.questionKey]) {
		throw new Error(`no question for key ${out.questionKey}`);
	}
	return out;
}

/** Playwright lives under tests/e2e; a worktree may borrow the main checkout's. */
function playwrightPackage() {
	const worktree = resolve(here, '../../../..');
	let mainRepo = worktree;
	try {
		const gitdir = readFileSync(join(worktree, '.git'), 'utf8').match(
			/gitdir:\s*(\S+)/
		)?.[1];
		if (gitdir) {
			mainRepo = dirname(dirname(dirname(gitdir)));
		}
	} catch {
		mainRepo = worktree;
	}
	for (const candidate of [
		join(worktree, 'tests/e2e/package.json'),
		join(mainRepo, 'tests/e2e/package.json'),
	]) {
		try {
			createRequire(candidate).resolve('playwright');
			return candidate;
		} catch {
			// Try the next checkout.
		}
	}
	throw new Error('playwright is not installed under tests/e2e');
}

/** The live site's cookie banner would cover the dock in every screenshot. */
async function dismissConsent(page) {
	const accept = page.locator('[data-cky-tag="accept-button"]');
	try {
		await accept.waitFor({ state: 'visible', timeout: 5000 });
		await accept.evaluate((button) => button.click());
		await page
			.locator('.cky-consent-container')
			.waitFor({ state: 'hidden', timeout: 5000 });
	} catch {
		// No banner, or its choice is already stored in this context.
	}
}

/** A stream's event names, without the model text. */
function streamEvents(body) {
	return [...body.matchAll(/^event: (.+)$/gm)].map((match) =>
		match[1].trim()
	);
}

/** What the turn route answered, in the shape the README cites. */
function turnRecord(response) {
	const record = { status: response.status, url: response.url };
	try {
		const body = response.body.toString('utf8');
		record.bytes = response.body.length;
		try {
			const parsed = JSON.parse(body);
			if (parsed && typeof parsed === 'object' && 'code' in parsed) {
				record.code = parsed.code;
				record.message = parsed.message;
			}
			if (parsed && typeof parsed === 'object' && 'stream' in parsed) {
				const stream = String(parsed.stream ?? '');
				record.stream_events = streamEvents(stream);
				record.stream_has_done = stream.includes('event: done');
			}
		} catch {
			record.stream_events = streamEvents(body);
			record.stream_has_done = body.includes('event: done');
		}
	} catch {
		// A response body can be gone when the request failed in transport.
	}
	return record;
}

/** Everything the screenshots must agree with, read from the page. */
async function observe(page, copy) {
	const alert = page
		.locator('.linker-genie-app__error[role="alert"]')
		.filter({ hasText: copy.failure })
		.first();
	const retry = page.getByRole('button', { name: copy.retry }).first();
	const dockField = page.locator(
		'#linker-genie-mount .linker-genie-app textarea'
	);
	const heroField = page.locator('.hero-prompt');
	const thread = page.locator('.linker-genie-app__thread').first();
	const dockApp = page.locator('#linker-genie-mount .linker-genie-app');
	const hero = page.locator('#linker-genie-hero-surface');
	let fieldValue = null;
	if (await dockField.isVisible().catch(() => false)) {
		fieldValue = await dockField.inputValue().catch(() => null);
	} else if (await heroField.isVisible().catch(() => false)) {
		fieldValue = await heroField.inputValue().catch(() => null);
	}
	const surface = await alert
		.evaluate((node) =>
			node.closest('#linker-genie-hero-surface')
				? 'hero'
				: node.closest('#linker-genie-mount')
					? 'dock'
					: 'other'
		)
		.catch(() => 'none');
	let box = null;
	if ('hero' === surface) {
		box = await hero.boundingBox().catch(() => null);
	} else if ('dock' === surface) {
		box = await dockApp.boundingBox().catch(() => null);
	}
	return {
		surface,
		error_text: (await alert.innerText()).trim(),
		error_visible: await alert.isVisible(),
		retry_visible: await retry.isVisible().catch(() => false),
		field_value: fieldValue,
		thread_text: (await thread.innerText().catch(() => '')).trim(),
		app_box: box,
		viewport: page.viewportSize(),
	};
}

async function waitForFile(path, timeoutMs, label) {
	if (!path) {
		return;
	}
	const started = Date.now();
	while (Date.now() - started < timeoutMs) {
		if (existsSync(path)) {
			return;
		}
		await new Promise((resolvePromise) => setTimeout(resolvePromise, 200));
	}
	throw new Error(`${label} file never appeared: ${path}`);
}

/**
 * The failure sentence, or a fast failure when the turn answered instead.
 * A VPS-KILL whose turn finishes during the 8s SIGTERM grace is a healthy
 * answer, not the state this run is for.
 */
async function waitForFailure(page, alert, answered, timeoutMs) {
	const started = Date.now();
	while (Date.now() - started < timeoutMs) {
		if (await alert.isVisible().catch(() => false)) {
			return;
		}
		if (answered()) {
			throw new Error(
				'the turn answered before the fault took effect (200 with done)'
			);
		}
		await new Promise((resolvePromise) => setTimeout(resolvePromise, 250));
	}
	throw new Error('the failure sentence never appeared');
}

function touch(path) {
	if (!path) {
		return;
	}
	writeFileSync(path, `${new Date().toISOString()}\n`);
}

async function main() {
	const options = parseArgs(process.argv);
	const copy = COPY[options.lang];
	const question = copy[options.questionKey];
	mkdirSync(options.out, { recursive: true });
	const runs = join(options.out, 'runs');
	mkdirSync(runs, { recursive: true });
	const { chromium } = createRequire(playwrightPackage())('playwright');

	const browser = await chromium.launch({ headless: true });
	const context = await browser.newContext({
		viewport: { width: options.width, height: options.height },
	});
	const page = await context.newPage();
	const turns = [];
	// A 200 whose stream has `done`: the turn answered instead of failing.
	let answered = false;
	page.on('response', (response) => {
		if (response.url().includes('/wp-json/linker-ai/v1/genie/turn')) {
			// The body is read on request completion; a stream is complete
			// once the response is, so this is not a race for the status.
			response
				.body()
				.then((body) => {
					const turn = turnRecord({
						status: response.status(),
						url: response.url(),
						body,
					});
					turns.push(turn);
					if (200 === turn.status && true === turn.stream_has_done) {
						answered = true;
					}
				})
				.catch(() => {
					turns.push({
						status: response.status(),
						url: response.url(),
					});
				});
		}
	});
	page.on('request', (request) => {
		if (
			request.method() === 'POST' &&
			request.url().includes('/wp-json/linker-ai/v1/genie/turn')
		) {
			touch(options.hook);
		}
	});

	const result = {
		id: options.name,
		url: options.wp + options.path,
		width: options.width,
		height: options.height,
		lang: options.lang,
		question,
		question_key: options.questionKey,
		failure_sentence: copy.failure,
		shots: {},
		live: null,
		reload: null,
		turns,
	};

	try {
		await page.goto(options.wp + options.path, {
			waitUntil: 'domcontentloaded',
			timeout: 60000,
		});
		await dismissConsent(page);
		await page.evaluate(() => document.fonts.ready);

		await page.evaluate(
			(message) =>
				window.dispatchEvent(
					new CustomEvent('linker-genie-ask', {
						detail: { message },
					})
				),
			question
		);

		const alert = page
			.locator('.linker-genie-app__error[role="alert"]')
			.filter({ hasText: copy.failure })
			.first();
		await waitForFailure(page, alert, () => answered, 120000);
		await page.waitForTimeout(500);
		result.live = await observe(page, copy);
		const liveShot = join(
			options.out,
			`${options.name}-live-${options.width}-${options.lang}.png`
		);
		await page.screenshot({ path: liveShot });
		result.shots.live = basename(liveShot);
		touch(options.liveDone);

		if (options.shots.includes('reload')) {
			await waitForFile(options.resume, 120000, 'resume');
			await page.reload({
				waitUntil: 'domcontentloaded',
				timeout: 60000,
			});
			await dismissConsent(page);
			await page.evaluate(() => document.fonts.ready);
			// The home hero boots with the stored thread; elsewhere the dock
			// opens from a visible opener. Either surface must show the
			// record, and the shot names the one that did.
			let opened = 'auto';
			if (!(await alert.isVisible().catch(() => false))) {
				const opener = page
					.locator('button.linker-genie-open')
					.filter({ visible: true })
					.first();
				if (await opener.isVisible().catch(() => false)) {
					await opener.click();
					opened = 'opener';
				}
			}
			await alert.waitFor({ state: 'visible', timeout: 30000 });
			await page.waitForTimeout(500);
			result.reload = { opened, ...(await observe(page, copy)) };
			const reloadShot = join(
				options.out,
				`${options.name}-reload-${options.width}-${options.lang}.png`
			);
			await page.screenshot({ path: reloadShot });
			result.shots.reload = basename(reloadShot);
		}
	} catch (error) {
		result.error = error instanceof Error ? error.message : String(error);
	} finally {
		await context.close();
		await browser.close();
	}

	const recordPath = join(
		runs,
		`${options.name}-${options.width}-${options.lang}.json`
	);
	writeFileSync(recordPath, JSON.stringify(result, null, 2) + '\n');
	console.log(recordPath);

	if (result.error) {
		console.error(
			`${options.name} ${options.width} ${options.lang}: ${result.error}`
		);
		process.exitCode = 1;
	}
}

await main();
