import { execFileSync } from 'node:child_process';
import { expect, test, type Page } from '@playwright/test';
import {
	applyTurnstileProfile,
	isolateMailBudgets,
	instance,
	instanceName,
	wp,
} from '../lib/instance';
import { since } from '../lib/mail';

let restoreProtection: (() => void) | undefined;
let restoreBudgets: (() => void) | undefined;
let inquiryEmail: string | undefined;
let bareProject: { path: string; id: string } | undefined;
test.beforeAll(() => {
	expect(instance().url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
	restoreProtection = applyTurnstileProfile(instanceName());
	restoreBudgets = isolateMailBudgets(true);
});
test.afterAll(() => {
	restoreBudgets?.();
	restoreProtection?.();
});
test.beforeEach(({ page }) => {
	inquiryEmail = undefined;
	bareProject = undefined;
	page.setDefaultTimeout(15_000);
});
test.afterEach(async ({ page }) => {
	if (inquiryEmail)
		wp([
			'eval',
			String.raw`
			if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
				throw new RuntimeException( 'A local WordPress mail sink is required.' );
			}
			foreach ( wc_get_orders( array( 'billing_email' => '${inquiryEmail}', 'limit' => -1 ) ) as $order ) {
				if ( $order->get_meta( \Linker\Commerce\Protection\IntakeStore::META ) ) {
					\Linker\Commerce\Protection\IntakeStore::forget( $order );
				}
				$order->delete( true );
			}
		`,
		]);
	if (bareProject) {
		await page.goto(instance().url + bareProject.path + '?projects=1');
		const row = page.getByRole('listitem').filter({
			has: page.locator('[id="sc-project-' + bareProject.id + '"]'),
		});
		await row.locator('button[aria-label]').click();
		await row
			.getByRole('group')
			.getByRole('button', { name: /^Delete project$|^Projekt löschen$/ })
			.click();
		await expect(row).toHaveCount(0);
	}
});

async function screenshot(page: Page, name: string) {
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
	const path = test.info().outputPath(name + '.png');
	await page.screenshot({ path, animations: 'disabled' });
	await test.info().attach(name, { path, contentType: 'image/png' });
}

/** Execute this inquiry's due native actions, including a reschedule by Woo's mail throttle. */
function receiptDelivery(orderId: number): string {
	return wp([
		'eval',
		String.raw`
		if (!defined('LINKER_LOCAL_MAIL_DIR') || '127.0.0.1' !== wp_parse_url(home_url(), PHP_URL_HOST)) {
			WP_CLI::error('A local mail sink is required.');
		}
		$order = wc_get_order(${orderId});
		$read = static function () use ($order) {
			$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read($order->get_id());
			if (is_wp_error($state)) {WP_CLI::error($state->get_error_code());}
			return $state;
		};
		$run_due = static function (string $hook, int $id): void {
			$actions = as_get_scheduled_actions([
				'hook' => $hook, 'args' => [$id], 'group' => \Linker\Commerce\Mail\Outbox::GROUP,
				'status' => \ActionScheduler_Store::STATUS_PENDING, 'per_page' => 1
			]);
			foreach ($actions as $action_id => $action) {
				$schedule = $action->get_schedule();
				if ($schedule instanceof \ActionScheduler_NullSchedule || $schedule->get_date()->getTimestamp() <= time()) {
					\ActionScheduler_QueueRunner::instance()->process_action($action_id, 'customer inquiry receipt');
				}
			}
		};
		\Linker\Commerce\Tests\E2E\PublicInquiryAssessment::process($order->get_id());
		$state = $read();
		$job = $state['jobs']['receipt'] ?? [];
		if (!empty($job['id']) && empty($job['delivered_at'])) {
			$run_due(\Linker\Commerce\Mail\Outbox::HOOK, $job['id']);
			$state = $read();
			$job = $state['jobs']['receipt'] ?? [];
		}
		if (!empty($job['delivered_at'])) {echo 'delivered';}
		else {
			$order->read_meta_data(true);
			echo wp_json_encode(['status' => $state['status'] ?? 'missing', 'skip' => $order->get_meta('_linker_receipt_skipped'), 'receipt_job' => $job['id'] ?? null]);
		}
	`,
	]);
}

const labels = {
	en: {
		directions: [
			'Solar and storage',
			'Storage for existing PV',
			'Solar',
			'Storage',
		],
		choose: 'Select',
		compare: 'Compare system options',
		project: 'Configure a matched PV & storage system',
		newProject: 'New project',
		steps: ['1Project & direction', '3Review & send'],
		send: 'Send inquiry',
		message: 'Please discuss this preliminary solution with me.',
	},
	de: {
		directions: [
			'Photovoltaik und Speicher',
			'PV-Speicher nachrüsten',
			'Photovoltaik',
			'Speicher',
		],
		choose: 'Auswählen',
		compare: 'Anlagenvarianten vergleichen',
		project: 'Passendes PV- und Speichersystem konfigurieren',
		newProject: 'Neues Projekt',
		steps: ['1Projekt & Richtung', '3Prüfen & anfragen'],
		send: 'Anfrage senden',
		message: 'Bitte besprechen Sie diesen ersten Lösungsvorschlag mit mir.',
	},
} as const;

for (const lang of ['en', 'de'] as const) {
	for (const width of [390, 1440]) {
		test(`${lang} ${width}: a first guest requests a preliminary solution with no project data`, async ({
			page,
			context,
		}) => {
			test.setTimeout(240_000);
			const { url } = instance();
			expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
			const words = labels[lang];
			const started = Date.now();
			expect(await context.cookies()).toEqual([]);
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(url + (lang === 'de' ? '/de/' : '/'));
			await page
				.getByRole('button', {
					name: lang === 'de' ? 'Alle ablehnen' : 'Reject all',
					exact: true,
				})
				.click();
			await page
				.locator('[data-linker-planner-entry="home-hero"] a')
				.click();
			const comparison = page.getByRole('table', { name: words.compare });
			for (const name of words.directions)
				await expect(
					comparison.getByRole('rowheader', { name, exact: true })
				).toBeVisible();
			await expect(page.locator('[aria-current="step"]')).toHaveText(
				words.steps[0]
			);
			await expect(
				page.getByRole('heading', { name: words.project, exact: true })
			).toBeInViewport();
			expect(
				await page.evaluate(() => document.documentElement.scrollWidth)
			).toBe(width);
			const chosen = words.directions[1];
			const row = comparison.getByRole('row').filter({
				has: page.getByRole('rowheader', { name: chosen, exact: true }),
			});
			if (width === 390) {
				const details = await row
					.getByRole('cell')
					.nth(1)
					.boundingBox();
				const button = await row.getByRole('button').boundingBox();
				expect(button!.y).toBeGreaterThanOrEqual(
					details!.y + details!.height
				);
			}
			await screenshot(page, `preliminary-solutions-${lang}-${width}`);
			await row
				.getByRole('button', { name: words.choose, exact: true })
				.click();
			const form = page.locator('form.linker-inquiry-form');
			await expect(form).toBeVisible({ timeout: 90_000 });
			await expect(page.locator('[aria-current="step"]')).toHaveText(
				words.steps[1]
			);
			await expect(
				page.getByRole('heading', {
					name: words.newProject,
					exact: true,
				})
			).toBeInViewport();
			expect(
				await page.evaluate(() => document.documentElement.scrollWidth)
			).toBe(width);
			await expect(
				form.getByText(/input revision|Eingabeversion/)
			).toHaveCount(0);
			const binding = await form
				.locator('[name="linker_preliminary_project"]')
				.inputValue();
			const projectUrl = new URL(page.url());
			bareProject = {
				path: projectUrl.pathname,
				id: projectUrl.searchParams.get('project')!,
			};
			const direction = await page
				.locator('.sc-draft-transfer p')
				.filter({ hasText: chosen })
				.innerText();
			expect(direction).toContain(chosen);
			const summary = page.locator(
				'.sc-draft-transfer .linker-inquiry-draft'
			);
			const formBox = await form.boundingBox();
			const summaryBox = await summary.boundingBox();
			expect(formBox).not.toBeNull();
			expect(summaryBox).not.toBeNull();
			if (width === 1440) expect(formBox!.x).toBeLessThan(summaryBox!.x);
			else expect(formBox!.y).toBeLessThan(summaryBox!.y);
			await screenshot(page, `review-and-inquire-${lang}-${width}`);
			const email =
				(inquiryEmail = `e2e-preliminary-${Date.now()}@example.test`);
			const message = lang === 'de' && width === 390 ? '' : words.message;
			await form.locator('[name="name"]').fill('E2E First Guest');
			await form.locator('[name="email"]').fill(email);
			await form.locator('textarea:visible').fill(message);
			await form.locator('[name="consent"]').check();
			await form
				.getByRole('button', { name: words.send, exact: true })
				.click();
			const receipt = page.getByRole('region', {
				name:
					lang === 'en' ? 'Inquiry received' : 'Anfrage eingegangen',
				exact: true,
			});
			await expect(receipt).toBeVisible({ timeout: 60_000 });
			await screenshot(page, `inquiry-received-${lang}-${width}`);
			const result = JSON.parse(
				wp([
					'eval',
					`
    $orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
    if (count($orders) !== 1) {throw new RuntimeException('Expected one inquiry');}
    $order = $orders[0];
    echo wp_json_encode(array('id'=>$order->get_id(),'number'=>$order->get_order_number(),'locale'=>Linker\\Commerce\\Inquiry\\OrderLocale::of($order),'customer'=>$order->get_customer_id(),'status'=>$order->get_status(),'items'=>count($order->get_items()),'note'=>$order->get_customer_note(),'project'=>$order->get_meta('_linker_preliminary_project')));
   `,
				])
			);
			expect(result).toEqual({
				id: expect.any(Number),
				number: expect.any(String),
				locale: lang === 'de' ? 'de_DE_formal' : 'en_US',
				customer: 0,
				status: 'inquiry-received',
				items: 0,
				project: binding,
				note: expect.stringContaining(direction),
			});
			if (message) expect(result.note).toContain(message);
			await expect(
				receipt.locator('.linker-receipt-number')
			).toContainText(result.number);
			const receiptUrl = new URL(page.url());
			expect(receiptUrl.searchParams.has('key')).toBe(true);
			const registration = new URL(
				(await receipt.getByRole('link').getAttribute('href'))!,
				receiptUrl
			);
			expect(registration.searchParams.get('linker_inquiry')).toBe(
				String(result.id)
			);
			expect(
				registration.searchParams.get('linker_key') ===
					receiptUrl.searchParams.get('key')
			).toBe(true);

			await expect
				.poll(() => receiptDelivery(Number(result.id)), {
					timeout: 180_000,
					intervals: [1_000, 2_000, 5_000],
				})
				.toBe('delivered');
			const delivered = since(started).filter((mail) =>
				mail.to.includes(email)
			);
			expect(delivered).toHaveLength(1);
			expect(delivered[0]!.subject).toContain(result.number);
			await test.info().attach('inquiry-readback', {
				body: JSON.stringify({
					lang,
					width,
					number: result.number,
					status: result.status,
					locale: result.locale,
					project: binding,
					direction,
					items: result.items,
					receipts: delivered.length,
					subject: delivered[0]!.subject,
				}),
				contentType: 'application/json',
			});
			expect(delivered[0]!.html).not.toContain('E2E First Guest');
			if (message) expect(delivered[0]!.html).not.toContain(message);
			expect(
				delivered[0]!.html
					.replaceAll('&amp;', '&')
					.includes(registration.href)
			).toBe(true);
		});
	}
}

test('keeps the selection and inquiry edits while changing language and returning to the comparison', async ({
	page,
}) => {
	const { url } = instance();
	const direction = 1;
	const changedDirection = 3;
	const note = 'I would like to discuss storage.';
	const form = page.locator('form.linker-inquiry-form');
	const compare = (name: string, action: string) =>
		page
			.getByRole('row')
			.filter({
				has: page.getByRole('rowheader', { name, exact: true }),
			})
			.getByRole('button', { name: action, exact: true });

	await page.goto(url + '/');
	await page
		.getByRole('link', {
			name: 'Compare system options',
			exact: true,
		})
		.click();
	await compare(labels.en.directions[direction], labels.en.choose).click();
	await expect(form).toBeVisible();
	await form.locator('textarea:visible').fill(note);
	const projectReference = form.locator(
		'[name="linker_preliminary_project"]'
	);
	const selected = await projectReference.inputValue();
	await page
		.locator('header')
		.getByRole('link', { name: 'DE', exact: true })
		.click();
	await expect(page).toHaveURL(
		/\/de\/loesungskonfigurator\/.*#sc-preliminary-review$/
	);
	await expect(
		form.getByRole('button', { name: labels.de.send, exact: true })
	).toBeVisible();
	await expect(form.locator('textarea:visible')).toHaveValue(note);
	await expect(projectReference).toHaveValue(selected);

	const editedNote = 'Bitte helfen Sie uns bei der Auswahl.';
	await form.locator('textarea:visible').fill(editedNote);
	await page.goBack();
	await expect(
		form.getByRole('button', { name: labels.en.send, exact: true })
	).toBeVisible();
	await expect(form.locator('textarea:visible')).toHaveValue(editedNote);

	await page
		.getByRole('button', { name: 'Change selection', exact: true })
		.click();
	await compare(
		labels.en.directions[changedDirection],
		labels.en.choose
	).click();
	await expect(form.locator('textarea:visible')).toHaveValue(editedNote);
	const [id, revision] = selected.split(':');
	await expect(projectReference).toHaveValue(`${id}:${Number(revision) + 1}`);
	const summary = page.locator('.sc-draft-transfer aside');
	await expect(summary).toContainText('Planned system: Storage');
	await expect(summary).not.toContainText(labels.en.directions[direction]);

	await page
		.getByRole('button', { name: 'Enter project details', exact: true })
		.click();
	await expect(
		page.getByRole('heading', { name: 'What is the project?' })
	).toBeFocused();
	await page.locator('select[name=country]').selectOption('DE');
	await page
		.locator('input[name=location_label]')
		.fill('Berlin project site');
	const savedDetails = page.waitForResponse((response) =>
		new URL(response.url()).pathname.endsWith('/projects/revise')
	);
	await page.goBack();
	const saved = await savedDetails;
	expect(saved.ok()).toBe(true);
	expect(saved.request().postDataJSON()).toMatchObject({
		project_id: id,
		inputs: { brief: { site: { location_label: 'Berlin project site' } } },
	});
	await expect(projectReference).toHaveValue(`${id}:${Number(revision) + 2}`);
	await expect(form.locator('textarea:visible')).toHaveValue(editedNote);
});

test('back after a lost receipt recovers the original Woo inquiry', async ({
	page,
}) => {
	const { url } = instance();
	const email = (inquiryEmail = `e2e-preliminary-${Date.now()}@example.test`);
	const message = 'Please help with my storage project.';
	await page.goto(url + '/');
	await page
		.getByRole('link', {
			name: 'Compare system options',
			exact: true,
		})
		.click();
	await page
		.getByRole('row')
		.filter({
			has: page.getByRole('rowheader', {
				name: 'Storage for existing PV',
				exact: true,
			}),
		})
		.getByRole('button', { name: labels.en.choose, exact: true })
		.click();
	const form = page.locator('form.linker-inquiry-form');
	await form.locator('[name="name"]').fill('E2E Lost Receipt');
	await form.locator('[name="email"]').fill(email);
	await form.locator('textarea:visible').fill(message);
	await form.locator('[name="consent"]').check();
	const uuid = await form.locator('[name="linker_request_id"]').inputValue();
	const receipt = /\/inquiry-received\/(\d+)\//;
	const adminPost = /\/wp-admin\/admin-post\.php$/;
	let order: string | undefined;
	await page.route(
		adminPost,
		async (route) => {
			const response = await route.fetch();
			order = response.url().match(receipt)?.[1];
			await route.fulfill({
				status: 503,
				contentType: 'text/html',
				body: '<!doctype html><title>Receipt unavailable</title><h1>Receipt unavailable</h1>',
			});
		},
		{ times: 1 }
	);
	await form
		.getByRole('button', { name: labels.en.send, exact: true })
		.click();
	await expect(
		page.getByRole('heading', { name: 'Receipt unavailable' })
	).toBeVisible();
	expect(order).toBeDefined();

	await page.goBack();
	const recover = form.getByRole('button', {
		name: 'Check inquiry status',
		exact: true,
	});
	await expect(recover).toBeVisible();
	await expect(form.locator('[name="linker_request_id"]')).toHaveValue(uuid);
	await expect(form.locator('textarea:visible')).toHaveValue(message);
	await recover.click();
	expect(page.url().match(receipt)?.[1]).toBe(order);
	await expect(
		page.getByRole('heading', { name: 'Inquiry received', exact: true })
	).toBeVisible();
	await expect(page.locator('.linker-inquiry-success')).toHaveAttribute(
		'data-linker-received-request',
		uuid
	);
	const orders = wp([
		'eval',
		`echo wp_json_encode(wc_get_orders(['billing_email'=>'${email}', 'return'=>'ids']));`,
	]);
	expect(JSON.parse(orders)).toEqual([Number(order)]);
});

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${lang} ${width}: a bare configurator visitor compares retrofit choices and receives the Woo inquiry`, async ({
			page,
		}) => {
			const words = labels[lang];
			const path =
				lang === 'de'
					? '/de/loesungskonfigurator/'
					: '/solution-configurator/';
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(instance().url + path);
			await page.locator('[data-cky-tag="reject-button"]').click();
			const scenarios = page.locator('.sc-scene-grid button');
			await expect(scenarios).toHaveCount(4);
			const retrofit = scenarios.filter({
				hasText:
					lang === 'de' ? 'Speicher nachrüsten' : 'Storage retrofit',
			});
			await expect(retrofit).toBeEnabled();
			if (width === 1440)
				await expect(retrofit).toBeInViewport({ ratio: 1 });
			await screenshot(page, `bare-entry-${lang}-${width}`);
			await retrofit.click();
			const rows = page.locator('.sc-direction-comparison tbody tr');
			await expect(rows).toHaveCount(2);
			const keep =
				lang === 'de'
					? 'Vorhandenen Wechselrichter beibehalten'
					: 'Keep the existing inverter';
			await expect(rows.first().getByRole('rowheader')).toHaveText(keep);
			await expect
				.poll(() =>
					page
						.locator('.sc-project-heading:visible')
						.evaluate((el) => {
							const header = document.getElementById('lc-header');
							return (
								el.getBoundingClientRect().top >=
								(header?.getBoundingClientRect().bottom ?? 0) -
									1
							);
						})
				)
				.toBe(true);
			await screenshot(page, `bare-options-${lang}-${width}`);
			await rows
				.first()
				.getByRole('button', { name: words.choose, exact: true })
				.click();
			const form = page.locator('form.linker-inquiry-form');
			await expect(form).toBeVisible();
			const id = new URL(page.url()).searchParams.get('project');
			expect(id).toMatch(/^[a-f0-9]{32}$/);
			bareProject = { id: id!, path };
			const binding = await form
				.locator('[name="linker_preliminary_project"]')
				.inputValue();
			await expect(page.locator('.sc-inquiry-overview')).toContainText(
				keep
			);
			await screenshot(page, `bare-review-${lang}-${width}`);
			const email =
				(inquiryEmail = `e2e-bare-${Date.now()}@example.test`);
			await form.locator('[name="name"]').fill('Retrofit inquiry');
			await form.locator('[name="email"]').fill(email);
			await form.locator('[name="consent"]').check();
			await form
				.getByRole('button', { name: words.send, exact: true })
				.click();
			const receipt = page.getByRole('region', {
				name:
					lang === 'de' ? 'Anfrage eingegangen' : 'Inquiry received',
				exact: true,
			});
			await expect(receipt).toBeVisible({ timeout: 60000 });
			const result = JSON.parse(
				wp([
					'eval',
					`$orders=wc_get_orders(['billing_email'=>'${email}','limit'=>2]); if(count($orders)!==1)throw new RuntimeException('Expected one inquiry'); $order=$orders[0]; echo wp_json_encode([$order->get_order_number(),$order->get_status(),$order->get_meta('_linker_preliminary_project')]);`,
				])
			);
			expect(result).toEqual([
				expect.any(String),
				'inquiry-received',
				binding,
			]);
			await expect(
				receipt.locator('.linker-receipt-number')
			).toContainText(result[0]);
			await screenshot(page, `bare-receipt-${lang}-${width}`);
		});
	}
}

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(
			lang +
				' ' +
				width +
				': a revised requested quantity reaches the PDF, materials CSV and Woo receipt',
			async ({ page }) => {
				const de = lang === 'de',
					url = instance().url,
					started = Date.now();
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				await page.goto(url + (de ? '/de/' : '/'));
				await page
					.getByRole('button', {
						name: de ? 'Alle ablehnen' : 'Reject all',
						exact: true,
					})
					.click();
				await page
					.locator('#configurator-showcase')
					.getByRole('link', {
						name: de
							? 'Konfigurator starten'
							: 'Launch Configurator',
						exact: true,
					})
					.click();
				const intake = page
					.locator('form[aria-label]')
					.filter({ has: page.locator('[name=system_scope]') });
				if (!(await intake.isVisible()))
					await page
						.getByRole('button', {
							name: de
								? 'Projektdaten eingeben'
								: 'Enter project details',
							exact: true,
						})
						.click();
				await intake
					.getByLabel(de ? 'Projektname' : 'Project name', {
						exact: true,
					})
					.fill('C1 equipment ' + lang + ' ' + width);
				await intake.locator('[name=country]').selectOption('DE');
				await intake
					.getByLabel(de ? 'Ort oder Standort' : 'Town or site')
					.fill('Berlin');
				await intake
					.locator('select[name=system_scope]')
					.selectOption('storage_only');
				await intake
					.getByLabel(de ? 'Nutzung des Standorts' : 'Site use')
					.selectOption('residential');
				await intake
					.locator('select[name=project_purpose]')
					.selectOption('backup');
				await intake
					.getByLabel(de ? 'Netzanschluss' : 'Grid connection')
					.selectOption('3');
				await intake
					.getByLabel(de ? 'Ersatzstromlast' : 'Backup load')
					.fill('3');
				await intake
					.getByLabel(de ? 'Gewünschte Dauer' : 'Required duration')
					.fill('2');
				await intake
					.getByRole('button', {
						name: de ? 'Systeme vergleichen' : 'Compare systems',
						exact: true,
					})
					.click();
				await page.waitForURL((u) => !!u.searchParams.get('project'));
				const project = new URL(page.url()).searchParams.get(
					'project'
				)!;
				bareProject = {
					path: new URL(page.url()).pathname,
					id: project,
				};
				const binding = (revision = 0) =>
					page.waitForResponse(
						(r) =>
							r.request().method() === 'POST' &&
							new URL(r.url()).pathname.endsWith(
								'/inquiry/form'
							) &&
							r.request().postDataJSON().report_run_id &&
							r.request().postDataJSON().revision > revision,
						{ timeout: 120000 }
					);
				const first = binding();
				await page
					.getByRole('button', {
						name: de
							? 'Konfiguration übernehmen'
							: 'Use this configuration',
						exact: true,
					})
					.first()
					.click({ timeout: 120000 });
				const initial = (await first).request().postDataJSON();
				const form = page.locator('form.linker-inquiry-form:visible'),
					line = page
						.locator(
							'.sc-draft-transfer:visible .linker-inquiry-line'
						)
						.first();
				const sku = await line
					.locator('.linker-inquiry-sku')
					.innerText();
				const before = Number(
					await line
						.locator('.linker-inquiry-stepper > span')
						.innerText()
				);
				const email = (inquiryEmail =
					'e2e-procurement-' + Date.now() + '@example.test');
				await form.locator('[name=name]').fill('C1 procurement');
				await form.locator('[name=email]').fill(email);
				const next = binding(initial.revision);
				await line
					.getByRole('button', {
						name: de ? /erhöhen/i : /Increase quantity/i,
					})
					.click();
				const changed = (await next).request().postDataJSON();
				expect(changed.project_id).toBe(project);
				expect(changed.revision).toBe(initial.revision + 1);
				expect(changed.report_run_id).not.toBe(initial.report_run_id);
				await expect(
					line.locator('.linker-inquiry-stepper > span')
				).toHaveText(String(before + 1));
				await expect(form.locator('[name=email]')).toHaveValue(email);
				await line.evaluate((el) =>
					el.scrollIntoView({ block: 'center', behavior: 'instant' })
				);
				await screenshot(
					page,
					'matched-quantity-' + lang + '-' + width
				);
				const exports = page.locator('.sc-export-strip:visible');
				const files: Record<string, string> = {};
				for (const [kind, label] of [
					['pdf', de ? 'PDF herunterladen' : 'Download PDF'],
					['csv', /CSV/i],
				] as const) {
					const waiting = page.waitForEvent('download');
					await exports
						.getByRole('button', {
							name: label,
							exact: typeof label === 'string',
						})
						.click();
					const download = await waiting;
					const dest = test
						.info()
						.outputPath(
							'procurement-' + lang + '-' + width + '.' + kind
						);
					await download.saveAs(dest);
					files[kind] = dest;
					expect(download.suggestedFilename()).toContain(
						'-r' + changed.revision + '-'
					);
				}
				const requested = de ? 'Anfragemenge' : 'Requested quantity';
				const csv = execFileSync(
					'python3',
					[
						'-c',
						'import csv,json,sys; rows=list(csv.DictReader(open(sys.argv[1], encoding="utf-8-sig"))); print(json.dumps([r for r in rows if sys.argv[2] in r.values() and r.get(sys.argv[3])==sys.argv[4]]))',
						files.csv!,
						sku,
						requested,
						String(before + 1),
					],
					{ encoding: 'utf8' }
				);
				expect(JSON.parse(csv)).toHaveLength(1);
				const pdf = execFileSync(
					'pdftotext',
					['-layout', files.pdf!, '-'],
					{ encoding: 'utf8' }
				).replace(/\s+/g, ' ');
				expect(pdf).toContain(requested + ': ' + (before + 1));
				await form.locator('[name=consent]').check();
				await form
					.getByRole('button', {
						name: de ? 'Anfrage senden' : 'Send inquiry',
						exact: true,
					})
					.click();
				const receipt = page.getByRole('region', {
					name: de ? 'Anfrage eingegangen' : 'Inquiry received',
					exact: true,
				});
				await expect(receipt).toBeVisible({ timeout: 65000 });
				const order = JSON.parse(
					wp([
						'eval',
						String.raw`
				$orders=wc_get_orders(['billing_email'=>'${email}','limit'=>1]); $o=$orders[0];
				$c=\Linker\Commerce\Planning\Context::stored($o); $ref=reset($c)['reference']; $lines=[];
				foreach($o->get_items() as $line){$p=wc_get_product(\Linker\Commerce\Products\Publication::canonical_id($line->get_product_id())); $lines[$p->get_sku()]=$line->get_quantity();}
				echo wp_json_encode(['id'=>$o->get_id(),'number'=>$o->get_order_number(),'status'=>$o->get_status(),'reference'=>$ref,'lines'=>$lines]);`,
					])
				);
				const number = String(order.number);
				await expect(receipt).toContainText(number);
				expect(order.status).toBe('inquiry-received');
				expect(order.reference.revision).toBe(changed.revision);
				expect(order.reference.report_run_id).toBe(
					changed.report_run_id
				);
				expect(order.lines[sku]).toBe(before + 1);
				await expect
					.poll(() => receiptDelivery(order.id), {
						timeout: 160000,
						intervals: [1000, 2500],
					})
					.toBe('delivered');
				const mail = since(started).filter((m) => m.to.includes(email));
				expect(mail).toHaveLength(1);
				expect(mail[0]!.subject).toContain(number);
				await test.info().attach('procurement-readback', {
					body: JSON.stringify({
						lang,
						width,
						sku,
						engineering: before,
						requested: before + 1,
						revision: changed.revision,
						run: changed.report_run_id,
						order: number,
						mail: mail.length,
					}),
					contentType: 'application/json',
				});
			}
		);
	}
}
