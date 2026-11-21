import { resumePlannerProject } from '../lib/resume-planner-project';
import { expect, test } from '@playwright/test';
import { instance, isolateMailBudgets, wp } from '../lib/instance';

const de = {
	'Reject all': 'Alle ablehnen',
	'Enter project details': 'Projektdaten eingeben',
	'Compare project options': 'Projektoptionen vergleichen',
	'Project name': 'Projektname',
	'Town or site': 'Ort oder Standort',
	'Site use': 'Nutzung des Standorts',
	'Grid connection': 'Netzanschluss',
	'Backup load': 'Ersatzstromlast',
	'Required duration': 'Gewünschte Dauer',
	'Compare systems': 'Systeme vergleichen',
	'Use this configuration': 'Konfiguration übernehmen',
	'Review the proposal': 'Lösungsvorschlag prüfen',
	'Generate project report': 'Projektbericht erstellen',
	'Add selected products to solution draft':
		'Ausgewählte Produkte zum Lösungsentwurf hinzufügen',
	'New quantity': 'Neue Menge',
	'Confirm and continue to inquiry': 'Bestätigen und weiter zur Anfrage',
	'Send inquiry': 'Anfrage senden',
	'Download PDF': 'PDF herunterladen',
} as const;

interface ProductQuantity {
	id: number;
	quantity: number;
}

