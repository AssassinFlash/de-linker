import {
	launchHomepageConfigurator,
	compareSavedFromHome,
} from '../lib/home-configurator';
import { resumePlannerProject } from '../lib/resume-planner-project';
import { randomUUID } from 'node:crypto';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { instance, isolateMailBudgets, wp } from '../lib/instance';

const words = {
	en: {
		home: '/',
		intake: 'Compare project options',
		title: 'Project name',
		location: 'Town or site',
		siteUse: 'Site use',
		phase: 'Grid connection',
		load: 'Backup load',
		duration: 'Required duration',
		existing: 'There is an existing system',
		existingName: 'Existing system name',
		existingPower: 'Existing inverter power (kW)',
		keep: 'Keep the existing inverter',
		inverter: 'Inverter or integrated storage system',
		saved: 'Saved projects',
		systemName: 'System name',
		compare: 'Compare systems',
		select: 'Use this configuration',
		review: 'Review your inquiry',
		send: 'Send inquiry',
		received: 'Inquiry received',
		report: 'Download PDF',
		message:
			'Please check availability for the equipment above and tell me whether any additional parts are needed for installation.',
	},
	de: {
		home: '/de/',
		intake: 'Projektoptionen vergleichen',
		title: 'Projektname',
		location: 'Ort oder Standort',
		siteUse: 'Nutzung des Standorts',
		phase: 'Netzanschluss',
		load: 'Ersatzstromlast',
		duration: 'Gewünschte Dauer',
		existing: 'Eine Anlage ist bereits vorhanden',
		existingName: 'Bezeichnung der vorhandenen Anlage',
		existingPower: 'Leistung des vorhandenen Wechselrichters (kW)',
		keep: 'Vorhandenen Wechselrichter beibehalten',
		inverter: 'Wechselrichter oder integriertes Speichersystem',
		saved: 'Gespeicherte Projekte',
		systemName: 'Systemname',
		compare: 'Systeme vergleichen',
		select: 'Konfiguration übernehmen',
		review: 'Anfrage prüfen',
		send: 'Anfrage senden',
		received: 'Anfrage eingegangen',
		report: 'PDF herunterladen',
		message:
			'Bitte prüfen Sie die Verfügbarkeit der aufgeführten Geräte und teilen Sie mir mit, ob für die Installation weitere Teile erforderlich sind.',
	},
} as const;

type Locale = keyof typeof words;

interface Scenario {
	name: string;
	country: 'DE' | 'NL';
	town: string;
	use: 'residential' | 'commercial';
	scope: 'new_pv_storage' | 'storage_addition' | 'storage_only' | 'pv_only';
	solar?: string;
	backup?: readonly [load: string, duration: string];
	retainedInverter?: { name: string; power: string };
	selectedInverter?: string;
	systems?: readonly string[];
	carried?: boolean;
}

// Customer sample inputs follow the Berlin, Rotterdam, Konstanz and
// Eindhoven cases in docs/acceptance/2026-11-17/demand-to-system.md.
const scenarios: readonly Scenario[] = [
	{
		name: 'storage only',
		country: 'DE',
		town: 'Berlin',
		use: 'residential',
		scope: 'storage_only',
		backup: ['3', '2'],
	},
	{
		name: 'new solar and storage',
		country: 'NL',
		town: 'Rotterdam',
		use: 'residential',
		scope: 'new_pv_storage',
		solar: '10',
		backup: ['3', '2'],
	},
	{
		name: 'existing PV with known capacity',
		country: 'DE',
		town: 'Konstanz',
		use: 'residential',
		scope: 'storage_addition',
		solar: '8',
	},
	{
		name: 'retrofit keeping the installed inverter',
		country: 'DE',
		town: 'Berlin',
		use: 'residential',
		scope: 'storage_addition',
		backup: ['3', '2'],
		retainedInverter: { name: 'Workshop inverter', power: '7.5' },
	},
	{
		name: 'already selected equipment',
		country: 'NL',
		town: 'Rotterdam',
		use: 'residential',
		scope: 'pv_only',
		solar: '10',
		selectedInverter: 'SAJ HS2-10K-T2-X',
	},
	{
		name: 'solar only',
		country: 'NL',
		town: 'Rotterdam',
		use: 'residential',
		scope: 'pv_only',
		solar: '10',
	},
	{
		name: 'larger multi-system project',
		country: 'NL',
		town: 'Eindhoven',
		use: 'commercial',
		scope: 'storage_only',
		backup: ['10', '4'],
		systems: ['Workshop', 'Warehouse'],
	},
	{
		name: 'saved project on a return visit',
		country: 'DE',
		town: 'Berlin',
		use: 'residential',
		scope: 'storage_only',
		backup: ['3', '2'],
		carried: true,
	},
];

