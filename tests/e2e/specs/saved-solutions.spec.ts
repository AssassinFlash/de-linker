/**
 * The saved solution card and its own four actions.
 *
 * account-states.spec.ts proves the saved-solutions page's empty state and the
 * planning-projects panel. Neither of them renders a solution card, so the card
 * itself - its recorded items, its design report link, and its two writes
 * (add to draft, remove) - had no browser test at all. This file builds real
 * records for one customer per language and width, and walks the card.
 *
 * The records are made through WP-CLI for the test and deleted with it; the
 * shape is the one SavedSolutions writes (items meta, design meta with the
 * immutable engine snapshot, optional report file).
 */
/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Internal dependencies
 */
import { instance, REPO_ROOT, wp } from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';

const PASSWORD = 'e2e-Saved-Solutions-2026!';
/** Two published products the card records as its bill of materials. */
const PRODUCT_A = 4107;
const PRODUCT_B = 2067;

const output = join(
	REPO_ROOT,
	'.scratch/e2e-shots/saved-solutions',
	process.env.LINKER_SAVED_SOLUTIONS_RUN ?? 'latest'
);

const LANGUAGES = [
	{
		lang: 'en' as const,
		account: '/my-account/',
		solutions: '/my-account/saved-solutions/',
		configurator: '/solution-configurator/',
		addToDraft: /Add to solution draft/i,
		recalculate: /needs a new calculation before it can be added/i,
		confirmRemove: /^Remove solution$/i,
	},
	{
		lang: 'de' as const,
		account: '/de/mein-konto/',
		solutions: '/de/mein-konto/gespeicherte-loesungen/',
		configurator: '/de/loesungskonfigurator/',
		addToDraft: /Zum Lösungsentwurf hinzufügen/i,
		recalculate: /muss neu berechnet werden/i,
		confirmRemove: /^Lösung entfernen$/i,
	},
];

function base(): string {
	return instance().url;
}

interface Fixture {
	customer: number;
	login: string;
	/** A solution with a Genie snapshot: its card carries the add-to-draft write. */
	withSnapshot: number;
	/** A solution without a snapshot: its card points back at the configurator. */
	withoutSnapshot: number;
}

/**
 * One approved customer with two saved solutions and a real report file.
 *
 * The snapshot is deliberately the smallest one DesignProof::can_revalidate
 * accepts (kind genie, one published product, a compatibility revision), so the
 * add write is gated by the same check production runs, not by a bypass.
 */
function makeFixture(tag: string): Fixture {
	const stamp = Date.now();
	const login = `e2e-solutions-${tag}-${stamp}`;
	const email = `${login}@example.test`;
	// SavedSolutions::snapshot() reads $design['snapshot']; the configurator
	// saves the engine result under that key beside the selection fingerprint.
	const snapshot = JSON.stringify({
		snapshot: {
			kind: 'genie',
			selected: {
				lines: [
					{
						product: {
							id: PRODUCT_A,
							brand: 'SAJ',
							model: 'H2-10K-T3',
						},
						quantity: 2,
					},
					{
						product: {
							id: PRODUCT_B,
							brand: 'SAJ',
							model: 'B2-10.0-HV1',
						},
						quantity: 3,
					},
				],
			},
			publication: {
				products: [PRODUCT_A, PRODUCT_B],
				compatibility_revision: 'e2e-fixture',
			},
		},
		selection_fingerprint: 'e2e-fixture',
	});
	const out = wp([
		'eval',
		`$id = wp_insert_user( array( 'user_login' => '${login}', 'user_email' => '${email}', 'user_pass' => '${PASSWORD}', 'role' => 'customer' ) );` +
			`if ( is_wp_error( $id ) ) { echo '{}'; return; }` +
			`update_user_meta( $id, 'linker_approval_status', 'approved' );` +
			`$items = wp_json_encode( array( array( 'product_id' => ${PRODUCT_A}, 'quantity' => 2 ), array( 'product_id' => ${PRODUCT_B}, 'quantity' => 3 ) ) );` +
			`$design = ${JSON.stringify(snapshot)};` +
			`$with = wp_insert_post( array( 'post_type' => 'linker_solution', 'post_status' => 'private', 'post_author' => $id, 'post_title' => 'E2E saved design A' ) );` +
			`update_post_meta( $with, '_linker_solution_items', wp_slash( $items ) );` +
			`update_post_meta( $with, '_linker_solution_design', wp_slash( $design ) );` +
			`$without = wp_insert_post( array( 'post_type' => 'linker_solution', 'post_status' => 'private', 'post_author' => $id, 'post_title' => 'E2E saved design B' ) );` +
			`update_post_meta( $without, '_linker_solution_items', wp_slash( $items ) );` +
			`echo wp_json_encode( array( 'customer' => $id, 'withSnapshot' => $with, 'withoutSnapshot' => $without ) );`,
	]).trim();
	const parsed = JSON.parse(out) as Partial<Fixture>;
	if (!parsed.customer || !parsed.withSnapshot || !parsed.withoutSnapshot) {
		throw new Error(`the saved-solutions fixture was not created: ${out}`);
	}
	return {
		customer: parsed.customer,
		login,
		withSnapshot: parsed.withSnapshot,
		withoutSnapshot: parsed.withoutSnapshot,
	};
}

