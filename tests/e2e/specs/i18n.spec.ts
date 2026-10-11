/**
 * i18n (docs/specs/9-i18n.md §验收): the German addresses answer, the German
 * pages are German on the server, English segments under /de/ 404, a product
 * and its German twin share their slug, the two languages mirror one stock,
 * and the Store API serves German behind `?lang=de`.
 *
 * The German address list is the live site's own `de-sitemap.xml` from the
 * snapshot (`~/de-linker-data/<snapshot>/site/sitemaps/`, docs/specs/
 * 6-live-pull.md); the addresses are requested through `linker-pull
 * check-urls`, which is the tool this repository already has for exactly
 * that.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';
import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

/**
 * Internal dependencies
 */
import { instance, runJustRaw, wp } from '../lib/instance';

/** The snapshot the instance was loaded from; `LINKER_E2E_SNAPSHOT` overrides. */
export function snapshotDir(): string {
	if (process.env.LINKER_E2E_SNAPSHOT) {
		return process.env.LINKER_E2E_SNAPSHOT;
	}
	const root = join(homedir(), 'de-linker-data');
	const candidates = readdirSync(root)
		.filter((name) => /^\d{8}-\d{4}$/.test(name))
		.sort()
		.reverse()
		.map((name) => join(root, name))
		.filter((path) =>
			existsSync(join(path, 'site/sitemaps/de-sitemap.xml'))
		);
	if (candidates.length === 0) {
		throw new Error(
			`no snapshot with a German sitemap under ${root}: pull one (just pull) or set LINKER_E2E_SNAPSHOT.`
		);
	}
	return candidates[0]!;
}

interface StoreProduct {
	id: number;
	name: string;
	permalink: string;
	sku: string;
	is_in_stock: boolean;
}

async function storeProducts(query: string): Promise<StoreProduct[]> {
	const response = await fetch(
		`${instance().url}/wp-json/wc/store/v1/products?${query}`
	);
	expect(response.status, `the Store API answers ${query}`).toBe(200);
	return (await response.json()) as StoreProduct[];
}