async function enterProject(
	intake: Locator,
	scenario: Scenario,
	title: string,
	text: (typeof words)[Locale]
) {
	await intake.getByLabel(text.title).fill(title);
	await intake.locator('select[name=country]').selectOption(scenario.country);
	await intake.getByLabel(text.location).fill(scenario.town);
	await intake
		.locator('select[name=system_scope]')
		.selectOption(scenario.scope);
	await intake.getByLabel(text.siteUse).selectOption(scenario.use);
	await intake
		.locator('select[name=project_purpose]')
		.selectOption(scenario.backup ? 'backup' : 'self');
	await intake.getByLabel(text.phase).selectOption('3');
	if (scenario.backup) {
		await intake.getByLabel(text.load).fill(scenario.backup[0]);
		await intake.getByLabel(text.duration).fill(scenario.backup[1]);
	}
	if (scenario.solar)
		await intake.locator('[name=pv_dc_kw]').fill(scenario.solar);
	if (scenario.retainedInverter) {
		await intake.getByLabel(text.existing).check();
		await intake
			.getByLabel(text.existingName)
			.fill(scenario.retainedInverter.name);
		await intake
			.getByLabel(text.existingPower)
			.fill(scenario.retainedInverter.power);
		await intake.getByLabel(text.keep).check();
	}
	if (scenario.selectedInverter || scenario.systems) {
		const equipment = intake.locator('details.sc-project-equipment');
		if (
			!(await equipment.evaluate(
				(section: HTMLDetailsElement) => section.open
			))
		)
			await equipment.locator('summary').first().click();
	}
	if (scenario.selectedInverter)
		await intake
			.getByLabel(text.inverter)
			.selectOption({ label: scenario.selectedInverter });
	if (scenario.systems) {
		await intake
			.getByRole('button', {
				name: /^Multiple systems$|^Mehrere Systeme$/,
			})
			.click();
		const names = intake.getByLabel(text.systemName, { exact: true });
		await expect(names).toHaveCount(scenario.systems.length);
		for (const [index, name] of scenario.systems.entries()) {
			await names.nth(index).fill(name);
		}
	}
}

interface ReviewLine {
	label: string;
	quantity: number;
}

async function draftLines(draft: Locator): Promise<ReviewLine[]> {
	return draft.locator('.linker-inquiry-line').evaluateAll((rows) =>
		rows.map((row) => {
			const label = row.querySelector(
				'.linker-inquiry-identity strong'
			)?.textContent;
			const controls = row.querySelector('.linker-inquiry-line-controls');
			const text = controls?.querySelector(
				'.linker-inquiry-stepper span, :scope > span:last-child'
			)?.textContent;
			const match = text?.match(/^(?:× )?(\d+)$/);
			if (!label || !match)
				throw new Error('Expected a product name and its quantity');
			return { label, quantity: Number(match[1]) };
		})
	);
}

const lineOrder = (a: ReviewLine, b: ReviewLine) =>
	a.label.localeCompare(b.label) || a.quantity - b.quantity;

function reply(page: Page, operation: string) {
	return page.waitForResponse(
		(response) =>
			response.request().method() === 'POST' &&
			new URL(response.url()).pathname.endsWith('/' + operation),
		{ timeout: 120_000 }
	);
}

async function screen(page: Page, width: number, name?: string) {
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
	expect(
		await page.evaluate(() => document.documentElement.scrollWidth)
	).toBe(width);
	if (name) {
		await page.screenshot({
			path: test.info().outputPath(name + '.png'),
			animations: 'disabled',
		});
	}
}

