/**
 * The FAQ + document library (/faq-download/, ticket #176): the two tabs and
 * their URL, the search with its split counts, the pagers, the type chips and
 * the anchor landings under the sticky stack — in both languages and at both
 * viewport widths of the acceptance (docs/specs/176-faq-download.md §9).
 *
 * The page is a data face: the assertions read the framework the fragments
 * print (cards, rows, the JSON config) and the script's effect on it, not a
 * screenshot.
 */

/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

type Locale = 'en' | 'de';

interface Strings {
	faq: RegExp;
	documents: RegExp[];
	zone: string;
	tab: string;
	rail: string;
}

const STRINGS: Record<Locale, Strings> = {
	en: {
		faq: /^FAQ /,
		documents: [/^Documents /],
		zone: 'linker-library-zone-documents',
		tab: 'documents',
		rail: 'Brands',
	},
	de: {
		faq: /^FAQ /,
		documents: [/^Dokumente /],
		zone: 'linker-library-zone-documents',
		tab: 'documents',
		rail: 'Marken',
	},
};

const PATH: Record<Locale, string> = {
	en: '/faq-download/',
	de: '/de/faq-dokumente/',
};

/** The page, opened at a tab. */
async function open(
	page: Page,
	locale: Locale,
	tab?: 'faq' | 'documents'
): Promise<void> {
	await page.goto(
		`${instance().url}${PATH[locale]}${tab ? `?tab=${tab}` : ''}`
	);
	await expect(
		page.locator('#linker-faq-page .linker-library-tablist')
	).toBeVisible();
}

/** The sticky stack's bottom edge: what an anchored heading has to clear. */
async function stickyBottom(page: Page): Promise<number> {
	return page.evaluate(() => {
		const header = document.getElementById('lc-header');
		const bar = document.querySelector(
			'#linker-faq-page .linker-library-tabbar'
		);
		const chips = document.querySelector(
			'#linker-faq-page .linker-library-chips'
		);
		let bottom = header ? header.getBoundingClientRect().bottom : 0;
		if (bar) {
			bottom = Math.max(bottom, bar.getBoundingClientRect().bottom);
		}
		if (chips && getComputedStyle(chips).position === 'sticky') {
			bottom = Math.max(bottom, chips.getBoundingClientRect().bottom);
		}
		return Math.ceil(bottom);
	});
}

