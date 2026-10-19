/**
 * Customer-visible refusal for a wrong type and for HEIC (#334, U1 and U2).
 *
 * Opens the local dock, sets a file, and records the alert. It never clicks
 * send. A turn request is recorded and left unsent only in the sense that
 * this script does not fire one; if the page posts by itself, that request
 * is the defect.
 *
 *   node browser.mjs [evidence-dir] [--wp URL] [--only U1,U2]
 *
 * `--only` is the selection. A run asked for U1 does not rewrite U2. `--wp`
 * is the dock origin and must be loopback. This script writes the raw
 * records only. run_battery.py grades them with grade.py. A grade in the
 * evidence directory comes from that grader.
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

export function parseArgs(argv, env = process.env) {
	const home = env.HOME || '';
	let evidence = env.C334_EVIDENCE || join(home, 'de-linker-data/campaign-334');
	let wp = env.C334_WP || 'http://127.0.0.1:9193';
	const only = [];
	let sawEvidence = false;
	for (let i = 2; i < argv.length; i += 1) {
		const arg = argv[i];
		if (arg === '--wp') {
			const value = argv[i + 1];
			if (value) {
				wp = value;
				i += 1;
			}
			continue;
		}
		if (arg === '--only') {
			const value = argv[i + 1] || '';
			only.push(
				...value
					.split(',')
					.map((item) => item.trim())
					.filter(Boolean)
			);
			i += 1;
			continue;
		}
		if (!arg.startsWith('-') && !sawEvidence) {
			evidence = arg;
			sawEvidence = true;
		}
	}
	return { evidence, wp, only: only.length ? only : ['U1', 'U2'] };
}

function record(id, fields) {
	// The runner grades from cases.py and builds the row in `_run_record`.
	// This file only reports what the dock did.
	return { id, channel: 'browser', ...fields };
}

function writeRecord(evidence, id, extra) {
	const path = join(evidence, 'runs', `${id}.json`);
	mkdirSync(dirname(path), { recursive: true });
	writeFileSync(path, JSON.stringify(extra, null, 2) + '\n');
	console.log(
		`${id} turn_requests=${extra.turn_requests} refusal=${JSON.stringify(extra.refusal_text)}`
	);
}

function invokedDirectly() {
	const entry = process.argv[1];
	if (!entry) {
		return false;
	}
	try {
		return realpathSync(entry) === realpathSync(fileURLToPath(import.meta.url));
	} catch {
		return import.meta.url === pathToFileURL(resolve(entry)).href;
	}
}

async function main() {
	const parsed = parseArgs(process.argv);
	const { evidence, wp } = parsed;
	const only = new Set(parsed.only);
	const worktree = join(here, '../../../..');
	let mainRepo = worktree;
	try {
		const gitdir = readFileSync(join(worktree, '.git'), 'utf8').match(/gitdir:\s*(\S+)/)?.[1];
		if (gitdir) {
			mainRepo = dirname(dirname(dirname(gitdir)));
		}
	} catch {
		mainRepo = worktree;
	}
	const playwrightPkg = [
		join(here, '../../../../tests/e2e/package.json'),
		join(mainRepo, 'tests/e2e/package.json'),
	].find((path) => {
		try {
			createRequire(path).resolve('playwright');
			return true;
		} catch {
			return false;
		}
	});
	if (!playwrightPkg) {
		console.error('playwright is not installed under tests/e2e');
		process.exit(2);
	}
	const { chromium } = createRequire(playwrightPkg)('playwright');
	const host = new URL(wp).hostname;
	if (!['127.0.0.1', 'localhost', '::1'].includes(host)) {
		console.error(`refusing non-local target ${wp}`);
		process.exit(2);
	}

	const browser = await chromium.launch({ headless: true });
	const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
	const turns = [];
	page.on('request', (request) => {
		const url = request.url();
		if (url.includes('/genie/turn') || url.includes('/assistant/turn')) {
			turns.push({ method: request.method(), url });
		}
	});

	const shots = join(evidence, 'browser');
	mkdirSync(shots, { recursive: true });
	const started = Date.now();
	const written = new Set();
	try {
		await page.goto(wp + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
		await page.evaluate(() =>
			window.dispatchEvent(
				new CustomEvent('linker-genie-ask', { detail: { attach: true } })
			)
		);
		const picker = page.locator('.linker-genie-app input[type="file"]');
		await picker.waitFor({ state: 'attached', timeout: 30000 });
		await page.screenshot({ path: join(shots, 'dock.png') });

		if (only.has('U1')) {
			const beforeWrong = turns.length;
			const wrongStarted = Date.now();
			await picker.setInputFiles({
				name: 'notes.docx',
				mimeType:
					'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
				buffer: Buffer.from('not a photo'),
			});
			const wrongAlert = page.locator('.linker-genie-app__attachment-state[role="alert"]');
			await wrongAlert.waitFor({ state: 'visible', timeout: 10000 });
			const wrongText = (await wrongAlert.innerText()).trim();
			await page.screenshot({ path: join(shots, 'u1-wrong-type.png') });
			writeRecord(
				evidence,
				'U1',
				record('U1', {
					file_name: 'notes.docx',
					mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
					duration_ms: Date.now() - wrongStarted,
					refusal_text: wrongText,
					turn_requests: turns.length - beforeWrong,
					turn_urls: turns.slice(beforeWrong),
					decoded_not_sent: false,
				})
			);
			written.add('U1');
			await page.locator('.linker-genie-app__attachment-remove').click();
		}

		if (only.has('U2')) {
			const heicPath = join(evidence, 'corpus', 'r-heic.heic');
			const heic = readFileSync(heicPath);
			const beforeHeic = turns.length;
			const heicStarted = Date.now();
			await picker.setInputFiles({
				name: 'photo.heic',
				mimeType: 'image/heic',
				buffer: heic,
			});
			const heicAlert = page.locator('.linker-genie-app__attachment-state[role="alert"]');
			const heicName = page.locator('.linker-genie-app__attachment-name');
			await Promise.race([
				heicAlert.waitFor({ state: 'visible', timeout: 10000 }),
				heicName.waitFor({ state: 'visible', timeout: 10000 }),
			]);
			// A decoded photo stays on the chip. Do not click send.
			const refused = await heicAlert.isVisible().catch(() => false);
			const heicText = refused ? (await heicAlert.innerText()).trim() : null;
			const decoded = !refused;
			await page.screenshot({ path: join(shots, 'u2-heic.png') });
			const send = page.locator('.linker-genie-app__send');
			if (await send.isEnabled().catch(() => false)) {
				// Enabled means a file is ready. Leave it. Removing it proves we did not send.
			}
			writeRecord(
				evidence,
				'U2',
				record('U2', {
					file_name: 'photo.heic',
					mime: 'image/heic',
					duration_ms: Date.now() - heicStarted,
					refusal_text: heicText,
					turn_requests: turns.length - beforeHeic,
					turn_urls: turns.slice(beforeHeic),
					decoded_not_sent: decoded,
					browser: 'chromium',
				})
			);
			written.add('U2');
			if (await page.locator('.linker-genie-app__attachment-remove').count()) {
				await page.locator('.linker-genie-app__attachment-remove').click();
			}
		}
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		for (const id of parsed.only) {
			if (written.has(id)) {
				continue;
			}
			writeRecord(
				evidence,
				id,
				record(id, {
					error: message,
					turn_requests: turns.length,
					duration_ms: Date.now() - started,
				})
			);
		}
		console.error(message);
		process.exitCode = 1;
	} finally {
		await browser.close();
	}
}

if (invokedDirectly()) {
	await main();
}