test.describe('i18n', () => {
	test('the 150 German addresses of the live sitemap answer 200', async () => {
		test.setTimeout(900_000);
		const snapshot = snapshotDir();
		// The tool exits non-zero as soon as one address does not answer 200;
		// its JSON summary is the answer either way.
		const { stdout } = runJustRaw([
			'pull',
			'check-urls',
			snapshot,
			'--base',
			instance().url,
			'--sitemap',
			'de-sitemap.xml',
		]);
		const output = stdout;
		// The tool's summary is the JSON object it prints last, one key per
		// line; the progress lines before it are not JSON.
		const lines = output.trim().split('\n');
		let start = -1;
		for (let index = lines.length - 1; index >= 0; index -= 1) {
			if (lines[index]!.trim() === '{') {
				start = index;
				break;
			}
		}
		expect(
			start,
			`check-urls reports a summary (${output.slice(-400)})`
		).toBeGreaterThanOrEqual(0);
		const summary = JSON.parse(lines.slice(start).join('\n')) as {
			statuses: Record<string, number>;
			not_200?: string[];
			urls?: number;
		};
		const answered = Object.values(summary.statuses).reduce(
			(a, b) => a + b,
			0
		);
		expect(
			answered,
			'every address of the live sitemap was requested'
		).toBe(150);
		// Three of the live site's German addresses are retired pages that this
		// site's own chrome redirects on purpose: /de/entwurfsflache/ (design
		// canvas) and /de/angebots-konfigurator/ (quote configurator) to the
		// configurator (docs/specs/12-site-chrome.md item 2), and
		// /de/linker-berater/ (the retired Adviser entry) to the products page
		// (docs/specs/19-tool-pages.md). A 200 there would mean the redirect
		// was lost; anything else means a German page broke.
		const retired = [
			'/de/entwurfsflache/',
			'/de/angebots-konfigurator/',
			'/de/linker-berater/',
		];
		const missing = summary.not_200 ?? [];
		for (const entry of missing) {
			const path = entry.replace(/^\d+\s+/, '');
			expect(
				retired,
				`${entry} answers something other than 200 and is not a retired tool address`
			).toContain(path);
			expect(entry, `${path} still redirects`).toMatch(/^301\b/);
		}
		expect(
			summary.statuses['200'] ?? 0,
			`the German tree answers (${JSON.stringify(summary.not_200 ?? [])})`
		).toBe(150 - missing.length);
	});

	test('the German pages are German in the server HTML, and English segments under /de/ 404', async () => {
		const samples = [
			'/de/',
			'/de/produkte/',
			'/de/warenkorb/',
			'/de/proforma-anfrage/',
			'/de/mein-konto/',
		];
		for (const path of samples) {
			const response = await fetch(`${instance().url}${path}`);
			expect(response.status, `${path} answers`).toBe(200);
			const html = await response.text();
			expect(html, `${path} declares German`).toMatch(
				/<html[^>]*lang="de/i
			);
			expect(html, `${path} is served in German`).toMatch(
				/\b(Startseite|Produkte|Anfrage|Anmeldung|Konto|Lösung|Preise)\b/
			);
		}
		for (const path of ['/de/about/', '/de/shop/', '/de/cart/']) {
			const response = await fetch(`${instance().url}${path}`, {
				redirect: 'manual',
			});
			expect(
				[404, 301, 302, 410],
				`${path} is not a second copy of an English page (answered ${response.status})`
			).toContain(response.status);
			if (response.status === 301 || response.status === 302) {
				const location = response.headers.get('location') ?? '';
				expect(
					location,
					`${path} redirects inside the German tree`
				).toContain('/de/');
			}
		}
	});

	test('a product and its German twin share their slug', async () => {
		const [product] = await storeProducts('per_page=1&lang=en');
		expect(product, 'there is a published product').toBeTruthy();
		const slug = product!.permalink.split('/').filter(Boolean).pop()!;
		const envProduct = await fetch(
			`${instance().url}/wp-json/wc/store/v1/products/${product!.id}?lang=en`
		).then((response) => response.json() as Promise<StoreProduct>);
		expect(
			envProduct.permalink,
			'the English permalink uses /product/'
		).toContain('/product/');

		const german = await fetch(`${instance().url}/de/produkt/${slug}/`, {
			redirect: 'manual',
		});
		expect(german.status, `the German twin of ${slug} answers`).toBe(200);
		const html = await german.text();
		expect(html, 'the German page is German').toMatch(
			/<html[^>]*lang="de/i
		);

		// The twin is a different object with the same address segment.
		const twin = await wp([
			'eval',
			`$en = get_page_by_path('${slug}', OBJECT, 'product');` +
				`$term = pll_get_post_language($en->ID);` +
				`$de = pll_get_post( $en->ID, 'de' );` +
				`echo wp_json_encode( array( 'en' => $en->post_name, 'lang' => $term, 'de' => $de ? get_post_field('post_name', $de) : '', 'de_lang' => $de ? pll_get_post_language($de) : '' ) );`,
		]);
		const pair = JSON.parse(twin.trim()) as {
			en: string;
			lang: string;
			de: string;
			de_lang: string;
		};
		expect(pair.lang).toBe('en');
		expect(pair.de, 'the twin exists').toBeTruthy();
		expect(pair.de_lang).toBe('de');
		expect(pair.de, 'the twin keeps the same slug').toBe(pair.en);
	});

	test('the German twin mirrors the English stock', async () => {
		const products = await storeProducts('per_page=5&lang=en');
		expect(products.length, 'there are published products').toBeGreaterThan(
			0
		);
		const ids = products.map((one) => one.id).join(',');

		const readState = (wanted: string) =>
			JSON.parse(
				wp([
					'eval',
					`foreach ( array(${wanted}) as $id ) {` +
						`$en = wc_get_product( $id ); $de = pll_get_post( $id, 'de' );` +
						`$de_product = $de ? wc_get_product( $de ) : null;` +
						`$out[] = array( 'id' => $id, 'lang' => pll_get_post_language( $id ), 'stock' => $en->get_stock_status(),` +
						`'de' => $de, 'de_lang' => $de ? pll_get_post_language( $de ) : '',` +
						`'de_stored_sku' => $de ? (string) get_post_meta( $de, '_sku', true ) : 'missing',` +
						`'de_sku' => $de_product ? $de_product->get_sku() : 'missing',` +
						`'en_sku' => $en ? $en->get_sku() : 'missing',` +
						`'de_stock' => $de_product ? $de_product->get_stock_status() : 'missing',` +
						`'de_manage' => $de_product ? $de_product->get_manage_stock() : 'missing' ); }` +
						`echo wp_json_encode( $out );`,
				]).trim()
			) as Array<{
				id: number;
				lang: string;
				stock: string;
				de: number;
				de_lang: string;
				de_stored_sku: string;
				de_sku: string;
				en_sku: string;
				de_stock: string;
				de_manage: boolean;
			}>;

		const before = readState(ids);
		for (const state of before) {
			expect(state.lang, `product ${state.id} is English`).toBe('en');
			expect(state.de_lang, `product ${state.id} has a German twin`).toBe(
				'de'
			);
			// The German product stores no SKU of its own — a SKU names one
			// product — and shows the shared English one; linker-i18n's
			// Storefront::sku() is the single implementation of that rule.
			expect(
				state.de_stored_sku,
				`${state.id} -> ${state.de}: the German twin stores no SKU of its own`
			).toBe('');
			expect(
				state.de_sku,
				`${state.id} -> ${state.de}: and shows the English product's SKU`
			).toBe(state.en_sku);
			expect(
				state.de_manage,
				`${state.id} -> ${state.de}: the German twin does not manage stock`
			).toBe(false);
			expect(
				state.de_stock,
				`${state.id} -> ${state.de}: the German twin mirrors the English status`
			).toBe(state.stock);
		}

		// One push on the English products, as the ERP would make it by SKU.
		const flipped = before.map((state) =>
			state.stock === 'outofstock' ? 'instock' : 'outofstock'
		);
		const quoted = (values: string[]) =>
			values.map((one) => `'${one}'`).join(',');
		try {
			wp([
				'eval',
				`foreach ( array(${ids}) as $i => $id ) { $p = wc_get_product( $id );` +
					`$p->set_stock_status( array(${quoted(flipped)})[$i] ); $p->save(); }`,
			]);
			const after = readState(ids);
			for (const [index, state] of after.entries()) {
				expect(
					state.stock,
					`the English product ${state.id} took the push`
				).toBe(flipped[index]);
				expect(
					state.de_stock,
					`${state.id} -> ${state.de}: both languages move together`
				).toBe(flipped[index]);
			}
		} finally {
			// Put the products back the way the run found it.
			wp([
				'eval',
				`foreach ( array(${ids}) as $i => $id ) { $p = wc_get_product( $id );` +
					`$p->set_stock_status( array(${quoted(
						before.map((state) => state.stock)
					)})[$i] ); $p->save(); }`,
			]);
		}
	});

	test('the Store API serves German behind ?lang=de', async () => {
		const english = await storeProducts('per_page=5&lang=en');
		const german = await storeProducts('per_page=5&lang=de');
		expect(english.length, 'the English list is not empty').toBeGreaterThan(
			0
		);
		expect(german.length, 'the German list is not empty').toBeGreaterThan(
			0
		);

		// The two languages are different posts; what they share is the slug
		// (docs/specs/9-i18n.md, SameSlug), so that is what pairs them.
		const slugOf = (permalink: string) =>
			permalink.split('/').filter(Boolean).pop() ?? '';
		const bySlug = new Map(
			german.map((product) => [slugOf(product.permalink), product])
		);
		for (const product of english) {
			const twin = bySlug.get(slugOf(product.permalink));
			expect(
				twin,
				`the German list carries the twin of ${product.permalink}`
			).toBeTruthy();
			expect(
				twin!.id,
				'the twin is its own post, not the English one'
			).not.toBe(product.id);
			expect(
				twin!.permalink,
				'the German link lives under /de/produkt/'
			).toContain('/de/produkt/');
		}
		// The German list is not the English list: no id is shared, and every
		// link is a German one. (Names may match — a model name is the same
		// word in both languages, AGENTS.md §3 keeps Produkt/Modell/Serie.)
		const englishIds = new Set(english.map((product) => product.id));
		expect(
			german
				.filter((product) => englishIds.has(product.id))
				.map((product) => product.id),
			'a German product is its own post'
		).toEqual([]);
		for (const product of german) {
			expect(
				product.permalink,
				'every German link is a German one'
			).toContain('/de/produkt/');
		}
	});
});