function receivedOrder(email: string) {
	return JSON.parse(
		wp([
			'eval',
			String.raw`
			if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
				throw new RuntimeException( 'A local WordPress mail sink is required.' );
			}
			$orders = wc_get_orders( array( 'billing_email' => '${email}', 'limit' => 2 ) );
			if ( count( $orders ) !== 1 ) { throw new RuntimeException( 'Expected one inquiry' ); }
			$order = $orders[0];
			$stored = \Linker\Commerce\Planning\Context::stored( $order );
			$lines = array();
			foreach ( $order->get_items() as $line ) {
				$lines[] = array( 'product_id' => $line->get_product_id(), 'label' => $line->get_name(), 'quantity' => $line->get_quantity() );
			}
			echo wp_json_encode( array(
				'id' => $order->get_id(), 'number' => $order->get_order_number(), 'locale' => \Linker\Commerce\Inquiry\OrderLocale::of( $order ),
				'customer' => $order->get_customer_id(), 'status' => $order->get_status(), 'note' => $order->get_customer_note(), 'lines' => $lines,
				'reference' => count( $stored ) === 1 ? reset( $stored )['reference'] : null
			) );
			`,
		])
	) as {
		id: number;
		number: string;
		lines: (ReviewLine & { product_id: number })[];
		reference: { handoff_id: string };
	};
}

test.beforeAll(async ({ request }) => {
	const { url, engineUrl } = instance();
	expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
	const health = await request.get(engineUrl + '/health');
	expect(health.ok(), 'The review Engine must be running').toBe(true);
});

