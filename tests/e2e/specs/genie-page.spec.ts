/**
 * Genie knows the page it is opened on (ticket #234; docs/specs/13-genie.md,
 * 目标 3 and "页面感知"). For each of the eight kinds of page, in English and
 * German, at 1440 and 390: the dock opens with two or three suggestions of
 * its own, naming the product or the category; the mount carries the page
 * context every turn sends. At 1440 a question about the page is answered
 * by the real Genie from what the page says.
 *
 * With LINKER_E2E_SHOTS=<dir> every state is also saved as a screenshot
 * (the acceptance record docs/acceptance/2026-10-18/234/).
 */

/**
 * External dependencies
 */
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, loginLink } from '../lib/instance';

type Lang = 'en' | 'de';
type Kind =
	| 'home'
	| 'product'
	| 'category'
	| 'solution'
	| 'blog'
	| 'faq'
	| 'draft'
	| 'account';

interface Visit {
	path: string;
	/** What the first suggestion names, when the page has a name to give. */
	named?: RegExp;
	/** A question about the page, and what its answer must say. */
	question: string;
	answer: RegExp;
}

const PAGES: Record<Lang, Record<Kind, Visit>> = {
	en: {
		home: {
			path: '/',
			question: 'Which project sizes does this page say Linker supplies?',
			answer: /utility/i,
		},
		product: {
			path: '/product/saj-h2-10k-t3/',
			named: /SAJ H2-10K-T3/,
			question: 'How many MPPTs does this one have?',
			answer: /MPPT/,
		},
		category: {
			path: '/product-category/inverters/',
			named: /Inverters/,
			question: 'Which brands are listed on this page?',
			answer: /GoodWe[\s\S]*SAJ|SAJ[\s\S]*GoodWe/,
		},
		solution: {
			path: '/solution/commercial-storage/',
			named: /commercial storage/,
			question: 'What does this page mean by peak shaving?',
			answer: /peak|demand/i,
		},
		blog: {
			path: '/hybrid-inverter-vs-ac-coupled-storage/',
			question: 'What does this post mean by AC coupling?',
			answer: /battery inverter|existing/i,
		},
		faq: {
			path: '/faq-download/',
			question: 'What does this page say about compatibility lists?',
			answer: /pairing|combin|check/i,
		},
		draft: {
			path: '/cart/',
			question: 'Check my draft',
			answer: /GW10K-EHA-G20|BAT-D-G20|H2-10K-T3|L260/,
		},
		account: {
			path: '/my-account/',
			question:
				'What do the statuses on this page mean for my inquiries?',
			answer: /Cancelled|Inquiry received|Proforma/i,
		},
	},
	de: {
		home: {
			path: '/de/',
			question:
				'Für welche Projektgrößen liefert Linker laut dieser Seite?',
			answer: /gewerb/i,
		},
		product: {
			path: '/de/produkt/saj-h2-10k-t3/',
			named: /SAJ H2-10K-T3/,
			question: 'Wie viele MPPT hat dieses Gerät?',
			answer: /MPPT/,
		},
		category: {
			path: '/de/produkt-kategorie/wechselrichter/',
			named: /Wechselrichter/,
			question: 'Welche Marken stehen auf dieser Seite?',
			answer: /GoodWe[\s\S]*SAJ|SAJ[\s\S]*GoodWe/,
		},
		solution: {
			path: '/de/loesung/gewerbespeicher/',
			named: /Gewerblicher Speicher/,
			question: 'Was meint diese Seite mit Lastspitzenkappung?',
			answer: /spitze|last/i,
		},
		blog: {
			path: '/de/hybridwechselrichter-vs-ac-speicher/',
			question: 'Was meint dieser Beitrag mit AC-gekoppelt?',
			answer: /Batteriewechselrichter|bestehend|separat|getrennt/i,
		},
		faq: {
			path: '/de/faq-download/',
			question: 'Was sagt diese Seite über Kompatibilitätslisten?',
			answer: /prüf|Kombination|kombinier/i,
		},
		draft: {
			path: '/de/warenkorb/',
			question: 'Meinen Entwurf prüfen',
			answer: /GW10K-EHA-G20|BAT-D-G20|H2-10K-T3|L260/,
		},
		account: {
			path: '/de/mein-konto/',
			question:
				'Was bedeuten die Status meiner Anfragen auf dieser Seite?',
			answer: /Storniert|Anfrage eingegangen|Proforma/i,
		},
	},
};