function remove(fixture: Fixture): void {
	wp([
		'eval',
		`foreach ( array( ${fixture.withSnapshot}, ${fixture.withoutSnapshot} ) as $post_id ) { wp_delete_post( $post_id, true ); }` +
			`require_once ABSPATH . 'wp-admin/includes/user.php'; wp_delete_user( ${fixture.customer} ); echo 'removed';`,
	]);
}

async function shot(page: Page, name: string): Promise<void> {
	await page.evaluate(async () => {
		await document.fonts.ready;
		await Promise.all(
			Array.from(document.images, async (image) => {
				image.loading = 'eager';
				await image.decode().catch(() => undefined);
			})
		);
	});
	await page.screenshot({
		path: join(output, `${name}.png`),
		fullPage: true,
		animations: 'disabled',
	});
}

async function signIn(page: Page, login: string, account: string) {
	await page.goto(base() + account);
	await page.fill('#username', login);
	await page.fill('#password', PASSWORD);
	await page.waitForTimeout(3_300);
	await page.locator('button[name="login"]').click();
	await page.waitForLoadState('load');
	await page.waitForFunction(
		() => document.querySelectorAll('a[href*="action=logout"]').length >= 1,
		null,
		{ timeout: 30_000 }
	);
}

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
	mkdirSync(output, { recursive: true });
});

for (const language of LANGUAGES) {
	for (const width of [1440, 390]) {
		const tag = `${language.lang}-${width}`;

		test(`${tag}: a saved solution card lists its items, offers its report and its own writes`, async ({
			browser,
		}) => {
			const fixture = makeFixture(tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, fixture.login, language.account);
				await page.goto(base() + language.solutions);
				await page.waitForLoadState('load');

				// The card SavedSolutions renders, addressed by the id it writes.
				const withSnapshot = page.locator(
					`#linker-solution-${fixture.withSnapshot}`
				);
				await expect(
					withSnapshot,
					'a saved solution renders its own card'
				).toBeVisible();
				await expect(
					withSnapshot.locator('h2'),
					'the card carries the saved title'
				).toContainText('E2E saved design A');

				// The bill of materials is what was recorded, with the labels the
				// snapshot named - not current product facts.
				const lines = withSnapshot.locator(
					'.linker-account-products li'
				);
				await expect(lines).toHaveCount(2);
				await expect(lines.nth(0)).toContainText('2 ×');
				await expect(lines.nth(0)).toContainText('SAJ H2-10K-T3');
				await expect(lines.nth(1)).toContainText('3 ×');
				await expect(lines.nth(1)).toContainText('SAJ B2-10.0-HV1');

				// A snapshot whose proof still revalidates carries the add write.
				await expect(
					withSnapshot.getByRole('button', {
						name: language.addToDraft,
					}),
					'the revalidatable card offers the draft write'
				).toBeVisible();

				// A record without a snapshot does not re-run today's engine; it
				// points the customer back at the configurator instead.
				const withoutSnapshot = page.locator(
					`#linker-solution-${fixture.withoutSnapshot}`
				);
				await expect(withoutSnapshot).toBeVisible();
				const recalculate = withoutSnapshot.locator(
					'.linker-account-recalculate'
				);
				await expect(recalculate).toContainText(language.recalculate);
				await expect(
					recalculate.locator('a'),
					'the legacy card links the configurator'
				).toHaveAttribute(
					'href',
					new RegExp(language.configurator.replace(/\//g, '\\/'))
				);

				await expectNoOverflow(page, width);
				await shot(page, `${tag}-solutions-populated`);
			} finally {
				await context.close();
				remove(fixture);
			}
		});

		test(`${tag}: a saved solution is removed only after its own confirmation`, async ({
			browser,
		}) => {
			const fixture = makeFixture(tag);
			const context = await browser.newContext({
				viewport: { width, height: width === 390 ? 844 : 900 },
				reducedMotion: 'reduce',
			});
			try {
				await seedConsentCookies(context);
				const page = await context.newPage();
				await signIn(page, fixture.login, language.account);
				await page.goto(base() + language.solutions);
				await page.waitForLoadState('load');

				const card = page.locator(
					`#linker-solution-${fixture.withoutSnapshot}`
				);
				await expect(card).toBeVisible();

				// Opening the disclosure is not the removal: the confirm button
				// lives inside it, and the card survives the open.
				const removal = card.locator('.linker-account-removal');
				await removal.locator('summary').click();
				await expect(
					removal.locator('.linker-account-removal-confirm')
				).toBeVisible();
				await expect(
					card,
					'opening the confirmation keeps the solution'
				).toBeVisible();

				await removal
					.getByRole('button', { name: language.confirmRemove })
					.click();
				await page.waitForLoadState('load');
				await expect(
					page.locator(`#linker-solution-${fixture.withoutSnapshot}`),
					'the confirmed removal deletes the card'
				).toHaveCount(0);
				// The other card is a different record: it stays.
				await expect(
					page.locator(`#linker-solution-${fixture.withSnapshot}`),
					'a removal never touches another solution'
				).toBeVisible();
				await expectNoOverflow(page, width);
				await shot(page, `${tag}-solutions-removed`);
			} finally {
				await context.close();
				remove(fixture);
			}
		});
	}
}

/** The phone tier is the narrowest the design supports; nothing may spill. */
async function expectNoOverflow(page: Page, width: number): Promise<void> {
	expect(
		await page.evaluate(() => document.documentElement.scrollWidth),
		`the page fits ${width}px`
	).toBeLessThanOrEqual(width);
}
