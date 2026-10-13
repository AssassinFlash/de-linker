// Real t112 rendered controls/states. Never modifies page content or e2e specs.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const require = createRequire(new URL('./e2e/package.json', import.meta.url));
const { chromium } = require('@playwright/test');
const root = resolve(new URL('..', import.meta.url).pathname);
const evidence = resolve(root, 'docs/acceptance/2026-10-13/auth-forms-mobile');
const base = 'http://127.0.0.1:8978';
const wp = (...args) => execFileSync('just', ['wp', 't112', '--', ...args], { cwd: root, encoding: 'utf8' }).trim().split('\n').at(-1);
const login = () => execFileSync('just', ['login', 't112', '--user', 'auth-forms-mobile-evidence'], { cwd: root, encoding: 'utf8' }).trim().split('\n').at(-1);
const browser = await chromium.launch({ headless: true });
const rows = [];
const viewports = [{ width: 390, height: 844 }, { width: 1440, height: 1000 }, { width: 430, height: 932 }];
async function settle(page) {
	await page.evaluate(async () => { await document.fonts.ready; });
	await page.waitForFunction(() => !document.querySelector('form.checkout.processing, .blockUI.blockOverlay'));
}
async function shot(page, width, name, target) {
	await settle(page);
	if (target) await page.locator(target).scrollIntoViewIfNeeded();
	await page.screenshot({ path: resolve(evidence, `ours-${width}/${name}.png`), animations: 'disabled' });
}
async function metrics(page, width, name, scope, primary) {
	const result = await page.locator(scope).evaluate((el, primarySelector) => {
		const round = n => Math.round(n * 100) / 100;
		const controls = [...el.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]), select, textarea, .select2-selection--single')]
			.filter(e => e.getBoundingClientRect().height > 0)
			.map(e => ({ field: e.id || e.name || e.className, height: round(e.getBoundingClientRect().height), width: round(e.getBoundingClientRect().width), radius: getComputedStyle(e).borderRadius }));
		const button = el.querySelector(primarySelector);
		const b = button?.getBoundingClientRect();
		const touch = [...el.querySelectorAll('button, a, label:has(input[type="checkbox"])')]
			.filter(e => e.getBoundingClientRect().height > 0)
			.map(e => ({ label: e.textContent.trim() || e.getAttribute('aria-label'), height: round(e.getBoundingClientRect().height) }));
		const group = el.matches('.linker-auth-step') ? el : el.querySelector('.linker-auth-step-fields, .woocommerce-billing-fields__field-wrapper') || el;
		const fields = [...group.querySelectorAll('.form-row, .linker-form-label')].filter(e => e.getBoundingClientRect().height > 0);
		const gaps = fields.slice(1).map((e, i) => round(e.getBoundingClientRect().top - fields[i].getBoundingClientRect().bottom));
		const r = el.getBoundingClientRect();
		return { controls, primary: b ? { height: round(b.height), width: round(b.width) } : null, touch, groupGaps: gaps, outerLeft: round(r.left), contentLeft: controls.length ? round(group.querySelector('input:not([type="hidden"]), select, textarea')?.getBoundingClientRect().left ?? r.left) : round(r.left), horizontalOverflow: document.documentElement.scrollWidth > innerWidth };
	}, primary);
	rows.push({ width, name, ...result });
	if (width < 640) {
		for (const c of result.controls) assert.ok(c.height >= 44, `${name} ${c.field}: ${c.height}`);
		for (const c of result.touch) assert.ok(c.height >= 44, `${name} ${c.label}: ${c.height}`);
		if (result.primary) assert.ok(result.primary.height >= 44, `${name} CTA`);
		assert.equal(result.horizontalOverflow, false, `${name} overflow`);
	}
}
try {
	for (const viewport of viewports) {
		await mkdir(resolve(evidence, `ours-${viewport.width}`), { recursive: true });
		const context = await browser.newContext({ viewport });
		const page = await context.newPage();
		for (const [lang, account, contact] of [['en', '/my-account/', '/contact/'], ['de', '/de/mein-konto/', '/de/kontakt/']]) {
			await page.goto(base + account);
			await page.locator('#username').waitFor();
			await shot(page, viewport.width, `${lang}-login`);
			await metrics(page, viewport.width, `${lang}-login`, '.linker-auth-card:not(.linker-auth-register)', 'button[name="login"]');
			for (let step = 1; step <= 3; step++) {
				const scope = `.linker-auth-step:nth-child(${step})`;
				await shot(page, viewport.width, `${lang}-register-${step}`, scope);
				await metrics(page, viewport.width, `${lang}-register-${step}`, scope, 'button[name="register"]');
			}
			await shot(page, viewport.width, `${lang}-register-submit`, 'button[name="register"]');
			await metrics(page, viewport.width, `${lang}-register`, '.linker-auth-register', 'button[name="register"]');
			const reset = await page.locator('.lost_password a').getAttribute('href');
			await page.goto(reset);
			await page.locator('#user_login').waitFor();
			await shot(page, viewport.width, `${lang}-forgot`);
			await metrics(page, viewport.width, `${lang}-forgot`, '.linker-auth-card', 'button[type="submit"]');
			await page.goto(base + contact + '#contact-form');
			await page.locator('.linker-contact-form textarea').waitFor();
			await shot(page, viewport.width, `${lang}-contact`, '.linker-contact-form');
			await metrics(page, viewport.width, `${lang}-contact`, '.linker-contact-form', 'button[type="submit"]');
			// Native browser validation remains in charge of required and email constraints.
			assert.equal(await page.locator('.linker-contact-form').evaluate(el => el.checkValidity()), false);
			if (process.env.CONTACT_SUBMIT === '1' && viewport.width === 390 && lang === 'en') {
				await page.locator('[name="message"]').fill('Mobile auth/forms acceptance: one local contact submission.');
				await page.locator('[name="name"]').fill('Auth Forms Mobile Evidence');
				await page.locator('[name="email"]').fill('auth-forms-mobile-evidence@example.test');
				await page.locator('[name="consent"]').check();
				await page.locator('.linker-contact-form button[type="submit"]').click();
				await page.waitForURL('**/contact/?contact=sent#contact-form');
				assert.equal(await page.locator('.linker-form-success.woocommerce-message').count(), 1);
				console.log('contact: one real local submission returned contact=sent and the native success marker');
			}
			await page.goto(base + contact + '?contact=invalid#contact-form');
			await shot(page, viewport.width, `${lang}-contact-error`, '.linker-contact-form');
			assert.equal(await page.locator('.linker-form-error.woocommerce-error').count(), 1);
			// State rendering only: no extra test email is sent to show the success state.
			await page.goto(base + contact + '?contact=sent#contact-form');
			await shot(page, viewport.width, `${lang}-contact-success`, '.linker-contact-form');
			assert.equal(await page.locator('.linker-form-success a').count(), 1);
			assert.equal(await page.locator('.linker-contact-form button[type="submit"]').count(), 0);
			await metrics(page, viewport.width, `${lang}-contact-success`, '.linker-form-success', 'a');
		}
		await page.goto(base + '/my-account/');
		await page.locator('#username').fill('auth-forms-mobile-evidence');
		await page.locator('#password').fill('incorrect-mobile-fixture');
		await page.locator('button[name="login"]').press('Enter');
		await page.locator('.linker-auth-card .woocommerce-error').waitFor();
		await shot(page, viewport.width, 'en-login-error', '.linker-auth-card .woocommerce-error');
		await page.goto(base + '/my-account/');
		await page.locator('#billing_company').fill('Auth Forms Mobile');
		await page.locator('#linker_customer_role').selectOption('installer');
		await page.locator('#billing_first_name').fill('Mobile');
		await page.locator('#billing_last_name').fill('Evidence');
		await page.locator('#billing_address_1').fill('Teststrasse 1');
		await page.locator('#billing_postcode').fill('10115');
		await page.locator('#billing_city').fill('Berlin');
		await page.locator('#reg_email').fill('x@y');
		await page.locator('#reg_password').fill('MobileEvidence!2026');
		await page.locator('button[name="register"]').press('Enter');
		await page.locator('.linker-auth-register .woocommerce-error').waitFor();
		assert.ok(new URL(page.url()).hash === '#linker-register', 'Registration errors stay anchored at the register card');
		await shot(page, viewport.width, 'en-register-error', '.linker-auth-register .woocommerce-error');
		await page.goto(login());
		await page.goto(base + '/product/saj-h2-10k-t3/');
		const add = await page.locator('a[href*="add-to-cart="]').first().getAttribute('href');
		assert.ok(add, 'Product has its own add-to-draft link');
		await page.goto(add);
		const request = '/proforma-request/';
		for (const [lang, path] of [['en', request], ['de', '/de/proforma-anfrage/']]) {
			await page.goto(base + path);
			await page.locator('#place_order').waitFor();
			await shot(page, viewport.width, `${lang}-proforma`, 'form.checkout');
			await metrics(page, viewport.width, `${lang}-proforma`, 'form.checkout', '#place_order');
			if (lang === 'de') assert.match(await page.locator('#place_order').innerText(), /Proforma anfordern/, 'AJAX review preserves German UI');
			await shot(page, viewport.width, `${lang}-proforma-submit`, '#place_order');
		}
		if (viewport.width === 390) {
			await page.goto(base + request);
			await page.locator('#billing_city').fill('');
			await page.locator('#terms').check();
			await page.locator('#place_order').scrollIntoViewIfNeeded();
			const before = await page.evaluate(() => scrollY);
			await page.locator('#place_order').click();
			await page.locator('.woocommerce-error').waitFor();
			await page.waitForTimeout(1200); // observes completion of Woo's former 1s animation
			const after = await page.evaluate(() => scrollY);
			assert.ok(Math.abs(after - before) < 4, `Checkout bounced ${before} -> ${after}`);
			assert.equal(await page.locator('.woocommerce-invalid .woocommerce-error').count(), 1);
			console.log(`mobile checkout error: scrollY ${before} -> ${after}; native notice beside invalid row`);
			await shot(page, viewport.width, 'en-proforma-error', '.woocommerce-invalid');
		}
		// Real Woo inquiry fixtures prove the confirmation hook and language-aware account action.
		for (const lang of ['en', 'de']) {
			const url = wp('eval', `$u=get_user_by("login","auth-forms-mobile-evidence"); $orders=wc_get_orders(array("customer_id"=>$u->ID,"limit"=>1,"meta_key"=>"_auth_forms_mobile_fixture","meta_value"=>"${lang}")); $o=$orders[0]??wc_create_order(array("customer_id"=>$u->ID,"status"=>"inquiry-received")); if (!$o->get_meta("_auth_forms_mobile_fixture")) { $p=get_page_by_path("saj-h2-10k-t3",OBJECT,"product"); $o->add_product(wc_get_product($p->ID),1); $o->set_address(array("first_name"=>"Mobile","last_name"=>"Evidence","company"=>"Auth Forms Mobile","address_1"=>"Teststrasse 1","postcode"=>"10115","city"=>"Berlin","country"=>"DE","email"=>$u->user_email),"billing"); $o->set_payment_method("linker_proforma"); $o->update_meta_data(Linker\\Commerce\\Inquiry\\OrderLocale::META,"${lang === 'de' ? 'de_DE_formal' : 'en_US'}"); $o->update_meta_data("_auth_forms_mobile_fixture","${lang}"); $o->calculate_totals(); $o->save(); } echo $o->get_checkout_order_received_url();`);
			await page.goto(url);
			await page.locator('.linker-proforma-success').waitFor({ state: 'attached' });
			await shot(page, viewport.width, `${lang}-proforma-success`, viewport.width < 640 ? '.linker-proforma-success' : '.woocommerce-order');
			await metrics(page, viewport.width, `${lang}-proforma-success`, '.linker-proforma-success', 'a');
		}
		await context.close();
		console.log(`${viewport.width}: EN/DE auth, three registration groups, reset, contact, Proforma screenshots and control assertions passed`);
	}
	await writeFile(resolve(evidence, 'metrics.json'), JSON.stringify(rows, null, 2) + '\n');
	console.log(`PASS: ${rows.length} real rendered surface measurements; screenshots at 390/1440/430`);
} finally {
	await browser.close();
}
