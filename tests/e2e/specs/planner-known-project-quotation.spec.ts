import { launchHomepageConfigurator } from '../lib/home-configurator';
import { randomUUID } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { approveCustomer } from '../lib/approval';
import {
	customerMail,
	downloadQuotation,
	fixture,
	inquiry,
	mailButton,
	quotationLink,
	recoverPassword,
	register,
	salesIssue,
	signIn,
} from '../lib/issued-quotation';
import { expect, test, type Locator, type Page } from '@playwright/test';
import {
	applyTurnstileProfile,
	instance,
	instanceName,
	isolateMailBudgets,
	wp,
} from '../lib/instance';

const labels = {
	en: {
		use: 'Site use',
		select: 'Select',
		direction: 'Keep the existing inverter',
		compare: 'Compare systems',
		send: 'Send inquiry',
		receipt: 'Inquiry received',
	},
	de: {
		use: 'Nutzung des Standorts',
		select: 'Auswählen',
		direction: 'Vorhandenen Wechselrichter beibehalten',
		compare: 'Systeme vergleichen',
		send: 'Anfrage senden',
		receipt: 'Anfrage eingegangen',
	},
} as const;
type Language = keyof typeof labels;
const projectForm = (page: Page) =>
	page
		.locator('[data-linker-planner] form')
		.filter({ has: page.locator('select[name=system_scope]') });
const field = (form: Locator, name: string) =>
	form.locator('[name="' + name + '"]');
const unknown =
	/unknown|not sure|don.t know|not yet known|unbekannt|nicht (bekannt|sicher)|weiß.*nicht/i;

async function fillProject(page: Page, language: Language, phaseKnown = false) {
	const form = await launchHomepageConfigurator(page, language);
	await field(form, 'project_title').fill('Bodensee');
	await field(form, 'country').selectOption('DE');
	await field(form, 'location_label').fill('Konstanz');
	await field(form, 'system_scope').selectOption('storage_addition');
	await form.getByLabel(labels[language].use).selectOption('residential');
	await field(form, 'project_purpose').selectOption('self');
	await field(form, 'pv_dc_kw').fill('8');
	await field(form, 'annual_load_kwh').fill('6200');
	await field(form, 'annual_load_basis').selectOption('bill_total');
	const phase = field(form, 'grid_phase');
	if (phaseKnown) {
		await phase.selectOption('3');
		return;
	}
	const choice = phase.getByRole('option').filter({ hasText: unknown });
	await expect(
		choice,
		'customers can explicitly choose an unknown grid connection'
	).toHaveCount(1);
	await phase.selectOption({ label: await choice.innerText() });
}

async function checkFacts(form: Locator) {
	await expect(field(form, 'country')).toHaveValue('DE');
	await expect(field(form, 'location_label')).toHaveValue('Konstanz');
	await expect(field(form, 'system_scope')).toHaveValue('storage_addition');
	await expect(field(form, 'project_purpose')).toHaveValue('self');
	await expect(field(form, 'pv_dc_kw')).toHaveValue('8');
	await expect(field(form, 'annual_load_kwh')).toHaveValue(/6[.,\s]?200/);
	await expect(field(form, 'annual_load_basis')).toHaveValue('bill_total');
	await expect(
		field(form, 'grid_phase').locator('option:checked')
	).toHaveText(unknown);
}

async function showsProject(summary: Locator) {
	for (const fact of [
		/Konstanz/i,
		/8\s*kWp/i,
		/6[,.\s]?200\s*kWh/i,
		/Electricity bill|Stromrechnung/i,
		/use more solar on site|mehr solarstrom selbst nutzen/i,
		/to confirm|zu (klären|bestätigen)|noch .*klären/i,
	]) {
		await expect(summary).toContainText(fact);
	}
}

async function changeLanguage(page: Page, to: Language) {
	const link = page
		.locator('a[data-linker-language-choice="' + to + '"]:visible')
		.first();
	await link.click();
	await expect(page.locator('html')).toHaveAttribute(
		'lang',
		to === 'de' ? /^de/ : /^en/
	);
	expect(new URL(page.url()).pathname).toBe(
		to === 'de' ? '/de/loesungskonfigurator/' : '/solution-configurator/'
	);
	await expect(projectForm(page)).toBeInViewport();
	expect(new URL(page.url()).href).not.toMatch(/Konstanz|Bodensee|6200/i);
}

async function shot(page: Page, name: string) {
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
	expect(
		await page.evaluate(() => document.documentElement.scrollWidth)
	).toBe(page.viewportSize()!.width);
	await page.screenshot({
		path: test.info().outputPath(name + '.png'),
		animations: 'disabled',
	});
}