/** The page type each kind prints into the mount (PageContext.php). */
const TYPES: Record<Kind, string> = {
	home: 'home',
	product: 'product',
	category: 'category',
	solution: 'solution',
	blog: 'blog',
	faq: 'faq',
	draft: 'draft',
	account: 'account',
};

/** The draft and the account are the signed-in customer's own pages. */
const SIGNED_IN: Kind[] = ['draft', 'account'];
const CUSTOMER = process.env.LINKER_E2E_CUSTOMER ?? '857558227@qq.com';

const VIEWPORTS = {
	1440: { width: 1440, height: 900 },
	390: { width: 390, height: 844 },
} as const;
const SHOTS = process.env.LINKER_E2E_SHOTS ?? '';

async function shot(page: Page, name: string): Promise<void> {
	if (!SHOTS) {
		return;
	}
	mkdirSync(SHOTS, { recursive: true });
	await page.screenshot({
		path: join(SHOTS, `${name}.png`),
		animations: 'disabled',
	});
}

/**
 * Opens the dock. Below 861 px the standing button is hidden (the live
 * page's own switch); the dock's loader answers any opener's click, so the
 * test clicks it from the page.
 */
async function openDock(page: Page): Promise<void> {
	await page.evaluate(() =>
		document.querySelector<HTMLElement>('.linker-genie-open')?.click()
	);
	await expect(page.locator('.linker-genie-app__composer')).toBeVisible({
		timeout: 30_000,
	});
}

/** Asks one question and waits for the answer's vote buttons. */
async function ask(page: Page, question: string): Promise<string> {
	const votes = page.locator('.linker-genie-app__votes');
	const before = await votes.count();
	await page.fill('#linker-genie-input', question);
	await page.locator('.linker-genie-app__send').click();
	await expect
		.poll(async () => votes.count(), {
			message: 'the answer arrives',
			timeout: 180_000,
		})
		.toBeGreaterThan(before);
	return (
		await page.locator('.linker-genie-app__message').last().innerText()
	).trim();
}

/** A new conversation, so the dock opens on its welcome. */
async function fresh(page: Page): Promise<void> {
	await page.context().clearCookies();
}

for (const lang of ['en', 'de'] as const) {
	for (const kind of Object.keys(PAGES[lang]) as Kind[]) {
		const visit = PAGES[lang][kind];
		test.describe(`${kind} page (${lang})`, () => {
			test.beforeEach(async ({ page }) => {
				await fresh(page);
				if (SIGNED_IN.includes(kind)) {
					await page.goto(loginLink(undefined, CUSTOMER));
				}
			});

			for (const width of [1440, 390] as const) {
				test(`the dock opens with this page's suggestions at ${width}`, async ({
					page,
				}) => {
					await page.setViewportSize(VIEWPORTS[width]);
					await page.goto(`${instance().url}${visit.path}`);
					const context = JSON.parse(
						(await page
							.locator('[data-linker-app="genie"]')
							.first()
							.getAttribute('data-page')) ?? '{}'
					) as { type?: string; url?: string; title?: string };
					expect(context.type).toBe(TYPES[kind]);
					expect(context.url).toContain(visit.path);
					await openDock(page);
					const prompts = page.locator('.linker-genie-app__prompt');
					const count = await prompts.count();
					expect(count).toBeGreaterThanOrEqual(2);
					expect(count).toBeLessThanOrEqual(3);
					if (visit.named) {
						await expect(prompts.first()).toContainText(
							visit.named
						);
					}
					await shot(page, `${lang}-${width}-${kind}-open`);
				});
			}

			test('a question about the page is answered from it', async ({
				page,
			}) => {
				test.setTimeout(240_000);
				await page.setViewportSize(VIEWPORTS[1440]);
				await page.goto(`${instance().url}${visit.path}`);
				await openDock(page);
				const answer = await ask(page, visit.question);
				expect(answer).toMatch(visit.answer);
				await shot(page, `${lang}-1440-${kind}-answered`);
			});
		});
	}
}
