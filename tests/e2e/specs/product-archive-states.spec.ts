/**
 * The product archive's own states, at the viewports and languages the
 * state matrix still listed as pending
 * (docs/acceptance/2026-10-22/full-site/state-matrix.json):
 *
 * - multiple-filters — the phone's filter drawer applies one facet, then a
 *   second on top of it, and the listing carries both.
 * - compare-selection — two cards fill the tab's tray, the chip counts them,
 *   and the selection survives a reload.
 * - filtered-pagination-count-consistency — a filtered listing's declared
 *   pages, its last page and the page past it agree, and the filter survives
 *   every one of them.
 * - add-to-draft and loading-error — the two states the archive does not
 *   have: its cards carry an inert placeholder instead of an add control,
 *   and it renders whole from the server with no request to fail. Both tests
 *   assert that absence rather than a fabricated interaction, so the rows
 *   close on measured facts (the EN-1440 siblings recorded the same
 *   `not-applicable-today` on production, 2026-11-08).
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance, wp } from '../lib/instance';

type Locale = 'en' | 'de';

const ARCHIVE: Record<Locale, string> = {
	en: '/products/',
	de: '/de/produkte/',
};
/** A product whose page states its availability; the stock fixture flips it. */
const PRODUCT: Record<Locale, string> = {
	en: '/product/saj-h2-10k-t3/',
	de: '/de/produkt/saj-h2-10k-t3/',
};
const COMPARE_LABEL: Record<Locale, RegExp> = {
	en: /Compare/i,
	de: /Vergleichen/i,
};
const AVAILABILITY: Record<Locale, [RegExp, RegExp]> = {
	en: [/In stock/, /Currently unavailable/],
	de: [/Auf Lager/, /Derzeit nicht verfügbar/],
};
/** WooCommerce's own refusal when the product is not purchasable. */
const REFUSAL: Record<Locale, RegExp> = {
	en: /is not available at the moment and cannot be added to the solution draft/i,
	de: /ist derzeit nicht verfügbar und kann nicht zum Lösungsentwurf hinzugefügt werden/i,
};
/** The requests a client-side listing would need; the archive makes none. */
const CLIENT_PATHS = ['**/wp-json/**', '**/admin-ajax.php**', '**/*wc-ajax*'];

/**
 * What one archive page says about itself: the cards (and their family ids),
 * the rail's applied-filter count, the results strip's chips, and the declared
 * pagination. Read from the DOM, never from a constant — the catalogue's size
 * is data, and the page size is derived from the first page in the test that
 * needs it.
 */
interface ArchiveFacts {
	cards: number;
	ids: string[];
	applied: string;
	chips: string[];
	lastPage: number | null;
	nextHref: string | null;
}

async function archiveFacts(
	page: import('@playwright/test').Page
): Promise<ArchiveFacts> {
	return page.evaluate(() => {
		const cards = Array.from(document.querySelectorAll('.sf-card'));
		const pageNumbers = Array.from(
			document.querySelectorAll('.tv-woo-pagination .page-numbers')
		)
			.map((el) => Number(el.textContent?.trim()))
			.filter((value) => Number.isFinite(value) && value > 0);
		const next = document.querySelector('.tv-woo-pagination .next');
		return {
			cards: cards.length,
			ids: cards
				.map((card) => card.getAttribute('data-product-id') ?? '')
				.filter((id) => id !== ''),
			applied:
				document.querySelector('[data-linker-applied-filter-count]')
					?.textContent ?? '',
			chips: Array.from(
				document.querySelectorAll('#linker-products .wbchip')
			).map((el) => (el.textContent ?? '').trim()),
			lastPage: pageNumbers.length ? Math.max(...pageNumbers) : null,
			nextHref: next?.getAttribute('href') ?? null,
		};
	});
}

test.beforeEach(async ({ context }) => {
	// The consent banner covers the phone's filter button and the cards'
	// compare controls until it is answered (lib/consent.ts).
	await seedConsentCookies(context);
});

