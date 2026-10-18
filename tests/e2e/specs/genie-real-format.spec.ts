/** Actual c223 replies: no response interception and no formatting in the question. */
import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT } from '../lib/instance';

for (const locale of ['en', 'de'] as const) {
	test(`${locale}: real multi-part guidance uses readable Markdown`, async ({
		page,
	}) => {
		test.setTimeout(240_000);
		const german = locale === 'de';
		const base = instance().url;
		const question = german
			? 'Welche Angaben brauchen Sie zur Auswahl eines Hybrid-Wechselrichters mit Batterie, wie vergleiche ich die Modelle auf dieser Seite und wie sende ich eine Anfrage?'
			: 'What information helps choose a hybrid inverter with a battery, how can I compare models on this page, and how do I send an inquiry?';
		const evidence = join(
			REPO_ROOT,
			'docs/acceptance/2026-10-18/223/replies-real'
		);
		mkdirSync(evidence, { recursive: true });
		let conversation = 0;
		let nonce = '';
		try {
			await page.setViewportSize({ width: 1440, height: 900 });
			await page.goto(base + (german ? '/de/produkte/' : '/products/'));
			await page.locator('.linker-genie-open').first().click();
			nonce =
				(await page
					.locator('[data-linker-app="genie"]')
					.getAttribute('data-rest-nonce')) ?? '';
			const response = page.waitForResponse(
				(r) =>
					r.url().endsWith('/wp-json/linker-ai/v1/genie/turn') &&
					r.request().method() === 'POST',
				{ timeout: 180_000 }
			);
			await page.locator('.linker-genie-app__input').fill(question);
			await page.locator('.linker-genie-app__send').click();
			const result = await response;
			expect(result.ok()).toBe(true);
			const payload = await result.json();
			conversation = payload.conversation_id;
			writeFileSync(
				join(evidence, `${locale}-received.json`),
				JSON.stringify({ question, stream: payload.stream }, null, 2) +
					'\n'
			);
			const body = page.locator('.linker-genie-message-body').last();
			await expect(body).toBeVisible();
			const full = page.getByRole('button', {
				name: german
					? 'Vollständige Antwort anzeigen'
					: 'Show full response',
			});
			if (await full.isVisible()) await full.click();
			await page.screenshot({
				path: join(evidence, `${locale}-1440-dock.png`),
			});
			// This observes generated output, not an instruction string or a hand-written Markdown fixture.
			expect(await body.locator('h2,h3').count()).toBeGreaterThan(0);
			expect(await body.locator('ul,ol').count()).toBeGreaterThan(0);
			const original = await body.textContent();
			for (const width of [390, 1440]) {
				await page.setViewportSize({ width, height: 900 });
				await page.screenshot({
					path: join(evidence, `${locale}-${width}-dock.png`),
				});
				await page
					.locator('.linker-genie-app__transcript')
					.evaluate((el) => {
						el.scrollTop = el.scrollHeight;
					});
				await page.screenshot({
					path: join(evidence, `${locale}-${width}-dock-latest.png`),
				});
				await page
					.locator('.linker-genie-app__transcript')
					.evaluate((el) => {
						el.scrollTop = 0;
					});
			}
			await page.goto(base + (german ? '/de/genie/' : '/genie/'));
			await expect(
				page.locator('.linker-genie-message-body').last()
			).toHaveText(original!);
			await expect(
				page.locator('.linker-genie-message-body h3').first()
			).toBeVisible();
			for (const width of [1440, 390]) {
				await page.setViewportSize({ width, height: 900 });
				const close = page
					.getByRole('button', {
						name: german
							? 'Seitenleiste schließen'
							: 'Close sidebar',
						exact: true,
					})
					.first();
				if (width === 390 && (await close.isVisible()))
					await close.click();
				await page.screenshot({
					path: join(evidence, `${locale}-${width}-workspace.png`),
				});
				await page
					.locator('.linker-genie-app__transcript')
					.evaluate((el) => {
						el.scrollTop = el.scrollHeight;
					});
				await page.screenshot({
					path: join(
						evidence,
						`${locale}-${width}-workspace-latest.png`
					),
				});
				await page
					.locator('.linker-genie-app__transcript')
					.evaluate((el) => {
						el.scrollTop = 0;
					});
			}
		} finally {
			if (conversation > 0) {
				const deleted = await page.request.delete(
					`${base}/wp-json/linker-ai/v1/genie/conversations/${conversation}`,
					{ headers: { 'X-WP-Nonce': nonce } }
				);
				expect(deleted.ok()).toBe(true);
			}
		}
	});
}
