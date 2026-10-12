/**
 * Drives an instance's WindPress admin through the official compile — the
 * only compile that exists, since Tailwind v4 has no server-side build: a
 * one-time login, then WindPress admin → Settings → Performance → Generate.
 * The browser-side compiler stores the result through the WindPress REST
 * route admin/settings/cache/store, whose answer carries the cache index;
 * this script refuses to report success unless the stored cache is newer
 * than the mtime given on the command line.
 *
 * Usage: node tools/windpress-compile.mjs <one-time-login-url> [before-mtime]
 *
 * Playwright resolves from plugins/linker-tools/node_modules (the only
 * node_modules in the repo) via createRequire, and the full chromium build is
 * the browser it drives (channel 'chromium'; `just windpress-compile` installs
 * it when missing).
 */

import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const [loginUrl, beforeArg] = process.argv.slice(2);
if (!loginUrl) {
	console.error('usage: node tools/windpress-compile.mjs <one-time-login-url> [before-mtime]');
	process.exit(2);
}
const before = Number.parseInt(beforeArg ?? '0', 10) || 0;
const startedAt = Date.now();

const browser = await chromium.launch({ channel: 'chromium' });
try {
	const context = await browser.newContext();
	const page = await context.newPage();

	// The one-time login redirects into wp-admin.
	await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 60_000 });
	if ( ! page.url().includes('/wp-admin/') ) {
		throw new Error(`the login link did not reach wp-admin (at ${page.url()})`);
	}
	const origin = new URL(page.url()).origin;
	await page.goto(`${origin}/wp-admin/admin.php?page=windpress`, { waitUntil: 'domcontentloaded', timeout: 60_000 });

	// The dashboard app mounts into #windpress-app; its locators stay scoped
	// there, so WordPress's own admin menu can never match.
	const app = page.locator('#windpress-app');
	await app.getByRole('link', { name: 'Settings', exact: true }).first().waitFor({ state: 'visible', timeout: 90_000 });
	await app.getByRole('link', { name: 'Settings', exact: true }).first().click();
	await app.getByRole('link', { name: 'Performance', exact: true }).first().waitFor({ state: 'visible', timeout: 30_000 });
	await app.getByRole('link', { name: 'Performance', exact: true }).first().click();

	const generate = app.getByRole('button', { name: 'Generate', exact: true });
	await generate.waitFor({ state: 'visible', timeout: 30_000 });

	// WindPress parks a review-request prompt in a fixed bottom-right
	// notification viewport; it swallows the pointer events of everything it
	// covers (measured 2026-10-11: the Generate click never landed while the
	// prompt was up). Dismiss it by its own button; if it stays, take the
	// notification viewport out of the layer.
	for (const label of [ 'Never', 'Later', "OK, Let's do it!" ]) {
		const prompt = page.getByRole('button', { name: label, exact: true });
		if ( await prompt.count() > 0 && await prompt.first().isVisible().catch(() => false) ) {
			await prompt.first().click().catch(() => {});
			await page.waitForTimeout(500);
			break;
		}
	}
	await page.evaluate(() => {
		const region = document.querySelector('[role="region"][aria-label*="Notification"]');
		if ( region ) region.remove();
	});

	const stored = page.waitForResponse(
		(response) =>
			response.url().includes('/windpress/v1/admin/settings/cache/store') &&
			response.request().method() === 'POST',
		{ timeout: 300_000 }
	);
	// A real click is the recipe's intent; the notification viewport (the one
	// blocker that intercepted it) is out of the layer above.
	await generate.click().catch(async () => {
		// Some app builds only answer the DOM event; keep that path as fallback.
		await generate.dispatchEvent('click');
	});
	let response;
	try {
		response = await stored;
	} catch (error) {
		if (page.isClosed()) {
			throw new Error('the admin page closed before the cache was stored (the browser-side compile crashed)');
		}
		throw new Error(`no cache store within 300s of Generate — the compile never finished (${error.message.split('\n')[0]})`);
	}
	if ( ! response.ok() ) {
		throw new Error(`the cache store answered HTTP ${response.status()}: ${await response.text()}`);
	}
	const { cache } = await response.json();
	if ( ! cache || ! Number.isFinite( cache.last_generated ) || cache.last_generated <= before ) {
		throw new Error(`the stored cache is not newer than the previous one (before ${before}, stored ${cache ? cache.last_generated : 'none'})`);
	}

	let toast = false;
	try {
		await app.getByText('Cache generated', { exact: false }).first().waitFor({ state: 'visible', timeout: 15_000 });
		toast = true;
	} catch {
		// The toast is confirmation, not the gate: the store answer is.
	}

	console.log(
		JSON.stringify({
			compiled: true,
			last_generated: cache.last_generated,
			file_size: cache.file_size,
			toast,
			ms: Date.now() - startedAt,
		})
	);
} catch (error) {
	console.error(`windpress-compile failed: ${error instanceof Error ? error.message : error}`);
	process.exitCode = 1;
} finally {
	await browser.close();
}
