/** Real library fragments: searchable documents, readable actions and keyboard continuation. */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { instance, REPO_ROOT } from '../lib/instance';

const output = join(
	REPO_ROOT,
	'tests/e2e/artifacts/library',
	new Date().toISOString().replaceAll(/[-:.]/g, '')
);
const evidence: Record<string, unknown>[] = [];
const navigationOutput = join(
	REPO_ROOT,
	'tests/e2e/artifacts/library-navigation',
	new Date().toISOString().replaceAll(/[-:.]/g, '')
);
const paths = { en: '/faq-download/', de: '/de/faq-dokumente/' };

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
				).toBeVisible();
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
			const separation = await root.evaluate((library) => {
				const help = library.querySelector('.linker-library-help')!;
				const ask = library.querySelector('[data-linker-genie-open]')!;
				return (
					ask.getBoundingClientRect().top -
					help.getBoundingClientRect().bottom
				);
			});
			expect(
				separation,
				'the contact line clears the Genie button'
			).toBeGreaterThanOrEqual(12);
			await root.locator('[data-library-tab="faq"]').click();
			await input.fill('AIO3');
			await expect(
				root.locator('#linker-library-result-count')
			).toHaveAttribute('aria-busy', 'false');
			await input.press('ArrowDown');
			await input.press('Enter');
			const summary = root
				.locator('#linker-library-answers-saj details[open] summary')
				.first();
			await expect(summary).toBeFocused();
			await expect
				.poll(async () => (await focusGeometry(page)).inReader)
				.toBe(true);
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

		test(`${locale} ${width}: native details, PDF and associated product links remain usable without JavaScript`, async ({
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
				const row = root.locator('li[data-t]').first();
				const download = row.locator('a').first();
				const title = await download.innerText();
				await expect(download).toHaveAttribute('href', /\.pdf$/i);
				await expect(row.locator('a').nth(1)).toHaveAttribute(
					'href',
					/\/(produkt|product)\//
				);
				await expect(row.locator('img')).toHaveCount(0);
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
					state: 'no-js-native-details-and-links',
					title,
					path: page.url(),
					source: 'server-rendered answer, PDF and product links',
				});
			} finally {
				await context.close();
			}
		});

		test(`${locale} ${width}: brand and document type refine model results without additional requests`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			const requests: string[] = [];
			page.on('request', (request) => {
				if (request.url().includes('/library-index'))
					requests.push(request.url());
			});
			await page.goto(`${instance().url}${paths[locale]}`);
			await dismissConsent(page);
			await page.locator('button[data-library-brand="saj"]').click();
			await page.locator('button[data-library-type="datasheet"]').click();
			expect(requests).toHaveLength(0);
			await page.locator('#linker-library-q').fill('SAJ');
			const rows = page.locator('[data-library-results] li[data-t]');
			await expect(rows.first()).toBeVisible();
			expect(
				await rows.evaluateAll((es) =>
					es.every(
						(e) =>
							e.getAttribute('data-t') === 'datasheet' &&
							e.getAttribute('data-library-brand') === 'saj'
					)
				)
			).toBe(true);
			await expect.poll(() => requests.length).toBe(1);
			expect(
				await rows
					.first()
					.locator('a')
					.first()
					.evaluate((a) => a.getBoundingClientRect().height)
			).toBeGreaterThanOrEqual(44);
			expect(
				await page.evaluate(
					() => document.documentElement.scrollWidth <= innerWidth
				)
			).toBe(true);
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
			expect(await products.count()).toBeGreaterThan(0);
			expect(await products.count()).toBeLessThan(200);
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
				page.locator('#linker-library-result-count')
			).toHaveAttribute('aria-busy', 'false');
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
			const cardId = await page
				.locator('[data-library-card][data-library-kind="answer"]')
				.filter({
					has: page.locator('[data-library-page="next"]:enabled'),
				})
				.first()
				.getAttribute('id');
			const card = page.locator(`#${cardId}`);
			await card.locator('[data-library-page="next"]').click();
			await expect(
				card
					.locator('[data-library-item]:not([hidden]) summary')
					.first()
			).toBeFocused();
			await expect
				.poll(async () => (await focusGeometry(page)).inReader)
				.toBe(true);
			await card.getByRole('button', { name: /^\d+$/ }).last().click();
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

for (const faq of ['/faq-download/', '/de/faq-dokumente/']) {
	test(`warranty contact includes the FAQ the visitor read: ${faq}`, async ({
		page,
	}) => {
		const source = new URL(faq, instance().url).href;
		await page.goto(source);
		const answer = page
			.locator('details.linker-library-qa')
			.filter({ has: page.locator('a[href*="intent=support"]') });
		await answer.locator('summary').click();
		await answer.getByRole('link').click();
		await expect(page.locator('select[name="intent"]')).toHaveValue(
			'support'
		);
		await expect(
			page.locator('.linker-contact-selection__summary a')
		).toHaveAttribute('href', source);
		const included = page.locator(
			'input[type="checkbox"][name="linker_contact_selection"]'
		);
		await expect(included).toBeChecked();
		expect(JSON.parse(await included.inputValue()).source).toBe(source);
	});
}