/**
 * multiple-filters, EN 390: the drawer is the phone's only way to the rail,
 * so the second facet is applied from inside it after the first navigation
 * has closed it. The listing must end up carrying both facets — the URL, the
 * bar's applied count, one chip per facet, and a card set that is the
 * intersection rather than one facet's set.
 */
test('en 390: the filter drawer stacks two facets on the listing', async ({
	page,
}) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.goto(`${instance().url}${ARCHIVE.en}`);

	const drawer = page.locator('#sidebar-filters');
	const openButton = page.locator('#product-filter-open');
	await expect(
		openButton,
		'the phone bar carries the filter button'
	).toBeVisible();

	await openButton.click();
	await expect(
		openButton,
		'the button reports the open drawer'
	).toHaveAttribute('aria-expanded', 'true');
	await expect(drawer, 'the drawer is the open state').toHaveClass(
		/is-mobile-open/
	);

	await drawer.locator('a[href*="brand=goodwe"]').first().click();
	await page.waitForLoadState('load');
	expect(page.url(), 'the brand facet is in the address').toContain(
		'brand=goodwe'
	);

	const brand = await archiveFacts(page);
	expect(brand.applied, 'the bar counts the one facet').toBe('1');
	expect(brand.chips.length, 'the strip carries its chip').toBe(1);
	expect(brand.cards, 'the brand filter leaves cards').toBeGreaterThan(0);

	// A second facet on top of the first, applied from the drawer again.
	await expect(
		openButton,
		'the navigation closed the drawer'
	).toHaveAttribute('aria-expanded', 'false');
	await openButton.click();
	await drawer.locator('a[href*="application=home"]').first().click();
	await page.waitForLoadState('load');

	expect(page.url(), 'both facets are in the address').toMatch(
		/brand=goodwe/
	);
	expect(page.url(), 'both facets are in the address').toContain(
		'application=home'
	);

	const both = await archiveFacts(page);
	expect(both.applied, 'the bar counts both facets').toBe('2');
	expect(both.chips.length, 'one chip per facet').toBe(2);
	expect(both.cards, 'the two facets leave cards').toBeGreaterThan(0);
	expect(
		both.cards,
		`the intersection is no larger than the brand alone (${both.cards} vs ${brand.cards})`
	).toBeLessThanOrEqual(brand.cards);

	// The card set is the intersection, read from the cards' own brand line.
	// (Family cards switch the member they show, so `data-product-id` moves
	// with the facets and cannot carry this assertion across pages.)
	const brands = await page.evaluate(() =>
		Array.from(document.querySelectorAll('#linker-products .sf-card')).map(
			(card) =>
				(card.querySelector('.sf-card-brand')?.textContent ?? '').trim()
		)
	);
	expect(brands.length, 'every card names its brand').toBe(both.cards);
	expect(
		brands.filter((name) => !/goodwe/i.test(name)),
		'no card escapes the brand facet'
	).toStrictEqual([]);

	const overflow = await page.evaluate(
		() => document.documentElement.scrollWidth - window.innerWidth
	);
	expect(
		overflow,
		'the phone layout stays in one column'
	).toBeLessThanOrEqual(1);
});

/**
 * compare-selection, EN and DE 390: two cards' compare controls fill the
 * tab's tray. The chip is the only feedback on the phone, so it must count,
 * address the comparison page with both ids, sit directly under the header,
 * and survive a reload (the selection is the tab's, not the page's).
 */
