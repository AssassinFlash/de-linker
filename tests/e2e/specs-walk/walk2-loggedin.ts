/** b2-inquiry acceptance walk — logged-in customer (EN). Standalone; not part of the suite. */
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT, wp } from '../lib/instance';
import { since } from '../lib/mail';

const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);
const out = join(REPO_ROOT, '.scratch/b2-walk');
mkdirSync(out, { recursive: true });
const t = (m: string) => console.log(new Date().toISOString(), m);

async function main() {
	const stamp = Date.now();
	const email = `b2walk-li-${stamp}@example.test`;
	const pass = `W2lk-${stamp}-Aa1!`;
	// Fresh customer with billing profile (approved, real name/email/company).
	wp([
		'eval',
		`$u = wp_insert_user(["user_login" => "b2walkli${stamp}", "user_email" => "${email}", "user_pass" => "${pass}", "role" => "customer", "first_name" => "Lena", "last_name" => "Login"]); if (is_wp_error($u)) { echo $u->get_error_message(); exit(1); } update_user_meta($u, "linker_approval_status", "approved"); $c = new WC_Customer($u); $c->set_billing_company("Login GmbH"); $c->set_billing_first_name("Lena"); $c->set_billing_last_name("Login"); $c->set_billing_email("${email}"); $c->save(); echo $u;`,
	]);
	const userId = Number(
		wp(['user', 'get', `b2walkli${stamp}`, '--field=ID']).trim()
	);
	t(`user ${userId}`);
	try {
		run('cleanup');
	} catch {
		/* no fixture from a previous run */
	}
	const setup = JSON.parse(run('setup', email, 'receipt')) as {
		product: number;
	};
	t(`fixture setup product=${setup.product}`);

	const browser = await chromium.launch();
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
	});
	const page = await context.newPage();
	const url = `${instance().url}/proforma-request/`;
	const evidence: Record<string, unknown> = {
		email,
		product: setup.product,
		userId,
	};
	try {
		// Log in as the customer.
		await page.goto(`${instance().url}/wp-login.php`);
		await page.locator('#user_login').fill(`b2walkli${stamp}`);
		await page.locator('#user_pass').fill(pass);
		await page.locator('#wp-submit').click();
		await page.waitForLoadState('networkidle');
		evidence.loggedIn =
			(await page.locator('#wp-admin-bar-my-account').count()) > 0 ||
			page.url().includes('my-account');
		t(`logged in=${evidence.loggedIn}`);

		await page.goto(url);
		const form = page.locator('form.linker-inquiry-form');
		await form.waitFor();
		await context.request.get(
			`${instance().url}/?add-to-cart=${setup.product}`
		);
		await page.reload();
		await page.locator('.linker-inquiry-line').first().waitFor();
		t('form ready with one draft line');

		// Profile row must be collapsed and prefilled.
		const details = form.locator('details');
		evidence.detailsCount = await details.count();
		if (await details.count()) {
			evidence.detailsOpen = await details
				.first()
				.evaluate((el) => (el as HTMLDetailsElement).open);
		}
		evidence.prefill = {
			name: await form.locator('[name="name"]').inputValue(),
			email: await form.locator('[name="email"]').inputValue(),
			company: await form.locator('[name="company"]').inputValue(),
		};
		const consentChecked = await form
			.locator('[name="consent"]')
			.isChecked();
		evidence.consentChecked = consentChecked;
		t(
			`details=${evidence.detailsCount} open=${evidence.detailsOpen} prefill=${JSON.stringify(evidence.prefill)} consent=${consentChecked}`
		);

		// Message + submit (fields already valid; fill only the message).
		await form
			.locator('[name="message"]')
			.fill(
				'Logged-in walk: please quote the draft product for our Bavaria project.'
			);
		await page.waitForTimeout(3_100);
		await Promise.all([
			page.waitForNavigation({ timeout: 30_000 }),
			form.locator('[type="submit"]').click(),
		]).catch(() => {});
		t(`after submit url=${page.url()}`);
		await page
			.locator('.linker-form-success')
			.first()
			.waitFor({ timeout: 30_000 });
		evidence.confirmedUrl = page.url();
		evidence.successText = await page
			.locator('.linker-form-success')
			.first()
			.textContent();
		await page.screenshot({
			path: join(out, 'loggedin-confirmation.png'),
			fullPage: true,
		});
		t(`confirmation=${String(evidence.successText).slice(0, 80)}`);

		// Async mail (#533).
		const before = Date.now();
		const id = Number(
			wp([
				'eval',
				`$os = wc_get_orders(["limit" => 1, "billing_email" => "${email}"]); echo $os ? $os[0]->get_id() : 0;`,
			]).trim()
		);
		evidence.orderId = id;
		let mail: unknown[] = [];
		let states: Record<string, unknown> = {};
		const deliveredCount = (s: {
			jobs?: Record<string, { delivered_at?: number | null }>;
		}) => Object.values(s.jobs ?? {}).filter((j) => j.delivered_at).length;
		const queued = () =>
			(evidence.queueMail as unknown[] | undefined)?.length ??
			mail.length;
		for (
			let i = 0;
			i < 40 && (queued() < 2 || deliveredCount(states) < 2);
			i++
		) {
			const readback = JSON.parse(run('read')) as { mail: unknown[] };
			mail = readback.mail;
			if (mail.length >= 2 && !evidence.queueMail)
				evidence.queueMail = mail;
			states = JSON.parse(
				wp([
					'eval',
					`$v = get_option("linker_inquiry_send_${id}"); if (is_string($v)) { $v = json_decode($v, true); } echo wp_json_encode(["status" => $v["status"] ?? null, "attempts" => $v["attempts"] ?? null, "verdict" => $v["verdict"]["decision"] ?? null, "reason" => $v["verdict"]["reason"] ?? null, "jobs" => $v["jobs"] ?? null]);`,
				]).trim()
			);
			t(
				`poll ${i}: mail=${mail.length} delivered=${deliveredCount(states)} state=${JSON.stringify(states)}`
			);
			if (queued() < 2 || deliveredCount(states) < 2) {
				const nextAt = Number(
					wp([
						'eval',
						`$v = get_option("linker_inquiry_send_${id}"); if (is_string($v)) { $v = json_decode($v, true); } echo (int) ($v["next_at"] ?? 0);`,
					]).trim()
				);
				const waitMs = Math.max(
					0,
					Math.min(90_000, nextAt * 1000 - Date.now())
				);
				if (waitMs > 2_000) {
					t(
						`waiting ${(waitMs / 1000).toFixed(0)}s for next retry window`
					);
					await new Promise((r) => setTimeout(r, waitMs));
				}
				try {
					wp(['linker-commerce', 'inquiry-assessments']);
				} catch {
					/* heartbeat */
				}
				try {
					wp([
						'action-scheduler',
						'run',
						'--group=linker-commerce',
						'--batches=3',
					]);
				} catch {
					/* runner */
				}
				await new Promise((r) => setTimeout(r, 5_000));
			}
		}
		evidence.sendStates = states;
		const spool = since(before);
		evidence.spool = spool.map((m) => ({
			to: m.to,
			subject: m.subject,
			file: m.file,
		}));
		const readback = JSON.parse(run('read')) as {
			orders: { customer: number }[];
		};
		evidence.readbackOrders = readback.orders;
		evidence.assertions = {
			detailsCollapsedOne:
				evidence.detailsCount === 1 && evidence.detailsOpen === false,
			prefillMatches:
				(evidence.prefill as Record<string, string>).name ===
					'Lena Login' &&
				(evidence.prefill as Record<string, string>).email === email &&
				(evidence.prefill as Record<string, string>).company ===
					'Login GmbH',
			consentChecked,
			orderCustomerIsUser: readback.orders[0]?.customer === userId,
			status: readback.orders[0] ? undefined : 'none',
			mailJobs: queued(),
			spoolRendered: spool.length,
		};
		t(`assertions=${JSON.stringify(evidence.assertions)}`);
	} finally {
		await context.close().catch(() => {});
		await browser.close().catch(() => {});
		writeFileSync(
			join(out, 'loggedin.json'),
			JSON.stringify(evidence, null, 2)
		);
		const done =
			Array.isArray(evidence.queueMail) &&
			evidence.queueMail.length >= 2 &&
			Object.values(
				(
					evidence.sendStates as {
						jobs?: Record<string, { delivered_at?: number }>;
					}
				)?.jobs ?? {}
			).every((j) => j.delivered_at);
		if (done) {
			try {
				run('cleanup');
			} catch {
				/* already clean */
			}
			wp(['user', 'delete', String(userId), '--yes', '--reassign=1']);
		} else {
			t('mail chain incomplete; fixture kept for retry driving');
		}
	}
}

void main();
