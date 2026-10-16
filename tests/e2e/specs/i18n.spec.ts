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

/**
 * The rendered region of a blog face: from the template's root id up to the
 * resource strip that closes it. The old faces rendered the theme's loop
 * container (`#container-content-archive`); since #175 the blog index, the
 * search results and the category archive are LiveCanvas templates from the
 * repository, so the region is the template's own. The full page also carries
 * the header, the footer and the navigation, whose links could match a post
 * URL, so the listing assertions run inside this region only — the recheck
 * round's openQ on the full-page substring checks (fix/recheck-blog-relations,
 * 2026-10-15), kept when the faces moved (#175).
 */
function faceRegion(html: string, rootId: string, end: string): string {
	const start = html.indexOf(`id="${rootId}"`);
	expect(start, `the face renders ${rootId}`).toBeGreaterThan(0);
	const stop = html.indexOf(`id="${end}"`, start);
	expect(stop, `${rootId} closes before ${end}`).toBeGreaterThan(start);
	return html.slice(start, stop);
}

/**
 * The article card links of a face region, by card class, in document order.
 *
 * @param region    The face region (faceRegion()).
 * @param className The card's class, e.g. tv-blog-feed-card.
 */
function cardLinks(region: string, className: string): string[] {
	const pattern = new RegExp(
		`<a[^>]*href="([^"]+)"[^>]*class="[^"]*${className}[^"]*"`,
		'g'
	);
	const found: string[] = [];
	for (const match of region.matchAll(pattern)) {
		found.push(match[1]!);
	}
	return found;
}

/**
 * The slugs of the posts the REST API serves in a language. The German faces'
 * article links are judged against this list, not against a fixture: the
 * ticket's assertion is that a German article is never linked through its
 * English-tree address.
 */
async function postSlugs(lang: 'en' | 'de'): Promise<string[]> {
	const response = await fetch(
		`${instance().url}/wp-json/wp/v2/posts?lang=${lang}&per_page=100`
	);
	expect(response.status, `the REST posts answer in ${lang}`).toBe(200);
	const posts = (await response.json()) as Array<{ slug: string }>;
	expect(posts.length, `there are ${lang} posts`).toBeGreaterThan(0);
	return posts.map((post) => post.slug);
}

/**
 * Every url a page links that is one of the given posts' English-tree
 * addresses. A German face that links this way is the #175 defect: the address
 * is a 404 because the article lives under /de/.
 */
/**
 * Every way a page links one of the given posts' English-tree addresses: the
 * absolute form the templates render (`href="<origin>/<slug>/"`) and the
 * root-relative form the defect was written in (`href="/<slug>/"`). A German
 * face carrying either is the #175 symptom; checking only the absolute form
 * would miss a template that regresses to `/{Field name}/`.
 */
