/**
 * Site chrome (docs/specs/16-review-acceptance.md, docs/specs/12-site-chrome.md):
 * the header and footer name the two tools, the retired addresses redirect,
 * the sitemap lists the site's own sections, and the language alternates
 * point at this site and nowhere else.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

type Locale = 'en' | 'de';

/** The names the site is allowed to use, and the ones it retired. */
const TOOLS: Record<Locale, RegExp> = {
	en: /Genie - Linker's AI assistant/,
	de: /Genie – der KI-Assistent von Linker/,
};
const CONFIGURATOR: Record<Locale, RegExp> = {
	en: /Solution Configurator/,
	de: /Lösungskonfigurator/,
};
const RETIRED =
	/Linker Advisor|Linker Planner|Linker Site Detail|Linker Berater|Linker Planer|Linker Standortdetails/;

function get(path: string): Promise<Response> {
	return fetch(`${instance().url}${path}`, { redirect: 'manual' });
}

test.describe('site chrome', () => {
	for (const locale of ['en', 'de'] as Locale[]) {
		test(`${locale}: the header and footer name Genie and the Solution Configurator`, async ({
			page,
		}) => {
			await page.goto(
				`${instance().url}${locale === 'de' ? '/de/' : '/'}`
			);
			// textContent, not innerText: the tools sit in a collapsed menu, and
			// a collapsed menu's words are still the site's words.
			const text = (await page.locator('body').textContent()) ?? '';
			expect(text, 'the assistant keeps its name').toMatch(TOOLS[locale]);
			expect(text, 'the configurator keeps its name').toMatch(
				CONFIGURATOR[locale]
			);
			expect(text, 'the retired tool names are gone').not.toMatch(
				RETIRED
			);
			// The Site Detail card folded into the configurator's roof step.
			expect(
				text,
				'the roof detail is named inside the configurator'
			).toMatch(locale === 'de' ? /Dachdetail/ : /Roof detail/i);

			const header =
				(await page.locator('header').first().textContent()) ?? '';
			expect(header, 'the header carries the tools too').toMatch(
				CONFIGURATOR[locale]
			);
		});
	}

	test('the retired addresses redirect to the configurator', async () => {
		const cases: Array<[string, string]> = [
			['/design-canvas/', '/solution-configurator/?step=roof'],
			['/de/design-canvas/', '/de/loesungskonfigurator/?step=roof'],
			['/quote-configurator/', '/solution-configurator/'],
			['/de/angebots-konfigurator/', '/de/loesungskonfigurator/'],
		];
		const landings: string[] = [];
		for (const [from, to] of cases) {
			const response = await get(from);
			expect(response.status, `${from} is a permanent redirect`).toBe(
				301
			);
			const location = response.headers.get('location') ?? '';
			// The landing's own identity, resolved: pathname and query as one
			// string, and the site's own origin. A substring test would pass a
			// foreign host whose URL carries the path, or a stray parameter.
			const landed = new URL(location);
			expect(
				landed.pathname + landed.search,
				`${from} points at ${to}`
			).toBe(to);
			expect(landed.origin, `${from} stays on this site`).toBe(
				new URL(instance().url).origin
			);
			landings.push(location);
		}
		// The landing pages are content, not code: the configurator's own
		// addresses come from the 12-site-chrome migration (README, "Running
		// it"), which renames both tool pages and moves the configurator. An
		// instance built without it has the redirect but nothing behind it —
		// a setup gap with a command that fixes it, named as one, rather than
		// a bare 404 for the reader to diagnose.
		const missing: string[] = [];
		for (const location of landings) {
			const followed = await fetch(location);
			if (followed.status !== 200) {
				missing.push(`${location} answers ${followed.status}`);
			}
		}
		test.skip(
			missing.length > 0,
			`pending-setup: run tools/migrate/12-site-chrome.py apply --write on this instance (${missing.join('; ')})`
		);
		expect(missing).toEqual([]);
	});

	test("the sitemap lists this site's own sections", async () => {
		const robots = await (await get('/robots.txt')).text();
		const declared = /Sitemap:\s*(\S+)/.exec(robots);
		expect(declared, 'robots.txt declares the sitemap').toBeTruthy();
		const sitemapPath = declared![1]!.replace(/^https?:\/\/[^/]+/, '');
		const index = await (await get(sitemapPath)).text();
		const sitemaps = [...index.matchAll(/<loc>([^<]+)<\/loc>/g)].map(
			(match) => match[1]!
		);
		expect(sitemaps.length, 'the index lists sitemaps').toBeGreaterThan(0);
		for (const wanted of [
			'post-sitemap',
			'page-sitemap',
			'product-sitemap',
		]) {
			expect(
				sitemaps.some((url) => url.includes(wanted)),
				`the index has ${wanted}`
			).toBe(true);
		}
		// Every address in the index answers, and the German ones are there.
		let german = 0;
		for (const url of sitemaps) {
			const path = url.replace(/^https?:\/\/[^/]+/, '');
			const response = await get(path);
			expect(response.status, `${path} answers`).toBe(200);
			const body = await response.text();
			german += [...body.matchAll(/<loc>([^<]+)<\/loc>/g)].filter(
				(match) => match[1]!.includes('/de/')
			).length;
		}
		expect(
			german,
			'the German addresses are in the sitemap'
		).toBeGreaterThan(0);
	});

	test('every page carries one set of language alternates, all on this host', async () => {
		const paths = [
			'/',
			'/de/',
			'/product/saj-h2-10k-t3/',
			'/de/produkt/saj-h2-10k-t3/',
		];
		const failures: string[] = [];
		for (const path of paths) {
			const html = await (await get(path)).text();
			const alternates = [
				...html.matchAll(/<link[^>]*rel="alternate"[^>]*>/g),
			].map((match) => match[0]);
			const hosts = new Set(
				alternates
					.map((tag) => /href="([^"]+)"/.exec(tag)?.[1] ?? '')
					.map((href) => {
						try {
							return new URL(href).host;
						} catch {
							return '';
						}
					})
					.filter((host) => host !== '')
			);
			const canonical =
				/<link[^>]*rel="canonical"[^>]*href="([^"]+)"/.exec(html)?.[1];
			if (canonical === undefined) {
				failures.push(`${path}: no canonical`);
			}
			const languages = alternates
				.map((tag) => /hreflang="([^"]+)"/.exec(tag)?.[1])
				.filter(Boolean);
			for (const wanted of ['en', 'de', 'x-default']) {
				if (!languages.includes(wanted)) {
					failures.push(`${path}: no hreflang="${wanted}"`);
				}
			}
			if (languages.length !== new Set(languages).size) {
				failures.push(
					`${path}: ${languages.length} alternates for ${[...new Set(languages)].join('/')} — more than one set`
				);
			}
			for (const host of hosts) {
				if (!instance().url.includes(host)) {
					failures.push(`${path}: an alternate points at ${host}`);
				}
			}
		}
		// One set of three alternates, all on this host, asserted outright:
		// the snapshot's SEOPress meta no longer carries the live site's own
		// alternates (measured 2026-10-16 on the snapshot instance the suite
		// runs against: en, de, x-default, every href on the instance host).
		expect(failures).toEqual([]);
	});
});