for (const locale of ['en', 'de'] as Locale[]) {
	test(`${locale} 390: two cards fill the comparison tray and the chip counts them`, async ({
		page,
	}) => {
		await page.setViewportSize({ width: 390, height: 844 });
		await page.goto(`${instance().url}${ARCHIVE[locale]}`);

		const controls = page.locator('[data-compare-product]');
		expect(
			await controls.count(),
			'the cards carry compare controls'
		).toBeGreaterThan(2);
		await expect(
			controls.first(),
			'the control is labelled in the page language'
		).toHaveAttribute('aria-label', COMPARE_LABEL[locale]);

		const first = await controls
			.nth(0)
			.getAttribute('data-compare-product');
		const second = await controls
			.nth(1)
			.getAttribute('data-compare-product');
		await controls.nth(0).click();
		await controls.nth(1).click();

		const chip = page.locator('#compare-chip');
		await expect(
			chip,
			'the tray appears once a card is picked'
		).toBeVisible();
		await expect(chip, 'the chip counts both cards').toContainText('2/');

		const tray = await page.evaluate(() => {
			const chipEl = document.querySelector('#compare-chip')!;
			const header = document.querySelector('#lc-header')!;
			const pressed = Array.from(
				document.querySelectorAll('[data-compare-product]')
			).filter((el) => el.getAttribute('aria-pressed') === 'true');
			return {
				href: chipEl.getAttribute('href') ?? '',
				top: chipEl.getBoundingClientRect().top,
				headerBottom: header.getBoundingClientRect().bottom,
				pressed: pressed.map((el) =>
					el.getAttribute('data-compare-product')
				),
				storage: window.sessionStorage.getItem('linkerCompareIds'),
			};
		});
		expect(
			tray.pressed.sort(),
			'the two controls report the selection'
		).toStrictEqual([first!, second!].sort());
		expect(
			tray.href,
			'the chip addresses the comparison with both ids'
		).toContain(`ids=${first},${second}`);
		expect(tray.storage, 'the tab holds the selection').toBe(
			JSON.stringify([first, second])
		);
		expect(
			Math.abs(tray.top - tray.headerBottom),
			`the chip sits under the header (${tray.top} vs ${tray.headerBottom})`
		).toBeLessThanOrEqual(1);

		// A reload keeps the tray: the selection belongs to the tab.
		await page.reload();
		await page.waitForLoadState('load');
		await expect(
			page.locator('#compare-chip'),
			'the selection survives a reload'
		).toContainText('2/');

		// Unpicking one card leaves the other counted.
		await page.locator('[data-compare-product]').nth(0).click();
		await expect(
			page.locator('#compare-chip'),
			'the chip follows the selection down'
		).toContainText('1/');
	});
}

/**
 * add-to-draft on the archive (EN 390, DE 390, DE 1440): the archive's cards
 * print `a[data-card-atc][hidden]` beside the price gate, but nothing in the
 * shipped scripts reveals it or handles a click — the operable add lives on
 * the product page, which is where the failure-injection suite exercises its
 * states. So the row is `not-applicable-today` by measurement, and the test
 * pins exactly that: an inert placeholder must never become a control the
 * customer can hit, and the product page must still carry the real one.
 */
for (const [locale, width] of [
	['en', 390],
	['de', 390],
	['de', 1440],
] as Array<[Locale, number]>) {
	test(`${locale} ${width}: the archive's add-to-draft placeholder stays inert`, async ({
		page,
	}) => {
		await page.setViewportSize({
			width,
			height: width === 390 ? 844 : 900,
		});
		await page.goto(`${instance().url}${ARCHIVE[locale]}`);

		const placeholders = page.locator('#linker-products [data-card-atc]');
		expect(
			await placeholders.count(),
			'every card prints the placeholder'
		).toBeGreaterThan(0);

		const inert = await page.evaluate(() => {
			const nodes = Array.from(
				document.querySelectorAll('#linker-products [data-card-atc]')
			);
			return {
				allHidden: nodes.every((el) => el.hasAttribute('hidden')),
				rendered: nodes.filter(
					(el) => el.getBoundingClientRect().height > 0
				).length,
				hrefs: Array.from(
					new Set(nodes.map((el) => el.getAttribute('href')))
				),
			};
		});
		expect(inert.allHidden, 'the placeholder is hidden in the markup').toBe(
			true
		);
		expect(inert.rendered, 'no placeholder reaches the screen').toBe(0);
		expect(inert.hrefs, 'the placeholder points nowhere').toStrictEqual([
			'#',
		]);

		// A synthetic click is the strongest form of "no consumer": the
		// markup's own event path runs and must change nothing. The `#` href
		// may add a fragment, never a document or a draft.
		const before = page.url();
		const draftBefore = await page.evaluate(() =>
			document.cookie
				.split(';')
				.map((row) => row.trim().split('=')[0] ?? '')
				.filter((name) => /woocommerce_session/.test(name))
		);
		await page.evaluate(() => {
			document
				.querySelectorAll<HTMLElement>(
					'#linker-products [data-card-atc]'
				)
				.forEach((el) => el.click());
		});
		await page.waitForTimeout(500);
		expect(
			page.url().split('#')[0],
			'clicking the placeholder opens no document'
		).toBe(before.split('#')[0]);
		const draftAfter = await page.evaluate(() =>
			document.cookie
				.split(';')
				.map((row) => row.trim().split('=')[0] ?? '')
				.filter((name) => /woocommerce_session/.test(name))
		);
		expect(draftAfter, 'nothing was added to the draft').toStrictEqual(
			draftBefore
		);

		// The counterpart: the product page carries the real control, so the
		// archive's absence is where the action lives, not a lost path.
		await page.goto(`${instance().url}${PRODUCT[locale]}`);
		const add = await page.evaluate(() => {
			const links = Array.from(
				document.querySelectorAll('a[href*="add-to-cart"]')
			);
			return links.filter((el) => {
				const box = el.getBoundingClientRect();
				return box.height > 0 && box.width > 0;
			}).length;
		});
		expect(
			add,
			'the product page offers the operable add control'
		).toBeGreaterThan(0);
	});
}

