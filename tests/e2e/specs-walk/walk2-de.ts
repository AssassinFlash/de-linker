/** b2-inquiry acceptance walk — standalone (mission 2026-10-29). Not part of the suite. */
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import {
	applyTurnstileProfile,
	instance,
	REPO_ROOT,
	wp,
} from '../lib/instance';
import { since } from '../lib/mail';
import { waitForTurnstile } from '../lib/turnstile';

const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);
const out = join(REPO_ROOT, '.scratch/b2-walk');
mkdirSync(out, { recursive: true });
const t = (m: string) => console.log(new Date().toISOString(), m);

async function main() {
	const email = `b2walk-${Date.now()}@example.test`;
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
	const url = `${instance().url}/de/proforma-anfrage/`;
	const evidence: Record<string, unknown> = { email, product: setup.product };
	const restoreTurnstile = applyTurnstileProfile();
	try {
		await page.goto(url);
		const form = page.locator('form.linker-inquiry-form');
		await form.waitFor();
		await context.request.get(
			`${instance().url}/?add-to-cart=${setup.product}`
		);
		await page.reload();
		await page.locator('.linker-inquiry-line').first().waitFor();
		t('form ready with one draft line');

		// Validation A: invalid email is blocked client-side (native + account-ui).
		await form.locator('[name="name"]').fill('B2 Walk Gast');
		await form.locator('[name="email"]').fill('not-an-email');
		await form.locator('[name="company"]').fill('Walk GmbH');
		await form
			.locator('[name="message"]')
			.fill(
				'Bitte kalkulieren Sie das Produkt aus dem Lösungsentwurf für ein Projekt in Bayern.'
			);
		await form.locator('[name="consent"]').check();
		await form.locator('[type="submit"]').click();
		evidence.validationANativeBlocked =
			page.url() === url &&
			(await form
				.locator('[name="email"]')
				.evaluate(
					(field: HTMLInputElement) => field.validity.typeMismatch
				));

		await form.locator('[name="email"]').fill(email);
		await waitForTurnstile(form);
		await form.locator('[type="submit"]').click();
		await page
			.locator('.linker-form-success')
			.first()
			.waitFor({ timeout: 30_000 });
		evidence.confirmedUrl = page.url();
		evidence.heading = await page
			.locator('.linker-form-success h2')
			.first()
			.textContent()
			.catch(() => null);
		evidence.successText = await page
			.locator('.linker-form-success')
			.first()
			.textContent();
		await page.screenshot({
			path: join(out, 'de-guest-confirmation.png'),
			fullPage: true,
		});
		t(`confirmation heading=${JSON.stringify(evidence.heading)}`);

		// Async mail (#533): poll the send-authorization state and outbox.
		const before = Date.now();
		const id = Number(
			wp([
				'eval',
				`$os = wc_get_orders(["limit" => 1, "billing_email" => "${email}"]); echo $os ? $os[0]->get_id() : 0;`,
			]).trim()
		);
		evidence.orderId = id;
		t(`order id=${id}`);
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
			i < 30 && (queued() < 2 || deliveredCount(states) < 2);
			i++
		) {
			const readback = JSON.parse(run('read')) as { mail: unknown[] };
			mail = readback.mail;
			// The queue posts are removed once delivered; keep the routing data
			// from the first read that sees both jobs.
			if (mail.length >= 2 && !evidence.queueMail) {
				evidence.queueMail = mail;
			}
			states = JSON.parse(
				wp([
					'eval',
					`$v = get_option("linker_inquiry_send_${id}"); if (is_string($v)) { $v = json_decode($v, true); } echo wp_json_encode(["status" => $v["status"] ?? null, "attempts" => $v["attempts"] ?? null, "verdict" => $v["verdict"]["decision"] ?? null, "reason" => $v["verdict"]["reason"] ?? null, "jobs" => $v["jobs"] ?? null]);`,
				]).trim()
			);
			t(
				`poll ${i}: mail=${mail.length} delivered=${deliveredCount(states)} state=${JSON.stringify(states)}`
			);
			if (mail.length < 2) {
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
					/* heartbeat output is not needed */
				}
				try {
					// Drive the Action Scheduler queue the way the host runner does.
					wp([
						'action-scheduler',
						'run',
						'--group=linker-commerce',
						'--batches=3',
					]);
				} catch {
					/* runner output is not needed */
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
		const readback = JSON.parse(run('read'));
		evidence.readback = readback;
		evidence.assertions = {
			oneOrder: readback.orders.length === 1,
			status: readback.orders[0]?.status,
			source: readback.orders[0]?.source,
			items: readback.orders[0]?.items,
			mailJobs: queued(),
			receiptToCustomer: (
				(evidence.queueMail ?? mail) as { to: string[] }[]
			).some((m) => m.to.includes(email)),
			spoolRendered: spool.length,
			validationBShowsError:
				typeof evidence.validationBError === 'string' &&
				evidence.validationBError.trim().length > 3,
			retainedSurvived:
				retainedName === 'B2 Walk Gast' && retainedEmail === email,
		};
		t(`assertions=${JSON.stringify(evidence.assertions)}`);
		const jobIds = Object.values(
			(states as { jobs?: Record<string, { id: number }> }).jobs ?? {}
		).map((j) => j.id);
		if (jobIds.length) {
			evidence.jobMessages = JSON.parse(
				wp([
					'eval',
					`$o=[]; foreach ([${jobIds.join(',')}] as $jid) { $m = get_post_meta($jid, "_linker_mail_message", true); $o[$jid] = $m ? json_decode($m, true) : null; } echo wp_json_encode($o, JSON_PARTIAL_OUTPUT_ON_ERROR);`,
				]).trim()
			);
			t(
				`jobMessages=${JSON.stringify(evidence.jobMessages).slice(0, 400)}`
			);
		}
	} finally {
		restoreTurnstile();
		await context.close().catch(() => {});
		await browser.close().catch(() => {});
		writeFileSync(
			join(out, 'de-guest.json'),
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
			} catch (e) {
				t(`cleanup failed: ${String(e)}`);
			}
		} else {
			t('mail chain incomplete; fixture kept for retry driving');
		}
	}
}

void main();
