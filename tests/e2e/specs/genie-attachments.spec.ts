/**
 * Photos and PDFs in the Genie dock (#236, docs/specs/13-genie.md "附件与铭牌"),
 * through the real proxy, the real service and deepseek-flash, EN and DE at
 * 1440 and 390:
 *
 * - opened for a nameplate photo (the home preview card's suggestion), the dock
 *   offers the picker;
 * - a nameplate of one of our models: the card, its product, and the
 *   confirmation sending a message that names the model;
 * - a nameplate whose model cannot be read: another photo or the model typed;
 * - a datasheet PDF and a question about it, answered from the reading;
 * - a file Genie does not read is refused before it is sent.
 *
 * With LINKER_E2E_SHOTS set, every state is saved as a screenshot
 * (docs/acceptance/2026-10-18/236/).
 */

/**
 * External dependencies
 */
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, REPO_ROOT, wp } from '../lib/instance';

type Lang = 'en' | 'de';

const HOME: Record<Lang, string> = { en: '/', de: '/de/' };
const SHOTS = process.env.LINKER_E2E_SHOTS ?? '';
const PHOTOS = join(REPO_ROOT, 'services/genie/eval/attachments/photos');
/** The research's synthetic label of a model we carry (SAJ H2-10K-T3). */
const EXACT = join(
	REPO_ROOT,
	'docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png'
);
const DATASHEET =
	process.env.LINKER_E2E_DATASHEET ??
	join(
		process.env.HOME ?? '',
		'de-linker-data/20261018-0541/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf'
	);

const WORDS: Record<
	Lang,
	{
		choose: string;
		inRange: RegExp;
		works: string;
		typeModel: string;
		unreadable: string;
		refused: string;
		question: string;
		sent: RegExp;
	}
> = {
	en: {
		choose: 'Choose a photo',
		inRange: /In our range: SAJ H2-10K-T3\. Is this your device\?/,
		works: 'Yes, what works with it?',
		typeModel: 'Type the model',
		unreadable: 'The model could not be read.',
		refused:
			'This file type cannot be sent. Genie reads photos (JPEG, PNG, WebP or HEIC) and PDFs.',
		question:
			'What is the maximum PV array power of the H2-10K-T3 in this datasheet?',
		sent: /Yes, it's the SAJ H2-10K-T3\. What works with it\?/,
	},
	de: {
		choose: 'Foto auswählen',
		inRange: /In unserem Sortiment: SAJ H2-10K-T3\. Ist das Ihr Gerät\?/,
		works: 'Ja, was passt dazu?',
		typeModel: 'Modell eingeben',
		unreadable: 'Das Modell konnte nicht gelesen werden.',
		refused:
			'Dieser Dateityp kann nicht gesendet werden. Genie liest Fotos (JPEG, PNG, WebP oder HEIC) und PDFs.',
		question:
			'Welche maximale PV-Leistung hat der H2-10K-T3 laut diesem Datenblatt?',
		sent: /Ja, es ist das Modell SAJ H2-10K-T3\. Was passt dazu\?/,
	},
};

async function shot(page: Page, name: string): Promise<void> {
	if (!SHOTS) {
		return;
	}
	mkdirSync(SHOTS, { recursive: true });
	await page.screenshot({
		path: join(SHOTS, `${name}.png`),
		animations: 'disabled',
	});
}

/** Opens the dock the way the preview card's nameplate suggestion does. */
async function openForPhoto(page: Page): Promise<void> {
	await page.evaluate(() =>
		window.dispatchEvent(
			new CustomEvent('linker-genie-ask', { detail: { attach: true } })
		)
	);
	await expect(page.locator('.linker-genie-app__composer')).toBeVisible({
		timeout: 30_000,
	});
}

/** Sends the composer and waits for the answer (its vote buttons). */
async function send(page: Page): Promise<void> {
	const votes = page.locator('.linker-genie-app__votes');
	const before = await votes.count();
	await expect(page.locator('.linker-genie-app__send')).toBeEnabled({
		timeout: 15_000,
	});
	await page.locator('.linker-genie-app__send').click();
	await expect
		.poll(async () => votes.count(), { timeout: 120_000 })
		.toBeGreaterThan(before);
}