async function enterAndSwitchLanguage(page: Page, language: Language) {
	const projectWrites: string[] = [];
	page.on('request', (request) => {
		const endpoint = new URL(request.url()).pathname;
		if (
			request.method() === 'POST' &&
			/\/projects\/(create|revise)$/.test(endpoint)
		)
			projectWrites.push(endpoint);
	});
	await page.goto(instance().url + (language === 'de' ? '/de/' : '/'));
	await page.locator('[data-cky-tag="reject-button"]').click();
	await fillProject(page, language);
	await field(projectForm(page), 'project_title').fill('');
	await changeLanguage(page, language === 'de' ? 'en' : 'de');
	await checkFacts(projectForm(page));
	await expect(field(projectForm(page), 'project_title')).toHaveValue('');
	await changeLanguage(page, language);
	await checkFacts(projectForm(page));
	await expect(field(projectForm(page), 'project_title')).toHaveValue('');
	expect(projectWrites).toEqual([]);
	await field(projectForm(page), 'project_title').fill('Bodensee');
	await shot(page, 'project-details');
}

async function sendInquiry(page: Page, language: Language, email: string) {
	await projectForm(page)
		.getByRole('button', {
			name: labels[language].compare,
			exact: true,
		})
		.click();
	const table = page.getByRole('table').filter({
		has: page.getByRole('rowheader', {
			name: labels[language].direction,
			exact: true,
		}),
	});
	await expect(table).toBeVisible();
	await expect(table.getByRole('rowheader')).toHaveCount(2);
	await showsProject(page.locator('.sc-project-facts:visible'));
	await shot(page, 'comparison');
	await table
		.getByRole('row')
		.filter({
			has: page.getByRole('rowheader', {
				name: labels[language].direction,
				exact: true,
			}),
		})
		.getByRole('button', {
			name: labels[language].select,
			exact: true,
		})
		.click();
	const form = page.locator('form.linker-inquiry-form');
	await expect(form).toBeVisible();
	const reference = await field(
		form,
		'linker_preliminary_project'
	).inputValue();
	expect(reference).toMatch(/^[a-f0-9]{32}:[1-9]\d*$/);
	const overview = page.locator('.sc-draft-transfer aside');
	const details = overview.locator('details');
	const disclosure = details.locator('summary');
	const mobile = (page.viewportSize()?.width ?? 1440) <= 600;
	await expect(disclosure).toBeVisible();
	await expect(details).toHaveJSProperty('open', !mobile);
	if (mobile) {
		await disclosure.focus();
		await page.keyboard.press('Enter');
	}
	await expect(details.getByText(/Konstanz/i).first()).toBeVisible();
	await showsProject(details);
	await expect(form).not.toContainText('Konstanz');
	if (mobile) {
		await disclosure.focus();
		await page.keyboard.press('Enter');
		await expect(details).toHaveJSProperty('open', false);
	}
	await shot(page, 'review');
	await field(form, 'name').fill('Konstanz Review');
	await field(form, 'email').fill(email);
	await field(form, 'consent').check();
	await form
		.getByRole('button', {
			name: labels[language].send,
			exact: true,
		})
		.click();
	const receipt = page.getByRole('region', {
		name: labels[language].receipt,
		exact: true,
	});
	await expect(receipt).toBeVisible();
	const order = inquiry(email);
	expect(order).toMatchObject({
		project: reference,
		owner: 0,
		status: 'inquiry-received',
		lines: 0,
		locale: language === 'de' ? 'de_DE_formal' : 'en_US',
	});
	await expect(receipt).toContainText(order.number);
	expect(order.note).toContain('Konstanz');
	expect(order.note).toMatch(
		/electricity bills?|strom(rechnung|abrechnung)/i
	);
	expect(order.note).toMatch(
		/use more solar on site|mehr solarstrom selbst nutzen/i
	);
	expect(order.note).toMatch(/to confirm|noch zu klären/i);
	expect(order.note).toMatch(/6[., ]?200\s*kWh/i);
	expect(order.note).toMatch(/8\s*kWp/i);
	return order;
}