function bareArticleLinks(html: string, slugs: string[]): string[] {
	const origin = instance().url;
	const bare = slugs.flatMap((slug) => [`${origin}/${slug}/`, `/${slug}/`]);
	return bare.filter((url) => html.includes(`href="${url}"`));
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
		// Five of the live site's German addresses are retired pages that
		// this site's own chrome redirects on purpose: /de/entwurfsflache/
		// (design canvas) and /de/angebots-konfigurator/ (quote configurator)
		// to the configurator (docs/specs/12-site-chrome.md item 2);
		// /de/linker-planer/ — the configurator's own former address, moved
		// to /de/loesungskonfigurator/ (owner ruling 2026-10-12); and
		// /de/linker-berater/ with its English slug under /de/ — the Genie
		// workspace's former addresses, moved to /de/genie/ (owner ruling
		// 2026-10-13). A 200 on a retired address would mean the redirect was
		// lost; anything else means a German page broke.
		const retired = [
			'/de/entwurfsflache/',
			'/de/angebots-konfigurator/',
			'/de/linker-planer/',
			'/de/linker-berater/',
			'/de/linker-advisor/',
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

	test('the German blog archive answers on the live slug and lists its posts', async () => {
		// The live German archive answers /de/category/system-design/ at 200
		// de-DE, titled Systemauslegung (docs/debt/DE-PARITY-2026-10-13.md
		// §4.1). A German term minted as systemauslegung - or no German term
		// at all - makes Polylang 301 this address to the English page. The
		// German term carries the same slug as the English one (SameSlug
		// allows it once the term has its language), and Polylang's canonical
		// keeps a slug the requested language also holds.
		const archive = await fetch(
			`${instance().url}/de/category/system-design/`,
			{ redirect: 'manual' }
		);
		expect(
			archive.status,
			'the German category archive answers without a redirect'
		).toBe(200);
		const archiveHtml = await archive.text();
		expect(archiveHtml, 'the archive stays German').toMatch(
			/<html[^>]*lang="de/i
		);
		expect(archiveHtml, 'the archive title is the German category').toMatch(
			/<title>[^<]*Systemauslegung/
		);
		// The archive lists the posts of its category. The 2026-10-14 online
		// recheck found the section empty once the post→category relations
		// were lost (families 16 and 22). Post 551 sits on system-design in
		// the snapshot; its German twin is /de/hybridwechselrichter-vs-ac-
		// speicher/ (docs/debt/DE-PARITY-2026-10-13.md §2: en=551, de=6893).
		// Scoped to the face's feed: the full page's header and footer links
		// must not satisfy this assertion.
		const feed = faceRegion(
			archiveHtml,
			'tv-blog-category-v1',
			'tv-blog-resources'
		);
		expect(
			feed,
			'the archive lists the German twin of a snapshot post of this category'
		).toContain('/de/hybridwechselrichter-vs-ac-speicher/');

		// The ticket's defect (#175): every card linked the slug under the site
		// root, which on this page is an English-tree address and a 404. Each
		// card now carries the article's own, language-resolved permalink.
		const cards = cardLinks(feed, 'tv-blog-feed-card');
		expect(
			cards.length,
			'the German archive lists its cards'
		).toBeGreaterThan(0);
		for (const href of cards) {
			expect(
				new URL(href).pathname,
				`${href} is a German address`
			).toMatch(/^\/de\//);
			const article = await fetch(href, { redirect: 'manual' });
			expect(article.status, `${href} answers`).toBe(200);
			expect(await article.text(), `${href} is German`).toMatch(
				/<html[^>]*lang="de/i
			);
		}
		expect(
			bareArticleLinks(archiveHtml, await postSlugs('de')),
			'the German archive links no article through its English-tree address'
		).toEqual([]);
	});

	test('the German blog index links its articles in German', async () => {
		// The blog posts index (#175): the live face's five card sections —
		// the featured article, the compact list, the practical list, the guide
		// card and the browse grid. Every one of them wrote the slug under the
		// site root, so on the German index every card led to a 404.
		const response = await fetch(`${instance().url}/de/blog/`, {
			redirect: 'manual',
		});
		expect(response.status, 'the German blog index answers').toBe(200);
		const html = await response.text();
		expect(html, 'the index stays German').toMatch(/<html[^>]*lang="de/i);
		const region = faceRegion(
			html,
			'tv-blog-index-v1',
			'tv-blog-resources'
		);
		const cards = [
			...cardLinks(region, 'tv-blog-featured-card'),
			...cardLinks(region, 'tv-blog-compact-item'),
			...cardLinks(region, 'tv-blog-practical-item'),
			...cardLinks(region, 'tv-blog-guide-card'),
			...cardLinks(region, 'tv-blog-browse-card-link'),
		];
		expect(
			cards.length,
			'the German index lists its cards'
		).toBeGreaterThan(0);
		for (const href of new Set(cards)) {
			expect(
				new URL(href).pathname,
				`${href} is a German address`
			).toMatch(/^\/de\//);
			const article = await fetch(href, { redirect: 'manual' });
			expect(article.status, `${href} answers`).toBe(200);
		}
		expect(
			bareArticleLinks(html, await postSlugs('de')),
			'the German index links no article through its English-tree address'
		).toEqual([]);
	});

	test('the German blog search links its results in German', async () => {
		// The search face (#175): same template engine, same defect — the
		// result cards wrote the slug under the site root.
		const response = await fetch(
			`${instance().url}/de/?s=wechselrichter&post_type=post`,
			{ redirect: 'manual' }
		);
		expect(response.status, 'the German search answers').toBe(200);
		const html = await response.text();
		expect(html, 'the search stays German').toMatch(/<html[^>]*lang="de/i);
		const region = faceRegion(
			html,
			'tv-blog-search-v1',
			'tv-blog-search-cta'
		);
		const cards = cardLinks(region, 'tv-blog-search-result-card');
		expect(cards.length, 'the German search lists results').toBeGreaterThan(
			0
		);
		for (const href of new Set(cards)) {
			expect(
				new URL(href).pathname,
				`${href} is a German address`
			).toMatch(/^\/de\//);
			const article = await fetch(href, { redirect: 'manual' });
			expect(article.status, `${href} answers`).toBe(200);
		}
		expect(
			bareArticleLinks(html, await postSlugs('de')),
			'the German search links no article through its English-tree address'
		).toEqual([]);
	});

	test('a German post names its category', async () => {
		// The single page carries the post's category. The 2026-10-14 online
		// recheck found the category metadata empty when the relations were
		// gone (families 16 and 22); with them restored, the page links the
		// German archive.
		const post = await fetch(
			`${instance().url}/de/hybridwechselrichter-vs-ac-speicher/`
		);
		expect(post.status, 'the German post answers').toBe(200);
		const html = await post.text();
		expect(html, 'the single page links its category archive').toContain(
			'/de/category/system-design/'
		);
	});

	test('the English blog archive lists its posts, and the post names the category', async () => {
		// Family 16's English side: the 2026-10-14 online recheck found the
		// category page's ARTICLES IN THIS CATEGORY section empty and the
		// single page's category metadata empty once the post→category
		// relations were lost. Post 551 sits on system-design in the
		// snapshot (docs/debt/DE-PARITY-2026-10-13.md §2).
		const archive = await fetch(
			`${instance().url}/category/system-design/`
		);
		expect(archive.status, 'the English category archive answers').toBe(
			200
		);
		const archiveHtml = await archive.text();
		const feed = faceRegion(
			archiveHtml,
			'tv-blog-category-v1',
			'tv-blog-resources'
		);
		expect(
			feed,
			'the archive lists a snapshot post of this category'
		).toContain('/hybrid-inverter-vs-ac-coupled-storage/');
		// The English face is unchanged by #175: its cards keep the English
		// addresses, which are the ones that answer.
		const cards = cardLinks(feed, 'tv-blog-feed-card');
		expect(
			cards.length,
			'the English archive lists its cards'
		).toBeGreaterThan(0);
		for (const href of cards) {
			expect(
				new URL(href).pathname,
				`${href} is the English address`
			).not.toMatch(/^\/de\//);
			const article = await fetch(href, { redirect: 'manual' });
			expect(article.status, `${href} answers`).toBe(200);
		}
		const post = await fetch(
			`${instance().url}/hybrid-inverter-vs-ac-coupled-storage/`
		);
		expect(post.status, 'the English post answers').toBe(200);
		const html = await post.text();
		expect(html, 'the single page links its category archive').toContain(
			'/category/system-design/'
		);
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