for (const scenario of scenarios) {
	for (const locale of ['en', 'de'] as const) {
		for (const width of [1440, 390]) {
			test(`${locale} ${width}: ${scenario.name} reaches an inquiry receipt in three actions`, async ({
				page,
				context,
			}) => {
				const { url } = instance();
				expect(await context.cookies()).toEqual([]);
				const restoreBudgets = isolateMailBudgets();
				try {
					const text = words[locale];
					const tag = randomUUID();
					const title = `${scenario.town} ${scenario.name} ${tag}`;
					const email = `e2e-guided-${tag}@example.test`;
					const draft = page.locator('.linker-inquiry-draft').filter({
						visible: true,
					});
					await page.setViewportSize({
						width,
						height: width === 390 ? 844 : 900,
					});
					await page.goto(url + text.home);
					const intake = await launchHomepageConfigurator(
						page,
						locale
					);

					let carriedProjectId: string | undefined;
					if (scenario.carried) {
						carriedProjectId =
							await test.step('Prepare a saved project through the homepage on an earlier visit', async () => {
								await enterProject(
									intake,
									scenario,
									title,
									text
								);
								await intake
									.getByRole('button', {
										name: text.compare,
										exact: true,
									})
									.click();
								await expect(
									page
										.getByRole('button', {
											name: text.select,
											exact: true,
										})
										.first()
								).toBeEnabled({ timeout: 120_000 });
								const id = new URL(page.url()).searchParams.get(
									'project'
								);
								expect(id).toMatch(/^[a-f0-9]{32}$/);
								await page.goto(url + text.home);
								return id!;
							});
					}

					await test.step('1. Bring or enter project details and compare', async () => {
						if (carriedProjectId) {
							await compareSavedFromHome(
								page,
								locale,
								carriedProjectId
							);
							return;
						}
						await enterProject(intake, scenario, title, text);
						const compare = intake.getByRole('button', {
							name: text.compare,
							exact: true,
						});
						await compare.scrollIntoViewIfNeeded();
						await screen(
							page,
							width,
							scenario === scenarios[0]
								? 'homepage-project'
								: undefined
						);
						const runReply = reply(page, 'runs/find-equipment');
						await compare.click();
						const run = await runReply;
						expect(run.ok()).toBe(true);
						expect(run.request().postDataJSON()).toMatchObject({
							inputs: {
								brief: {
									project_use: scenario.use,
									system_scope: scenario.scope,
									site: {
										country_code: scenario.country,
										location_label: scenario.town,
									},
								},
							},
						});
					});

					const selected =
						await test.step('2. Select a configuration', async () => {
							const select = page
								.getByRole('button', {
									name: text.select,
									exact: true,
								})
								.first();
							await expect(select).toBeEnabled({
								timeout: 120_000,
							});
							const projectId = new URL(
								page.url()
							).searchParams.get('project');
							expect(projectId).toMatch(/^[a-f0-9]{32}$/);
							if (carriedProjectId)
								expect(projectId).toBe(carriedProjectId);
							await select.scrollIntoViewIfNeeded();
							await screen(
								page,
								width,
								scenario === scenarios[0]
									? 'comparison'
									: undefined
							);

							const reportReply = reply(page, 'runs/report');
							const formReply = reply(page, 'inquiry/form');
							await select.click();
							const [reportResponse, formResponse] =
								await Promise.all([reportReply, formReply]);
							expect(reportResponse.ok()).toBe(true);
							expect(formResponse.ok()).toBe(true);
							const prepared = formResponse
								.request()
								.postDataJSON();
							const generated = reportResponse
								.request()
								.postDataJSON();
							expect(prepared).toMatchObject({
								report_run_id:
									expect.stringMatching(/^[a-f0-9]{32}$/),
								project_id: projectId,
								revision: generated.expected_revision,
							});
							const report = {
								id: prepared.report_run_id,
								revision: prepared.revision,
							};
							await expect(
								page.getByRole('heading', {
									name: text.review,
									exact: true,
								})
							).toBeVisible();
							await expect(
								page.locator('form.linker-inquiry-form')
							).toBeVisible();
							const lines = await draftLines(draft);
							if (scenario.retainedInverter)
								expect(lines).toEqual([]);
							else expect(lines.length).toBeGreaterThan(0);
							if (scenario.selectedInverter)
								expect(
									lines.map(({ label }) => label)
								).toContain(scenario.selectedInverter);
							expect(
								lines.every(({ quantity }) => quantity > 0)
							).toBe(true);
							return { projectId, report, lines };
						});

					await test.step('3. Review, send and receive the inquiry', async () => {
						const form = page.locator('form.linker-inquiry-form');
						await expect(form).toBeVisible();
						await expect(page.locator('html')).toHaveAttribute(
							'lang',
							new RegExp('^' + locale)
						);
						await screen(
							page,
							width,
							scenario === scenarios[0]
								? 'inquiry-review'
								: undefined
						);
						await form
							.locator('[name=name]')
							.fill('E2E project visitor');
						await form.locator('[name=email]').fill(email);
						await form
							.locator('textarea[name=message]')
							.pressSequentially(text.message, {
								delay: 28,
							});
						await form.locator('[name=consent]').check();
						await form
							.getByRole('button', {
								name: text.send,
								exact: true,
							})
							.click();
						await expect(
							page.getByRole('heading', {
								name: text.received,
								exact: true,
							})
						).toBeVisible({ timeout: 90_000 });

						const order = receivedOrder(email);
						expect(order).toMatchObject({
							locale: locale === 'de' ? 'de_DE_formal' : 'en_US',
							customer: 0,
							status: 'inquiry-received',
							note: expect.stringContaining(text.message),
							reference: {
								title,
								handoff_id:
									expect.stringMatching(/^[a-f0-9]{32}$/),
								project_id: selected.projectId,
								report_run_id: selected.report.id,
								revision: selected.report.revision,
							},
						});
						expect(
							order.lines.every(
								({ product_id }: { product_id: number }) =>
									product_id > 0
							)
						).toBe(true);
						expect(
							order.lines
								.map(({ label, quantity }: ReviewLine) => ({
									label,
									quantity,
								}))
								.sort(lineOrder)
						).toEqual(selected.lines.sort(lineOrder));
						await expect(
							page.locator(
								'.woocommerce-order-overview__order strong'
							)
						).toHaveText(order.number);
						const reportLink = page.getByRole('link', {
							name: text.report,
							exact: true,
						});
						await expect(reportLink).toHaveAttribute(
							'href',
							new RegExp(
								`/inquiries/${order.id}/planning-report/${order.reference.handoff_id}`
							)
						);
						const pdf = await context.request.get(
							new URL(
								(await reportLink.getAttribute('href'))!,
								page.url()
							).href
						);
						expect(pdf.ok()).toBe(true);
						expect(
							(await pdf.body()).subarray(0, 5).toString()
						).toBe('%PDF-');
					});
				} finally {
					restoreBudgets();
				}
			});
		}
	}
}