let restoreProtection: (() => void) | undefined;
test.beforeAll(() => {
	expect(instance().url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
	restoreProtection = applyTurnstileProfile(instanceName());
});
test.afterAll(() => restoreProtection?.());

const journeys = [
	{ language: 'en', width: 1440, branch: 'login' },
	{ language: 'en', width: 390, branch: 'reset' },
	{ language: 'de', width: 1440, branch: 'register' },
	{ language: 'de', width: 390, branch: 'confirm' },
] as const;

for (const { language, width, branch } of journeys) {
	test(`${language} ${width}: known project reaches its issued quotation`, async ({
		page,
		browser,
	}) => {
		test.setTimeout(480_000);
		page.setDefaultTimeout(20_000);
		const email = 'e2e-known-' + randomUUID() + '@example.test';
		const outsider = email.replace('@', '-other@');
		const started = Date.now();
		const password = 'Solar-' + randomUUID();
		const restoreBudgets = isolateMailBudgets(true);
		try {
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await enterAndSwitchLanguage(page, language);
			const order = await sendInquiry(page, language, email);
			const ack = await customerMail(
				started,
				email,
				(m) =>
					m.subject.includes('#' + order.number) &&
					/received|eingegangen/i.test(m.subject),
				'receipt'
			);
			if (branch !== 'register') fixture('account', email, password);
			const quote = await salesIssue(browser, order, email);
			const mail = await customerMail(
				started,
				email,
				(m) =>
					m.subject.includes(quote) &&
					m.subject.includes(order.number),
				'quotation'
			);
			expect(ack.file).not.toBe(mail.file);
			const entry = await mailButton(
				page,
				mail,
				/open quotation|angebot öffnen/i
			);
			const actions = ['Open the quotation link in the received email'];
			const account =
				instance().url +
				(language === 'de' ? '/de/mein-konto/' : '/my-account/');
			if (branch === 'confirm') {
				await page.goto(account);
				await signIn(page, email, password);
			}
			await page.goto(entry);
			expect(inquiry(email).owner).toBe(0);
			if (branch === 'reset') {
				await recoverPassword(
					page,
					email,
					'Reset-' + randomUUID(),
					actions
				);
			} else if (branch === 'register') {
				await register(page, email, password);
				actions.push(
					'Enter business details',
					'Register the matching account'
				);
			} else if (branch === 'confirm') {
				await page
					.getByRole('button', {
						name: /link inquiry to my account|anfrage meinem konto zuordnen/i,
					})
					.click();
				actions.push('Confirm adding the inquiry');
			} else {
				await signIn(page, email, password);
				actions.push('Sign in to claim the inquiry');
			}
			const owner = Number(wp(['user', 'get', email, '--field=ID']));
			await expect.poll(() => inquiry(email).owner).toBe(owner);
			if (branch === 'register') {
				expect(
					wp([
						'user',
						'meta',
						'get',
						String(owner),
						'linker_approval_status',
					]).trim()
				).toBe('pending');
				await expect(quotationLink(page)).toHaveCount(0);
				await expect(page.locator('main')).not.toContainText(
					/€\s*\d|\d\s*€/
				);
				await shot(page, 'pending-account');
				await approveCustomer(browser, email);
				await page.goto(entry);
				actions.push('Reopen the quotation email after staff approval');
			}
			await expect(quotationLink(page).first()).toBeVisible();
			await shot(page, 'quotation');
			const pdf = await downloadQuotation(page, order, quote);
			actions.push('Download quotation PDF');
			await page.goto(entry);
			await expect(quotationLink(page).first()).toBeVisible();
			await expect(page.locator('[name=linker_claim_nonce]')).toHaveCount(
				0
			);
			if (branch === 'login') {
				const other = await browser.newContext();
				try {
					fixture('account', outsider, password);
					const otherPage = await other.newPage();
					await otherPage.goto(account);
					await signIn(otherPage, outsider, password);
					await otherPage.goto(entry);
					await expect(quotationLink(otherPage)).toHaveCount(0);
					await expect(otherPage.locator('body')).not.toContainText(
						quote
					);
					expect(inquiry(email).owner).toBe(owner);
				} finally {
					await other.close();
				}
			}
			writeFileSync(
				test.info().outputPath('journey.json'),
				JSON.stringify(
					{
						language,
						width,
						branch,
						order: order.number,
						project: order.project,
						receiptSubject: ack.subject,
						quotationSubject: mail.subject,
						quote,
						pdf,
						firstVisit: 'Reject optional cookies',
						projectActions: [
							'Compare project details',
							'Select a direction',
							'Send inquiry',
						],
						accountActions: actions,
						salesProduct: 'DLK-SAJ-B250HV1',
						reopenedClaimedQuotation: true,
					},
					null,
					2
				)
			);
		} finally {
			fixture('cleanup', email);
			fixture('cleanup', outsider);
			restoreBudgets();
		}
	});
}

test('a known three-phase connection opens equipment comparison for Konstanz', async ({
	page,
}) => {
	await page.goto(instance().url + '/');
	await page.locator('[data-cky-tag="reject-button"]').click();
	await fillProject(page, 'en', true);
	const run = page.waitForResponse(
		(response) =>
			response.request().method() === 'POST' &&
			new URL(response.url()).pathname.endsWith('/runs/find-equipment'),
		{ timeout: 120_000 }
	);
	await projectForm(page)
		.getByRole('button', { name: labels.en.compare, exact: true })
		.click();
	const response = await run;
	expect(response.ok()).toBe(true);
	await expect(
		page
			.getByRole('button', {
				name: 'Use this configuration',
				exact: true,
			})
			.first()
	).toBeEnabled({ timeout: 120_000 });
	await shot(page, 'three-phase-equipment');
});

test('an account-owned quotation survives native password recovery and a later price restriction', async ({
	page,
	browser,
}) => {
	test.setTimeout(360_000);
	const email = 'e2e-known-' + randomUUID() + '@example.test';
	const restore = isolateMailBudgets(true);
	try {
		const owner = fixture('account', email, 'Solar-' + randomUUID());
		fixture('owned-inquiry', email);
		const order = inquiry(email);
		expect(order.owner).toBe(Number(owner));
		const started = Date.now();
		const quote = await salesIssue(browser, order, email);
		const mail = await customerMail(
			started,
			email,
			(m) => m.subject.includes(quote),
			'quotation'
		);
		const entry = await mailButton(page, mail, /open quotation/i);
		expect(new URL(entry).searchParams.has('linker_key')).toBe(false);
		await page.goto(entry);
		const actions = ['Open the quotation link in the received email'];
		await recoverPassword(
			page,
			email,
			'New-Solar-' + randomUUID(),
			actions
		);
		await expect(quotationLink(page).first()).toBeVisible();
		const pdf = await downloadQuotation(page, order, quote);
		actions.push('Download quotation PDF');
		wp([
			'user',
			'meta',
			'update',
			owner,
			'linker_approval_status',
			'restricted',
		]);
		await page.goto(entry);
		await expect(quotationLink(page)).toHaveCount(0);
		await expect(page.locator('main')).not.toContainText(/€\s*\d|\d\s*€/);
		writeFileSync(
			test.info().outputPath('owned-quotation.json'),
			JSON.stringify(
				{ order: order.number, quote, pdf, actions, restricted: true },
				null,
				2
			)
		);
	} finally {
		fixture('cleanup', email);
		restore();
	}
});

test('an unfinished CSV mapping stays in place until the customer removes it', async ({
	page,
}) => {
	await page.goto(instance().url + '/');
	await page.locator('[data-cky-tag="reject-button"]').click();
	await fillProject(page, 'en');
	const form = projectForm(page);
	const filename = 'cossmic-konstanz-load-2017-06-19.csv';
	await field(form, 'load_profile').setInputFiles('fixtures/' + filename);
	await field(form, 'load_profile_delimiter').selectOption(';');
	await field(form, 'load_profile_source').fill('Konstanz meter reading');
	await page
		.locator('header a[data-linker-language-choice=de]:visible')
		.first()
		.click();
	await expect(page.locator('html')).toHaveAttribute('lang', /^en/);
	await expect(form).toContainText(filename);
	await expect(field(form, 'load_profile_source')).toHaveValue(
		'Konstanz meter reading'
	);
	const csvNotice = page
		.locator('[data-linker-planner]')
		.getByRole('alert')
		.filter({ hasText: /your CSV is still here/i });
	await expect(csvNotice).toBeVisible();
	await shot(page, 'csv-language-recovery');
	await csvNotice
		.getByRole('button', { name: 'Remove CSV', exact: true })
		.click();
	await changeLanguage(page, 'de');
	await checkFacts(projectForm(page));
});

test('changing the preliminary selection keeps the project and inquiry edits', async ({
	page,
}) => {
	await page.goto(instance().url + '/');
	await page.locator('[data-cky-tag="reject-button"]').click();
	await fillProject(page, 'en');
	await projectForm(page)
		.getByRole('button', { name: labels.en.compare, exact: true })
		.click();
	const select = (name: string) =>
		page
			.getByRole('row')
			.filter({ has: page.getByRole('rowheader', { name, exact: true }) })
			.getByRole('button', { name: labels.en.select, exact: true });
	await select(labels.en.direction).click();
	const form = page.locator('form.linker-inquiry-form');
	const message = 'I can check the label with my installer.';
	await form.locator('textarea:visible').fill(message);
	const original = await field(
		form,
		'linker_preliminary_project'
	).inputValue();
	await page
		.getByRole('button', { name: 'Change selection', exact: true })
		.click();
	await select('Consider a replacement inverter').click();
	await expect(form.locator('textarea:visible')).toHaveValue(message);
	const revised = (
		await field(form, 'linker_preliminary_project').inputValue()
	).split(':');
	expect(revised[0]).toBe(original.split(':')[0]);
	expect(Number(revised[1])).toBeGreaterThan(Number(original.split(':')[1]));
	await showsProject(page.locator('.sc-draft-transfer aside'));
	await shot(page, 'revised-selection');
});