/**
 * loading-error on the archive (EN 390, DE 1440, DE 390): the listing, its
 * rail and its pagination are printed by the server, and the shipped scripts
 * make no request that a loading state could hang on. The probe that proves
 * it: abort every request a client-side listing would use and count what the
 * page tried to make. Zero attempts and a complete page is the fact the row
 * records as `not-applicable-today`; a later client-side layer would fail
 * here immediately.
 */
for (const [locale, width] of [
	['en', 390],
	['de', 1440],
	['de', 390],
] as Array<[Locale, number]>) {
	test(`${locale} ${width}: the archive renders whole when every client request fails`, async ({
		page,
	}) => {
		await page.setViewportSize({
			width,
			height: width === 390 ? 844 : 900,
		});
		const attempted: string[] = [];
		for (const pattern of CLIENT_PATHS) {
			await page.route(pattern, (route) => {
				attempted.push(route.request().url());
				return route.abort();
			});
		}

		await page.goto(`${instance().url}${ARCHIVE[locale]}`);
		await page.waitForLoadState('load');

		const facts = await archiveFacts(page);
		expect(facts.cards, 'the listing is complete').toBeGreaterThan(0);
		expect(
			await page.locator('#sidebar-filters a[href*="brand="]').count(),
			'the facet rail is complete'
		).toBeGreaterThan(0);
		expect(facts.lastPage, 'the pagination is complete').not.toBeNull();

		const stuck = await page.evaluate(() => ({
			busy: document.querySelectorAll('[aria-busy="true"]').length,
			loading: document.querySelectorAll('.is-loading, .skeleton').length,
			empty: document.querySelectorAll('.wb-empty').length,
		}));
		expect(stuck, 'no loading state is left on the page').toStrictEqual({
			busy: 0,
			loading: 0,
			empty: 0,
		});

		// A facet still navigates: the rail's links are plain GETs to the
		// server, not calls behind the aborted client layer.
		await page.goto(
			`${instance().url}${ARCHIVE[locale]}?brand=goodwe&application=home`
		);
		const filtered = await archiveFacts(page);
		expect(filtered.applied, 'the filtered page reports its facets').toBe(
			'2'
		);
		expect(
			filtered.cards,
			'the filtered page lists products'
		).toBeGreaterThan(0);

		expect(
			attempted,
			'the archive makes no request a loading state could strand'
		).toStrictEqual([]);
	});
}

/**
 * filtered-pagination-count-consistency (EN 390, DE 1440): a filtered
 * listing's declared pages are all real, its last page is partial, the page
 * past it lands back on the last one with the filter intact, and no card
 * appears twice across the pages. The page size is derived from the unfiltered
 * first page, so the test follows the catalogue instead of a constant.
 */
