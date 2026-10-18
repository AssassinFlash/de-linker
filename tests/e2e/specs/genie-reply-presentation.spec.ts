/** Frontend-only presentation fixtures; never change the Genie service/options. */
import { expect, test } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT } from '../lib/instance';

test.use({ video: 'on' });
test.afterEach(async ({ page }, info) => {
	const video = page.video();
	if (!video || info.status !== 'passed') return;
	await page.context().close();
	await video.saveAs(
		join(
			REPO_ROOT,
			'docs/acceptance/2026-10-18/223/replies',
			info.title.split(':')[0] + '.webm'
		)
	);
});

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const surface of ['dock', 'workspace']) {
			test(`${locale}-${width}-${surface}: waiting, formatted response and reader-controlled scroll`, async ({
				page,
			}) => {
				const german = locale === 'de';
				const home = german ? '/de/' : '/';
				const answer = german
					? '## Passende Produkte\n\nDie **Kompatibilität** muss zum Projekt passen.\n\n- Phasen und Leistung prüfen\n- Batterie und Wechselrichter abgleichen\n\n'
					: '## Suitable products\n\nThe **compatibility** must match the project.\n\n- Check phases and power\n- Match the battery and inverter\n\n';
				const complete =
					answer +
					Array.from(
						{ length: 14 },
						(_, index) =>
							`${german ? 'Prüfschritt' : 'Check'} ${index + 1}: ${german ? 'Prüfen Sie die Angaben im Datenblatt für Ihr Projekt.' : 'Check the datasheet details for your project.'}`
					).join('\n\n');
				let release!: () => void;
				const held = new Promise<void>((resolve) => {
					release = resolve;
				});
				let posted: {
					messages: Array<{ role: string; content: string }>;
				};
				await page.route(
					'**/wp-json/linker-ai/v1/genie/conversation',
					(route) => route.fulfill({ json: { messages: [] } })
				);
				await page.route(
					'**/wp-json/linker-ai/v1/genie/conversations',
					(route) =>
						route.fulfill({
							json: { current_id: 0, conversations: [] },
						})
				);
				await page.route(
					'**/wp-json/linker-ai/v1/genie/turn',
					async (route) => {
						posted = route.request().postDataJSON();
						await held;
						const stream = `event: meta\ndata: ${JSON.stringify({ grounded: true, fallback: false, attempts: 1, failures: [], language: locale, turn_id: 223 })}\n\nevent: block\ndata: ${JSON.stringify({ type: 'text', text: complete, refs: [] })}\n\nevent: done\ndata: {"ok":true}\n\n`;
						await route.fulfill({
							json: { conversation_id: 223, stream },
						});
					}
				);
				await page.setViewportSize({ width, height: 900 });
				await page.emulateMedia({ reducedMotion: 'no-preference' });
				await page.goto(
					instance().url +
						(surface === 'workspace'
							? home + 'genie/'
							: german
								? '/de/produkte/'
								: '/products/')
				);
				if (surface === 'dock')
					await page
						.locator(
							width === 390
								? '.product-mobile-actions .linker-genie-chip'
								: '.linker-genie-open'
						)
						.first()
						.click();
				const composer = page.locator('.linker-genie-app__input');
				await composer.fill(
					german ? 'Welche Produkte passen?' : 'Which products fit?'
				);
				await page.locator('.linker-genie-app__send').click();
				await expect(
					page.locator('.linker-genie-wait [role="status"]')
				).toBeVisible();
				await expect(
					page.locator('.linker-genie-app__send')
				).toBeDisabled();
				const thinking = page.locator('.linker-genie-wait__status');
				await expect(thinking).toHaveCSS(
					'animation-name',
					'linker-genie-thinking'
				);
				const started = await thinking.evaluate(
					(el) => el.getAnimations()[0].currentTime as number
				);
				await expect
					.poll(() =>
						thinking.evaluate(
							(el) => el.getAnimations()[0].currentTime as number
						)
					)
					.toBeGreaterThan(started);
				const evidence = join(
					REPO_ROOT,
					'docs/acceptance/2026-10-18/223/replies'
				);
				mkdirSync(evidence, { recursive: true });
				const name = `${locale}-${width}-${surface}`;
				await page.screenshot({
					path: join(evidence, `${name}-waiting.png`),
				});
				release();
				const showFull = page.getByRole('button', {
					name: german
						? 'Vollständige Antwort anzeigen'
						: 'Show full response',
				});
				await expect(showFull).toBeVisible();
				await showFull.click();
				await expect(
					page.getByRole('heading', {
						name: german
							? 'Passende Produkte'
							: 'Suitable products',
					})
				).toBeVisible();
				await expect(
					page.locator('.linker-genie-message-body strong')
				).toHaveText(german ? 'Kompatibilität' : 'compatibility');
				expect(posted.messages.at(-1).role).toBe('user');
				const transcript = page.locator(
					'.linker-genie-app__transcript'
				);
				await expect
					.poll(() =>
						transcript.evaluate(
							(el) =>
								el.scrollHeight - el.clientHeight - el.scrollTop
						)
					)
					.toBeGreaterThan(48);
				await transcript.focus();
				await transcript.press('Home');
				await expect(
					page.getByRole('button', {
						name: german
							? 'Zur neuesten Nachricht'
							: 'Jump to latest',
					})
				).toBeVisible();
				await page.screenshot({
					path: join(evidence, `${name}-answer.png`),
				});
				await page
					.getByRole('button', {
						name: german
							? 'Zur neuesten Nachricht'
							: 'Jump to latest',
					})
					.click();
				await expect
					.poll(() =>
						transcript.evaluate(
							(el) =>
								el.scrollHeight - el.clientHeight - el.scrollTop
						)
					)
					.toBeLessThan(2);
				await expect(
					page.locator('.linker-genie-app__composer')
				).toBeInViewport();
				expect(
					await page.evaluate(
						() => document.documentElement.scrollWidth <= innerWidth
					)
				).toBe(true);
			});
		}
	}
}

