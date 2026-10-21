/** Real library fragments: loaded search thumbnails, readable actions and keyboard continuation. */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { instance, REPO_ROOT } from '../lib/instance';

const output = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/full-site/library/local',
	new Date().toISOString().replaceAll(/[-:.]/g, '')
);
const evidence: Record<string, unknown>[] = [];
const paths = { en: '/faq-download/', de: '/de/faq-dokumente/' };
const thumbnail =
	'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="220"><rect width="160" height="220" fill="white"/><path d="M20 30h120M20 50h80M20 70h110" stroke="#0c7f73" stroke-width="8"/></svg>';

async function dismissConsent(page: Page) {
	const reject = page.getByRole('button', {
		name: /^(Reject all|Alle ablehnen)$/,
	});
	await expect(reject).toBeVisible({ timeout: 5000 });
	await reject.click();
	await expect(reject).toBeHidden();
}

async function focusGeometry(page: Page) {
	return page.evaluate(() => {
		const active = document.activeElement!;
		const rect = active.getBoundingClientRect();
		const stickyBottom = [
			'#lc-header',
			'.linker-library-tabbar',
			'.linker-library-chips',
		].reduce((bottom, selector) => {
			const node = document.querySelector(selector);
			return node && getComputedStyle(node).display !== 'none'
				? Math.max(bottom, node.getBoundingClientRect().bottom)
				: bottom;
		}, 0);
		return {
			rect: rect.toJSON(),
			stickyBottom,
			inReader: rect.top >= stickyBottom && rect.bottom <= innerHeight,
		};
	});
}

