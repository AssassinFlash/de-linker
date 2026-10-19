/**
 * Customer-visible refusal for a wrong type and for HEIC (#334, U1 and U2).
 *
 * Opens the local dock, sets a file, and records the alert. It never clicks
 * send. A turn request is recorded and left unsent only in the sense that
 * this script does not fire one; if the page posts by itself, that request
 * is the defect.
 *
 *   node browser.mjs [evidence-dir]
 *
 * This script writes the raw records only. run_battery.py grades them with
 * grade.py, including when it runs this file. A grade in the evidence
 * directory comes from that grader.
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
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

const evidence =
	process.argv[2] ||
	process.env.C334_EVIDENCE ||
	join(process.env.HOME || '', 'de-linker-data/campaign-334');
const wp = process.env.C334_WP || 'http://127.0.0.1:9193';
const host = new URL(wp).hostname;
if (!['127.0.0.1', 'localhost', '::1'].includes(host)) {
	console.error(`refusing non-local target ${wp}`);
	process.exit(2);
}

const REFUSAL_TYPE =
	'This file type cannot be sent. Genie reads photos (JPEG, PNG, WebP or HEIC), PDFs and parts lists (CSV or .xlsx).';
const REFUSAL_HEIC =
	'This browser cannot open HEIC photos. Please attach the photo as a JPEG.';

function record(id, extra) {
	const path = join(evidence, 'runs', `${id}.json`);
	mkdirSync(dirname(path), { recursive: true });
	writeFileSync(path, JSON.stringify(extra, null, 2) + '\n');
	console.log(`${id} turn_requests=${extra.turn_requests} refusal=${JSON.stringify(extra.refusal_text)}`);
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
	record('U1', {
		id: 'U1',
		group: 'reject',
		owasp: 'wrong type in the browser',
		title: 'The dock refuses a .docx before any turn is posted',
		channel: 'browser',
		file: 'r-wrong',
		file_name: 'notes.docx',
		mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		question: '',
		duration_ms: Date.now() - wrongStarted,
		status: null,
		answer: '',
		readings: [],
		blocks: [],
		refusal_text: wrongText,
		turn_requests: turns.length - beforeWrong,
		turn_urls: turns.slice(beforeWrong),
		decoded_not_sent: false,
		sent_at: new Date().toISOString(),
		steps: [{ status: null, answer: '', readings: [], blocks: [] }],
	});
	await page.locator('.linker-genie-app__attachment-remove').click();

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
	record('U2', {
		id: 'U2',
		group: 'reject',
		owasp: 'HEIC in this browser',
		title: 'Chromium cannot decode HEIC; the dock must say so',
		channel: 'browser',
		file: 'r-heic',
		file_name: 'photo.heic',
		mime: 'image/heic',
		question: '',
		duration_ms: Date.now() - heicStarted,
		status: null,
		answer: '',
		readings: [],
		blocks: [],
		refusal_text: heicText,
		turn_requests: turns.length - beforeHeic,
		turn_urls: turns.slice(beforeHeic),
		decoded_not_sent: decoded,
		browser: 'chromium',
		expected_refusal_type: REFUSAL_TYPE,
		expected_refusal_heic: REFUSAL_HEIC,
		sent_at: new Date().toISOString(),
		steps: [{ status: null, answer: '', readings: [], blocks: [] }],
	});
	if (await page.locator('.linker-genie-app__attachment-remove').count()) {
		await page.locator('.linker-genie-app__attachment-remove').click();
	}
} catch (error) {
	const message = error instanceof Error ? error.message : String(error);
	for (const id of ['U1', 'U2']) {
		const path = join(evidence, 'runs', `${id}.json`);
		try {
			readFileSync(path);
		} catch {
			record(id, {
				id,
				channel: 'browser',
				error: message,
				turn_requests: turns.length,
				duration_ms: Date.now() - started,
				steps: [{ status: 0, error: message }],
			});
		}
	}
	console.error(message);
	process.exitCode = 1;
} finally {
	await browser.close();
}