interface NativeCartLine {
	key: string;
	id: number;
	sku: string;
	quantity: number;
	permalink: string;
}

const draftWords = {
	en: {
		enter: 'Enter project details',
		newProject: 'New project',
		storage: 'Continue with storage',
		proposal: 'Review the proposal',
		generate: 'Generate project report',
		add: 'Add selected products to solution draft',
		confirm: 'Confirm and continue to inquiry',
		decline: 'Reject all',
	},
	de: {
		enter: 'Projektdaten eingeben',
		newProject: 'Neues Projekt',
		storage: 'Weiter zum Speicher',
		proposal: 'Lösungsvorschlag prüfen',
		generate: 'Projektbericht erstellen',
		add: 'Ausgewählte Produkte zum Lösungsentwurf hinzufügen',
		confirm: 'Bestätigen und weiter zur Anfrage',
		decline: 'Alle ablehnen',
	},
} as const;

const exactButton = (container: Page | Locator, name: string) =>
	container.getByRole('button', { name, exact: true });

async function keepEarlierProjectInDraft(
	page: Page,
	url: string,
	locale: Locale,
	title: string
) {
	const text = words[locale];
	const draftText = draftWords[locale];
	await page.goto(url + text.home);
	const decline = exactButton(page, draftText.decline);
	if (await decline.isVisible()) await decline.click();
	const workspace = page.locator('[data-linker-planner]');
	const project = await launchHomepageConfigurator(page, locale);
	await project.getByLabel(text.title).fill(title);
	await project.locator('select[name=country]').selectOption('DE');
	await project.getByLabel(text.location).fill('Berlin');
	await project
		.locator('select[name=system_scope]')
		.selectOption('storage_only');
	await project.getByLabel(text.siteUse).selectOption('residential');
	await project
		.locator('select[name=project_purpose]')
		.selectOption('backup');
	await exactButton(project, text.compare).click();
	await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
	await resumePlannerProject(page, locale, title, 'energy');
	await workspace.getByLabel(text.phase).selectOption('3');
	await workspace.getByLabel(text.load).fill('3');
	await workspace.getByLabel(text.duration).fill('2');
	await exactButton(workspace, text.compare).click();
	await exactButton(workspace, text.select)
		.first()
		.click({ timeout: 90_000 });
	await exactButton(workspace, draftText.proposal).click();
	await exactButton(workspace, draftText.generate).click();
	await exactButton(workspace, draftText.add).click({ timeout: 90_000 });
	const applied = reply(page, 'draft/apply');
	await exactButton(workspace, draftText.confirm).click();
	const transfer = await applied;
	expect(transfer.ok()).toBe(true);
	const request = transfer.request().postDataJSON();
	expect(request).toMatchObject({
		project_id: expect.stringMatching(/^[a-f0-9]{32}$/),
		report_run_id: expect.stringMatching(/^[a-f0-9]{32}$/),
	});
	await expect(page.locator('form.linker-inquiry-form')).toBeVisible();
	return { project: request.project_id, report: request.report_run_id };
}

