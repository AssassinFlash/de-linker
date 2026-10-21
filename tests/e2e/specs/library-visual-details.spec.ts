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
const navigationOutput = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/full-site/marketing-library-online/navigation-local',
	new Date().toISOString().replaceAll(/[-:.]/g, '')
);
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

/** Capture the uncorrected reader position before assertions or diagnostics. */
async function captureNavigation(page: Page, name: string) {
	const geometry = await page.evaluate(() => {
		const root = document.querySelector('#linker-faq-page')!;
		const host = root.querySelector<HTMLElement>('[data-library-results]');
		const first = host?.querySelector('.linker-library-doc');
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
			url: location.href,
			scrollY,
			width: innerWidth,
			height: innerHeight,
			stickyBottom,
			selected: root
				.querySelector('[data-library-tab][aria-selected="true"]')
				?.getAttribute('data-library-tab'),
			query: root.querySelector<HTMLInputElement>('.linker-library-q')
				?.value,
			first: first?.getBoundingClientRect().toJSON() ?? null,
			results: host?.getBoundingClientRect().toJSON() ?? null,
			active: Array.from(
				root.querySelectorAll('[data-library-spy-link].is-active')
			).map((link) => ({
				href: link.getAttribute('href'),
				current: link.getAttribute('aria-current'),
				hidden: !!link.closest('[hidden]'),
			})),
			focus: {
				id: document.activeElement?.id,
				tag: document.activeElement?.tagName,
			},
		};
	});
	mkdirSync(navigationOutput, { recursive: true });
	writeFileSync(
		join(navigationOutput, `${name}.json`),
		JSON.stringify(geometry, null, 2)
	);
	await page.screenshot({ path: join(navigationOutput, `${name}.png`) });
	evidence.push({ state: name, ...geometry });
	return geometry;
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
		test(`${locale} ${width}: native early anchor and hash history keep the intended tab`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 1000 });
			await page.emulateMedia({ reducedMotion: 'reduce' });
			// Establish only the native consent choice before holding the deferred
			// Library script; no page DOM or Library state is substituted.
			await page.goto(`${instance().url}${paths[locale]}`);
			await dismissConsent(page);
			let release!: () => void;
			let intercepted = false;
			const held = new Promise<void>((resolve) => {
				release = resolve;
			});
			await page.route('**/library-ui.js*', async (route) => {
				intercepted = true;
				await held;
				await route.continue();
			});
			try {
				await page.goto(`${instance().url}${paths[locale]}`, {
					waitUntil: 'commit',
				});
				const root = page.locator('#linker-faq-page');
				await expect.poll(() => intercepted).toBe(true);
				await expect(root).not.toHaveClass(/is-enhanced/);
				await root.locator('#linker-library-tab-documents').click();
				await expect(page).toHaveURL(
					/#linker-library-panel-documents$/
				);
				await captureNavigation(
					page,
					`${locale}-${width}-native-early-documents`
				);
				release();
				await expect(root).toHaveClass(/is-enhanced/);
				await expect(
					root.locator('#linker-library-tab-documents')
				).toHaveAttribute('aria-selected', 'true');
				await expect(
					root.locator('[data-library-panel="documents"]')
				).toBeVisible();
				await expect(
					root.locator('[data-library-panel="faq"]')
				).toBeHidden();
				await expect(page).toHaveURL(
					/#linker-library-panel-documents$/
				);
				const input = root.locator('#linker-library-q');
				await input.fill('AIO3');
				await input.press('Escape');
				await expect(
					root.locator('[data-library-results] .linker-library-doc')
				).toHaveCount(3);
				await page.evaluate(() => {
					location.hash = '#linker-library-panel-faq';
				});
				await expect(
					root.locator('#linker-library-tab-faq')
				).toHaveAttribute('aria-selected', 'true');
				await input.fill('AIO3');
				await page.goBack();
				await expect(
					root.locator('#linker-library-tab-documents')
				).toHaveAttribute('aria-selected', 'true');
				await expect(input).toHaveValue('AIO3');
				await page.goForward();
				await expect(
					root.locator('#linker-library-tab-faq')
				).toHaveAttribute('aria-selected', 'true');
				await expect(input).toHaveValue('AIO3');
				await captureNavigation(
					page,
					`${locale}-${width}-hash-forward-preserved-query`
				);
			} finally {
				release();
				await page.unroute('**/library-ui.js*');
			}
		});

		test(`${locale} ${width}: visible FAQ brand and deep filtered tab switch preserve the reader`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 1000 });
			await page.emulateMedia({ reducedMotion: 'reduce' });
			await page.goto(`${instance().url}${paths[locale]}`);
			await dismissConsent(page);
			const root = page.locator('#linker-faq-page');
			const input = root.locator('#linker-library-q');
			// A directory click must identify its destination immediately; a
			// reduced-motion jump may finish before the scroll-spy lock expires.
			const directory = root.locator(
				width === 1440
					? '.linker-library-rail [data-library-nav="faq"]'
					: '.linker-library-chips [data-library-nav="faq"]'
			);
			await directory
				.locator('a[href="#linker-library-answers-saj"]')
				.click();
			await expect(
				directory.locator('a[href="#linker-library-answers-saj"]')
			).toHaveAttribute('aria-current', 'location');
			await input.fill('AIO3');
			await input.press('ArrowDown');
			await input.press('Enter');
			const summary = root
				.locator('#linker-library-answers-saj details[open] summary')
				.first();
			await expect(summary).toBeFocused();
			await expect
				.poll(async () => (await focusGeometry(page)).inReader)
				.toBe(true);
			const navigation = root.locator(
				width === 1440
					? '.linker-library-rail [data-library-nav="faq"]'
					: '.linker-library-chips [data-library-nav="faq"]'
			);
			await expect(
				navigation.locator('a[href="#linker-library-answers-saj"]')
			).toHaveAttribute('aria-current', 'location');
			await expect(
				navigation.locator('a[href="#linker-library-answers-goodwe"]')
			).not.toHaveClass(/is-active/);
			await captureNavigation(
				page,
				`${locale}-${width}-saj-visible-brand`
			);
			await input.fill('AIO3');
			await input.press('Escape');
			const questions = root.locator(
				'[data-library-results] .linker-library-qa summary'
			);
			expect(await questions.count()).toBeGreaterThan(3);
			await questions.last().scrollIntoViewIfNeeded();
			const before = await captureNavigation(
				page,
				`${locale}-${width}-deep-faq-before-tab`
			);
			expect(before.scrollY).toBeGreaterThan(500);
			await root.locator('#linker-library-tab-documents').click();
			await expect(
				root.locator('[data-library-results] .linker-library-doc')
			).toHaveCount(3);
			// Do not focus/scroll a result to make this pass: observe the actual
			// tab transition before any optional diagnostic reader movement.
			const after = await captureNavigation(
				page,
				`${locale}-${width}-deep-documents-after-tab`
			);
			expect(after.query).toBe('AIO3');
			expect(after.selected).toBe('documents');
			expect(after.first).not.toBeNull();
			expect(after.first!.top).toBeGreaterThanOrEqual(after.stickyBottom);
			expect(after.first!.bottom).toBeLessThanOrEqual(after.height);
			await expect(
				root.locator('#linker-library-tab-documents')
			).toBeFocused();
		});

		test(`${locale} ${width}: refining a visible search does not pull the reader or move focus`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 1000 });
			await page.emulateMedia({ reducedMotion: 'reduce' });
			await page.goto(`${instance().url}${paths[locale]}?tab=documents`);
			await dismissConsent(page);
			const input = page.locator('#linker-library-q');
			await input.fill('AIO');
			await input.press('Escape');
			const before = await page.evaluate(() => scrollY);
			await input.press('3');
			await input.press('Escape');
			await expect(input).toBeFocused();
			await expect(input).toHaveValue('AIO3');
			const after = await captureNavigation(
				page,
				`${locale}-${width}-visible-query-no-scroll`
			);
			expect(Math.abs(after.scrollY - before)).toBeLessThanOrEqual(1);
		});

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
