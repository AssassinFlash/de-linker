/**
 * The planner's full customer chain on one saved project: site -> roof (with
 * export permission) -> coordinate references -> module spec -> array ->
 * three interval profiles -> real PVGIS weather -> PV model -> equipment
 * selection with PV strings -> equipment check -> three-section scenario ->
 * energy calculation -> re-check at the saved revision -> planning report
 * (PDF + BOM CSV) -> transfer to the Woo solution draft -> cart readback.
 *
 * Drives the real review stack end to end; the equipment-check retries absorb
 * one-time late-edit revision drift (409 evaluation_revision_changed), the
 * way a customer's second click would.
 */
import { expect, test, type Page } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

test('the full planner chain: report, transfer and the Woo solution draft', async ({
	page,
}) => {
	test.setTimeout(900_000);

	const equipResponses: string[] = [];
	const equipStatuses: number[] = [];
	// Route interception is the only reliable way to read the error body
	// (page.on('response') bodies race the app's own reader).
	void page.route('**/rpc/runs/equipment', async (route) => {
		const response = await route.fetch();
		equipStatuses.push(response.status());
		let body = '';
		try {
			body = (await response.text()).slice(0, 400);
		} catch {
			body = '<unreadable>';
		}
		await route.fulfill({ response });
	});

	const domClick = async (text: string, scope = '#lp-calculations') => {
		for (let attempt = 0; attempt < 10; attempt += 1) {
			const ok = await page.evaluate(
				(arg: string[]) => {
					const needle = arg[0] ?? '';
					const root = arg[1] ?? '#lp-calculations';
					const button = Array.from(
						document.querySelectorAll(`${root} button`)
					).find(
						(n) =>
							n.textContent?.trim() === needle ||
							(n.textContent?.includes(needle) ?? false)
					);
					if (button && !(button as HTMLButtonElement).disabled) {
						(button as HTMLElement).click();
						return true;
					}
					return false;
				},
				[text, scope]
			);
			if (ok) {
				await page.waitForTimeout(900);
				return;
			}
			await page.waitForTimeout(1000);
		}
		throw new Error(`dom click missed: ${text}`);
	};
	const switchTab = async (name: string) => {
		await domClick(name);
		await page.waitForTimeout(600);
	};
	const saveProject = async () => {
		for (let attempt = 0; attempt < 3; attempt += 1) {
			const state = await page.locator('.lp-save-state').textContent();
			if (state?.includes('Unsaved')) {
				await page
					.getByRole('button', { name: 'Save project' })
					.click({ noWaitAfter: true });
				await expect(page.locator('.lp-save-state')).toContainText(
					'Saved',
					{
						timeout: 90_000,
					}
				);
				await page.waitForTimeout(2500);
			} else break;
		}
	};

	// operations.start silently no-ops while ANY stored record is
	// unconfirmed (resultId null): clear every pending recovery row before
	// starting a run.
	const clearUnconfirmed = async () => {
		for (let round = 0; round < 6; round += 1) {
			const pending = await page.locator(
				'#lp-calculations button:visible',
				{
					hasText: 'Discard stored request',
				}
			);
			if (!(await pending.count())) break;
			await domClick('Discard stored request');
			await page.waitForTimeout(1200);
		}
	};

	// --- Project, site, roof, coordinate references, array (all proven). ---
	await page.goto(instance().url + '/solution-configurator/', {
		waitUntil: 'networkidle',
	});
	await page.getByRole('button', { name: 'New project' }).first().click();
	await page.locator('input[maxlength="256"]').first().fill('Report chain');
	await page.getByRole('button', { name: 'Create project' }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });

	const site = page.locator('#lp-site');
	await site.locator('select').first().selectOption('DE');
	await site.locator('input').nth(0).fill('Triftstrasse 5');
	await site.locator('input').nth(1).fill('48.1689');
	await site.locator('input').nth(2).fill('11.5844');

	await page.getByRole('link', { name: 'Project overview' }).click();
	const roofEntry = page.locator('.lp-overview-empty .lp-button');
	await roofEntry.waitFor({ state: 'attached' });
	await page.evaluate(
		(el) => (el as HTMLElement).click(),
		await roofEntry.elementHandle()
	);
	await expect(page).toHaveURL(/#lp-design/, { timeout: 15_000 });

	await page
		.locator('#lp-design button', { hasText: 'Add roof face' })
		.click();
	const faceForm = page.locator('#lp-design form');
	await faceForm.locator('[name="name"]').fill('Main roof');
	await faceForm.locator('[name="width"]').fill('10');
	await faceForm.locator('[name="length"]').fill('6');
	await faceForm.locator('[name="pitch"]').fill('30');
	await faceForm.locator('[name="bearing"]').fill('180');
	await faceForm.locator('[name="source"]').fill('Owner measurement');
	await faceForm
		.locator('[name="rights_note"]')
		.fill('Owner-provided tape measurement');
	await faceForm.locator('[name="rights"]').check();
	// Reports that include the geometry require its export permission;
	// the select defaults to 'unknown' which the report refuses.
	await faceForm.locator('[name="export"]').selectOption('permitted');
	await faceForm.locator('button[type="submit"]').click();

	await page
		.locator('#lp-design button', { hasText: 'Coordinate references' })
		.click();
	const coordForm = page.locator('#lp-design form');
	await coordForm.locator('select[name="north"]').selectOption('true_north');
	await coordForm.locator('[name="latitude"]').fill('48.1689');
	await coordForm.locator('[name="longitude"]').fill('11.5844');
	const northSource = coordForm.locator('select[name="north_source"]');
	if ((await northSource.locator('option').count()) > 1)
		await northSource.selectOption({ index: 1 });
	const anchorSource = coordForm.locator('select[name="anchor_source"]');
	if ((await anchorSource.locator('option').count()) > 1)
		await anchorSource.selectOption({ index: 1 });
	await coordForm.locator('button[type="submit"]').click();

	await page
		.locator('#lp-design button', { hasText: 'Add module specification' })
		.click({ timeout: 15_000 });
	const moduleForm = page.locator('#lp-design form');
	await moduleForm.locator('select').first().selectOption({ index: 0 });
	await moduleForm.locator('button[type="submit"]').click();
	await expect(
		page.locator('#lp-design button', { hasText: 'Add module array' })
	).toBeEnabled({ timeout: 30_000 });
	await page
		.locator('#lp-design button', { hasText: 'Add module array' })
		.click();
	const arrayForm = page.locator('#lp-design form');
	await arrayForm.locator('[name="name"]').fill('Main array');
	await arrayForm.locator('[name="module"]').selectOption({ index: 1 });
	const fillField = async (name: string, value: string) => {
		const field = arrayForm.locator(`[name="${name}"]`);
		if (await field.count()) await field.fill(value);
	};
	await fillField('u', '1');
	await fillField('v', '1');
	await fillField('rows', '2');
	await fillField('columns', '4');
	await fillField('rotation', '0');
	await fillField('tilt', '0');
	await fillField('column_gap', '0.02');
	await fillField('row_gap', '0.1');
	await fillField('height', '0.1');
	await fillField('mounting', 'Fixed rails on roof hooks');
	await arrayForm.locator('button', { hasText: 'Apply properties' }).click();
	await expect(page.locator('#lp-design')).toContainText(
		'Included modules8',
		{
			timeout: 30_000,
		}
	);
	await saveProject();

	// --- Interval profile import + draft selection (proven sequence). ---
	await page
		.getByRole('link', { name: 'Energy inputs' })
		.click({ timeout: 15_000 });
	await page.waitForTimeout(800);
	// The scenario needs three interval roles (scenario_profiles_required):
	// gross load, available PV and separate AC auxiliary.
	const importProfile = async (measurement: string, label: string) => {
		const csv = join(tmpdir(), label + '.csv');
		const rows: string[] = ['timestamp,power'];
		const start = Date.UTC(2026, 0, 1) / 1000;
		for (let i = 0; i < 30 * 96; i += 1) {
			const hour = ((i % 96) * 15) / 60;
			const base = 40 + 30 * Math.sin(((hour - 6) / 24) * 2 * Math.PI);
			rows.push(
				new Date((start + i * 900) * 1000).toISOString().slice(0, 19) +
					',' +
					Math.round(Math.max(5, base) * 1000) / 1000
			);
		}
		writeFileSync(csv, rows.join('\n'));
		await page
			.locator('#lp-profiles button', { hasText: 'Import interval data' })
			.first()
			.click({ noWaitAfter: true });
		await page
			.locator('#lp-profiles input[type="file"]')
			.setInputFiles(csv);
		await page.waitForTimeout(1500);
		await page
			.locator('#lp-profiles select')
			.first()
			.selectOption({ label: 'Comma' });
		await domClick('Preview columns', '#lp-profiles');
		const byLabel = (text: string) =>
			page
				.locator('#lp-profiles label', { hasText: text })
				.locator('select');
		await byLabel('Timestamp column').selectOption({ label: 'timestamp' });
		await byLabel('Value column').selectOption({ label: 'power' });
		await byLabel('Measurement point').selectOption({ label: measurement });
		await byLabel('Value meaning').selectOption({
			label: 'Average power over each interval · kW',
		});
		await byLabel('Decimal separator').selectOption({
			label: 'Point · 12.5',
		});
		await byLabel('Source type').selectOption({
			label: 'Synthetic test data',
		});
		await byLabel('Interval boundaries').selectOption({
			label: 'Timestamp and fixed duration',
		});
		await byLabel('The timestamp identifies').selectOption({ index: 1 });
		await page
			.locator('#lp-profiles label', { hasText: 'Interval duration' })
			.locator('input')
			.fill('15');
		await byLabel('Source time zone').selectOption({ label: 'UTC' });
		await byLabel('Repeated-time column').selectOption({
			label: 'Not used',
		});
		await page
			.locator('#lp-profiles label', { hasText: 'Source label' })
			.locator('input')
			.fill(label);
		await page
			.locator('#lp-profiles label', { hasText: 'Source and Permission' })
			.locator('textarea')
			.fill('Generated for the e2e chain');
		await page
			.locator('#lp-profiles label', { hasText: 'Source and permission' })
			.locator('textarea')
			.fill('Generated for the e2e chain');
		await domClick('Import and review data', '#lp-profiles');
		await domClick('Use this profile in the open draft', '#lp-profiles');
		await page.waitForTimeout(800);
	};
	await importProfile('Total site load', 'E2E synthetic load');
	await importProfile('Available PV output · AC', 'E2E synthetic pv');
	await importProfile('External auxiliary load · AC', 'E2E synthetic aux');
	await saveProject();

	// --- Weather (panel-direct selection; all proven). ---
	await page
		.getByRole('link', { name: 'Energy calculation' })
		.click({ timeout: 15_000 });
	await page.waitForTimeout(1000);
	await switchTab('Weather source');
	await domClick('Use roof coordinates');
	const weatherTab = page.locator('#lp-calculations');
	await weatherTab.getByLabel('First source year').fill('2005');
	await weatherTab.getByLabel('Last source year').fill('2023');
	await weatherTab
		.getByLabel('Expected radiation database')
		.selectOption({ index: 1 });
	await weatherTab.getByLabel('Terrain horizon').selectOption({ index: 1 });
	await weatherTab.getByLabel('Synthetic calculation year').fill('2023');
	await domClick('Prepare weather settings');
	await page.waitForTimeout(1500);
	await saveProject();
	await expect
		.poll(
			async () =>
				page
					.locator('#lp-calculations button', {
						hasText: 'Request weather for saved inputs',
					})
					.first()
					.isEnabled(),
			{ timeout: 60_000 }
		)
		.toBe(true);
	await domClick('Request weather for saved inputs');
	await expect
		.poll(
			async () =>
				(
					await page.locator('#lp-calculations').textContent()
				)?.includes('passed validation'),
			{ timeout: 240_000, intervals: [3000] }
		)
		.toBe(true);
	await expect
		.poll(
			async () =>
				(await page
					.locator('#lp-calculations')
					.getByRole('button', { name: 'Use this weather source' })
					.count()) > 0,
			{ timeout: 60_000 }
		)
		.toBe(true);
	await page
		.locator('#lp-calculations')
		.getByRole('button', { name: 'Use this weather source' })
		.first()
		.click({ force: true, noWaitAfter: true });
	await expect
		.poll(
			async () =>
				(await page
					.getByText('Selected in the current draft')
					.count()) > 0,
			{ timeout: 30_000 }
		)
		.toBe(true);
	await saveProject();

	// --- PV model + calculation (proven sequence). ---
	await switchTab('PV generation');
	await expect
		.poll(
			async () =>
				page
					.locator('#lp-calculations button', {
						hasText: 'Update parameters for current roof layout',
					})
					.first()
					.isVisible(),
			{ timeout: 30_000 }
		)
		.toBe(true);
	await domClick('Update parameters for current roof layout');
	await page.waitForTimeout(1500);
	await domClick('02Array models');
	await page.waitForTimeout(400);
	for (const field of await page
		.locator('#lp-calculations input[inputMode="decimal"]:visible')
		.all()) {
		if (!(await field.inputValue())) await field.fill('98');
	}
	for (const field of await page
		.locator('#lp-calculations select:visible')
		.all()) {
		if (!(await field.inputValue()))
			await field.selectOption({ index: 1 }).catch(() => undefined);
	}
	for (const field of await page
		.locator('#lp-calculations textarea:visible')
		.all()) {
		if (!(await field.inputValue()))
			await field.fill('Reference model assumption for the e2e chain');
	}
	await domClick('03Power conversion');
	await page.waitForTimeout(400);
	await domClick('Add conversion group');
	await page.waitForTimeout(900);
	for (const field of await page
		.locator('#lp-calculations input[inputMode="decimal"]:visible')
		.all()) {
		if (!(await field.inputValue())) await field.fill('97');
	}
	for (const field of await page
		.locator('#lp-calculations textarea:visible')
		.all()) {
		if (!(await field.inputValue()))
			await field.fill('Declared PVWatts reference conversion');
	}
	for (
		let b = 0;
		b <
		(await page
			.locator('#lp-calculations input[type="checkbox"]:visible')
			.count());
		b += 1
	) {
		const box = page
			.locator('#lp-calculations input[type="checkbox"]:visible')
			.nth(b);
		if (!(await box.isChecked())) await box.check({ noWaitAfter: true });
	}
	await domClick('Prepare PV model');
	await page.waitForTimeout(2500);
	await saveProject();
	await expect
		.poll(
			async () =>
				(
					await page.locator('#lp-calculations').textContent()
				)?.includes('PV model prepared in this draft'),
			{ timeout: 60_000 }
		)
		.toBe(true);
	await expect
		.poll(
			async () =>
				page
					.locator('#lp-calculations button', {
						hasText: 'Calculate PV for saved inputs',
					})
					.first()
					.isEnabled(),
			{ timeout: 60_000 }
		)
		.toBe(true);
	await domClick('Calculate PV for saved inputs');
	await page.waitForTimeout(60_000);

	// --- Equipment: requirements, manual picker, string plan, DIAG. ---
	await switchTab('Equipment');
	await domClick('Single system');
	await page.waitForTimeout(800);
	const equipment = page.locator('#lp-calculations');
	await equipment
		.getByLabel('Choose an operating mode')
		.selectOption({ index: 1 });
	await equipment.getByLabel('Grid connection').selectOption({ index: 1 });
	await equipment.getByLabel('PV array kWp').fill('8');
	await equipment.getByLabel('Required usable energy kWh').fill('10');
	await equipment
		.getByLabel('Required continuous AC discharge power kW')
		.fill('5');
	await domClick('Reload product data');
	await page.waitForTimeout(2500);
	await page
		.locator('#lp-calculations summary', {
			hasText: 'Choose equipment manually',
		})
		.first()
		.click({ force: true, noWaitAfter: true });
	await page.waitForTimeout(800);
	const inverterSelect = page
		.locator('#lp-calculations label', {
			hasText: 'Inverter or integrated storage system',
		})
		.locator('select');
	await inverterSelect.selectOption({ index: 1 });
	await page.waitForTimeout(1500);
	for (const field of await page
		.locator('#lp-calculations input:visible:not([type="checkbox"])')
		.all()) {
		const mode = await field.getAttribute('inputmode');
		if (mode !== 'decimal' && mode !== 'numeric') continue;
		if (!(await field.inputValue())) await field.fill('1');
	}
	await saveProject();

	// PV strings: open details, create plan, complete, assign all modules.
	await page
		.locator('#lp-calculations summary', {
			hasText: 'PV strings and inputs',
		})
		.first()
		.click({ force: true, noWaitAfter: true });
	await page.waitForTimeout(800);
	const stringsDetails = page
		.locator('#lp-calculations details', {
			hasText: 'PV strings and inputs',
		})
		.first();
	await expect(stringsDetails).toBeVisible();
	const createPlan = page.locator('#lp-calculations button:visible', {
		hasText: 'Set up PV strings',
	});
	if ((await createPlan.count()) > 0) {
		await createPlan.first().click({ force: true, noWaitAfter: true });
		await page.waitForTimeout(1200);
	}
	await stringsDetails
		.getByLabel('Lowest design ambient temperature')
		.fill('-10');
	await stringsDetails
		.getByLabel('Temperature source and location')
		.fill('Local design minimum, Munich');
	await stringsDetails.getByLabel('MPPT').fill('1');
	await stringsDetails.getByLabel('Inverter input').fill('1');
	const selectAllState = await page.evaluate(() => {
		const details = Array.from(
			document.querySelectorAll('#lp-calculations details')
		).find((n) => n.textContent?.includes('Array 1'));
		if (details instanceof HTMLDetailsElement && !details.open)
			details.open = true;
		const button = Array.from(
			document.querySelectorAll<HTMLButtonElement>(
				'#lp-calculations button'
			)
		).find((n) => n.textContent?.includes('Select all available modules'));
		if (button && !button.disabled) {
			button.click();
			return true;
		}
		return false;
	});
	expect(selectAllState).toBe(true);
	await page.waitForTimeout(800);
	const addState = await page.evaluate(() => {
		const button = Array.from(
			document.querySelectorAll<HTMLButtonElement>(
				'#lp-calculations button'
			)
		).find((n) =>
			n.textContent?.includes('Add selected modules to string')
		);
		if (button && !button.disabled) {
			button.click();
			return true;
		}
		return false;
	});
	expect(addState).toBe(true);
	await page.waitForTimeout(1500);
	await expect(stringsDetails).toContainText('8 of 8 roof modules assigned', {
		timeout: 15_000,
	});
	await saveProject();

	// The earlier "disabled" reads hit the hidden Multiple-systems panel's
	// button; the visible Single-system instance is the customer's control.
	const prepareVisible = page
		.locator('#lp-calculations button:visible', {
			hasText: 'Prepare equipment selection',
		})
		.first();
	// The #1031 fix: every recovery row offers Discard stored request. Use
	// it until the journal is empty - the customer's escape hatch.
	for (let clear = 0; clear < 4; clear += 1) {
		const step = await page.evaluate(() => {
			const discard = Array.from(
				document.querySelectorAll<HTMLButtonElement>(
					'#lp-calculations button'
				)
			).find((n) => n.textContent?.includes('Discard stored request'));
			if (discard && !discard.disabled) {
				discard.click();
				return 'discard';
			}
			return 'done';
		});
		if (step === 'done') break;
		await page.waitForTimeout(2000);
	}
	// The journal must be empty now; give the UI a beat to recompute gates.
	await page.waitForTimeout(3000);
	await expect(prepareVisible).toBeEnabled({ timeout: 90_000 });
	await domClick('Prepare equipment selection');
	await saveProject();
	await clearUnconfirmed();

	// The equipment check consumes the saved selection. The evaluate job
	// runs ~7-15s (DB-proven); the run label renders in the runs view only, so
	// settle and move on rather than polling for text that never lands here.
	// A late draft edit can bump the revision after the last save, so the
	// first check attempt returns 409 evaluation_revision_changed; a real
	// customer clicks again after the record clears - mirror that.
	for (let attempt = 0; attempt < 3; attempt += 1) {
		await saveProject();
		await clearUnconfirmed();
		await domClick('Check saved equipment selection');
		await page.waitForTimeout(12_000);
		if (equipStatuses.length && equipStatuses.at(-1) === 200) break;
		if (equipStatuses.length && equipStatuses.at(-1) !== 409) break;
	}
	await page.waitForTimeout(15_000);

	// The calculations workspace must be VISIBLE before :visible fills run:
	// ProjectEditor hides the whole section (hidden attr, active=false) when
	// the workspace is not calculations/equipment, and chooseWorkspace
	// REFUSES to re-enter while editor-wide valid=false. Restore via the hash
	// path a real link uses, then prove visibility before proceeding.
	// No hashchange listener exists: the workspace reads the hash at mount
	// only, so restore the way a real link/refresh does - reload with the
	// hash (remount bypasses chooseWorkspace's valid=false refusal).
	// The equipment stage entered via chooseWorkspace('equipment') (hash
	// #lp-equipment); the check's openResults() back-switch was REFUSED
	// (editor-wide valid=false from the incomplete scenario form), so the
	// workspace state is stuck on 'equipment' and equipmentFocus hides every
	// form view. A hash-only goto is same-document (no remount) and a plain
	// reload would re-read #lp-equipment: fix the hash first, THEN reload so
	// the remount's workspaceFromHash resolves 'calculations'.
	const mount = new URL(page.url());
	mount.hash = '#lp-calculations';
	await page.goto(mount.toString());
	await page.reload({ waitUntil: 'load' });
	await page.waitForTimeout(4000);
	const visibility = await page.evaluate(() => {
		const section = document.getElementById('lp-calculations');
		const wrapper = section?.parentElement;
		return {
			wrapperHidden: wrapper?.hidden ?? null,
			sectionInDom: Boolean(section),
			visibleButtons: Array.from(
				document.querySelectorAll('#lp-calculations button')
			).filter((b) => b instanceof HTMLElement && b.offsetParent !== null)
				.length,
			hash: window.location.hash,
		};
	});
	expect(visibility.visibleButtons).toBeGreaterThan(0);

	// Scenario: all three sections must be complete before Prepare accepts
	// the draft (scenarioBattery refuses an empty source note with
	// battery_source_required - the j2 root cause).
	for (let attempt = 0; attempt < 5; attempt += 1) {
		await domClick('Scenario settings');
		await page.waitForTimeout(1000);
		const pressed = await page.evaluate(() =>
			Array.from(document.querySelectorAll('#lp-calculations button'))
				.find((b) => b.getAttribute('aria-pressed') === 'true')
				?.textContent?.trim()
		);
		if (pressed === 'Scenario settings') break;
	}
	// Do NOT click 'Review energy inputs' here: its onClick is
	// openProfiles() -> chooseWorkspace('energy'), which hides the whole
	// calculations section again (j9 DIAG: view=scenario pressed but the
	// workspace wrapper DIV hidden). The profiles were already selected in
	// the profile stage of this chain.
	await domClick('Use the shared profile range');
	// The planner re-renders continuously (the equipment stage needed
	// force:true for the same reason), so Playwright's stability-gated
	// actions can wait forever here. Fill through the DOM with React's
	// native value setters + input events instead.
	const fillVisibleNumbers = async () => {
		await page.waitForTimeout(1200);
		const inventory = await page.evaluate(() => {
			const inputs = Array.from(
				document.querySelectorAll('#lp-calculations input')
			).map((f) => {
				const i = f as HTMLInputElement;
				return {
					m: i.getAttribute('inputmode'),
					v: i.value.slice(0, 8),
					h: Boolean(i.closest('[hidden]')),
					d: i.disabled,
				};
			});
			const usable = document.querySelector('#lp-calculations input');
			const usableLabel = Array.from(
				document.querySelectorAll('#lp-calculations .lp-field span')
			).find((sp) => sp.textContent?.includes('Usable stored energy'));
			const activeTab = Array.from(
				document.querySelectorAll('#lp-calculations button')
			)
				.filter((b) => b.getAttribute('aria-pressed') === 'true')
				.map((b) => b.textContent?.trim());
			const hiddenWrappers = Array.from(
				document.querySelectorAll('#lp-calculations [hidden]')
			).map((el) => el.className || el.tagName);
			return {
				total: inputs.length,
				hiddenCount: inputs.filter((x) => x.h).length,
				emptyNumeric: inputs.filter((x) => !x.h && x.v === ''),
				usableLabelPresent: Boolean(usableLabel),
				usableLabelHidden: usableLabel
					? Boolean(usableLabel.closest('[hidden]'))
					: null,
				activeTab,
				hiddenWrappers: hiddenWrappers.slice(0, 15),
				url: window.location.search,
			};
		});
		const touched = await page.evaluate(() => {
			const touched: string[] = [];
			for (const field of Array.from(
				document.querySelectorAll('#lp-calculations input')
			)) {
				const input = field as HTMLInputElement;
				if (input.type === 'checkbox' || input.closest('[hidden]'))
					continue;
				const mode = input.getAttribute('inputmode');
				if (mode !== 'decimal' && mode !== 'numeric') continue;
				if (input.value === '' && !input.disabled) {
					const setter = Object.getOwnPropertyDescriptor(
						window.HTMLInputElement.prototype,
						'value'
					)?.set;
					setter?.call(input, '1');
					input.dispatchEvent(new Event('input', { bubbles: true }));
					touched.push(input.name || input.id || mode);
				}
			}
			return touched;
		});
	};
	// Step 01 Storage: battery numbers plus the source/assumption note.
	await domClick('Storage');
	const storageButtons = await page.evaluate(() =>
		Array.from(document.querySelectorAll('#lp-calculations button'))
			.map((b, index) => ({ b, index }))
			.filter(({ b }) => b.textContent?.includes('Storage'))
			.map(({ b, index }) => ({
				globalIndex: index,
				text: b.textContent?.trim().slice(0, 50),
				disabled: (b as HTMLButtonElement).disabled,
				view: b.closest('div[class]')?.className?.slice(0, 40) ?? null,
				inSection:
					b.closest('section')?.className?.slice(0, 40) ?? null,
			}))
	);
	const workspaceState = await page.evaluate(() => ({
		wrapperHidden:
			document.getElementById('lp-calculations')?.parentElement?.hidden,
		hash: window.location.hash,
		bodyClass: document.body.className.slice(0, 60),
	}));
	await fillVisibleNumbers();
	const noteSet = await page.evaluate(() => {
		for (const ta of Array.from(
			document.querySelectorAll('#lp-calculations textarea')
		)) {
			const el = ta as HTMLTextAreaElement;
			if (el.closest('[hidden]')) continue;
			if (
				el.previousElementSibling?.textContent?.includes(
					'Source or assumption for storage parameters'
				)
			) {
				const setter = Object.getOwnPropertyDescriptor(
					window.HTMLTextAreaElement.prototype,
					'value'
				)?.set;
				setter?.call(
					el,
					'Constant-window storage assumption for the chain probe.'
				);
				el.dispatchEvent(new Event('input', { bubbles: true }));
				return true;
			}
		}
		return false;
	});
	expect(noteSet).toBe(true);
	// Step 02 Starting state: the explicit empty inventory writes its own basis.
	await domClick('Starting state');
	await domClick('Start with an empty battery');
	// Step 03 Operation: one period, its values, and the terminal choice.
	await domClick('Operation');
	// emptyScenario() already carries ONE default period; 'Add operating
	// period' would create a second that stays empty and blocks the run
	// (j19: operating_period_incomplete with one complete fieldset).
	await fillVisibleNumbers();
	const terminalSet = await page.evaluate(() => {
		for (const sel of Array.from(
			document.querySelectorAll('#lp-calculations select')
		)) {
			const s = sel as HTMLSelectElement;
			if (s.closest('[hidden]')) continue;
			if (
				Array.from(s.options).some(
					(o) =>
						o.value === 'none' &&
						/no minimum/i.test(o.textContent ?? '')
				)
			) {
				const setter = Object.getOwnPropertyDescriptor(
					window.HTMLSelectElement.prototype,
					'value'
				)?.set;
				setter?.call(s, 'none');
				s.dispatchEvent(new Event('change', { bubbles: true }));
				return true;
			}
		}
		return false;
	});
	expect(terminalSet).toBe(true);
	// The period selects default to null ('Choose an option') and start/end
	// are TEXT fields the numeric fill never touches; the engine refuses an
	// incomplete period (operating_period_incomplete, j18).
	const periodSet = await page.evaluate(() => {
		const fieldset = document.querySelector(
			'#lp-calculations fieldset.lp-scenario-period'
		) as HTMLFieldSetElement | null;
		if (!fieldset) return { error: 'no fieldset' };
		const setControl = (label: string, value: string) => {
			const lab = Array.from(
				fieldset.querySelectorAll('label.lp-field')
			).find((l) =>
				l.querySelector('span')?.textContent?.includes(label)
			);
			if (!lab) return false;
			const control =
				(lab.querySelector('select') as HTMLSelectElement | null) ??
				(lab.querySelector('input') as HTMLInputElement | null);
			if (!control) return false;
			const proto =
				control instanceof HTMLSelectElement
					? HTMLSelectElement.prototype
					: HTMLInputElement.prototype;
			const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
			setter?.call(control, value);
			control.dispatchEvent(
				new Event(
					control instanceof HTMLSelectElement ? 'change' : 'input',
					{
						bubbles: true,
					}
				)
			);
			return true;
		};
		return [
			setControl('Start with UTC', '2026-01-01T00:00:00Z'),
			setControl('End with UTC', '2026-01-30T23:45:00Z'),
			setControl('Grid condition', 'connected'),
			setControl('PV available', 'true'),
			setControl('Grid charging', 'false'),
			setControl('Grid import limit', 'unlimited'),
			setControl('Grid export limit', 'unlimited'),
		] as boolean[];
	});
	if (Array.isArray(periodSet)) {
		expect(periodSet.every(Boolean)).toBe(true);
	} else {
		throw new Error(periodSet.error);
	}
	await domClick('Prepare scenario settings');
	await page.waitForTimeout(2000);
	const scenarioText = await page.locator('#lp-calculations').textContent();
	await saveProject();
	await expect
		.poll(
			async () =>
				page
					.locator('#lp-calculations button:visible', {
						hasText: 'Calculate saved scenario',
					})
					.first()
					.isEnabled(),
			{ timeout: 90_000 }
		)
		.toBe(true);
	await domClick('Calculate saved scenario');
	await expect
		.poll(
			async () =>
				(
					await page.locator('#lp-calculations').textContent()
				)?.includes('Scenario settings') ?? false,
			{ timeout: 300_000, intervals: [5000] }
		)
		.toBe(true);
	await page.waitForTimeout(30_000);
	// The engine refuses a report whose equipment check predates the saved
	// PV strings (report_wiring_check_required, j24): re-run the check at the
	// CURRENT input revision after the energy calculation, then report.
	await switchTab('Equipment');
	for (let attempt = 0; attempt < 3; attempt += 1) {
		await saveProject();
		await clearUnconfirmed();
		await domClick('Check saved equipment selection');
		await page.waitForTimeout(12_000);
		if (equipStatuses.length && equipStatuses.at(-1) === 200) break;
		if (equipStatuses.length && equipStatuses.at(-1) !== 409) break;
	}
	await page.waitForTimeout(20_000);
	// The Equipment tab enters the equipment WORKSPACE (chooseWorkspace);
	// other tabs only switch the view, so equipmentFocus would keep the
	// report form hidden (j25: the report select waited out the test).
	// Recover the calculations workspace the proven way before reporting.
	const back = new URL(page.url());
	back.hash = '#lp-calculations';
	await page.goto(back.toString());
	await page.reload({ waitUntil: 'load' });
	await page.waitForTimeout(4000);
	await switchTab('Planning report');
	// The report form lives in the 'Planning report' tab (the energy run
	// leaves the view on 'runs'; j20's generate poll timed out polling a
	// hidden tab).
	// A real customer reviews the saved results to include: pick the newest
	// energy and PV runs (options are 'Not included' + newest first). Labels
	// match twice (hidden view copies persist in the DOM): take the first.
	for (const label of ['Energy calculation', 'PV generation']) {
		// getByLabel matches the section heading (#lp-calculations is titled
		// 'Energy calculation'); scope to the form label wrapping the select.
		const select = page
			.locator('#lp-calculations label.lp-field', { hasText: label })
			.first()
			.locator('select');
		if ((await select.count()) > 0) {
			const options = await select.locator('option').all();
			if (options.length > 1) await select.selectOption({ index: 1 });
		} else {
			throw new Error(`report select missing: ${label}`);
		}
	}
	// The planning report is the keystone's summit.
	await expect
		.poll(
			async () =>
				page
					.locator('#lp-calculations button:visible', {
						hasText: 'Generate planning report',
					})
					.first()
					.isEnabled(),
			{ timeout: 120_000 }
		)
		.toBe(true);
	await domClick('Generate planning report');
	// The finished report offers its real artifacts; the transfer below
	// consumes it: preview -> confirm -> receipt -> the real Woo draft.
	await expect
		.poll(
			async () =>
				page
					.locator('#lp-calculations button:visible', {
						hasText: 'Add selected products to solution draft',
					})
					.first()
					.isEnabled(),
			{ timeout: 120_000 }
		)
		.toBe(true);
	await domClick('Add selected products to solution draft');
	await expect
		.poll(
			async () =>
				page
					.locator('#lp-calculations button:visible', {
						hasText: 'Confirm changes',
					})
					.count(),
			{ timeout: 60_000 }
		)
		.toBeGreaterThan(0);
	const previewRows = await page
		.locator('#lp-calculations .lp-data-table tbody tr')
		.allTextContents();
	await domClick('Confirm changes');
	await expect
		.poll(
			async () =>
				(
					await page.locator('#lp-calculations').textContent()
				)?.includes('Selected products added to solution draft.'),
			{ timeout: 120_000 }
		)
		.toBe(true);
	const receiptUrl = await page
		.locator('#lp-calculations a.lp-button', {
			hasText: 'View solution draft',
		})
		.first()
		.getAttribute('href');
	expect(receiptUrl).toBeTruthy();
	await page.goto(receiptUrl!, { waitUntil: 'load' });
	// The real Woo solution draft carries the transferred product.
	await expect(page.locator('body')).toContainText('SAJ', {
		timeout: 30_000,
	});
	await expect(page.locator('body')).toContainText(/inquir|anfrage/i);
});
