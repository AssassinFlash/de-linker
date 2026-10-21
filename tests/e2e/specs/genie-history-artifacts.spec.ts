/** Saved body stays historical; real current product authority presents its artifacts. */
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import { instance, REPO_ROOT } from '../lib/instance';

const PRODUCT = 3573;
const OUTPUT = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/genie-history-locale'
);

test.use({ reducedMotion: 'reduce' });
test.describe.configure({ timeout: 50_000 });

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const surface of ['workspace', 'hero', 'dock'] as const) {
			test(`${surface}-${locale}-${width}: restored opposite-language artifacts follow current guest authority`, async ({
				page,
			}) => {
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 1000,
				});
				const german = locale === 'de';
				const originalQuestion = german
					? 'Please show the datasheet.'
					: 'Bitte zeigen Sie das Datenblatt.';
				const originalReply = german
					? 'Here is the datasheet you asked for.'
					: 'Hier ist das gewünschte Datenblatt.';
				const pdf = `${instance().url}/wp-content/uploads/2026/08/saj_esolar-aio3_datasheet_en.pdf#page=1`;
				const oldLabel = german
					? 'SAJ eSolar AIO3 Datasheet (EN) · p. 1'
					: 'SAJ eSolar AIO3 Datenblatt (EN), Seite 1';
				const stream = [
					[
						'meta',
						{
							grounded: true,
							fallback: false,
							attempts: 1,
							failures: [],
							language: german ? 'en' : 'de',
						},
					],
					['block', { type: 'text', text: originalReply, refs: [] }],
					[
						'block',
						{
							type: 'cards',
							product_ids: [PRODUCT],
							prices: [
								{ product_id: PRODUCT, text: '9.999,99 €' },
							],
						},
					],
					[
						'block',
						{
							type: 'document',
							ref: `p${PRODUCT}.document.0`,
							label: oldLabel,
							url: pdf,
						},
					],
					['done', { ok: true }],
				]
					.map(
						([event, data]) =>
							`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
					)
					.join('');
				let turns = 0;
				let savedStream = stream;
				let savedMessages = [
					{ role: 'user', content: originalQuestion },
				];
				await page.route(
					'**/wp-json/linker-ai/v1/genie/turn',
					(route) => {
						turns++;
						savedMessages = route.request().postDataJSON().messages;
						// The current service returns the canonical English document title,
						// even on a German turn. Live and restored UI must still agree.
						savedStream = [
							[
								'meta',
								{
									grounded: true,
									fallback: false,
									attempts: 1,
									failures: [],
									language: locale,
								},
							],
							[
								'block',
								{
									type: 'text',
									text: german
										? 'Die aktuelle Antwort.'
										: 'The current answer.',
									refs: [],
								},
							],
							[
								'block',
								{
									type: 'cards',
									product_ids: [PRODUCT],
									prices: [
										{
											product_id: PRODUCT,
											text: german
												? 'Nettopreis nach Partner-Anmeldung'
												: 'Net price after partner sign-in',
											reason: 'login',
										},
									],
								},
							],
							[
								'block',
								{
									type: 'document',
									ref: `p${PRODUCT}.document.0`,
									label: 'SAJ eSolar AIO3 Datasheet (EN) · p. 1',
									url: pdf,
								},
							],
							['done', { ok: true }],
						]
							.map(
								([event, data]) =>
									`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
							)
							.join('');
						return route.fulfill({
							json: { conversation_id: 1, stream: savedStream },
						});
					}
				);
				await page.route(
					'**/wp-json/linker-ai/v1/genie/conversation',
					(route) =>
						route.fulfill({
							json: {
								messages: savedMessages,
								stream: savedStream,
							},
						})
				);
				await page.route(
					'**/wp-json/linker-ai/v1/genie/conversations',
					(route) =>
						route.fulfill({
							json: { current_id: 0, conversations: [] },
						})
				);
				await page.goto(
					`${instance().url}${surface === 'hero' ? (german ? '/de/' : '/') : surface === 'dock' ? (german ? '/de/produkte/' : '/products/') : german ? '/de/genie/' : '/genie/'}`
				);
				const reject = page.getByRole('button', {
					name: /^(Reject all|Alle ablehnen)$/,
				});
				if (await reject.isVisible()) await reject.click();
				async function currentApp() {
					if (surface === 'hero') {
						await expect(
							page.locator(
								'.hero-cinematic[data-linker-genie-hero="ready"]'
							)
						).toHaveCount(1);
						const choosing = page.waitForEvent('filechooser');
						await page
							.locator(
								'.hero-cinematic [data-linker-assistant-open="attach"]'
							)
							.click();
						await (await choosing).setFiles([]);
						return page.locator('.linker-genie-hero__surface');
					}
					if (surface === 'dock') {
						await page
							.locator(
								width === 390
									? '.linker-genie-chip:visible'
									: '.linker-genie-open'
							)
							.click();
					}
					return page.locator('.linker-genie-app:visible');
				}
				const app = await currentApp();
				const card = app.locator('.linker-card').first();
				await expect(card).toBeVisible();
				if (surface === 'hero') {
					const grid = app.locator('.linker-genie-hero__cards');
					const geometry = await card.evaluate((element) => {
						const parent =
							element.parentElement!.getBoundingClientRect();
						const own = element.getBoundingClientRect();
						const media = element
							.querySelector('.linker-card__media')!
							.getBoundingClientRect();
						return {
							card: own.width,
							grid: parent.width,
							media: media.width,
						};
					});
					await expect(grid).toBeVisible();
					expect(geometry.card).toBeGreaterThanOrEqual(
						geometry.grid - 1
					);
					if (width === 1440)
						expect(geometry.media).toBeLessThanOrEqual(121);
				}
				if (surface === 'dock') {
					const wordLines = await card
						.locator('.linker-card__title a')
						.evaluate((element) => {
							const node = element.firstChild!;
							const start =
								node.textContent!.indexOf('Bluetooth');
							const range = element.ownerDocument.createRange();
							range.setStart(node, start);
							range.setEnd(node, start + 'Bluetooth'.length);
							return range.getClientRects().length;
						});
					expect(
						wordLines,
						'Bluetooth remains a whole title word at the dock’s actual width'
					).toBe(1);
				}
				for (const action of await card
					.locator('.linker-genie-app__card-action')
					.all()) {
					const box = await action.boundingBox();
					expect(box!.height).toBeGreaterThanOrEqual(44);
				}

				await expect(
					app.getByText(originalQuestion, { exact: true })
				).toBeVisible();
				await expect(
					app.getByText(originalReply, { exact: true })
				).toBeVisible();
				await expect(card.locator('.linker-card__price')).toHaveText(
					german
						? 'Nettopreis nach Partner-Anmeldung'
						: 'Net price after partner sign-in'
				);
				await expect(card.locator('.linker-card__price')).toHaveClass(
					/--note/
				);
				await expect(app).not.toContainText('9.999,99');
				const document = app.locator('.linker-genie-app__document');
				await expect(document).toHaveText(
					german
						? 'eSolar AIO3 · Datenblatt (EN) · S.\u00a01↗'
						: 'eSolar AIO3 · Datasheet (EN) · p.\u00a01↗'
				);
				await expect(document).toHaveAttribute('href', pdf);
				await expect(document).toHaveAttribute(
					'title',
					'SAJ eSolar AIO3 Datasheet (EN)'
				);
				await expect(
					card.getByRole('button', {
						name: german
							? 'Zum Lösungsentwurf hinzufügen'
							: 'Add to solution draft',
						exact: true,
					})
				).toBeVisible();
				expect(
					turns,
					'history restoration makes no new model request'
				).toBe(0);
				expect(
					await document.evaluate(
						(element) =>
							element.scrollWidth <= element.clientWidth + 1
					)
				).toBe(true);
				mkdirSync(OUTPUT, { recursive: true });
				await app.screenshot({
					path: join(
						OUTPUT,
						`${surface}-${locale}-${width}-transcript.png`
					),
				});
				const primary = card.locator(
					'.linker-genie-app__card-action--primary'
				);
				await primary.scrollIntoViewIfNeeded();
				await expect(primary).toBeInViewport();
				await expect(
					card.locator('.linker-card__price')
				).toBeInViewport();
				await app.screenshot({
					path: join(
						OUTPUT,
						`${surface}-${locale}-${width}-restored.png`
					),
				});
				const label = await document.textContent();
				if (surface === 'hero') {
					await page
						.locator('.hero-prompt')
						.fill('A fixture follow-up');
					await page.locator('.hero-prompt').press('Enter');
				} else {
					await app
						.locator('.linker-genie-app__input')
						.fill('A fixture follow-up');
					await app.locator('.linker-genie-app__send').click();
				}
				await expect(
					app
						.locator('li')
						.getByText(
							german
								? 'Die aktuelle Antwort.'
								: 'The current answer.',
							{ exact: true }
						)
				).toBeVisible();
				await expect(document).toHaveText(label!);
				await expect(document).toHaveAttribute('href', pdf);
				await document.scrollIntoViewIfNeeded();
				await app.screenshot({
					path: join(
						OUTPUT,
						`${surface}-${locale}-${width}-live.png`
					),
				});
				expect(turns).toBe(1);
				await page.reload();
				const restoredApp = await currentApp();
				await expect(
					restoredApp.locator('.linker-genie-app__document')
				).toHaveText(label!);
				await expect(
					restoredApp.locator('.linker-card__price').first()
				).toHaveText(
					german
						? 'Nettopreis nach Partner-Anmeldung'
						: 'Net price after partner sign-in'
				);
				expect(
					turns,
					'reloading the new turn makes no additional model request'
				).toBe(1);
				await page.unrouteAll({ behavior: 'wait' });
			});
		}
	}
}