for (const [locale, width] of [
	['en', 390],
	['de', 1440],
] as Array<[Locale, number]>) {
	test(`${locale} ${width}: a filtered listing's pages and counts agree`, async ({
		page,
	}) => {
		await page.setViewportSize({
			width,
			height: width === 390 ? 844 : 900,
		});
		const base = `${instance().url}${ARCHIVE[locale]}`;

		await page.goto(base);
		const open = await archiveFacts(page);
		expect(open.cards, 'the open archive lists products').toBeGreaterThan(
			0
		);
		const pageSize = open.cards;
		expect(open.lastPage, 'the open archive paginates').not.toBeNull();
		const openPages = open.lastPage!;

		// The last page of the open archive is the remainder, not a full page.
		await page.goto(`${base}?product-page=${openPages}`);
		const openLast = await archiveFacts(page);
		expect(openLast.cards, 'the last page carries cards').toBeGreaterThan(
			0
		);
		expect(
			openLast.cards,
			`the last page is the remainder (${openLast.cards} ≤ ${pageSize})`
		).toBeLessThanOrEqual(pageSize);
		expect(
			openLast.cards,
			'the open archive is not a whole number of pages'
		).toBeLessThan(pageSize);

		// A filtered view: the filter must survive every page it declares.
		await page.goto(`${base}?application=home`);
		const first = await archiveFacts(page);
		expect(
			first.cards,
			'the filter leaves a full first page'
		).toBeGreaterThan(0);
		expect(first.applied, 'the filter is applied').toBe('1');
		expect(first.chips.length, 'the filtered view names its facet').toBe(1);
		expect(first.lastPage, 'the filtered view paginates').not.toBeNull();
		expect(
			first.nextHref ?? '',
			'the next link carries the filter'
		).toContain('application=home');

		const filteredPages = first.lastPage!;
		expect(
			filteredPages,
			'the filter narrows the pagination below the open archive'
		).toBeLessThanOrEqual(openPages);

		const seen = new Set(first.ids);
		let total = first.cards;
		for (let index = 2; index <= filteredPages; index += 1) {
			await page.goto(`${base}?application=home&product-page=${index}`);
			const next = await archiveFacts(page);
			expect(next.applied, `page ${index} keeps the filter`).toBe('1');
			expect(next.chips.length, `page ${index} keeps the chip`).toBe(1);
			expect(next.cards, `page ${index} carries cards`).toBeGreaterThan(
				0
			);
			const repeats = next.ids.filter((id) => seen.has(id));
			expect(
				repeats,
				`page ${index} repeats no earlier card`
			).toStrictEqual([]);
			next.ids.forEach((id) => seen.add(id));
			total += next.cards;
		}
		expect(
			total,
			'the declared pages account for the filtered listing'
		).toBe(seen.size);

		// Past the last page the server sends the visitor back to it, with
		// the filter still on the address.
		await page.goto(
			`${base}?application=home&product-page=${filteredPages + 1}`
		);
		await page.waitForLoadState('load');
		expect(
			page.url(),
			'the page past the last one lands on the last one'
		).toContain(`product-page=${filteredPages}`);
		expect(page.url(), 'the redirect keeps the filter').toContain(
			'application=home'
		);
		const landed = await archiveFacts(page);
		expect(landed.cards, 'the landed page is not empty').toBeGreaterThan(0);
		expect(landed.applied, 'the landed page keeps the filter').toBe('1');

		// One facet more than the listing can fill a page: no pagination at
		// all, and the count still names both facets.
		await page.goto(`${base}?application=home&brand=goodwe`);
		const single = await archiveFacts(page);
		expect(single.applied, 'both facets are applied').toBe('2');
		expect(single.chips.length, 'both chips are shown').toBe(2);
		if (single.cards > 0 && single.cards < pageSize) {
			expect(
				single.lastPage,
				'a listing that fits one page declares no second'
			).toBeNull();
		}
	});
}

/**
 * product:out-of-stock (EN 390, DE 1440, DE 390). The owner's ruling states
 * the status and never the quantity (AGENTS.md §2, 2026-10-11), and Woo's own
 * quantity-derived status is the authority: the fixture flips the shared
 * slug's product through WP-CLI — the side an ERP push lands on — and puts it
 * back. Both halves of the state are asserted: the availability line names
 * the state, and the add control the page still offers refuses it in Woo's own
 * words with nothing added to the draft (a recoverable refusal, not a dead
 * end).
 */