const byId = (a: ProductQuantity, b: ProductQuantity) => a.id - b.id;
const byLabel = (a: { label: string }, b: { label: string }) =>
	a.label.localeCompare(b.label);

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: a reviewed product report goes directly to the Woo inquiry`, async ({
			page,
			context,
		}) => {
			const url = instance().url;
			expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
			const restoreBudgets = isolateMailBudgets();
			try {
				const name = (english: keyof typeof de) =>
					locale === 'de' ? de[english] : english;
				const tag = Date.now();
				const email = `e2e-product-report-${locale}-${width}-${tag}@example.test`;
				const title = `E2E storage report ${tag}`;
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				const workspace = page.locator('[data-linker-planner]');
				await page.goto(url + (locale === 'de' ? '/de/' : '/'));
				const reject = page.getByRole('button', {
					name: name('Reject all'),
				});
				if (await reject.isVisible()) await reject.click();
				await page
					.locator('[data-linker-planner-entry="home-hero"] a')
					.click();
				await workspace
					.getByRole('button', {
						name: name('Enter project details'),
					})
					.click();
				const project = workspace.getByRole('form', {
					name: name('Compare project options'),
				});
				await project.getByLabel(name('Project name')).fill(title);
				await project
					.locator('select[name=country]')
					.selectOption('DE');
				await project.getByLabel(name('Town or site')).fill('Berlin');
				await project
					.locator('select[name=system_scope]')
					.selectOption('storage_only');
				await project
					.getByLabel(name('Site use'))
					.selectOption('residential');
				await project
					.locator('select[name=project_purpose]')
					.selectOption('backup');
				await project
					.getByRole('button', {
						name: name('Compare systems'),
						exact: true,
					})
					.click();
				await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
				const navigation = await resumePlannerProject(
					page,
					locale,
					title
				);
				await navigation
					.getByRole('button', {
						name: locale === 'de' ? /Strombedarf$/ : /Energy use$/,
					})
					.click();
				await workspace
					.getByLabel(name('Grid connection'))
					.selectOption('3');
				await workspace.getByLabel(name('Backup load')).fill('3');
				await workspace.getByLabel(name('Required duration')).fill('2');
				await workspace
					.getByRole('button', { name: name('Compare systems') })
					.click();
				const use = workspace
					.getByRole('button', {
						name: name('Use this configuration'),
						exact: true,
					})
					.first();
				await expect(use).toBeEnabled({ timeout: 90_000 });
				await use.click();
				await workspace
					.getByRole('button', { name: name('Review the proposal') })
					.click();

				const projectId = new URL(page.url()).searchParams.get(
					'project'
				);
				expect(projectId).toMatch(/^[a-f0-9]{32}$/);
				const reportReply = page.waitForResponse(
					(response) =>
						new URL(response.url()).pathname.endsWith(
							'/runs/report'
						),
					{ timeout: 90_000 }
				);
				await workspace
					.getByRole('button', {
						name: name('Generate project report'),
					})
					.click();
				const reportResponse = await reportReply;
				expect(reportResponse.ok()).toBe(true);
				const report = reportResponse.request().postDataJSON();
				expect(report).toMatchObject({
					project_id: projectId,
					expected_revision: expect.any(Number),
				});
				const add = workspace.getByRole('button', {
					name: name('Add selected products to solution draft'),
					exact: true,
				});
				await expect(add).toBeEnabled({ timeout: 90_000 });
				const previewReply = page.waitForResponse((response) =>
					new URL(response.url()).pathname.endsWith('/draft/preview')
				);
				await add.click();
				const previewResponse = await previewReply;
				expect(previewResponse.ok()).toBe(true);
				const preview = previewResponse.request().postDataJSON();
				expect(preview).toMatchObject({
					project_id: projectId,
					report_run_id: expect.stringMatching(/^[a-f0-9]{32}$/),
					expected_revision: report.expected_revision,
				});
				const table = workspace.getByRole('table').filter({
					has: page.getByRole('columnheader', {
						name: name('New quantity'),
						exact: true,
					}),
				});
				await expect(table).toBeVisible();
				const reviewed = await table
					.locator('tbody tr')
					.evaluateAll((rows) =>
						rows.map((row) => {
							const cells = row.querySelectorAll('td');
							return {
								label: cells[0]!.textContent!.trim(),
								quantity: Number(cells[2]!.textContent),
							};
						})
					);
				expect(reviewed.length).toBeGreaterThan(0);
				expect(
					reviewed.every(
						({ label, quantity }) => label && quantity > 0
					)
				).toBe(true);
				const confirm = workspace.getByRole('button', {
					name: name('Confirm and continue to inquiry'),
					exact: true,
				});
				await expect(confirm).toBeVisible();
				await confirm.scrollIntoViewIfNeeded();
				await page.evaluate(() =>
					document.fonts.ready.then(() => undefined)
				);
				await page.screenshot({
					path: test.info().outputPath('product-transfer-review.png'),
					animations: 'disabled',
				});
				const before = await context.request.get(
					`${url}/wp-json/wc/store/v1/cart`
				);
				expect(before.ok()).toBe(true);
				expect((await before.json()).items).toEqual([]);

				const documents: string[] = [];
				page.on('request', (request) => {
					if (
						request.isNavigationRequest() &&
						request.frame() === page.mainFrame()
					)
						documents.push(request.url());
				});
				const applyReply = page.waitForResponse(
					(response) =>
						new URL(response.url()).pathname.endsWith(
							'/draft/apply'
						),
					{ timeout: 90_000 }
				);
				await confirm.click();
				const applyResponse = await applyReply;
				expect(applyResponse.ok()).toBe(true);
				expect(applyResponse.request().postDataJSON()).toMatchObject({
					project_id: projectId,
					report_run_id: preview.report_run_id,
					expected_revision: report.expected_revision,
					expected_draft_sha256:
						expect.stringMatching(/^[a-f0-9]{64}$/),
				});
				const inquiryUrl =
					locale === 'de'
						? '/de/proforma-anfrage/'
						: '/proforma-request/';
				const form = page.locator('form.linker-inquiry-form');
				await expect(form).toBeVisible({ timeout: 20_000 });
				await expect(page).toHaveURL(url + inquiryUrl);
				await expect(page.locator('html')).toHaveAttribute(
					'lang',
					new RegExp('^' + locale)
				);
				expect(documents).toEqual([url + inquiryUrl]);
				expect(
					await page.evaluate(
						() => document.documentElement.scrollWidth
					)
				).toBe(width);
				await page.evaluate(() =>
					document.fonts.ready.then(() => undefined)
				);
				await page.screenshot({
					path: test.info().outputPath('native-product-inquiry.png'),
					animations: 'disabled',
				});
				const nativeDraft = page.locator(
					'.linker-inquiry-lines .linker-inquiry-line'
				);
				await expect(nativeDraft).toHaveCount(reviewed.length);
				const shown = await nativeDraft.evaluateAll((rows) =>
					rows.map((row) => ({
						label: row
							.querySelector(
								'.linker-inquiry-product > span:last-child'
							)!
							.textContent!.trim(),
						quantity:
							row.querySelector<HTMLInputElement>('input.qty')!
								.valueAsNumber,
					}))
				);
				expect(shown.sort(byLabel)).toEqual(
					[...reviewed].sort(byLabel)
				);
				const nativeCart = await context.request.get(
					`${url}/wp-json/wc/store/v1/cart`
				);
				expect(nativeCart.ok()).toBe(true);
				const cartItems: (ProductQuantity & { name: string })[] = (
					await nativeCart.json()
				).items;
				expect(
					cartItems
						.map(({ name, quantity }) => ({
							label: name,
							quantity,
						}))
						.sort(byLabel)
				).toEqual([...reviewed].sort(byLabel));
				const lines = cartItems
					.map(({ id, quantity }) => ({ id, quantity }))
					.sort(byId);

				await form
					.locator('[name="name"]')
					.fill('E2E Product Report Guest');
				await form.locator('[name="email"]').fill(email);
				await form.locator('[name="consent"]').check();
				await form
					.getByRole('button', {
						name: name('Send inquiry'),
						exact: true,
					})
					.click();
				await expect(page.locator('.linker-form-success')).toBeVisible({
					timeout: 60_000,
				});
				const order = JSON.parse(
					wp([
						'eval',
						`
						$orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
						if (count($orders) !== 1) { throw new RuntimeException('Expected one inquiry'); }
						$order = $orders[0];
						$stored = Linker\\Commerce\\Planning\\Context::stored($order);
						$reference = count($stored) === 1 ? reset($stored)['reference'] : null;
						$lines = array();
						foreach ($order->get_items() as $line) {
							$lines[] = array('id' => $line->get_product_id(), 'quantity' => $line->get_quantity());
						}
						echo wp_json_encode(array('id' => $order->get_id(), 'status' => $order->get_status(), 'lines' => $lines, 'reference' => $reference));
					`,
					])
				);
				expect(order).toMatchObject({
					status: 'inquiry-received',
					reference: {
						title,
						handoff_id: expect.stringMatching(/^[a-f0-9]{32}$/),
						project_id: projectId,
						report_run_id: preview.report_run_id,
						revision: report.expected_revision,
					},
				});
				expect(order.lines.sort(byId)).toEqual([...lines].sort(byId));
				await expect(
					page.getByRole('link', {
						name: name('Download PDF'),
						exact: true,
					})
				).toHaveAttribute(
					'href',
					new RegExp(
						`/inquiries/${order.id}/planning-report/${order.reference.handoff_id}`
					)
				);
			} finally {
				restoreBudgets();
			}
		});
	}
}
