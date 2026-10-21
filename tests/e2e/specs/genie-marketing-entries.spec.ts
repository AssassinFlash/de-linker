/** Actual LC editor → lazy dock → rendered user message and one intercepted turn. */
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { instance, loginLink, REPO_ROOT } from '../lib/instance';

const OUTPUT = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/full-site/genie-entry-inventory/batch-a',
	process.env.LINKER_MARKETING_RUN ??
		new Date().toISOString().replaceAll(/[-:.]/g, '')
);
const rows: Record<string, unknown>[] = [];
const paths = {
	residential: {
		en: '/solution/residential-storage/',
		de: '/de/loesung/heimspeicher/',
	},
	commercial: {
		en: '/solution/commercial-storage/',
		de: '/de/loesung/gewerbespeicher/',
	},
	installer: { en: '/for-installer/', de: '/de/fuer-installateur/' },
};
test.use({ reducedMotion: 'reduce' });
test.describe.configure({ timeout: 50_000 });
test.afterEach(async ({ page }, info) => {
	mkdirSync(OUTPUT, { recursive: true });
	if (info.status !== info.expectedStatus)
		await page.screenshot({
			path: join(
				OUTPUT,
				`failed-${info.title.replaceAll(/[^a-z0-9-]/gi, '-')}.png`
			),
		});
	const resultsPath = join(OUTPUT, 'case-results');
	mkdirSync(resultsPath, { recursive: true });
	writeFileSync(
		join(
			resultsPath,
			`${info.testId.replaceAll(/[^a-z0-9-]/gi, '_')}.json`
		),
		JSON.stringify(
			{
				title: info.title,
				status: info.status,
				expectedStatus: info.expectedStatus,
				journey:
					rows.find((row) => info.title.startsWith(`${row.name}:`)) ??
					null,
				errors: info.errors.map((error) => error.message),
			},
			null,
			2
		)
	);
	const results = readdirSync(resultsPath)
		.filter((file) => file.endsWith('.json'))
		.map(
			(file) =>
				JSON.parse(readFileSync(join(resultsPath, file), 'utf8')) as {
					status: string;
					expectedStatus: string;
					journey: Record<string, unknown> | null;
				}
		);
	writeFileSync(
		join(OUTPUT, 'summary.json'),
		JSON.stringify(
			{
				source: 'real published local LC/App/attachment preparation and native scope/login/logout; turn and empty-history fixtures; home-recovery alone uses seeded scoped failure and scope503→verified fixture; controlled SpeechRecognition available/unavailable API in capability/draft cases',
				testResults: results,
				rows: results.flatMap((result) =>
					result.journey ? [result.journey] : []
				),
			},
			null,
			2
		)
	);
});
async function prepare(
	page: Page,
	locale: 'en' | 'de',
	width: number,
	path: string
) {
	await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
	const requests: Array<{
		messages: Array<{ role: string; content: string }>;
		attachments?: unknown[];
		locale: string;
	}> = [];
	let fail = false;
	await page.route('**/wp-json/linker-ai/v1/genie/turn', async (route) => {
		requests.push(route.request().postDataJSON());
		if (fail) {
			fail = false;
			return route.fulfill({
				status: 502,
				json: { code: 'upstream', message: 'fixture upstream failure' },
			});
		}
		const stream = [
			[
				'meta',
				{
					turn_id: requests.length,
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
					text:
						locale === 'de'
							? 'Die passende Batterie wird mit dem Wechselrichter abgeglichen.'
							: 'The battery is checked against the inverter.',
					refs: [],
				},
			],
			['done', { ok: true }],
		]
			.map(
				([event, data]) =>
					`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
			)
			.join('');
		return route.fulfill({ json: { conversation_id: 1, stream } });
	});
	await page.route('**/wp-json/linker-ai/v1/genie/conversation', (route) =>
		route.fulfill({ json: { messages: [], stream: '' } })
	);
	await page.route('**/wp-json/linker-ai/v1/genie/conversations', (route) =>
		route.fulfill({ json: { current_id: 0, conversations: [] } })
	);
	const errors: string[] = [];
	page.on('pageerror', (error) => errors.push(error.message));
	await page.goto(`${instance().url}${path}`);
	const reject = page.getByRole('button', {
		name: /^(Reject all|Alle ablehnen)$/,
	});
	if (await reject.isVisible()) await reject.click();
	const source = page.locator(
		path === '/' || path === '/de/'
			? '.hero-prompt'
			: path.includes('installer') || path.includes('installateur')
				? '#installer-mobile-query'
				: '#system-search .lk-dialog-prompt'
	);
	const send = page.locator(
		path === '/' || path === '/de/'
			? '.hero-send'
			: path.includes('installer') || path.includes('installateur')
				? '.installer-assistant-send'
				: '#system-search .lk-send-btn'
	);
	if (path === '/' || path === '/de/') {
		await expect(page.locator('.hero-cinematic')).toHaveAttribute(
			'data-linker-genie-hero',
			'ready'
		);
	} else {
		await expect(source).toHaveAttribute('data-genie-entry-bound', '1');
	}
	return {
		source,
		send,
		requests,
		errors,
		failNext: () => {
			fail = true;
		},
		composer: page.locator('#linker-genie-input'),
	};
}
async function snapshot(page: Page, name: string) {
	mkdirSync(OUTPUT, { recursive: true });
	// Resolve finite decorative transitions before reading the rendered state.
	await page.evaluate(() =>
		document.getAnimations().forEach((animation) => {
			if (animation.effect?.getComputedTiming().iterations !== Infinity) {
				try {
					animation.finish();
				} catch {
					/* A pending/inactive animation has no final frame. */
				}
			}
		})
	);
	const controls = await page
		.locator(
			[
				'.linker-genie-app__prompt:visible',
				'.linker-genie-app__attachment-remove:visible',
				'#system-search .lk-send-btn:visible',
				'#system-search [data-linker-assistant-open]:visible',
				'.installer-mobile-assistant .installer-assistant-send:visible',
				'.installer-mobile-assistant [data-linker-assistant-open]:visible',
			].join(', ')
		)
		.evaluateAll((buttons) =>
			buttons.map((button) => {
				const box = button.getBoundingClientRect();
				return {
					text:
						button.getAttribute('aria-label') ?? button.textContent,
					className: button.className,
					width: box.width,
					height: box.height,
					left: box.left,
					right: box.right,
				};
			})
		);

	const fields = await page.locator('textarea:visible').evaluateAll((items) =>
		items.map((item) => {
			const field = item as HTMLTextAreaElement;
			const style = getComputedStyle(field);
			return {
				className: field.className,
				value: field.value,
				clientHeight: field.clientHeight,
				scrollHeight: field.scrollHeight,
				scrollTop: field.scrollTop,
				styleHeight: field.style.height,
				lineHeight: style.lineHeight,
				paddingTop: style.paddingTop,
				paddingBottom: style.paddingBottom,
				boxSizing: style.boxSizing,
				whiteSpace: style.whiteSpace,
				overflowY: style.overflowY,
				width: field.getBoundingClientRect().width,
			};
		})
	);
	const hero = await page
		.locator('.hero-cinematic.linker-genie-hero--open:visible')
		.evaluateAll((items) =>
			items.map((item) => {
				const dialog = item.querySelector<HTMLElement>('.hero-dialog')!;
				const bounds = dialog.getBoundingClientRect();
				const style = getComputedStyle(dialog);
				const nameplate = item.querySelector<HTMLElement>(
					'.hero-nameplate-btn'
				)!;
				const nameplateBox = nameplate.getBoundingClientRect();
				const send = item.querySelector<HTMLElement>('.hero-send')!;
				const sendStyle = getComputedStyle(send);
				const svg = send.querySelector('svg');
				const luminance = (value: string) => {
					const rgb =
						value
							.match(/[\d.]+/g)
							?.slice(0, 3)
							.map(Number) ?? [];
					const linear = rgb.map((channel) => {
						const c = channel / 255;
						return c <= 0.04045
							? c / 12.92
							: ((c + 0.055) / 1.055) ** 2.4;
					});
					return (
						0.2126 * (linear[0] ?? 0) +
						0.7152 * (linear[1] ?? 0) +
						0.0722 * (linear[2] ?? 0)
					);
				};
				const foreground = luminance(sendStyle.color),
					background = luminance(sendStyle.backgroundColor);
				return {
					contentLeft:
						bounds.left +
						parseFloat(style.borderLeftWidth) +
						parseFloat(style.paddingLeft),
					contentRight:
						bounds.right -
						parseFloat(style.borderRightWidth) -
						parseFloat(style.paddingRight),
					nameplate: {
						left: nameplateBox.left,
						right: nameplateBox.right,
						height: nameplateBox.height,
					},
					send: {
						disabled: send.getAttribute('aria-disabled') === 'true',
						active:
							dialog.matches(':focus-within') ||
							send.matches(':hover'),
						color: sendStyle.color,
						background: sendStyle.backgroundColor,
						svgColor: svg ? getComputedStyle(svg).color : null,
						contrast:
							(Math.max(foreground, background) + 0.05) /
							(Math.min(foreground, background) + 0.05),
					},
				};
			})
		);
	const welcome = await page
		.locator('.linker-genie-app__welcome:visible')
		.evaluateAll((items) =>
			items.map((item) => {
				const bounds = item.getBoundingClientRect();
				const title = item.querySelector(
					'.linker-genie-app__welcome-greeting'
				)!;
				return {
					top: bounds.top,
					bottom: bounds.bottom,
					clientHeight: item.clientHeight,
					scrollHeight: item.scrollHeight,
					scrollTop: item.scrollTop,
					paddingTop: parseFloat(getComputedStyle(item).paddingTop),
					titleTop: title.getBoundingClientRect().top,
				};
			})
		);
	const sourceErrors = await page
		.locator(
			'#system-search .linker-genie-app__error:visible, .installer-mobile-assistant .linker-genie-app__error:visible'
		)
		.evaluateAll((items) =>
			items.map((item) => ({
				text: item.textContent?.trim() ?? '',
				height: item.getBoundingClientRect().height,
			}))
		);
	writeFileSync(
		join(OUTPUT, `${name}-geometry.json`),
		JSON.stringify(
			{ controls, fields, hero, welcome, sourceErrors },
			null,
			2
		)
	);
	for (const item of sourceErrors)
		expect(
			item.text,
			`${name}: a cleared source error must not leave an empty visible alert`
		).not.toBe('');
	for (const item of welcome) {
		if (item.scrollTop === 0)
			expect(
				item.titleTop,
				`${name}: welcome title must remain reachable at its scroll origin`
			).toBeGreaterThanOrEqual(item.top + item.paddingTop - 0.5);
	}
	for (const control of controls) {
		expect(
			control.height,
			`${name}: ${control.text}`
		).toBeGreaterThanOrEqual(43.9);
		expect(
			control.width,
			`${name}: ${control.text}`
		).toBeGreaterThanOrEqual(43.9);
		expect(control.left).toBeGreaterThanOrEqual(-0.5);
		expect(control.right).toBeLessThanOrEqual(
			(page.viewportSize()?.width ?? 1440) + 0.5
		);
	}
	for (const field of fields.filter((item) =>
		item.className.includes('hero-prompt')
	)) {
		expect(
			field.clientHeight,
			`${name}: native Hero follow-up must show both complete fixture lines`
		).toBeGreaterThanOrEqual(field.scrollHeight);
	}
	for (const item of hero) {
		expect(item.nameplate.left).toBeGreaterThanOrEqual(
			item.contentLeft - 0.5
		);
		expect(item.nameplate.right).toBeLessThanOrEqual(
			item.contentRight + 0.5
		);
		expect(item.nameplate.height).toBeGreaterThanOrEqual(43.9);
		if (!item.send.disabled) {
			if (item.send.active)
				expect(item.send.color).toBe('rgb(255, 255, 255)');
			expect(item.send.svgColor).toBe(item.send.color);
			expect(item.send.contrast).toBeGreaterThanOrEqual(3);
		}
	}
	for (const field of fields.filter((item) =>
		item.className.includes('linker-genie-app__input')
	)) {
		expect(
			field.clientHeight,
			`${name}: composer must display its full content up to six lines`
		).toBeGreaterThanOrEqual(Math.min(field.scrollHeight, 144) - 1);
		if (field.scrollHeight > 144) expect(field.overflowY).toBe('auto');
	}
	await page.screenshot({ path: join(OUTPUT, `${name}.png`) });
}
for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		for (const kind of [
			'residential',
			'commercial',
			'installer',
		] as const) {
			if (kind === 'installer' && width === 1440) continue; // Desktop Plan is explicitly Batch B.
			test(`${kind}-${locale}-${width}: cold/warm exact question, keyboard and source ownership`, async ({
				page,
			}) => {
				const { source, send, requests, errors, composer } =
					await prepare(page, locale, width, paths[kind][locale]);
				const question =
					locale === 'de'
						? 'Welche Batterie passt zu meinem SAJ H2? Bitte prüfen Sie auch das Datenblatt.'
						: 'Which battery works with my SAJ H2? Please check the datasheet too.';
				let release!: () => void;
				const gate = new Promise<void>((resolve) => {
					release = resolve;
				});
				await page.route(
					'**/plugins/linker-tools/build/genie.js?*',
					async (route) => {
						await gate;
						return route.continue();
					}
				);
				if (kind !== 'installer') {
					const capsule = page
						.locator('#system-search .lk-capsule[data-lk-ask]')
						.first();
					if (await capsule.count()) {
						const prefill =
							(await capsule.getAttribute('data-lk-ask')) ||
							(await capsule.innerText()).trim();
						await capsule.click();
						await expect(source).toHaveValue(prefill);
						expect(requests).toHaveLength(0);
					}
				}
				await source.fill(question);
				await send.dblclick();
				await expect(send).toHaveAttribute('aria-busy', 'true');
				await expect(source).toHaveValue(question);
				await snapshot(page, `${kind}-${locale}-${width}-cold`);
				release();
				await expect.poll(() => requests.length).toBe(1);
				await expect(
					page.locator('.linker-genie-app__votes')
				).toHaveCount(1);
				expect(
					requests[0]?.messages.filter((item) => item.role === 'user')
				).toEqual([{ role: 'user', content: question }]);
				expect(requests[0]?.locale).toBe(locale);
				await expect(page.getByRole('dialog')).toContainText(question);
				await expect(source).toHaveValue('');
				await expect(composer).toBeFocused();
				if (width === 390) {
					await expect(page.getByRole('dialog')).toHaveAttribute(
						'aria-modal',
						'true'
					);
					let accountFocused = false;
					for (let i = 0; i < 18; i++) {
						await page.keyboard.press('Tab');
						const focus = await page.evaluate(() => ({
							inside: !!document.activeElement?.closest(
								'[data-linker-genie-mount]'
							),
							active: document.activeElement?.outerHTML.slice(
								0,
								300
							),
							account: !!document.activeElement?.closest(
								'.linker-guest-account-links'
							),
						}));
						expect(
							focus.inside,
							`Tab ${i}: ${JSON.stringify(focus)}`
						).toBe(true);
						accountFocused ||= focus.account;
					}
					const account = page.locator('.linker-guest-account-links');
					if (await account.isVisible())
						expect(accountFocused).toBe(true);
				} else
					await expect(page.getByRole('dialog')).not.toHaveAttribute(
						'aria-modal',
						'true'
					);
				await snapshot(page, `${kind}-${locale}-${width}-answered`);
				await page.keyboard.press('Escape');
				await expect(page.getByRole('dialog')).toHaveCount(0);
				await expect(send).toBeFocused();
				const second =
					locale === 'de'
						? 'Und welche Unterlagen gibt es dazu?'
						: 'Which documents are available?';
				await source.fill(second);
				await source.press('Enter');
				await expect.poll(() => requests.length).toBe(2);
				await expect(
					page.locator('.linker-genie-app__votes')
				).toHaveCount(2);
				expect(requests[1]?.messages.at(-1)?.content).toBe(second);
				expect(errors).toEqual([]);
				expect(
					await page.evaluate(
						() => document.documentElement.scrollWidth <= innerWidth
					)
				).toBe(true);
				const scope = await page.context().cookies();
				expect(
					scope.some(
						(cookie) => cookie.name === 'linker_genie_browser'
					)
				).toBe(true);
				rows.push({
					name: `${kind}-${locale}-${width}`,
					states: [
						'cold',
						'unique-turn',
						'warm-enter',
						'keyboard',
						'focus-return',
					],
					turns: requests.length,
					errors,
				});
			});
		}
		test(`recovery-${locale}-${width}: boot failure retries original, upstream retry is one user message`, async ({
			page,
		}) => {
			const { source, send, requests, composer, errors, failNext } =
				await prepare(page, locale, width, paths.residential[locale]);
			let first = true;
			await page.route(
				'**/plugins/linker-tools/build/genie.js?*',
				(route) => {
					if (first) {
						first = false;
						return route.abort('failed');
					}
					return route.continue();
				}
			);
			const question =
				locale === 'de'
					? 'Bitte behalten Sie diese ursprüngliche Frage.'
					: 'Keep this original question.';
			await source.fill(question);
			await send.click();
			await expect(
				page.locator('[data-linker-genie-load-error]')
			).toBeVisible();
			await expect(source).toHaveValue(question);
			expect(requests).toHaveLength(0);
			await expect(send).not.toHaveAttribute('aria-busy', 'true');
			await snapshot(page, `recovery-${locale}-${width}-boot-failed`);
			failNext();
			await page
				.locator(
					'[data-linker-genie-load-error] .linker-genie-load-error__actions button'
				)
				.click();
			await expect.poll(() => requests.length).toBe(1);
			await expect(composer).toHaveValue(question);
			await page
				.getByRole('button', { name: /^(Try again|Erneut versuchen)$/ })
				.click();
			await expect.poll(() => requests.length).toBe(2);
			await expect(page.locator('.linker-genie-app__votes')).toHaveCount(
				1
			);
			expect(
				requests[1]?.messages.filter((item) => item.role === 'user')
			).toEqual([{ role: 'user', content: question }]);
			expect(errors).toEqual([]);
			rows.push({
				name: `recovery-${locale}-${width}`,
				states: ['boot-failed', 'same-attempt-retry', 'upstream-retry'],
				turns: 2,
				errors,
			});
		});
		test(`draft-${locale}-${width}: real attachment preparation, refusal, reload and voice capability`, async ({
			page,
		}) => {
			await page.addInitScript(() => {
				for (const key of [
					'SpeechRecognition',
					'webkitSpeechRecognition',
				])
					Object.defineProperty(window, key, {
						value: undefined,
						configurable: true,
						writable: true,
					});
			});
			const { source, requests, composer, errors } = await prepare(
				page,
				locale,
				width,
				paths.commercial[locale]
			);
			const question =
				locale === 'de'
					? 'Prüfen Sie bitte meinen Schaltplan.'
					: 'Please check my schematic.';
			await source.fill(question);
			await page
				.locator('#system-search [data-linker-assistant-open="attach"]')
				.click();
			await expect(composer).toHaveValue(question);
			expect(requests).toHaveLength(0);
			const file = page.locator(
				'[data-linker-genie-mount] input[type=file]'
			);
			await file.setInputFiles({
				name: 'blocked.exe',
				mimeType: 'application/octet-stream',
				buffer: Buffer.from('not accepted'),
			});
			await expect(
				page.locator('.linker-genie-app__attachment--refused')
			).toBeVisible();
			await expect(composer).toHaveValue(question);
			expect(requests).toHaveLength(0);
			await file.setInputFiles({
				name: 'schematic.pdf',
				mimeType: 'application/pdf',
				buffer: Buffer.from(
					'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'
				),
			});
			await expect(
				page
					.locator('.linker-genie-app__attachment')
					.filter({ hasText: 'schematic.pdf' })
			).toBeVisible();
			await expect(page.locator('.linker-genie-app__send')).toBeEnabled();
			await snapshot(page, `draft-${locale}-${width}-prepared`);
			await page.reload();
			await expect(source).toHaveAttribute('data-genie-entry-bound', '1');
			// Reopen only: reload itself never sends.
			await page.evaluate(() =>
				window.dispatchEvent(
					new CustomEvent('linker-genie-ask', {
						detail: { refresh: true },
					})
				)
			);
			await expect(composer).toHaveValue(question);
			await expect(page.getByRole('dialog')).toContainText(
				'schematic.pdf'
			);
			await expect(
				page.locator('.linker-genie-app__send')
			).toBeDisabled();
			expect(requests).toHaveLength(0);
			await snapshot(page, `draft-${locale}-${width}-missing`);
			await page.keyboard.press('Escape');
			await source.fill(question);
			await page
				.locator('#system-search [data-linker-assistant-open="voice"]')
				.click();
			await expect(
				page.locator('[data-genie-entry-review]')
			).toBeVisible();
			await snapshot(page, `draft-${locale}-${width}-voice-conflict`);
			await page
				.locator('[data-genie-entry-review]')
				.getByRole('button', {
					name: /^(Open as draft|Als Entwurf öffnen)$/,
				})
				.click();
			const unavailableText =
				locale === 'de'
					? 'Dieser Browser unterstützt keine Spracheingabe. Sie können Ihre Frage eintippen.'
					: 'Dictation is not available in this browser. You can type your question.';
			// Entry review/parked records share this styling class; await the actual capability consumer.
			const unavailable = page
				.locator('.linker-genie-app__photo-prompt')
				.filter({ hasText: unavailableText });
			await expect(unavailable.locator('p')).toHaveText(unavailableText);
			await expect(unavailable.locator('button')).toHaveCount(0);
			await snapshot(page, `draft-${locale}-${width}-voice-unavailable`);
			// Existing recovered draft has explicit ownership; opening voice never sends or overwrites it.
			await expect(composer).toHaveValue(question);
			expect(requests).toHaveLength(0);
			expect(errors).toEqual([]);
			rows.push({
				name: `draft-${locale}-${width}`,
				states: [
					'attachment-intent',
					'refusal',
					'prepared',
					'reload-missing',
					'voice-conflict',
					'voice-unavailable-explicit-draft',
				],
				turns: 0,
				errors,
			});
		});
	}
}

// Only SpeechRecognition is controlled; the rendered App and attachment preparation run normally.
for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`capabilities-${locale}-${width}: IME, dictation insertion/stop/refusal and image/PDF payload`, async ({
			page,
		}) => {
			await page.addInitScript(() => {
				type Speech = {
					lang: string;
					onresult: ((event: unknown) => void) | null;
					onend: (() => void) | null;
					onerror: (() => void) | null;
					start: () => void;
					stop: () => void;
				};
				const state = {
					sessions: [] as Speech[],
					denied: false,
					starts: 0,
					stops: 0,
				};
				class Recognition implements Speech {
					lang = '';
					onresult: Speech['onresult'] = null;
					onend: Speech['onend'] = null;
					onerror: Speech['onerror'] = null;
					constructor() {
						state.sessions.push(this);
					}
					start() {
						state.starts++;
						if (state.denied) throw new Error('not-allowed');
					}
					stop() {
						state.stops++;
						this.onend?.();
					}
				}
				Object.assign(window, {
					SpeechRecognition: Recognition,
					__entrySpeech: state,
				});
			});
			const { source, requests, composer, errors } = await prepare(
				page,
				locale,
				width,
				paths.residential[locale]
			);
			await source.fill('Alpha Beta');
			await source.dispatchEvent('keydown', {
				key: 'Enter',
				code: 'Enter',
				keyCode: 229,
				isComposing: true,
			});
			await source.press('Shift+Enter');
			await expect(source).toHaveValue('Alpha Beta\n');
			expect(requests).toHaveLength(0);
			await source.fill('Alpha Beta');
			await page
				.locator('#system-search [data-linker-assistant-open="voice"]')
				.click();
			await expect(composer).toHaveValue('Alpha Beta');
			const voiceAction = page.locator('.linker-genie-app__photo-prompt');
			await expect(voiceAction.locator('p')).toHaveCount(0);
			await expect(
				voiceAction.getByRole('button', {
					name: /^(Dictate|Diktieren)$/,
				})
			).toBeVisible();
			await composer.fill(
				Array.from(
					{ length: 8 },
					(_, index) => `Line ${index + 1}`
				).join('\n')
			);
			await expect
				.poll(() => composer.evaluate((node) => node.clientHeight))
				.toBe(144);
			await snapshot(page, `capabilities-${locale}-${width}-eight-lines`);
			await composer.fill('Alpha Beta');
			const speech = () =>
				page.evaluate(() => {
					const state = (
						window as unknown as {
							__entrySpeech: {
								starts: number;
								stops: number;
								sessions: Array<{ lang: string }>;
							};
						}
					).__entrySpeech;
					return {
						starts: state.starts,
						stops: state.stops,
						lang: state.sessions.at(-1)?.lang,
					};
				});
			expect((await speech()).starts).toBe(0);
			await composer.evaluate((field) => {
				(field as HTMLTextAreaElement).setSelectionRange(6, 6);
			});
			await page.locator('.linker-genie-app__mic').click();
			expect(await speech()).toMatchObject({
				starts: 1,
				lang: locale === 'de' ? 'de-DE' : 'en-US',
			});
			await page.evaluate(() => {
				const state = (
					window as unknown as {
						__entrySpeech: {
							sessions: Array<{
								onresult: (event: unknown) => void;
							}>;
						};
					}
				).__entrySpeech;
				state.sessions
					.at(-1)
					?.onresult({ results: [[{ transcript: 'heard' }]] });
			});
			await expect(composer).toHaveValue('Alpha heard Beta');
			await page.locator('.linker-genie-app__mic').click();
			await page.evaluate(() => {
				const state = (
					window as unknown as {
						__entrySpeech: {
							sessions: Array<{
								onresult: (event: unknown) => void;
							}>;
						};
					}
				).__entrySpeech;
				state.sessions.at(-1)?.onresult({
					results: [[{ transcript: 'LATE PRIVATE WORDS' }]],
				});
				(
					window as unknown as { __entrySpeech: { denied: boolean } }
				).__entrySpeech.denied = true;
			});
			await expect(composer).toHaveValue('Alpha heard Beta');
			await page.locator('.linker-genie-app__mic').click();
			await expect(page.getByRole('dialog')).toContainText(
				locale === 'de'
					? 'Die Spracheingabe konnte nicht gestartet werden.'
					: 'Dictation could not start.'
			);
			await expect(composer).toHaveValue('Alpha heard Beta');
			expect(requests).toHaveLength(0);
			const chooserReady = page.waitForEvent('filechooser');
			await page.locator('.linker-genie-app__attach').click();
			await (await chooserReady).setFiles([]);
			await expect(composer).toHaveValue('Alpha heard Beta');
			const photo = Buffer.from(
				await page.evaluate(() => {
					const canvas = document.createElement('canvas');
					canvas.width = 16;
					canvas.height = 16;
					canvas.getContext('2d')!.fillRect(0, 0, 16, 16);
					return canvas.toDataURL('image/png').split(',')[1]!;
				}),
				'base64'
			);
			await page
				.locator('[data-linker-genie-mount] input[type=file]')
				.setInputFiles([
					{
						name: 'nameplate.png',
						mimeType: 'image/png',
						buffer: photo,
					},
					{
						name: 'schematic.pdf',
						mimeType: 'application/pdf',
						buffer: Buffer.from(
							'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'
						),
					},
				]);
			await expect(
				page.locator('.linker-genie-app__attachment')
			).toHaveCount(2);
			await expect(
				page.locator('.linker-genie-app__attachment-state')
			).toHaveCount(0);
			await expect(page.locator('.linker-genie-app__send')).toBeEnabled();
			await snapshot(page, `capabilities-${locale}-${width}-prepared`);
			await page.locator('.linker-genie-app__send').click();
			await expect.poll(() => requests.length).toBe(1);
			const payload = requests[0]?.attachments as Array<{
				name: string;
				type: string;
				data: string;
			}>;
			expect(payload.map((file) => file.name)).toEqual([
				'nameplate.jpg',
				'schematic.pdf',
			]);
			expect(payload.every((file) => file.data.length > 0)).toBe(true);
			expect(requests[0]?.messages.at(-1)?.content).toContain(
				'Alpha heard Beta'
			);
			expect(errors).toEqual([]);
			rows.push({
				name: `capabilities-${locale}-${width}`,
				states: [
					'IME-no-turn',
					'shift-enter',
					'voice-no-autostart',
					'selection-insert',
					'stop-late-ignored',
					'refused-preserved',
					'empty-picker',
					'image-PDF-transport',
				],
				turns: 1,
				errors,
			});
		});
	}
}
async function nativeScope(page: Page, nonce?: string) {
	return page.evaluate(async (forced) => {
		const mount = document.querySelector<HTMLElement>(
			'[data-linker-app="genie"]'
		)!;
		const tab =
			sessionStorage.getItem('linker-genie-entry-tab') ??
			crypto.randomUUID();
		sessionStorage.setItem('linker-genie-entry-tab', tab);
		const response = await fetch(
			`${mount.dataset.restUrl}linker-ai/v1/genie/entry-context`,
			{
				method: 'POST',
				credentials: 'same-origin',
				cache: 'no-store',
				headers: {
					'Content-Type': 'application/json',
					'X-WP-Nonce': forced ?? mount.dataset.restNonce ?? '',
				},
				body: JSON.stringify({ tab }),
			}
		);
		const body = await response.json();
		return {
			status: response.status,
			keys: Object.keys(body),
			scope: body.scope as string | undefined,
			cache: response.headers.get('cache-control'),
			vary: response.headers.get('vary'),
		};
	}, nonce);
}
for (const locale of ['en', 'de'] as const) {
	test(`native-scope-${locale}: guest epoch, native login/logout, stale nonce and zero cached private rendering`, async ({
		page,
	}) => {
		const width = locale === 'en' ? 1440 : 390;
		const { source, composer, requests, errors } = await prepare(
			page,
			locale,
			width,
			paths.residential[locale]
		);
		const note = `PRIVATE ${locale} UNSENT ENTRY`;
		await source.fill(note);
		await page
			.locator('#system-search [data-linker-assistant-open="attach"]')
			.click();
		await expect(composer).toHaveValue(note);
		const guest = await nativeScope(page);
		expect(guest.status).toBe(200);
		expect(guest.keys).toEqual(['scope']);
		expect(guest.cache).toContain('no-store');
		expect(guest.vary).toMatch(/Cookie/i);
		expect(
			(await nativeScope(page, 'deliberately-expired-nonce')).status
		).toBe(403);
		await page.context().clearCookies({ name: 'linker_genie_browser' });
		const nextGuest = await nativeScope(page);
		expect(nextGuest.scope).not.toBe(guest.scope);
		await page.addInitScript(() => {
			const seen: string[] = [];
			const descriptor = Object.getOwnPropertyDescriptor(
				HTMLTextAreaElement.prototype,
				'value'
			)!;
			Object.defineProperty(HTMLTextAreaElement.prototype, 'value', {
				...descriptor,
				set(value: string) {
					seen.push(String(value));
					descriptor.set!.call(this, value);
				},
			});
			Object.assign(window, { __entryPainted: seen });
		});
		await page.reload();
		await expect(source).toHaveAttribute('data-genie-entry-bound', '1');
		await expect
			.poll(() =>
				page.evaluate(() =>
					sessionStorage.getItem('linker-genie-entry-draft')
				)
			)
			.toBeNull();
		await page.evaluate(() =>
			window.dispatchEvent(
				new CustomEvent('linker-genie-ask', {
					detail: { refresh: true },
				})
			)
		);
		await expect(composer).toHaveValue('');
		expect(
			await page.evaluate(() =>
				(
					window as unknown as { __entryPainted: string[] }
				).__entryPainted.some((text) => text.includes('PRIVATE'))
			)
		).toBe(false);
		await page.goto(loginLink(undefined, 'customer-18'));
		await page.goto(`${instance().url}${paths.residential[locale]}`);
		const signed = await nativeScope(page);
		expect(signed.status).toBe(200);
		expect(signed.scope).not.toBe(nextGuest.scope);
		await source.fill(note);
		await page
			.locator('#system-search [data-linker-assistant-open="attach"]')
			.click();
		await expect(composer).toHaveValue(note);
		const logout = await page
			.locator('a[href*="action=logout"]')
			.first()
			.getAttribute('href');
		expect(logout).toBeTruthy();
		await page.goto(logout!);
		await page.goto(`${instance().url}${paths.residential[locale]}`);
		const loggedOut = await nativeScope(page);
		expect(loggedOut.status).toBe(200);
		expect(loggedOut.scope).not.toBe(signed.scope);
		await expect
			.poll(() =>
				page.evaluate(() =>
					sessionStorage.getItem('linker-genie-entry-draft')
				)
			)
			.toBeNull();
		await page.evaluate(() =>
			window.dispatchEvent(
				new CustomEvent('linker-genie-ask', {
					detail: { refresh: true },
				})
			)
		);
		await expect(composer).toHaveValue('');
		expect(
			await page.evaluate(() =>
				(
					window as unknown as { __entryPainted: string[] }
				).__entryPainted.some((text) => text.includes('PRIVATE'))
			)
		).toBe(false);
		expect(requests).toHaveLength(0);
		expect(errors).toEqual([]);
		await snapshot(page, `native-scope-${locale}-after-logout`);
		rows.push({
			name: `native-scope-${locale}`,
			states: [
				'native-private-response',
				'invalid-nonce-rejected',
				'guest-epoch-change',
				'zero-private-paint',
				'native-login',
				'native-logout',
			],
			turns: 0,
			errors,
		});
	});
}

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`home-recovery-${locale}-${width}: actual controller outage, new draft preserved, explicit recovery`, async ({
			page,
		}) => {
			let available = false;
			const original =
				locale === 'de'
					? 'Meine ursprüngliche Frage zum Schaltplan.'
					: 'My original schematic question.';
			await page.addInitScript(
				({ text }) =>
					sessionStorage.setItem(
						'linker-genie-turn-failure',
						JSON.stringify({
							v: 1,
							kind: null,
							text,
							question: text,
							uploads: [],
							omitted: [],
							entryId: 'home-scope-fixture',
							entryScope: 'a'.repeat(64),
						})
					),
				{ text: original }
			);
			await page.route(
				'**/wp-json/linker-ai/v1/genie/entry-context',
				(route) =>
					available
						? route.fulfill({ json: { scope: 'a'.repeat(64) } })
						: route.fulfill({
								status: 503,
								json: { code: 'fixture-scope-unavailable' },
							})
			);
			const { source, requests, errors } = await prepare(
				page,
				locale,
				width,
				locale === 'de' ? '/de/' : '/'
			);
			const surface = page.locator('#linker-genie-hero-surface');
			await expect(surface).toBeVisible();
			await expect(source).toHaveValue('');
			await expect(surface).not.toContainText(original);
			await expect(
				surface.getByRole('button', {
					name: /^(Try again|Erneut versuchen)$/,
				})
			).toBeVisible();
			await snapshot(page, `home-recovery-${locale}-${width}-outage`);
			const fresh =
				locale === 'de'
					? 'Mein neuer ungesendeter Entwurf.'
					: 'My new unsent draft.';
			await source.fill(fresh);
			available = true;
			await surface
				.getByRole('button', { name: /^(Try again|Erneut versuchen)$/ })
				.click();
			await expect(source).toHaveValue(fresh);
			await expect(
				surface.locator('[data-genie-parked-draft]')
			).toContainText(original);
			expect(requests).toHaveLength(0);
			await snapshot(page, `home-recovery-${locale}-${width}-parked`);
			await surface
				.getByRole('button', {
					name: /^(Restore unsent draft|Bisherigen Entwurf wiederherstellen)$/,
				})
				.click();
			await expect(source).toHaveValue(original);
			await expect(
				surface.locator('[data-genie-parked-draft]')
			).toContainText(fresh);
			expect(requests).toHaveLength(0);
			expect(errors).toEqual([]);
			await snapshot(page, `home-recovery-${locale}-${width}-restored`);
			rows.push({
				name: `home-recovery-${locale}-${width}`,
				states: [
					'real-controller',
					'scope-503-no-private-paint',
					'new-draft-preserved',
					'verified-park',
					'explicit-swap',
				],
				turns: 0,
				fixtures: ['turn/history', 'scope-503→verified-fixture'],
				errors,
			});
		});
	}
}

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`bootstrap-${locale}-${width}: Close/Esc, real late-ready, safe reopen, new intent and workspace recovery`, async ({
			page,
		}) => {
			const { source, send, requests, errors, composer } = await prepare(
				page,
				locale,
				width,
				paths.residential[locale]
			);
			let rejectBundle = true;
			let appURL = '';
			await page.route(
				'**/plugins/linker-tools/build/genie.js?*',
				(route) => {
					appURL = route.request().url();
					return rejectBundle
						? route.abort('failed')
						: route.continue();
				}
			);
			const original =
				locale === 'de'
					? 'Meine ursprüngliche Frage bleibt erhalten.'
					: 'Keep my original question.';
			await source.fill(original);
			await send.click();
			const fallback = page.locator('[data-linker-genie-load-error]');
			const retry = fallback.locator(
				'.linker-genie-load-error__actions button'
			);
			const close = fallback.getByRole('button', {
				name: /^(Close|Schließen)$/,
			});
			await expect(fallback).toBeVisible();
			await expect(close).toBeVisible();
			await expect(retry).toBeFocused();
			if (width === 390) {
				await expect(page.getByRole('dialog')).toHaveAttribute(
					'aria-modal',
					'true'
				);
				for (let i = 0; i < 8; i++) {
					await page.keyboard.press('Tab');
					expect(
						await page.evaluate(
							() =>
								!!document.activeElement?.closest(
									'[data-linker-genie-mount]'
								)
						)
					).toBe(true);
				}
			}
			await snapshot(page, `bootstrap-${locale}-${width}-helper-failed`);
			// Retry fails again, then native Esc must still return to the page's original Send.
			await retry.click();
			await expect(fallback).toBeVisible();
			await page.keyboard.press('Escape');
			await expect(
				page.locator('[data-linker-genie-mount]')
			).toBeHidden();
			await expect(send).toBeFocused();
			await expect(source).toHaveValue(original);
			expect(requests).toHaveLength(0);
			// The real previously unavailable bundle finishes after dismissal: its real ready event must not reopen/send.
			rejectBundle = false;
			await page.evaluate(() => {
				Object.assign(window, { __lateGenieReady: false });
				window.addEventListener(
					'linker-genie-ready',
					() => Object.assign(window, { __lateGenieReady: true }),
					{ once: true }
				);
			});
			await page.addScriptTag({ url: appURL });
			await expect
				.poll(() =>
					page.evaluate(
						() =>
							(window as unknown as { __lateGenieReady: boolean })
								.__lateGenieReady
					)
				)
				.toBe(true);
			await expect(
				page.locator('[data-linker-genie-mount]')
			).toBeHidden();
			expect(requests).toHaveLength(0);
			await page.evaluate(() =>
				window.dispatchEvent(
					new CustomEvent('linker-genie-ask', {
						detail: {
							refresh: true,
							opener: document.querySelector(
								'#system-search .lk-send-btn'
							),
						},
					})
				)
			);
			await expect(page.getByRole('dialog')).toBeVisible();
			await expect(page.getByRole('dialog')).toContainText(original);
			expect(requests).toHaveLength(0);
			await snapshot(page, `bootstrap-${locale}-${width}-safe-reopen`);
			await page.keyboard.press('Escape');
			await expect(send).toBeFocused();
			const latest =
				locale === 'de'
					? 'Diese neue Frage möchte ich senden.'
					: 'Send this different new question.';
			await source.fill(latest);
			await send.click();
			const incoming = page
				.locator('[data-genie-entry-review]')
				.filter({ hasText: latest });
			await expect(incoming).toBeVisible();
			expect(requests).toHaveLength(0);
			await snapshot(page, `bootstrap-${locale}-${width}-new-intent`);
			await incoming
				.getByRole('button', {
					name: /^(Send question separately|Frage separat senden)$/,
				})
				.click();
			await expect.poll(() => requests.length).toBe(1);
			expect(
				requests[0]?.messages.filter((item) => item.role === 'user')
			).toEqual([{ role: 'user', content: latest }]);
			await page.keyboard.press('Escape');
			await expect(send).toBeFocused();
			rejectBundle = true;
			await page.goto(
				`${instance().url}${locale === 'de' ? '/de/genie/' : '/genie/'}`
			);
			await expect(fallback).toBeVisible();
			await expect(
				fallback.getByRole('button', { name: /^(Close|Schließen)$/ })
			).toHaveCount(0);
			await page.keyboard.press('Escape');
			await expect(fallback).toBeVisible();
			await snapshot(
				page,
				`bootstrap-${locale}-${width}-workspace-failed`
			);
			rejectBundle = false;
			await retry.click();
			await expect(composer).toBeVisible();
			expect(requests).toHaveLength(1);
			expect(errors).toEqual([]);
			rows.push({
				name: `bootstrap-${locale}-${width}`,
				states: [
					'native-failure-retry',
					'native-phone-dialog-account-trap',
					'Esc-original-opener',
					'real-late-ready-no-reopen',
					'plain-reopen-no-turn',
					'different-intent-not-old-question',
					'workspace-no-close',
					'workspace-retry',
				],
				turns: 1,
				errors,
			});
		});
	}
}