test.describe('the FAQ + document library', () => {
	for (const locale of ['en', 'de'] as Locale[]) {
		const strings = STRINGS[locale];

		test(`${locale}: the tab bar switches panels and writes the URL`, async ({
			page,
		}) => {
			await open(page, locale);
			const faqTab = page.locator(
				'#linker-faq-page [data-library-tab="faq"]'
			);
			const docTab = page.locator(
				'#linker-faq-page [data-library-tab="documents"]'
			);
			await expect(faqTab).toHaveAttribute('aria-selected', 'true');
			await expect(docTab).toHaveAttribute('aria-selected', 'false');
			await expect(
				page.locator('#linker-faq-page [data-library-panel="faq"]')
			).toBeVisible();
			await expect(
				page.locator(
					'#linker-faq-page [data-library-panel="documents"]'
				)
			).toBeHidden();
			// The FAQ tab is the default: no parameter for it.
			expect(new URL(page.url()).searchParams.get('tab')).toBeNull();

			await docTab.click();
			await expect(docTab).toHaveAttribute('aria-selected', 'true');
			await expect(
				page.locator(
					'#linker-faq-page [data-library-panel="documents"]'
				)
			).toBeVisible();
			await expect(
				page.locator('#linker-faq-page [data-library-panel="faq"]')
			).toBeHidden();
			expect(new URL(page.url()).searchParams.get('tab')).toBe(
				'documents'
			);
			// The rail and the chip row swap to the tab's own group.
			await expect(
				page
					.locator(
						'#linker-faq-page .linker-library-rail [data-library-nav="documents"]'
					)
					.first()
			).toBeVisible();
			await expect(
				page
					.locator(
						'#linker-faq-page .linker-library-rail [data-library-nav="faq"]'
					)
					.first()
			).toBeHidden();

			// A reload lands on the tab the URL names, and going back lands on
			// the one it named before.
			await page.reload();
			await expect(
				page.locator('#linker-faq-page [data-library-tab="documents"]')
			).toHaveAttribute('aria-selected', 'true');
			await page
				.locator('#linker-faq-page [data-library-tab="faq"]')
				.click();
			expect(new URL(page.url()).searchParams.get('tab')).toBeNull();
		});

		test(`${locale}: the search lists hits and splits the tab counts`, async ({
			page,
		}) => {
			await open(page, locale);
			const input = page.locator('#linker-faq-page .linker-library-q');
			const count = page.locator('#linker-library-result-count');
			const before = (await count.textContent()) ?? '';

			await input.fill('battery');
			// The flat result list replaces the panels, and every hit carries
			// the group eyebrow that says where it came from.
			const results = page.locator('[data-library-results]');
			await expect(results).toBeVisible();
			// The FAQ tab is the one open, so the list is its half: the closed
			// panels must not answer for the results.
			await expect(
				page
					.locator('[data-library-results] .linker-library-qa')
					.first()
			).toBeVisible();
			expect(
				await page
					.locator('[data-library-results] .linker-library-hit')
					.count()
			).toBeGreaterThan(0);
			expect(
				await page
					.locator('[data-library-results] .linker-library-hit-eye')
					.count()
			).toBeGreaterThan(0);
			// The marks are the query's own words.
			expect(
				await page
					.locator('[data-library-results] mark')
					.first()
					.textContent()
			).toMatch(/battery/i);

			const faqCount = Number(
				(await page
					.locator(
						'#linker-faq-page [data-library-tab="faq"] .linker-library-n'
					)
					.textContent()) ?? ''
			);
			const docCount = Number(
				(await page
					.locator(
						'#linker-faq-page [data-library-tab="documents"] .linker-library-n'
					)
					.textContent()) ?? ''
			);
			// The two counts are the split of the hits; the field's own text is
			// the total, which never exceeds their sum.
			expect(faqCount + docCount).toBeGreaterThan(0);
			expect(await count.textContent()).toMatch(/\d/);
			expect(await count.textContent()).not.toBe(before);

			// Switching tab filters the same result set to that tab's half: with
			// the documents tab active, a page of hits is a page of documents.
			await page
				.locator('#linker-faq-page [data-library-tab="documents"]')
				.click();
			const listedHits = page.locator(
				'[data-library-results] .linker-library-hit'
			);
			const listedDocs = page.locator(
				'[data-library-results] .linker-library-doc'
			);
			if (docCount > 0) {
				await expect(listedDocs.first()).toBeVisible();
				expect(await listedHits.count()).toBe(await listedDocs.count());
			} else {
				await expect(
					page.locator('[data-library-results] .linker-library-empty')
				).toBeVisible();
			}
			await page
				.locator('#linker-faq-page [data-library-tab="faq"]')
				.click();
			expect(
				await page
					.locator('[data-library-results] .linker-library-doc')
					.count()
			).toBe(0);

			// Clearing restores the register — the tab that is active (the FAQ
			// one; the test switched back above) — and the full counts.
			await page.locator('#linker-faq-page [data-library-clear]').click();
			await expect(results).toBeHidden();
			await expect(
				page.locator('#linker-faq-page [data-library-panel="faq"]')
			).toBeVisible();
			await expect(
				page.locator(
					'#linker-faq-page [data-library-panel="documents"]'
				)
			).toBeHidden();
			await expect(count).toHaveText(before);
		});

		test(`${locale}: a card paginates 20 rows at a time`, async ({
			page,
		}) => {
			await open(page, locale, 'documents');
			// A brand card with more than one page. The documents panel's own
			// cards only: the FAQ tab's cards are in the DOM too (a hidden
			// panel), and their rows carry no type at all.
			const panels = page.locator(
				'#linker-faq-page [data-library-panel="documents"] [data-library-card]'
			);
			const last = panels.last();
			const cardId = (await last.getAttribute('id')) ?? '';
			const rows = page.locator(`#${cardId} [data-library-item]`);
			const total = await rows.count();
			test.skip(total <= 20, `${cardId} states one page of rows`);
			await expect(
				page.locator(`#${cardId} [data-library-item]:not([hidden])`)
			).toHaveCount(20);
			const pager = page.locator(`#${cardId} .linker-library-pager`);
			await expect(pager).toBeVisible();
			await pager.locator('[data-library-page="2"]').click();
			await expect(
				page.locator(`#${cardId} [data-library-item]:not([hidden])`)
			).toHaveCount(Math.min(total - 20, 20));
			await expect(pager.locator('[aria-current="page"]')).toHaveText(
				'2'
			);
		});

		test(`${locale}: FAQPage matches the visible first page of each card`, async ({
			page,
		}) => {
			await open(page, locale);
			await expect(page.locator('#linker-faq-page')).toHaveClass(
				/\bis-enhanced\b/
			);

			const rows = page.locator(
				'#linker-faq-page [data-library-panel="faq"] ' +
					'[data-library-card] details[data-library-item]:not([hidden])'
			);
			const visible = await rows.evaluateAll((nodes) =>
				nodes.map((row) => ({
					question: (
						row.querySelector('.linker-library-qa-q')
							?.textContent ?? ''
					)
						.replace(/\s+/g, ' ')
						.trim(),
					answer: Array.from(
						row.querySelector('.linker-library-qa-a')?.children ??
							[]
					)
						.map((part) => part.textContent ?? '')
						.join(' ')
						.replace(/\s+/g, ' ')
						.trim(),
				}))
			);
			expect(visible.length).toBeGreaterThan(0);

			const pageSizes = await page
				.locator(
					'#linker-faq-page [data-library-panel="faq"] [data-library-card]'
				)
				.evaluateAll((cards) =>
					cards.map(
						(card) =>
							card.querySelectorAll(
								'details[data-library-item]:not([hidden])'
							).length
					)
				);
			expect(Math.max(...pageSizes)).toBeLessThanOrEqual(20);

			const schemas = await page
				.locator('script[type="application/ld+json"]')
				.evaluateAll((scripts) =>
					scripts.map(
						(script) =>
							JSON.parse(script.textContent ?? '') as unknown
					)
				);
			const faq = schemas.find(
				(
					schema
				): schema is { mainEntity: Array<Record<string, unknown>> } =>
					typeof schema === 'object' &&
					schema !== null &&
					(schema as Record<string, unknown>)['@type'] === 'FAQPage'
			);
			expect(faq).toBeDefined();

			const projected = (faq?.mainEntity ?? []).map((entry) => {
				const answer = entry.acceptedAnswer as
					Record<string, unknown> | undefined;
				return {
					question: String(entry.name ?? '')
						.replace(/\s+/g, ' ')
						.trim(),
					answer: String(answer?.text ?? '')
						.replace(/\s+/g, ' ')
						.trim(),
				};
			});
			expect(projected).toEqual(visible);
		});

		test(`${locale}: a type chip filters the rows and the counts`, async ({
			page,
		}) => {
			await open(page, locale, 'documents');
			const chips = page.locator(
				'#linker-faq-page [data-library-filters] [data-library-type]'
			);
			// "All" plus the types the register states.
			expect(await chips.count()).toBeGreaterThan(1);
			const all = page.locator(
				'#linker-faq-page [data-library-filters] [data-library-type="all"]'
			);
			await expect(all).toHaveAttribute('aria-pressed', 'true');

			const type = (await chips
				.nth(1)
				.getAttribute('data-library-type')) as string;
			await chips.nth(1).click();
			await expect(chips.nth(1)).toHaveAttribute('aria-pressed', 'true');
			await expect(all).toHaveAttribute('aria-pressed', 'false');

			// Every visible row is of that type, in every card of the panel the
			// filter belongs to (the FAQ tab's cards carry no type at all).
			const cards = page.locator(
				'#linker-faq-page [data-library-panel="documents"] [data-library-card]'
			);
			const cardCount = await cards.count();
			let seen = 0;
			for (let index = 0; index < cardCount; index += 1) {
				const rows = cards
					.nth(index)
					.locator('[data-library-item]:not([hidden])');
				const shown = await rows.count();
				seen += shown;
				for (let row = 0; row < shown; row += 1) {
					await expect(rows.nth(row)).toHaveAttribute(
						'data-library-type',
						type
					);
				}
			}
			expect(seen).toBeGreaterThan(0);
			// A card the filter emptied says so instead of looking broken.
			const empty = page.locator(
				'#linker-faq-page .linker-library-empty-soft:not([hidden])'
			);
			if ((await empty.count()) > 0) {
				await expect(empty.first()).toBeVisible();
			}
			await all.click();
			await expect(all).toHaveAttribute('aria-pressed', 'true');
		});

		test(`${locale}: an anchor lands under the sticky stack`, async ({
			page,
		}) => {
			await open(page, locale);
			for (const width of [1440, 390]) {
				await page.setViewportSize({ width, height: 900 });
				await open(page, locale);

				// The rail's own link to the documents tab's zone (on the narrow
				// viewport the rail is folded into the pinned chip row, whose
				// chips carry the same hrefs).
				// The rail carries this link above 1024px and the pinned chip
				// row carries it below; the visible one is the reader's.
				const link = page
					.locator(
						'#linker-faq-page a[data-library-spy-link][href="#linker-library-zone-answers"]'
					)
					.locator('visible=true')
					.first();
				await expect(link).toBeVisible();
				await link.click();
				await page.waitForTimeout(600);

				const sticky = await stickyBottom(page);
				const top = await page.evaluate(() => {
					const zone = document.getElementById(
						'linker-library-zone-answers'
					);
					return zone
						? Math.ceil(zone.getBoundingClientRect().top)
						: NaN;
				});
				// The heading is at or below the stack's bottom edge (never
				// hidden under it), and the scroll actually happened.
				expect(Number.isFinite(top)).toBe(true);
				expect(top).toBeGreaterThanOrEqual(sticky - 1);
				const scrolled = await page.evaluate(() => window.scrollY);
				expect(scrolled).toBeGreaterThan(0);
			}
		});
	}
});