for (const [locale, width] of [
	['en', 1440],
	['de', 390],
] as const) {
	test(`${locale} ${width}: a guided inquiry leaves earlier same-SKU project and manual draft rows intact`, async ({
		page,
		context,
	}) => {
		const { url } = instance();
		const restoreBudgets = isolateMailBudgets();
		try {
			const text = words[locale];
			const tag = randomUUID();
			const title = `Send Berlin project ${tag}`;
			const email = `e2e-mixed-${tag}@example.test`;
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			async function cart() {
				const response = await context.request.get(
					url + '/wp-json/wc/store/v1/cart'
				);
				expect(response.ok()).toBe(true);
				const body: { items: NativeCartLine[] } = await response.json();
				return body.items.map(
					({ key, id, sku, quantity, permalink }) => ({
						key,
						id,
						sku,
						quantity,
						permalink,
					})
				);
			}

			const earlier =
				await test.step('Keep an earlier project and a manual addition in the solution draft', async () => {
					const retained = await keepEarlierProjectInDraft(
						page,
						url,
						locale,
						`Keep earlier Berlin project ${tag}`
					);
					const prior = await cart();
					expect(prior.length).toBeGreaterThan(0);
					const shared = prior[0]!;
					expect(shared.sku).toBeTruthy();
					expect(new URL(shared.permalink).origin).toBe(url);
					await page.goto(shared.permalink);
					await page
						.locator('a[href*="add-to-cart="]:visible')
						.first()
						.click();
					await expect
						.poll(
							async () =>
								(await cart()).filter(
									({ id }) => id === shared.id
								).length,
							{ timeout: 30_000 }
						)
						.toBe(2);
					const mixed = await cart();
					expect(mixed).toEqual(expect.arrayContaining(prior));
					return { ...retained, shared, mixed };
				});

			await page.goto(url + text.home);
			await test.step('1. Enter a different project and compare', async () => {
				const intake = await launchHomepageConfigurator(page, locale);
				await enterProject(intake, scenarios[0]!, title, text);
				const pending = reply(page, 'runs/find-equipment');
				await exactButton(intake, text.compare).click();
				expect((await pending).ok()).toBe(true);
			});
			const selected =
				await test.step('2. Choose one configuration and review only that project', async () => {
					const pending = reply(page, 'inquiry/form');
					await exactButton(page, text.select)
						.first()
						.click({ timeout: 90_000 });
					const prepared = await pending;
					expect(prepared.ok()).toBe(true);
					const request = prepared.request().postDataJSON();
					expect(request.project_id).not.toBe(earlier.project);
					expect(request.report_run_id).not.toBe(earlier.report);
					const shown = page
						.locator('.linker-inquiry-draft')
						.filter({ visible: true });
					await expect(
						shown.locator('.linker-inquiry-line').first()
					).toBeVisible();
					const lines = await draftLines(shown);
					expect(new Set(lines.map(({ label }) => label)).size).toBe(
						lines.length
					);
					expect(await cart()).toEqual(earlier.mixed);
					return { request, lines };
				});
			await test.step('3. Send this project, receive its PDF, and retain the existing draft', async () => {
				const form = page.locator('form.linker-inquiry-form');
				await expect(form).toBeVisible();
				await form.locator('[name=name]').fill('E2E project visitor');
				await form.locator('[name=email]').fill(email);
				await form
					.locator('textarea[name=message]')
					.pressSequentially(text.message, { delay: 28 });
				await form.locator('[name=consent]').check();
				await exactButton(form, text.send).click();
				await expect(
					page.getByRole('heading', {
						name: text.received,
						exact: true,
					})
				).toBeVisible({ timeout: 90_000 });
				const order = receivedOrder(email);
				expect(order).toMatchObject({
					status: 'inquiry-received',
					reference: {
						title,
						project_id: selected.request.project_id,
						report_run_id: selected.request.report_run_id,
						revision: selected.request.revision,
					},
				});
				expect(
					order.lines.some(
						({ product_id }) => product_id === earlier.shared.id
					)
				).toBe(true);
				expect(
					order.lines
						.map(({ label, quantity }) => ({ label, quantity }))
						.sort(lineOrder)
				).toEqual(selected.lines.sort(lineOrder));
				const report = page.getByRole('link', {
					name: text.report,
					exact: true,
				});
				await expect(report).toHaveAttribute(
					'href',
					new RegExp(
						`/inquiries/${order.id}/planning-report/${order.reference.handoff_id}`
					)
				);
				const pdf = await context.request.get(
					new URL((await report.getAttribute('href'))!, page.url())
						.href
				);
				expect(pdf.ok()).toBe(true);
				expect((await pdf.body()).subarray(0, 5).toString()).toBe(
					'%PDF-'
				);
				expect(await cart()).toEqual(earlier.mixed);
			});
		} finally {
			restoreBudgets();
		}
	});
}