for (const [locale, width] of [
	['en', 390],
	['de', 1440],
	['de', 390],
] as Array<[Locale, number]>) {
	test(`${locale} ${width}: an out-of-stock product says so and refuses the draft add`, async ({
		page,
	}) => {
		const slug = PRODUCT[locale].split('/').filter(Boolean).pop()!;
		// get_page_by_path answers the source object for the shared slug (the
		// language layer's twins keep it, docs/specs/9-i18n.md).
		const id = Number(
			wp([
				'eval',
				`$en = get_page_by_path( '${slug}', OBJECT, 'product' );` +
					`echo $en ? $en->ID : 0;`,
			]).trim()
		);
		expect(id, `${PRODUCT[locale]} resolves to a product`).toBeGreaterThan(
			0
		);

		const before = wp([
			'eval',
			`echo wc_get_product( ${id} )->get_stock_status();`,
		]).trim();
		/** The status the instance currently reports for the product. */
		const status = () =>
			wp([
				'eval',
				`echo wc_get_product( ${id} )->get_stock_status();`,
			]).trim();
		const flip = (state: string) =>
			wp([
				'eval',
				`$p = wc_get_product( ${id} ); $p->set_stock_status( '${state}' ); $p->save();`,
			]);

		try {
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			const readAvailability = () =>
				page.evaluate(() => {
					const line = document.querySelector('.pdp-avail-label');
					const dot = line?.querySelector('.pdp-dot');
					return {
						label: line?.textContent?.trim() ?? '',
						className: dot?.className ?? '',
						color: dot ? getComputedStyle(dot).backgroundColor : '',
					};
				});

			// The in-stock state the same product shows otherwise: the
			// unavailable wording and the wait dot must be this state's, not
			// the page's only rendering.
			flip('instock');
			await page.goto(`${instance().url}${PRODUCT[locale]}`);
			const inStock = await readAvailability();
			expect(
				inStock.label,
				'the in-stock state is the page default'
			).toMatch(AVAILABILITY[locale][0]);

			flip('outofstock');
			await page.goto(`${instance().url}${PRODUCT[locale]}`);

			const availability = await readAvailability();
			expect(
				availability.label,
				'the page names the unavailable state'
			).toMatch(AVAILABILITY[locale][1]);
			expect(availability.className, 'the wait dot is marked').toContain(
				'is-wait'
			);
			expect(availability.color, 'the wait dot has a colour').not.toBe(
				''
			);
			expect(
				availability.color,
				'the two states differ in colour'
			).not.toBe(inStock.color);

			// The add control is still offered (the page's own contract for
			// anyone who reaches a product directly), and the add is refused
			// in Woo's words with nothing landing in the draft.
			const add = page
				.locator('a[href*="add-to-cart"]')
				.filter({ visible: true })
				.first();
			await add.click();
			await page.waitForLoadState('load');
			const notices = await page.evaluate(() =>
				Array.from(
					document.querySelectorAll(
						'.woocommerce-error, .woocommerce-message, .woocommerce-info, [role="alert"]'
					)
				).map((el) => (el.textContent ?? '').trim())
			);
			expect(
				notices.join(' '),
				'the refusal names the unavailable state'
			).toMatch(REFUSAL[locale]);
			const draftRows = await page.evaluate(
				() =>
					document.querySelectorAll(
						'.cart_item, tr.woocommerce-cart-form__cart-item, [data-draft-line]'
					).length
			);
			expect(draftRows, 'the draft stays empty').toBe(0);
		} finally {
			// Leave the instance as it was found. A page render can leave the
			// persistent object cache holding the flipped status after the
			// write, so a mismatch is corrected once from a flushed cache
			// rather than left behind for the next suite.
			flip(before);
			if (status() !== before) {
				wp([
					'eval',
					`wp_cache_flush(); $p = wc_get_product( ${id} ); $p->set_stock_status( '${before}' ); $p->save();`,
				]);
			}
			expect(status(), 'the stock state is restored').toBe(before);
		}
	});
}