test.use({ reducedMotion: 'no-preference' });
test.describe.configure({ timeout: 45_000 });
test.afterEach(async ({ page }, info) => {
	mkdirSync(output, { recursive: true });
	if (info.status !== info.expectedStatus) {
		await page.screenshot({
			path: join(
				output,
				`failed-${info.title.replaceAll(/[^a-z0-9-]/gi, '-')}.png`
			),
		});
	}
	writeFileSync(
		join(output, 'summary.json'),
		JSON.stringify({ evidence }, null, 2)
	);
});

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: native details and real document thumbnails remain usable without JavaScript`, async ({
			browser,
		}) => {
			const context = await browser.newContext({
				javaScriptEnabled: false,
				viewport: { width, height: 1000 },
			});
			const page = await context.newPage();
			try {
				await page.goto(`${instance().url}${paths[locale]}`);
				const root = page.locator('#linker-faq-page');
				await expect(root).not.toHaveClass(/is-enhanced/);
				await expect(
					root.locator('[data-library-panel="faq"]')
				).toBeVisible();
				await expect(
					root.locator('[data-library-panel="documents"]')
				).toBeVisible();
				const question = root
					.locator('[data-library-kind="answer"] details')
					.first();
				await question.locator('summary').click();
				await expect(question).toHaveAttribute('open', '');
				await expect(
					question.locator('.linker-library-qa-product')
				).toBeVisible();
				const document = root.locator('.linker-library-doc').first();
				await document.evaluate((e) =>
					e.scrollIntoView({ block: 'center', behavior: 'instant' })
				);
				const image = document.locator('.linker-library-thumb img');
				await expect(image).toBeVisible();
				await expect
					.poll(() =>
						image.evaluate(
							(e) => (e as HTMLImageElement).naturalWidth
						)
					)
					.toBeGreaterThan(0);
				await expect(image).toHaveCSS('opacity', '1');
				const title = await document
					.locator('.linker-library-doc-title')
					.innerText();
				await expect(
					document.locator('.linker-library-dl')
				).toHaveAccessibleName(
					new RegExp(title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
				);
				mkdirSync(output, { recursive: true });
				await page.screenshot({
					path: join(
						output,
						`${locale}-${width}-no-js-native-documents.png`
					),
				});
				evidence.push({
					locale,
					width,
					state: 'no-js-native-details-and-real-thumbnail',
					title,
					path: page.url(),
					source: 'native library fragments and real thumbnail bytes; no network intercept',
				});
			} finally {
				await context.close();
			}
		});

		test(`${locale} ${width}: search clone loads after the source and file actions stay readable`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 1000 });
			let release!: () => void;
			const held = new Promise<void>((resolve) => {
				release = resolve;
			});
			await page.route('**/faq-thumbs/**', async (route) => {
				await held;
				await route.fulfill({
					contentType: 'image/svg+xml',
					body: thumbnail,
				});
			});
			try {
				await page.goto(
					`${instance().url}${paths[locale]}?tab=documents`,
					{ waitUntil: 'domcontentloaded' }
				);
				await dismissConsent(page);
				const input = page.locator('#linker-library-q');
				await input.fill('AIO3');
				await input.press('Escape');
				const rows = page.locator(
					'[data-library-results] .linker-library-doc'
				);
				await expect(rows).toHaveCount(3);
				const images = rows.locator('img');
				await expect(images).toHaveCount(3);
				// All result clones exist before any image response is delivered.
				expect(
					await images.evaluateAll((es) =>
						es.every((e) => !(e as HTMLImageElement).naturalWidth)
					)
				).toBe(true);
				release();
				for (const image of await images.all()) {
					await image.scrollIntoViewIfNeeded();
					await expect
						.poll(() =>
							image.evaluate(
								(e) => (e as HTMLImageElement).naturalWidth
							)
						)
						.toBeGreaterThan(0);
					await expect(image.locator('..')).toHaveClass(/has-img/);
					await expect
						.poll(() =>
							image.evaluate((e) => getComputedStyle(e).opacity)
						)
						.toBe('1');
				}
				for (const row of await rows.all()) {
					const title = await row
						.locator('.linker-library-doc-title')
						.innerText();
					const download = row.locator('.linker-library-dl');
					await expect(download).toHaveAccessibleName(
						new RegExp(title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
					);
					const geometry = await row.evaluate((e) => ({
						row: e.getBoundingClientRect().toJSON(),
						title: e
							.querySelector('.linker-library-doc-title')!
							.getBoundingClientRect()
							.toJSON(),
						action: e
							.querySelector('.linker-library-dl')!
							.getBoundingClientRect()
							.toJSON(),
					}));
					expect(geometry.action.height).toBeGreaterThanOrEqual(44);
					if (width === 390) {
						expect(geometry.title.width).toBeGreaterThan(180);
						expect(geometry.action.top).toBeGreaterThanOrEqual(
							geometry.title.bottom
						);
					}
					evidence.push({
						locale,
						width,
						state: 'search-document',
						title,
						geometry,
					});
				}
				await rows.first().evaluate((e) => {
					const bar = document.querySelector(
						'.linker-library-tabbar'
					)!;
					window.scrollTo({
						top:
							e.getBoundingClientRect().top +
							scrollY -
							bar.getBoundingClientRect().bottom -
							12,
						behavior: 'instant',
					});
				});
				await page.screenshot({
					path: join(
						output,
						`${locale}-${width}-loaded-documents.png`
					),
				});
				expect(
					await page.evaluate(
						() => document.documentElement.scrollWidth <= innerWidth
					)
				).toBe(true);
			} finally {
				release();
			}
		});

		test(`${locale} ${width}: identified FAQ, keyboard result selection and paging preserve a useful focus`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 1000 });
			await page.emulateMedia({ reducedMotion: 'reduce' });
			await page.goto(`${instance().url}${paths[locale]}`);
			await dismissConsent(page);
			const products = page.locator(
				'[data-library-kind="answer"] summary .linker-library-qa-product'
			);
			expect(await products.count()).toBeGreaterThan(200);
			expect(
				(await products.allTextContents()).every(
					(text) => text.trim().length > 0
				)
			).toBe(true);
			await expect(
				page.locator(
					'[data-library-kind="trade"] .linker-library-qa-product'
				)
			).toHaveCount(0);
			const input = page.locator('#linker-library-q');
			await input.fill('AIO3');
			await expect(
				page.locator('#linker-library-sug-0 .linker-library-sug-meta')
			).toContainText('AIO3');
			await input.press('ArrowDown');
			await input.press('Enter');
			const answer = page
				.locator('[data-library-kind="answer"] details[open]')
				.filter({ hasText: 'AIO3' })
				.first();
			await expect(answer.locator('summary')).toBeFocused();
			await expect
				.poll(async () => (await focusGeometry(page)).inReader)
				.toBe(true);
			await page.keyboard.press('Tab');
			await expect(
				answer.locator('.linker-library-qa-source a').first()
			).toBeFocused();
			await expect
				.poll(async () => (await focusGeometry(page)).inReader)
				.toBe(true);
			const card = page.locator('#linker-library-answers-ecoflow');
			await card.locator('[data-library-page="next"]').click();
			await expect(
				card
					.locator('[data-library-item]:not([hidden]) summary')
					.first()
			).toBeFocused();
			await expect
				.poll(async () => (await focusGeometry(page)).inReader)
				.toBe(true);
			await expect(
				card.locator('[data-library-page="next"]')
			).toBeDisabled();
			await expect(
				card.locator('[data-library-page="prev"]')
			).toBeEnabled();
			await page.screenshot({
				path: join(output, `${locale}-${width}-identified-faq.png`),
			});
			evidence.push({
				locale,
				width,
				state: 'faq-keyboard-pager',
				productCount: await products.count(),
				path: page.url(),
				focus: await focusGeometry(page),
			});
		});
	}
}
