import { expect, test } from '@playwright/test';
import { instance, isolateVisitorBudgets, wp } from '../lib/instance';

const de = {
	'Reject all': 'Alle ablehnen',
	'Enter project details': 'Projektdaten eingeben',
	'New project': 'Neues Projekt',
	'Project name': 'Projektname',
	'Town or site': 'Ort oder Standort',
	'Site use': 'Nutzung des Standorts',
	'Continue with storage': 'Weiter zum Speicher',
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
	'Include planning reports and project notes with this inquiry':
		'Planungsberichte und Projektnotizen mit dieser Anfrage senden',
	'Send inquiry': 'Anfrage senden',
	'Download PDF': 'PDF herunterladen',
} as const;

interface ProductQuantity {
	id: number;
	quantity: number;
}

const byId = (a: ProductQuantity, b: ProductQuantity) => a.id - b.id;
const byQuantity = (a: number, b: number) => a - b;

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: a reviewed product report goes directly to the Woo inquiry`, async ({
			page,
			context,
		}) => {
			const url = instance().url;
			expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
			const restoreBudgets = isolateVisitorBudgets();
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
					name: name('New project'),
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
						name: name('Continue with storage'),
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
				const report = await reportResponse.json();
				expect(report).toMatchObject({
					id: expect.stringMatching(/^[a-f0-9]{32}$/),
					project_id: projectId,
					revision: expect.any(Number),
				});
				const add = workspace.getByRole('button', {
					name: name('Add selected products to solution draft'),
					exact: true,
				});
				await expect(add).toBeEnabled({ timeout: 90_000 });
				await add.click();
				const table = workspace.getByRole('table').filter({
					has: workspace.getByRole('columnheader', {
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
				for (const item of reviewed) {
					expect(item.label).not.toBe('');
					expect(item.quantity).toBeGreaterThan(0);
				}
				const confirm = workspace.getByRole('button', {
					name: name('Confirm and continue to inquiry'),
					exact: true,
				});
				await expect(confirm).toBeVisible();
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
				const transfer = await applyResponse.json();
				expect(transfer).toMatchObject({
					project_id: projectId,
					report_run_id: report.id,
					revision: report.revision,
				});
				const lines: ProductQuantity[] = transfer.items;
				const quantities = reviewed
					.map((item) => item.quantity)
					.sort(byQuantity);
				expect(
					lines.map((item) => item.quantity).sort(byQuantity)
				).toEqual(quantities);
				const inquiryUrl =
					locale === 'de'
						? '/de/proforma-anfrage/'
						: '/proforma-request/';
				const form = page.locator('form.linker-inquiry-form');
				await expect(form).toBeVisible({ timeout: 60_000 });
				await expect(page).toHaveURL(url + inquiryUrl);
				await expect(page.locator('html')).toHaveAttribute(
					'lang',
					new RegExp('^' + locale)
				);
				expect(documents).toEqual([url + inquiryUrl]);
				await expect(
					form.getByRole('checkbox', {
						name: name(
							'Include planning reports and project notes with this inquiry'
						),
					})
				).toBeChecked();
				await expect(
					form.getByText(title, { exact: false }).first()
				).toBeVisible();
				const nativeDraft = page.locator(
					'.linker-inquiry-lines .linker-inquiry-line'
				);
				await expect(nativeDraft).toHaveCount(lines.length);
				const shown = await nativeDraft
					.locator('input.qty')
					.evaluateAll((inputs) =>
						inputs.map(
							(input) => (input as HTMLInputElement).valueAsNumber
						)
					);
				expect(shown.sort(byQuantity)).toEqual(quantities);
				const nativeCart = await context.request.get(
					`${url}/wp-json/wc/store/v1/cart`
				);
				expect(nativeCart.ok()).toBe(true);
				const cartItems: ProductQuantity[] = (await nativeCart.json())
					.items;
				expect(
					cartItems
						.map(({ id, quantity }) => ({ id, quantity }))
						.sort(byId)
				).toEqual([...lines].sort(byId));

				await form
					.locator('[name="name"]')
					.fill('E2E Product Report Guest');
				await form.locator('[name="email"]').fill(email);
				await form.locator('[name="consent"]').check();
				// The legacy PublicGuard accepts submission three seconds after render.
				await page.waitForTimeout(3100);
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
						handoff_id: transfer.handoff_id,
						project_id: projectId,
						report_run_id: report.id,
						revision: report.revision,
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
						`/inquiries/${order.id}/planning-report/${transfer.handoff_id}`
					)
				);
			} finally {
				restoreBudgets();
			}
		});
	}
}
