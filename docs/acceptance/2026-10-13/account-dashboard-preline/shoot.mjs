/**
 * Capture the signed-in account pages of t110 (http://127.0.0.1:8975) for the
 * dashboard redesign review. One run logs in once per user (one-time link from
 * `just login t110 --user <login>`) and shoots every account page at 1440x900,
 * plus the overview at 390x844.
 *
 * Usage:
 *   node shoot.mjs --user dash-preline --prefix ours --out <dir>
 *   node shoot.mjs --user customer-3 --prefix ours-data --out <dir>
 *
 * The login link comes from `just login t110 --user <user>` run by this
 * script itself (it shells out to just). Run from anywhere; paths resolve
 * against this file.
 */
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const worktree = path.resolve(here, '../../../..');
// Playwright comes from the e2e suite's own node_modules (task constraint).
const { chromium } = createRequire(path.join(worktree, 'tests/e2e/package.json'))('playwright');
const base = 'http://127.0.0.1:8975';

const args = process.argv.slice(2);
const opt = (name, fallback) => {
	const i = args.indexOf(`--${name}`);
	return i >= 0 ? args[i + 1] : fallback;
};
const user = opt('user', 'dash-preline');
const prefix = opt('prefix', 'ours');
const outDir = opt('out', here);

// The account pages, URL path → screenshot name. The EN tree is the
// reference language; DE gets one overview shot to prove the locale renders.
const pages = [
	['/my-account/', 'overview'],
	['/my-account/inquiries/', 'inquiries'],
	['/my-account/saved-solutions/', 'saved-solutions'],
	['/my-account/documents/', 'documents'],
	['/my-account/company/billing/', 'company'],
	['/my-account/edit-account/', 'account-details'],
];

const login = execFileSync('just', ['login', 't110', `--user=${user}`], {
	cwd: worktree,
	encoding: 'utf8',
}).trim().split('\n').pop();

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
await page.goto(login, { waitUntil: 'domcontentloaded' });
await page.waitForURL(/my-account|\/$/);

for (const [url, name] of pages) {
	await page.goto(`${base}${url}`, { waitUntil: 'networkidle' });
	await page.screenshot({ path: path.join(outDir, `${prefix}-${name}-1440.png`) });
	console.log(`${prefix}-${name}-1440.png`);
}

// First inquiry detail, when the list has rows (customer-3 has 49).
const firstRow = page.locator('.linker-account-row, .linker-account-card a[href*="inquiry"], .woocommerce-orders-table a[href*="view"]').first;
await page.goto(`${base}/my-account/inquiries/`, { waitUntil: 'networkidle' });
const detail = page.locator('a[href*="/inquiry/"]').first();
if ((await detail.count()) > 0) {
	await detail.click();
	await page.waitForLoadState('networkidle');
	await page.screenshot({ path: path.join(outDir, `${prefix}-inquiry-detail-1440.png`) });
	console.log(`${prefix}-inquiry-detail-1440.png`);
}

// Mobile pass: overview + inquiries at 390x844.
await page.setViewportSize({ width: 390, height: 844 });
for (const [url, name] of [['/my-account/', 'overview'], ['/my-account/inquiries/', 'inquiries'], ['/my-account/documents/', 'documents']]) {
	await page.goto(`${base}${url}`, { waitUntil: 'networkidle' });
	await page.screenshot({ path: path.join(outDir, `${prefix}-${name}-390.png`) });
	console.log(`${prefix}-${name}-390.png`);
}

await browser.close();
