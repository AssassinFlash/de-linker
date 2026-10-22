/** Published LC + real App/controller/preparation/native guest authority; model/history are fixtures. */
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { instance, loginLink, REPO_ROOT } from '../lib/instance';

const OUTPUT = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/genie-failure-ownership/browser',
	process.env.LINKER_FAILURE_RUN ??
		new Date().toISOString().replaceAll(/[-:.]/g, '')
);
const scopeKey = 'linker-genie-turn-failure:v2:';
test.use({ reducedMotion: 'reduce' });
test.describe.configure({ timeout: 60000 });
test.afterEach(async ({ page }, info) => {
	mkdirSync(OUTPUT, { recursive: true });
	const directory = join(OUTPUT, 'case-results');
	mkdirSync(directory, { recursive: true });
	if (info.status !== info.expectedStatus)
		await page.screenshot({
			path: join(
				OUTPUT,
				'failed-' + info.testId.replaceAll(/[^a-z0-9-]/gi, '_') + '.png'
			),
		});
	writeFileSync(
		join(directory, info.testId.replaceAll(/[^a-z0-9-]/gi, '_') + '.json'),
		JSON.stringify(
			{
				title: info.title,
				status: info.status,
				expectedStatus: info.expectedStatus,
				finishedAt: new Date().toISOString(),
				url: page.url(),
				viewport: page.viewportSize(),
				errors: info.errors.map((error) => error.message),
			},
			null,
			2
		)
	);
	const cases = readdirSync(directory)
		.filter((name) => name.endsWith('.json'))
		.map((name) => JSON.parse(readFileSync(join(directory, name), 'utf8')));
	writeFileSync(
		join(OUTPUT, 'summary.json'),
		JSON.stringify(
			{
				source: 'published local LC + App/startHero/native scope guest rotation/login/logout and real PDF preparation; turn/history plus selected scope503/storage exceptions are explicit fixtures, no external model or email',
				cases,
			},
			null,
			2
		)
	);
});
function workspace(locale: 'en' | 'de') {
	return locale === 'de' ? '/de/genie/' : '/genie/';
}
function home(locale: 'en' | 'de') {
	return locale === 'de' ? '/de/' : '/';
}
async function navigate(page: Page, path: string) {
	await page.goto(instance().url + path);
	const reject = page.getByRole('button', {
		name: /^(Reject all|Alle ablehnen)$/,
	});
	if (await reject.isVisible()) await reject.click();
}
async function nativeOwner(page: Page) {
	return page.evaluate(async () => {
		const mount = document.querySelector<HTMLElement>(
			'[data-linker-app="genie"]'
		)!;
		const tab = sessionStorage.getItem('linker-genie-entry-tab');
		const response = await fetch(
			`${mount.dataset.restUrl}linker-ai/v1/genie/entry-context`,
			{
				method: 'POST',
				credentials: 'same-origin',
				cache: 'no-store',
				headers: {
					'Content-Type': 'application/json',
					'X-WP-Nonce': mount.dataset.restNonce ?? '',
				},
				body: JSON.stringify({ tab }),
			}
		);
		const value = await response.json();
		return {
			scope: value.scope as string,
			status: response.status,
			cache: response.headers.get('cache-control'),
			vary: response.headers.get('vary'),
		};
	});
}
async function capture(page: Page, name: string) {
	mkdirSync(OUTPUT, { recursive: true });
	await page.evaluate(async () => {
		await document.fonts.ready;
		document.getAnimations().forEach((a) => {
			if (a.effect?.getComputedTiming().iterations !== Infinity) {
				try {
					a.finish();
				} catch {
					/* inactive transition */
				}
			}
		});
	});
	const geometry = await page
		.locator(
			'.linker-genie-app__prompt:visible,.linker-genie-app__attachment-remove:visible'
		)
		.evaluateAll((nodes) =>
			nodes.map((node) => {
				const r = node.getBoundingClientRect();
				return {
					text: node.textContent,
					label: node.getAttribute('aria-label'),
					x: r.x,
					y: r.y,
					width: r.width,
					height: r.height,
				};
			})
		);
	for (const item of geometry) {
		expect(item.height, `${name}: control height`).toBeGreaterThanOrEqual(
			43.5
		);
		expect(item.x, `${name}: control left`).toBeGreaterThanOrEqual(0);
		expect(
			item.x + item.width,
			`${name}: control right`
		).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
	}
	await page.screenshot({ path: join(OUTPUT, name + '.png') });
	writeFileSync(
		join(OUTPUT, name + '.json'),
		JSON.stringify(
			{
				capturedAt: new Date().toISOString(),
				url: page.url(),
				viewport: page.viewportSize(),
				geometry,
			},
			null,
			2
		)
	);
}
async function fixtures(page: Page, locale: 'en' | 'de') {
	const turns: Record<string, unknown>[] = [];
	let fail = true;
	let unavailable = false;
	let forbidden = false;
	await page.route('**/wp-json/linker-ai/v1/genie/entry-context', (route) =>
		unavailable
			? route.fulfill({
					status: 503,
					json: { code: 'fixture_scope_outage' },
				})
			: route.continue()
	);
	await page.route('**/wp-json/linker-ai/v1/genie/conversation', (route) =>
		forbidden
			? route.fulfill({
					status: 403,
					json: { code: 'fixture_history_forbidden' },
				})
			: route.fulfill({ json: { messages: [], stream: '' } })
	);
	await page.route('**/wp-json/linker-ai/v1/genie/conversations', (route) =>
		route.fulfill({ json: { current_id: 0, conversations: [] } })
	);
	await page.route('**/wp-json/linker-ai/v1/genie/turn', (route) => {
		turns.push(route.request().postDataJSON());
		if (fail)
			return route.fulfill({
				status: 502,
				json: { code: 'fixture_upstream', message: 'fixture only' },
			});
		const stream = [
			[
				'meta',
				{
					turn_id: turns.length,
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
							? 'Ihre neue Frage wurde beantwortet.'
							: 'Your current question was answered.',
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
	return {
		turns,
		success: () => {
			fail = false;
		},
		outage: (value: boolean) => {
			unavailable = value;
		},
		denyHistory: () => {
			forbidden = true;
		},
	};
}
for (const locale of ['en', 'de'] as const)
	for (const width of [1440, 390]) {
		for (const surface of ['home', 'workspace'] as const) {
			test(`ordinary-${surface}-${locale}-${width}: real producer retains A while guest B writes separately and A explicitly restores`, async ({
				page,
			}, info) => {
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 1000,
				});
				const fixture = await fixtures(page, locale);
				const label = `${surface}-${locale}-${width}`;
				const privateA =
					locale === 'de'
						? 'Private Projektfrage von Gast A'
						: 'Private project question from guest A';
				const filename = 'guest-A-private-plan.pdf';
				await navigate(
					page,
					surface === 'home' ? home(locale) : workspace(locale)
				);
				const field = page.locator(
					surface === 'home' ? '.hero-prompt' : '#linker-genie-input'
				);
				await expect(field).toBeEnabled();
				const a = await nativeOwner(page);
				expect(a.status).toBe(200);
				expect(a.scope).toMatch(/^[a-f0-9]{64}$/);
				const cookieA = (await page.context().cookies()).find(
					(cookie) => cookie.name === 'linker_genie_browser'
				);
				expect(cookieA).toBeTruthy();
				await field.fill(privateA);
				if (surface === 'home') {
					await page
						.locator('input[type=file]')
						.first()
						.setInputFiles({
							name: filename,
							mimeType: 'application/pdf',
							buffer: Buffer.from('%PDF-1.4\nPRIVATE-A-PLANNING'),
						});
				} else await page.locator('.linker-genie-app__send').click();
				await expect.poll(() => fixture.turns.length).toBe(1);
				await expect(
					page.getByRole('button', {
						name: /^(Try again|Erneut versuchen)$/,
					})
				).toBeVisible();
				const storedA = await page.evaluate(
					(key) => sessionStorage.getItem(key),
					scopeKey + a.scope
				);
				expect(storedA).toContain(privateA);
				if (surface === 'home') expect(storedA).toContain(filename);
				await capture(page, label + '-A-failed');
				await page
					.context()
					.clearCookies({ name: 'linker_genie_browser' });
				if (width === 390) fixture.denyHistory();
				await navigate(page, workspace(locale));
				const current = page.locator('#linker-genie-input');
				await expect(current).toBeEnabled();
				const b = await nativeOwner(page);
				expect(b.scope).not.toBe(a.scope);
				await expect(current).toHaveValue('');
				await expect(page.locator('body')).not.toContainText(privateA);
				await expect(page.locator('body')).not.toContainText(filename);
				expect(fixture.turns.length).toBe(1);
				await capture(page, label + '-B-no-private-recovery');
				await current.fill(
					locale === 'de'
						? 'Gast B stellt eine eigene Frage'
						: 'Guest B asks its own question'
				);
				await page.locator('.linker-genie-app__send').click();
				await expect.poll(() => fixture.turns.length).toBe(2);
				expect(
					await page.evaluate(
						(key) => sessionStorage.getItem(key),
						scopeKey + a.scope
					)
				).toBe(storedA);
				expect(
					await page.evaluate(
						(key) => sessionStorage.getItem(key),
						scopeKey + b.scope
					)
				).toContain('"owner"');
				await page
					.context()
					.clearCookies({ name: 'linker_genie_browser' });
				await page.context().addCookies([cookieA!]);
				await navigate(page, workspace(locale));
				await expect(current).toBeEnabled();
				const returned = await nativeOwner(page);
				expect(returned.scope).toBe(a.scope);
				await expect(
					page.getByRole('button', {
						name: /^(Restore unsent draft|Bisherigen Entwurf wiederherstellen)$/,
					})
				).toBeVisible();
				expect(fixture.turns.length).toBe(2);
				await capture(page, label + '-A-explicit-recovery');
				await page
					.getByRole('button', {
						name: /^(Restore unsent draft|Bisherigen Entwurf wiederherstellen)$/,
					})
					.click();
				await expect(current).toHaveValue(privateA);
				if (surface === 'home')
					await expect(
						page.locator('.linker-genie-app__attachment-name')
					).toContainText(filename);
				fixture.success();
				await page
					.getByRole('button', {
						name: /^(Try again|Erneut versuchen)$/,
					})
					.click();
				await expect.poll(() => fixture.turns.length).toBe(3);
				const request = fixture.turns[2]!;
				expect(JSON.stringify(request)).toContain(privateA);
				if (surface === 'home')
					expect(JSON.stringify(request)).toContain(filename);
				await expect(page.locator('body')).toContainText(
					locale === 'de'
						? 'Ihre neue Frage wurde beantwortet.'
						: 'Your current question was answered.'
				);
				await capture(page, label + '-A-retry-success');
				writeFileSync(
					join(
						OUTPUT,
						info.testId.replaceAll(/[^a-z0-9-]/gi, '_') +
							'-case.json'
					),
					JSON.stringify(
						{
							title: info.title,
							status: 'passed',
							native: {
								a: a.status,
								b: b.status,
								returned: returned.status,
								rotated: b.scope !== a.scope,
								restored: returned.scope === a.scope,
							},
							surface,
							locale,
							width,
							turns: fixture.turns.length,
							source: 'actual ordinary producer + actual PDF preparation for home; actual native guest-cookie rotation/authority; history empty/403 and model fixtures; no marketing binder or seeded failure',
						},
						null,
						2
					)
				);
			});
		}
		test(`ordinary-outage-${locale}-${width}: pending native lookup quarantines accepted text and auxiliary retry makes no model turn`, async ({
			page,
		}) => {
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 1000,
			});
			const fixture = await fixtures(page, locale);
			await navigate(page, workspace(locale));
			const field = page.locator('#linker-genie-input');
			await expect(field).toBeEnabled();
			const text =
				locale === 'de'
					? 'Angenommene Frage bleibt bei diesem Gast'
					: 'Accepted question remains with this guest';
			await field.fill(text);
			fixture.outage(true);
			await page.locator('.linker-genie-app__send').click();
			await expect(field).toBeDisabled();
			await expect(field).toHaveValue('');
			expect(fixture.turns.length).toBe(0);
			await capture(page, `outage-${locale}-${width}-hidden-retry`);
			fixture.outage(false);
			await page
				.getByRole('button', { name: /^(Try again|Erneut versuchen)$/ })
				.click();
			await expect(field).toBeEnabled();
			await expect(field).toHaveValue(text);
			expect(fixture.turns.length).toBe(0);
			await capture(page, `outage-${locale}-${width}-verified-retry`);
		});
	}

for (const locale of ['en', 'de'] as const) {
	test(`ordinary-auth-${locale}: native logout and same-account new session cannot claim the previous failure`, async ({
		page,
	}) => {
		await page.setViewportSize({
			width: locale === 'en' ? 1440 : 390,
			height: 1000,
		});
		const fixture = await fixtures(page, locale);
		await page.goto(loginLink(undefined, 'customer-18'));
		await navigate(page, workspace(locale));
		const field = page.locator('#linker-genie-input');
		await expect(field).toBeEnabled();
		const first = await nativeOwner(page);
		const privateText =
			'Same-account earlier authenticated session private plan';
		await field.fill(privateText);
		await page.locator('.linker-genie-app__send').click();
		await expect.poll(() => fixture.turns.length).toBe(1);
		await expect(
			page.getByRole('button', { name: /^(Try again|Erneut versuchen)$/ })
		).toBeVisible();
		const logout = await page
			.locator('a[href*="action=logout"]')
			.first()
			.getAttribute('href');
		expect(logout).toBeTruthy();
		await page.goto(logout!);
		await navigate(page, workspace(locale));
		await expect(field).toBeEnabled();
		const guest = await nativeOwner(page);
		expect(guest.scope).not.toBe(first.scope);
		await expect(field).toHaveValue('');
		await expect(page.locator('body')).not.toContainText(privateText);
		await page.goto(loginLink(undefined, 'customer-18'));
		await navigate(page, workspace(locale));
		await expect(field).toBeEnabled();
		const next = await nativeOwner(page);
		expect(next.scope).not.toBe(first.scope);
		await expect(field).toHaveValue('');
		await expect(page.locator('body')).not.toContainText(privateText);
		expect(fixture.turns.length).toBe(1);
		expect(
			await page.evaluate(
				(key) => sessionStorage.getItem(key),
				scopeKey + first.scope
			)
		).toContain(privateText);
		await capture(page, `auth-${locale}-rotated-no-private-recovery`);
	});
}
for (const locale of ['en', 'de'] as const)
	for (const method of ['getItem', 'setItem'] as const) {
		test(`ordinary-memory-${locale}-${method}: current mount warns and retries under native memory-tab ownership`, async ({
			page,
		}) => {
			await page.setViewportSize({
				width: locale === 'en' ? 1440 : 390,
				height: 1000,
			});
			await page.addInitScript((method) => {
				const original = Storage.prototype[method];
				Object.defineProperty(Storage.prototype, method, {
					configurable: true,
					value: function (
						this: Storage,
						key: string,
						value?: string
					) {
						if (key.startsWith('linker-genie-'))
							throw new DOMException(
								'fixture storage denied',
								'SecurityError'
							);
						return method === 'getItem'
							? (
									original as typeof Storage.prototype.getItem
								).call(this, key)
							: (
									original as typeof Storage.prototype.setItem
								).call(this, key, value!);
					},
				});
			}, method);
			const fixture = await fixtures(page, locale);
			await navigate(page, workspace(locale));
			const field = page.locator('#linker-genie-input');
			await expect(field).toBeEnabled();
			await field.fill(
				locale === 'de'
					? 'Eigene Frage ohne gespeicherten Entwurf'
					: 'Own question without persisted draft'
			);
			await page.locator('.linker-genie-app__send').click();
			await expect.poll(() => fixture.turns.length).toBe(1);
			await expect(page.locator('body')).toContainText(
				locale === 'de'
					? 'Ihre Frage konnte nicht gespeichert werden.'
					: 'This question could not be saved.'
			);
			await capture(page, `memory-${locale}-${method}-warning`);
			fixture.success();
			await page
				.getByRole('button', { name: /^(Try again|Erneut versuchen)$/ })
				.click();
			await expect.poll(() => fixture.turns.length).toBe(2);
			await expect(page.locator('body')).toContainText(
				locale === 'de'
					? 'Ihre neue Frage wurde beantwortet.'
					: 'Your current question was answered.'
			);
			await capture(page, `memory-${locale}-${method}-retry-success`);
		});
	}