async function newConversation(page: Page, lang: Lang): Promise<void> {
	await page
		.getByRole('button', {
			name: lang === 'de' ? 'Neues Gespräch' : 'New conversation',
		})
		.click();
	await expect(page.locator('.linker-genie-app__message')).toHaveCount(0);
}

// Each run starts with a fresh hourly upload allowance (Attachments::LIMIT, 20
// files an hour per connection): the suite sends 8 files a test, and a second
// run within the hour would meet the limit it does not test.
test.beforeEach(() => {
	wp([
		'db',
		'query',
		"DELETE FROM wp_options WHERE option_name LIKE 'linker\\_tools\\_limit\\_genie\\_upload.%'",
	]);
});

for (const lang of ['en', 'de'] as Lang[]) {
	for (const width of [1440, 390]) {
		test(`attachments ${lang} ${width}`, async ({ page }) => {
			const words = WORDS[lang];
			const tag = `${lang}-${width}`;
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(instance().url + HOME[lang]);
			await openForPhoto(page);
			const picker = page.locator('.linker-genie-app input[type="file"]');

			// Opened for a nameplate photo: the picker is one click away.
			await expect(
				page.getByRole('button', { name: words.choose })
			).toBeVisible();
			await shot(page, `${tag}-1-photo-prompt`);

			// A file Genie does not read never leaves the browser.
			await picker.setInputFiles({
				name: 'parts.xlsx',
				mimeType: 'application/vnd.ms-excel',
				buffer: Buffer.from('not a photo'),
			});
			await expect(page.getByRole('alert')).toHaveText(words.refused);
			await shot(page, `${tag}-2-refused`);
			await page.locator('.linker-genie-app__attachment-remove').click();

			// A nameplate of one of our models: the card and its product.
			await picker.setInputFiles(EXACT);
			await expect(
				page.locator('.linker-genie-app__attachment-name')
			).toHaveText('nameplate-probe.jpg');
			await shot(page, `${tag}-3-picked`);
			await send(page);
			await expect(
				page.locator('.linker-genie-attachment__status')
			).toHaveText(words.inRange);
			await expect(page.locator('.linker-card').first()).toBeVisible({
				timeout: 30_000,
			});
			await shot(page, `${tag}-4-nameplate-exact`);
			await page
				.locator('.linker-genie-attachment')
				.screenshot(
					SHOTS
						? { path: join(SHOTS, `${tag}-4-nameplate-card.png`) }
						: {}
				);

			// Confirming sends a message that names the model.
			const votes = page.locator('.linker-genie-app__votes');
			const before = await votes.count();
			await page.getByRole('button', { name: words.works }).click();
			await expect(
				page.locator('.linker-genie-app__message--user').last()
			).toHaveText(words.sent);
			await expect
				.poll(async () => votes.count(), { timeout: 120_000 })
				.toBeGreaterThan(before);
			await shot(page, `${tag}-5-confirmed`);

			// A nameplate whose model cannot be read.
			await newConversation(page, lang);
			await picker.setInputFiles(
				join(PHOTOS, 'pylontech-us3000c-thumbnail.jpg')
			);
			await send(page);
			await expect(
				page.locator('.linker-genie-attachment__status')
			).toHaveText(words.unreadable);
			await expect(
				page.getByRole('button', { name: words.typeModel })
			).toBeVisible();
			await shot(page, `${tag}-6-nameplate-unreadable`);
			await page.getByRole('button', { name: words.typeModel }).click();
			await expect(page.locator('#linker-genie-input')).toBeFocused();
			await shot(page, `${tag}-7-type-the-model`);

			// A datasheet PDF and a question about it.
			await newConversation(page, lang);
			await picker.setInputFiles(DATASHEET);
			await page.fill('#linker-genie-input', words.question);
			await send(page);
			await expect(
				page.locator('.linker-genie-attachment__status')
			).toContainText(
				lang === 'de' ? 'Gelesen: H2-10-30K' : 'Read: H2-10-30K'
			);
			await expect(
				page.locator('.linker-genie-app__message--assistant').last()
			).toContainText(/20[.,\s]?000/);
			await shot(page, `${tag}-8-datasheet`);
		});
	}
}
