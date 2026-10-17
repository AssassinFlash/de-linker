/** Account review through real WordPress screens and authenticated REST. */
import { expect, test } from '@playwright/test';
import { instance, loginLink, wp } from '../lib/instance';

for (const locale of ['en_US', 'de_DE_formal'] as const) {
	for (const width of [1440, 390]) {
		test(`accounts admin ${locale} ${width}: review, reasons, history and toolbar`, async ({
			page,
		}) => {
			const staff = wp([
				'user',
				'list',
				'--role=administrator',
				'--field=ID',
			])
				.trim()
				.split('\n')[0]!;
			let previousLocale: string | null = null;
			try {
				previousLocale = wp([
					'user',
					'meta',
					'get',
					staff,
					'locale',
				]).trim();
			} catch {
				/* no preference saved */
			}
			const savedMailOptions = new Map<string, string | null>();
			for (const name of [
				'linker_commerce_test_mail_to',
				'linker_commerce_mail_sends',
			]) {
				try {
					savedMailOptions.set(
						name,
						wp(['option', 'get', name, '--format=json']).trim()
					);
				} catch {
					savedMailOptions.set(name, null);
				}
			}
			const tag = `a227-e2e-${Date.now()}`;
			const mailMarker = Number(
				wp([
					'eval',
					'echo (int) (get_posts(array("post_type" => Linker\\Commerce\\Mail\\JobStore::POST_TYPE, "post_status" => "any", "posts_per_page" => 1, "orderby" => "ID", "order" => "DESC", "fields" => "ids"))[0] ?? 0);',
				]).trim()
			);
			const id = wp([
				'user',
				'create',
				tag,
				`${tag}@example.test`,
				'--role=customer',
				'--porcelain',
			]).trim();
			try {
				wp(['user', 'meta', 'update', staff, 'locale', locale]);
				wp([
					'eval',
					`$c = new WC_Customer(${id}); $c->set_billing_company('A227 Browser Solar GmbH'); $c->set_billing_country('DE'); $c->set_billing_first_name('Maria'); $c->set_billing_last_name('Example'); $c->save(); update_user_meta(${id}, 'locale', '${locale}'); update_option('linker_commerce_test_mail_to', 'tester@example.test'); update_option('linker_commerce_mail_sends', array_fill(0, Linker\\Commerce\\Mail\\Throttle::PER_DAY, time()));`,
				]);
				await page.setViewportSize({ width, height: 900 });
				await page.goto(
					loginLink(
						undefined,
						wp(['user', 'get', staff, '--field=user_login']).trim()
					)
				);
				await page.goto(`${instance().url}/wp-admin/index.php`);
				const pendingCount = page.locator(
					'#linker-accounts-widget .postbox-header [data-linker-account-count]'
				);
				const initialPending = Number(await pendingCount.textContent());
				await page
					.locator(`#linker-accounts-queue [data-account-id="${id}"]`)
					.getByRole('button', {
						name:
							locale === 'de_DE_formal' ? 'Freigeben' : 'Approve',
						exact: true,
					})
					.click();
				await expect(pendingCount).toHaveText(
					String(initialPending - 1)
				);
				await expect(
					page.locator(
						'#wp-admin-bar-linker-accounts [data-linker-account-count]'
					)
				).toHaveText(String(initialPending - 1));
				const notificationLink = wp([
					'eval',
					`$emails = WC()->mailer()->get_emails(); $emails[Linker\\Commerce\\Registration\\Emails\\NewCustomerEmail::class]->trigger(${id}); $jobId = get_posts(array("post_type" => Linker\\Commerce\\Mail\\JobStore::POST_TYPE, "post_status" => "any", "posts_per_page" => 1, "orderby" => "ID", "order" => "DESC", "fields" => "ids"))[0]; $job = (new Linker\\Commerce\\Mail\\JobStore())->load($jobId); preg_match('/href="([^"]*page=linker-accounts[^"]*)"/', html_entity_decode($job['message']->body, ENT_QUOTES, 'UTF-8'), $link); echo $link[1];`,
				]).trim();
				expect(notificationLink).toContain(`&focus=${id}`);
				await page.goto(notificationLink);
				const card = page.locator(
					`#linker-accounts-focus [data-account-id="${id}"]`
				);
				await expect(card).toBeVisible();
				await expect(card).toContainText(
					locale === 'de_DE_formal' ? 'Deutschland' : 'Germany'
				);
				await expect(card.locator('details')).toHaveAttribute(
					'open',
					''
				);
				const route = `${instance().url}/wp-json/linker/v1/accounts/${id}/approval?_locale=user`;
				const nonce = await page
					.locator('#linker-accounts-app')
					.getAttribute('data-nonce');
				const missingNonce = await page.request.post(route, {
					data: { status: 'approved' },
				});
				expect(missingNonce.status()).toBe(403);
				const blankReason = await page.request.post(route, {
					data: { status: 'restricted' },
					headers: { 'X-WP-Nonce': nonce! },
				});
				expect(blankReason.status()).toBe(400);
				for (const [status, button] of [
					[
						'approved',
						locale === 'de_DE_formal' ? 'Freigeben' : 'Approve',
					],
					[
						'restricted',
						locale === 'de_DE_formal' ? 'Einschränken' : 'Restrict',
					],
					[
						'rejected',
						locale === 'de_DE_formal' ? 'Ablehnen' : 'Reject',
					],
					[
						'approved',
						locale === 'de_DE_formal' ? 'Freigeben' : 'Approve',
					],
				] as const) {
					await card
						.getByRole('button', { name: button, exact: true })
						.click();
					if (status !== 'approved') {
						await card
							.getByRole('textbox')
							.fill(
								locale === 'de_DE_formal'
									? 'Bitte ergänzen Sie Ihre Unternehmenswebsite.'
									: 'Please provide the company website.'
							);
						await card
							.getByRole('button', {
								name:
									locale === 'de_DE_formal'
										? `${button} und Kunden informieren`
										: `${button} and notify customer`,
								exact: true,
							})
							.click();
					}
					await expect(card.getByRole('status')).toContainText(
						locale === 'de_DE_formal'
							? 'Die Entscheidung wurde gespeichert.'
							: 'Decision saved.'
					);
					expect(
						wp([
							'user',
							'meta',
							'get',
							id,
							'linker_approval_status',
						]).trim()
					).toBe(status);
					if (locale === 'de_DE_formal') {
						await expect(card).not.toContainText('Email domain:');
					}
				}
				const before = page.url();
				const flag = page.locator('#wp-admin-bar-linker-accounts > a');
				await flag.scrollIntoViewIfNeeded();
				await expect(flag).toBeInViewport();
				if (width === 390) {
					await expect(page.locator('#wpadminbar')).toHaveCSS(
						'position',
						'absolute'
					);
				}
				await flag.click();
				await expect(page.getByRole('dialog')).toBeVisible();
				if (width === 390) {
					await expect(page.locator('#wpadminbar')).toHaveCSS(
						'position',
						'fixed'
					);
				}
				expect(page.url()).toBe(before);
				await page.keyboard.press('Escape');
				await expect(page.getByRole('dialog')).not.toBeVisible();
				await expect(flag).toBeFocused();
				if (width === 390) {
					await expect(page.locator('#wpadminbar')).toHaveCSS(
						'position',
						'absolute'
					);
				}
				await page.goto(
					`${instance().url}/wp-admin/admin.php?page=linker-accounts&status=approved&s=A227+Browser+Solar`
				);
				await expect(
					page.locator(`#linker-account-row-${id}`)
				).toBeVisible();
				const rowToggle = page.locator(
					`#linker-account-row-${id} .toggle-row`
				);
				await expect(rowToggle).toHaveCount(1);
				if (width === 390) {
					await rowToggle.click();
					await expect(
						page.locator(`#linker-account-row-${id} .column-status`)
					).toBeVisible();
				}
				await page
					.locator(`#linker-account-row-${id} [data-linker-account]`)
					.first()
					.click();
				await expect(
					page
						.getByRole('dialog')
						.locator(`[data-account-id="${id}"]`)
				).toBeVisible();
				const historicalCard = page
					.getByRole('dialog')
					.locator(`[data-account-id="${id}"]`);
				await historicalCard
					.getByRole('button', {
						name:
							locale === 'de_DE_formal'
								? 'Einschränken'
								: 'Restrict',
						exact: true,
					})
					.click();
				await historicalCard
					.getByRole('textbox')
					.fill('Please provide your company website.');
				await historicalCard
					.getByRole('button', {
						name:
							locale === 'de_DE_formal'
								? 'Einschränken und Kunden informieren'
								: 'Restrict and notify customer',
						exact: true,
					})
					.click();
				await expect(
					page.locator(`#linker-account-row-${id}`)
				).toBeHidden();
				await expect(
					page.locator(
						`#linker-accounts-restricted [data-account-id="${id}"]`
					)
				).toBeVisible();
				await historicalCard
					.getByRole('button', {
						name:
							locale === 'de_DE_formal' ? 'Freigeben' : 'Approve',
						exact: true,
					})
					.click();
				await expect(
					page.locator(`#linker-account-row-${id}`)
				).toBeVisible();
				await expect(
					page.locator(
						`#linker-accounts-restricted [data-account-id="${id}"]`
					)
				).toHaveCount(0);
				await historicalCard
					.getByRole('button', {
						name:
							locale === 'de_DE_formal'
								? 'Einschränken'
								: 'Restrict',
						exact: true,
					})
					.click();
				await historicalCard
					.getByRole('textbox')
					.fill('Please provide your company website.');
				await historicalCard
					.getByRole('button', {
						name:
							locale === 'de_DE_formal'
								? 'Einschränken und Kunden informieren'
								: 'Restrict and notify customer',
						exact: true,
					})
					.click();
				await expect(
					page.locator(`#linker-account-row-${id}`)
				).toBeHidden();
				await page.keyboard.press('Escape');
				await expect(page.getByRole('dialog')).not.toBeVisible();
				await expect(flag).toBeFocused();
				expect(
					await page.evaluate(
						() =>
							document.documentElement.scrollWidth <=
							window.innerWidth
					)
				).toBe(true);
			} finally {
				wp([
					'eval',
					`foreach (get_posts(array("post_type" => Linker\\Commerce\\Mail\\JobStore::POST_TYPE, "post_status" => "any", "posts_per_page" => -1, "fields" => "ids")) as $jobId) { if ($jobId > ${mailMarker}) { as_unschedule_all_actions(Linker\\Commerce\\Mail\\Outbox::HOOK, array($jobId), Linker\\Commerce\\Mail\\Outbox::GROUP); wp_delete_post($jobId, true); } }`,
				]);
				if (previousLocale === null) {
					wp(['user', 'meta', 'delete', staff, 'locale']);
				} else {
					wp([
						'user',
						'meta',
						'update',
						staff,
						'locale',
						previousLocale,
					]);
				}
				for (const [name, value] of savedMailOptions) {
					if (value === null) {
						wp(['option', 'delete', name]);
					} else {
						wp(['option', 'update', name, value, '--format=json']);
					}
				}
				wp(['user', 'delete', id, '--yes']);
			}
		});
	}
}
