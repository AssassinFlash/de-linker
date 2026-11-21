import { expect, test, type Locator, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { seedConsentCookies } from '../lib/consent';
import { instance, isolateMailBudgets, wp } from '../lib/instance';

const PASSWORD = 'e2e-Report-Account-2026!';

const de = {
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
	'Continue to inquiry': 'Weiter zur Anfrage',
	'Include planning reports and project notes with this inquiry':
		'Planungsberichte und Projektnotizen mit dieser Anfrage senden',
	'Send inquiry': 'Anfrage senden',
	'Download PDF': 'PDF herunterladen',
	'View inquiries': 'Anfragen ansehen',
	'Inquiry received': 'Anfrage eingegangen',
	'input revision': 'Eingabeversion',
} as const;

async function downloadPdf(page: Page, control: Locator) {
	const [download] = await Promise.all([
		page.waitForEvent('download'),
		control.click(),
	]);
	const file = await download.path();
	expect(file).toBeTruthy();
	const bytes = readFileSync(file!);
	expect(bytes.subarray(0, 5).toString()).toBe('%PDF-');
	return { filename: download.suggestedFilename(), bytes };
}

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: an account owner retrieves the exact report sent with their inquiry`, async ({
			browser,
		}) => {
			const name = (english: keyof typeof de) =>
				locale === 'de' ? de[english] : english;
			const { url } = instance();
			expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
			const home = locale === 'de' ? '/de/' : '/';
			const account =
				locale === 'de' ? '/de/mein-konto/' : '/my-account/';
			const documents =
				account + (locale === 'de' ? 'dokumente/' : 'documents/');
			const planner =
				locale === 'de'
					? '/de/loesungskonfigurator/'
					: '/solution-configurator/';
			const login = `e2e-report-account-${locale}-${width}-${Date.now()}`;
			const email = `${login}@example.test`;
			const title = `E2E report ${locale} ${width} ${Date.now()}`;
			const restoreBudgets = isolateMailBudgets();
			let customer = 0;
			try {
				customer = Number(
					wp([
						'eval',
						`$id = wp_insert_user( array( 'user_login' => '${login}', 'user_email' => '${email}', 'user_pass' => '${PASSWORD}', 'role' => 'customer', 'first_name' => 'Report', 'last_name' => 'Customer' ) );` +
							`if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); }` +
							`update_user_meta( $id, 'linker_approval_status', 'approved' ); echo $id;`,
					]).trim()
				);
				expect(customer).toBeGreaterThan(0);
				const context = await browser.newContext({
					viewport: { width, height: width === 390 ? 844 : 900 },
					isMobile: width === 390,
					hasTouch: width === 390,
					reducedMotion: 'reduce',
				});
				try {
					await seedConsentCookies(context);
					const page = await context.newPage();
					await page.goto(url + home);
					await page
						.locator(`.hero-ops a[href$="${account}"]:visible`)
						.click();
					await expect(page).toHaveURL(url + account);
					await page.locator('#username').fill(login);
					await page.locator('#password').fill(PASSWORD);
					await page.locator('button[name="login"]').click();
					await expect(
						page.getByRole('search', {
							name:
								locale === 'de'
									? 'Gespeichertes Projekt finden'
									: 'Find a saved project',
						})
					).toBeVisible();

					await page.goto(url + planner);
					const workspace = page.locator('[data-linker-planner]');
					const project = workspace.getByRole('form', {
						name: name('New project'),
					});
					await project.getByLabel(name('Project name')).fill(title);
					await project
						.locator('select[name=country]')
						.selectOption('DE');
					await project
						.getByLabel(name('Town or site'))
						.fill('Berlin');
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
						.getByRole('button', {
							name: name('Continue with solar'),
						})
						.click();
					await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/);
					const projectId = new URL(page.url()).searchParams.get(
						'project'
					);
					await workspace
						.getByRole('button', {
							name: name('Continue with energy use'),
						})
						.click();
					await workspace
						.getByLabel(name('Grid connection'))
						.selectOption('3');
					await workspace.getByLabel(name('Backup load')).fill('3');
					await workspace
						.getByLabel(name('Required duration'))
						.fill('2');
					await workspace
						.getByRole('button', { name: name('Compare systems') })
						.click();
					await expect(
						workspace.getByRole('heading', {
							name: name('Keep the existing inverter'),
						})
					).toBeVisible({ timeout: 90_000 });
					await workspace
						.getByRole('button', {
							name: name('Review the proposal'),
						})
						.click();
					await workspace
						.getByRole('button', {
							name: name('Generate project report'),
						})
						.click();
					const attach = workspace.getByRole('button', {
						name: name('Attach report to inquiry'),
						exact: true,
					});
					await expect(attach).toBeVisible({ timeout: 90_000 });
					const original = await downloadPdf(
						page,
						workspace.getByRole('button', {
							name: name('Download PDF'),
							exact: true,
						})
					);
					const fileRun = original.filename.match(
						new RegExp(
							`^linker-planning-${projectId}-r([1-9][0-9]*)-${locale}\\.pdf$`
						)
					);
					expect(fileRun).not.toBeNull();
					const reviewedRevision = `${title} · ${name('input revision')} ${fileRun![1]}`;
					await attach.click();
					await workspace
						.getByRole('link', {
							name: name('Continue to inquiry'),
						})
						.click();
					const form = page.locator('form.linker-inquiry-form');
					await expect(
						form.getByText(reviewedRevision)
					).toBeVisible();
					await expect(
						form.getByRole('checkbox', {
							name: name(
								'Include planning reports and project notes with this inquiry'
							),
						})
					).toBeChecked();
					await expect(form.locator('[name="email"]')).toHaveValue(
						email
					);
					await form
						.getByRole('button', { name: name('Send inquiry') })
						.click();

					const receipt = page.locator('.linker-form-success');
					await expect(receipt).toBeVisible({ timeout: 60_000 });
					const receivedReport = page.getByRole('link', {
						name: name('Download PDF'),
						exact: true,
					});
					const receiptUrl =
						await receivedReport.getAttribute('href');
					const receiptOrder = receiptUrl?.match(
						/\/inquiries\/([1-9][0-9]*)\/planning-report\/[a-f0-9]{32}/
					);
					expect(receiptOrder).toBeTruthy();
					expect(
						(await downloadPdf(page, receivedReport)).bytes.equals(
							original.bytes
						)
					).toBe(true);
					await receipt
						.getByRole('link', { name: name('View inquiries') })
						.click();
					const inquiry = page.locator(
						`.linker-account-inquiry[data-inquiry="${receiptOrder![1]}"]`
					);
					await expect(inquiry).toContainText(
						name('Inquiry received')
					);
					await inquiry.locator('.linker-account-row-view').click();
					await expect(
						page.getByText(reviewedRevision)
					).toBeVisible();
					await expect(
						page.getByRole('link', {
							name: name('Download PDF'),
							exact: true,
						})
					).toHaveAttribute('href', receiptUrl!);

					await page.goto(url + account);
					await page
						.locator(
							`.linker-account-content a[href$="${documents}"]:visible`
						)
						.first()
						.click();
					await expect(page).toHaveURL(url + documents);
					const accountReport = page
						.locator(
							'.linker-account-file-list .linker-account-doc'
						)
						.filter({ hasText: title })
						.getByRole('link');
					await expect(accountReport).toHaveAttribute(
						'href',
						receiptUrl!
					);
					expect(
						(await downloadPdf(page, accountReport)).bytes.equals(
							original.bytes
						)
					).toBe(true);
				} finally {
					await context.close();
				}
			} finally {
				try {
					if (customer > 0) {
						wp([
							'eval',
							`foreach ( wc_get_orders( array( 'customer_id' => ${customer}, 'limit' => -1 ) ) as $order ) { $order->delete( true ); }` +
								`require_once ABSPATH . 'wp-admin/includes/user.php'; wp_delete_user( ${customer} );`,
						]);
					}
				} finally {
					restoreBudgets();
				}
			}
		});
	}
}