test('reduced-motion: waiting stays static and a received answer appears immediately', async ({
	page,
}) => {
	await page.emulateMedia({ reducedMotion: 'reduce' });
	await page.setViewportSize({ width: 390, height: 900 });
	await page.route('**/wp-json/linker-ai/v1/genie/conversation', (route) =>
		route.fulfill({ json: { messages: [] } })
	);
	await page.route('**/wp-json/linker-ai/v1/genie/conversations', (route) =>
		route.fulfill({ json: { conversations: [] } })
	);
	let release!: () => void;
	const held = new Promise<void>((resolve) => {
		release = resolve;
	});
	await page.route('**/wp-json/linker-ai/v1/genie/turn', async (route) => {
		await held;
		await route.fulfill({
			json: {
				stream: 'event: block\ndata: {"type":"text","text":"A complete answer.","refs":[]}\n\nevent: done\ndata: {"ok":true}\n\n',
			},
		});
	});
	await page.goto(instance().url + '/genie/');
	await page.locator('.linker-genie-app__input').fill('Which product fits?');
	await page.locator('.linker-genie-app__send').click();
	await expect(page.locator('.linker-genie-wait__status')).toHaveCSS(
		'animation-name',
		'none'
	);
	await expect(page.locator('.linker-genie-wait__dot')).toHaveCSS(
		'animation-name',
		'none'
	);
	release();
	await expect(page.getByText('A complete answer.')).toBeVisible();
	await expect(
		page.getByRole('button', { name: 'Show full response' })
	).toHaveCount(0);
});

test('history: a restored long answer starts at its beginning without replay', async ({
	page,
}) => {
	const text = Array.from(
		{ length: 18 },
		(_, index) =>
			`Paragraph ${index + 1}. This is an already received answer in the conversation.`
	).join('\n\n');
	const stream = `event: block\ndata: ${JSON.stringify({ type: 'text', text, refs: [] })}\n\nevent: done\ndata: {"ok":true}\n\n`;
	await page.route('**/wp-json/linker-ai/v1/genie/conversation', (route) =>
		route.fulfill({
			json: {
				messages: [{ role: 'user', content: 'Earlier question' }],
				stream,
			},
		})
	);
	await page.route('**/wp-json/linker-ai/v1/genie/conversations', (route) =>
		route.fulfill({ json: { conversations: [] } })
	);
	await page.setViewportSize({ width: 390, height: 900 });
	await page.emulateMedia({ reducedMotion: 'no-preference' });
	await page.goto(instance().url + '/genie/');
	await expect(
		page.getByText(
			'Paragraph 18. This is an already received answer in the conversation.'
		)
	).toBeAttached();
	await expect(
		page.locator('.linker-genie-app__transcript')
	).toHaveJSProperty('scrollTop', 0);
	await expect(
		page.getByRole('button', { name: 'Show full response' })
	).toHaveCount(0);
});
