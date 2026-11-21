import { expect, test } from '@playwright/test';
import { instance, isolateMailBudgets, wp } from '../lib/instance';

const local = /^http:\/\/127\.0\.0\.1:\d+$/;

let restoreBudgets: (() => void) | undefined;
test.beforeEach(() => {
	restoreBudgets = isolateMailBudgets();
});
test.afterEach(() => {
	restoreBudgets?.();
});

const de = {
	'Reject all': 'Alle ablehnen',
	'Enter project details': 'Projektdaten eingeben',
	'New project': 'Neues Projekt',
	'Project name': 'Projektname',
	'Town or site': 'Ort oder Standort',
	'Site use': 'Nutzung des Standorts',
	'There is an existing system': 'Eine Anlage ist bereits vorhanden',
	'Existing system name': 'Bezeichnung der vorhandenen Anlage',
	'Existing inverter power (kW)':
		'Leistung des vorhandenen Wechselrichters (kW)',
	'Keep the existing inverter': 'Vorhandenen Wechselrichter beibehalten',
	'Continue with solar': 'Weiter zur PV-Anlage',
	'Continue with energy use': 'Weiter zum Energiebedarf',
	'Grid connection': 'Netzanschluss',
	'Backup load': 'Ersatzstromlast',
	'Required duration': 'Gewünschte Dauer',
	'Compare systems': 'Systeme vergleichen',
	'Review the proposal': 'Lösungsvorschlag prüfen',
	'Generate project report': 'Projektbericht erstellen',
	'Attach report to inquiry': 'Bericht an Anfrage anhängen',
	'Add selected products to solution draft':
		'Ausgewählte Produkte zum Lösungsentwurf hinzufügen',
	'Report ready to include with your inquiry.':
		'Der Bericht ist zur Anfrage hinzugefügt.',
	'Continue to inquiry': 'Weiter zur Anfrage',
	'Include planning reports and project notes with this inquiry':
		'Planungsberichte und Projektnotizen mit dieser Anfrage senden',
	'Send inquiry': 'Anfrage senden',
	'Download PDF': 'PDF herunterladen',
} as const;

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: a guest sends a retained-inverter report without adding any products`, async ({
			page,
			context,
		}) => {
			const name = (english: keyof typeof de) =>
				locale === 'de' ? de[english] : english;
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			const { url } = instance();
			expect(url).toMatch(local);
			const tag = Date.now();
			const email = `e2e-retained-${tag}@example.test`;
			const title = `E2E retained inverter ${tag}`;
			const workspace = page.locator('[data-linker-planner]');
			expect(await context.cookies()).toEqual([]);
			await page.goto(url + (locale === 'de' ? '/de/' : '/'));
			const reject = page.getByRole('button', {
				name: name('Reject all'),
				exact: true,
			});
			if (await reject.isVisible()) await reject.click();
			page.setDefaultTimeout(15_000);
			await page
				.locator('[data-linker-planner-entry="home-hero"] a')
				.click();
			await workspace
				.getByRole('button', {
					name: name('Enter project details'),
					exact: true,
				})
				.click();
			const project = page.getByRole('form', {
				name: name('New project'),
			});
			await project.getByLabel(name('Project name')).fill(title);
			await project.locator('select[name=country]').selectOption('DE');
			await project.getByLabel(name('Town or site')).fill('Berlin');
			await project
				.locator('select[name=system_scope]')
				.selectOption('storage_addition');
			await project
				.getByLabel(name('Site use'))
				.selectOption('residential');
			await project
				.locator('select[name=project_purpose]')
				.selectOption('backup');
			await project
				.getByLabel(name('There is an existing system'))
				.check();
			await project
				.getByLabel(name('Existing system name'))
				.fill('Workshop inverter');
			await project
				.getByLabel(name('Existing inverter power (kW)'))
				.fill('7.5');
			await project
				.getByLabel(name('Keep the existing inverter'))
				.check();
			await project
				.getByRole('button', { name: name('Continue with solar') })
				.click();
			await workspace
				.getByRole('button', { name: name('Continue with energy use') })
				.click();
			await workspace
				.getByLabel(name('Grid connection'))
				.selectOption('3');
			await workspace.getByLabel(name('Backup load')).fill('3');
			await workspace.getByLabel(name('Required duration')).fill('2');
			await workspace
				.getByRole('button', { name: name('Compare systems') })
				.click();
			await expect(
				workspace.getByRole('heading', {
					name: name('Keep the existing inverter'),
				})
			).toBeVisible({ timeout: 90_000 });
			await workspace
				.getByRole('button', { name: name('Review the proposal') })
				.click();
			await workspace
				.getByRole('button', { name: name('Generate project report') })
				.click();
			const attach = workspace.getByRole('button', {
				name: name('Attach report to inquiry'),
				exact: true,
			});
			await expect(attach).toBeVisible({ timeout: 90_000 });
			await expect(
				workspace.getByRole('button', {
					name: name('Add selected products to solution draft'),
				})
			).toHaveCount(0);
			const emptyCart = await context.request.get(
				`${url}/wp-json/wc/store/v1/cart`
			);
			expect(emptyCart.ok()).toBe(true);
			expect((await emptyCart.json()).items).toEqual([]);
			const applied = page.waitForResponse((response) =>
				new URL(response.url()).pathname.endsWith('/draft/apply')
			);
			await attach.click();
			const transfer = await applied;
			expect(transfer.ok()).toBe(true);
			const attached = transfer.request().postDataJSON();
			expect(attached).toMatchObject({
				project_id: new URL(page.url()).searchParams.get('project'),
				report_run_id: expect.stringMatching(/^[a-f0-9]{32}$/),
				expected_revision: expect.any(Number),
			});
			await expect(
				workspace.getByText(
					name('Report ready to include with your inquiry.')
				)
			).toBeVisible();
			const attachedCart = await context.request.get(
				`${url}/wp-json/wc/store/v1/cart`
			);
			expect(attachedCart.ok()).toBe(true);
			expect((await attachedCart.json()).items).toEqual([]);
			await workspace
				.getByRole('link', { name: name('Continue to inquiry') })
				.click();
			const form = page.locator('form.linker-inquiry-form');
			await expect(form).toBeVisible();
			await expect(page.locator('html')).toHaveAttribute(
				'lang',
				new RegExp('^' + locale)
			);
			expect(
				await page.evaluate(() => document.documentElement.scrollWidth)
			).toBe(width);
			await expect(
				form.getByRole('checkbox', {
					name: name(
						'Include planning reports and project notes with this inquiry'
					),
				})
			).toBeChecked();
			await expect(
				page.getByText(title, { exact: false }).first()
			).toBeVisible();
			await form.locator('[name="name"]').fill('E2E Report Guest');
			await form.locator('[name="email"]').fill(email);
			await form.locator('[name="consent"]').check();
			await form
				.getByRole('button', { name: name('Send inquiry') })
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
				echo wp_json_encode(array('id' => $order->get_id(), 'customer' => $order->get_customer_id(), 'status' => $order->get_status(), 'items' => count($order->get_items()), 'reference' => $reference));
			`,
				])
			);
			expect(order).toMatchObject({
				customer: 0,
				status: 'inquiry-received',
				items: 0,
				reference: {
					title,
					project_id: attached.project_id,
					revision: attached.expected_revision,
					report_run_id: attached.report_run_id,
					report_only: true,
					items: [],
				},
			});
			const download = page.getByRole('link', {
				name: name('Download PDF'),
				exact: true,
			});
			await expect(download).toBeVisible();
			const href = await download.getAttribute('href');
			expect(href).toContain(
				`/inquiries/${order.id}/planning-report/${order.reference.handoff_id}`
			);
			const pdf = await context.request.get(new URL(href!, url).href);
			expect(pdf.ok()).toBe(true);
			expect(pdf.headers()['content-type']).toContain('application/pdf');
			expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-');
		});
	}
}
