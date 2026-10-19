/**
 * A parts list becomes products (#251, docs/specs/13-genie.md goal 2): pasted
 * and uploaded, EN and DE at 1440 and 390, through the real proxy, the real
 * service and the real product data.
 *
 * - a 20-row mixed list: matched, uncertain and missing rows marked;
 * - the unclear rows answered one at a time;
 * - one click adds every confirmed row to the solution draft, and the draft
 *   page shows the products;
 * - a CSV upload is read as the same rows (the #236 channel).
 *
 * With LINKER_E2E_SHOTS set, every state is saved as a screenshot
 * (docs/acceptance/2026-10-19/251/).
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
const DRAFT: Record<Lang, string> = { en: '/cart/', de: '/de/warenkorb/' };
const SHOTS = process.env.LINKER_E2E_SHOTS ?? '';
/** The #251 fixtures: a 20-row workbook and a handwritten-style page. */
const FIXTURES = join(REPO_ROOT, 'services/genie/eval/parts');

const LIST: Record<Lang, string> = {
	en: [
		'Item | Qty',
		'2x SAJ H2-10K-T3',
		'1 x S.A.J. H2-12K-T3',
		'3 Stk. GoodWe GW10K-ETA-G20',
		'SAJ H2-15K-T3 - 2',
		'1× SAJ H2-20K T3',
		'4 x GoodWe GW5.1-BAT-D-G21',
		'2 x SAJ B2-10.0-HV1',
		'1 x EcoFlow EF BD-8-S2',
		'2 x EcoFlow EF BD-5-S2',
		'10 x GoodWe GM330',
		'1 x Chint DTSU666',
		'2 x Pylontech L260-OMNI',
		'1 x GoodWe GW7K-HCA-20',
		'3 x SAJ eSolar AIO3',
		'1 x SAJ BC2-HV1',
		'2 x SAJ BU2-5.0-HV1',
		'2 x GoodWe HCA',
		'4 x SAJ H2',
		'2 x SMA Sunny Boy 5.0',
		'1 x Fronius Symo 10',
	].join('\n'),
	de: [
		'Produkt;Menge',
		'2x SAJ H2-10K-T3',
		'1 x S.A.J. H2-12K-T3',
		'3 Stück GoodWe GW10K-ETA-G20',
		'2 Stk. SAJ H2-15K-T3',
		'1× SAJ H2-20K T3',
		'4 x GoodWe GW5.1-BAT-D-G21',
		'2 x SAJ B2-10.0-HV1',
		'1 x EcoFlow EF BD-8-S2',
		'2 x EcoFlow EF BD-5-S2',
		'10 x GoodWe GM330',
		'1 x Chint DTSU666',
		'2 x Pylontech L260-OMNI',
		'1 x GoodWe GW7K-HCA-20',
		'3 x SAJ eSolar AIO3',
		'1 x SAJ BC2-HV1',
		'2 x SAJ BU2-5.0-HV1',
		'2 x GoodWe HCA',
		'4 x SAJ H2',
		'2 x SMA Sunny Boy 5.0',
		'1 x Fronius Symo 10',
	].join('\n'),
};

const CSV: Record<Lang, string> = {
	en: [
		'Item,Qty',
		'SAJ H2-10K-T3,2',
		'S.A.J. H2-12K-T3,1',
		'GoodWe GW10K-ETA-G20,3',
		'SAJ H2-15K-T3,2',
		'SAJ H2-20K T3,1',
		'GoodWe GW5.1-BAT-D-G21,4',
		'SAJ B2-10.0-HV1,2',
		'EcoFlow EF BD-8-S2,1',
		'EcoFlow EF BD-5-S2,2',
		'GoodWe GM330,10',
		'Chint DTSU666,1',
		'Pylontech L260-OMNI,2',
		'GoodWe GW7K-HCA-20,1',
		'SAJ eSolar AIO3,3',
		'SAJ BC2-HV1,1',
		'SAJ BU2-5.0-HV1,2',
		'GoodWe HCA,2',
		'SAJ H2,4',
		'SMA Sunny Boy 5.0,2',
		'Fronius Symo 10,1',
	].join('\n'),
	de: [
		'Produkt,Menge',
		'SAJ H2-10K-T3,2',
		'S.A.J. H2-12K-T3,1',
		'GoodWe GW10K-ETA-G20,3',
		'SAJ H2-15K-T3,2',
		'SAJ H2-20K T3,1',
		'GoodWe GW5.1-BAT-D-G21,4',
		'SAJ B2-10.0-HV1,2',
		'EcoFlow EF BD-8-S2,1',
		'EcoFlow EF BD-5-S2,2',
		'GoodWe GM330,10',
		'Chint DTSU666,1',
		'Pylontech L260-OMNI,2',
		'GoodWe GW7K-HCA-20,1',
		'SAJ eSolar AIO3,3',
		'SAJ BC2-HV1,1',
		'SAJ BU2-5.0-HV1,2',
		'GoodWe HCA,2',
		'SAJ H2,4',
		'SMA Sunny Boy 5.0,2',
		'Fronius Symo 10,1',
	].join('\n'),
};

const WORDS: Record<
	Lang,
	{
		choose: string;
		title: string;
		match: RegExp;
		missing: string;
		ask: string;
		added: string;
		answer: string;
		addButton: RegExp;
		unreadable: string;
		range: string;
	}
> = {
	en: {
		choose: 'Choose a file',
		title: 'Your parts list',
		match: /In our range: H2-10K-T3/,
		missing: 'Not in our range.',
		ask: 'Which model does this line mean?',
		added: 'In your solution draft.',
		answer: 'Row %d: GW7K-HCA-20',
		addButton: /Add \d+ products to the solution draft/,
		unreadable: 'broken.xlsx could not be read.',
		range: 'In our range: ',
	},
	de: {
		choose: 'Datei auswählen',
		title: 'Ihre Teileliste',
		match: /In unserem Sortiment: H2-10K-T3/,
		missing: 'Nicht in unserem Sortiment.',
		ask: 'Welches Modell ist mit dieser Zeile gemeint?',
		added: 'Im Lösungsentwurf.',
		answer: 'Zeile %d: GW7K-HCA-20',
		addButton: /\d+ Produkte dem Lösungsentwurf hinzufügen/,
		unreadable: 'broken.xlsx konnte nicht gelesen werden.',
		range: 'In unserem Sortiment: ',
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

/**
 * The card from its first row and from its last: a 20-row card is taller than
 * the dock's transcript, so the viewport shot shows one part at a time. (An
 * element screenshot is clipped through the dock's transformed panel and
 * catches the page behind it.)
 */
async function cardShots(page: Page, name: string): Promise<void> {
	const transcript = page.locator('.linker-genie-app__transcript');
	await transcript.evaluate((element) => {
		const card = element.querySelector(
			'.linker-genie-parts'
		) as HTMLElement | null;
		if (card) {
			element.scrollTop = card.offsetTop - 12;
		}
	});
	await shot(page, `${name}-top`);
	await transcript.evaluate((element) => {
		const card = element.querySelector(
			'.linker-genie-parts'
		) as HTMLElement | null;
		if (card) {
			element.scrollTop =
				card.offsetTop + card.offsetHeight - element.clientHeight + 12;
		}
	});
	await shot(page, `${name}-bottom`);
}

async function newConversation(page: Page, lang: Lang): Promise<void> {
	await page
		.getByRole('button', {
			name: lang === 'de' ? 'Neues Gespräch' : 'New conversation',
		})
		.click();
	await expect(page.locator('.linker-genie-app__message')).toHaveCount(0);
}

/** Opens the dock for a list: the preview card on the desktop, the event on a phone. */
async function arriveForList(
	page: Page,
	lang: Lang,
	tag: string
): Promise<void> {
	const desktop = (page.viewportSize()?.width ?? 0) >= 1024;
	if (desktop) {
		await page.clock.install({ time: new Date('2026-10-19T09:00:00Z') });
	}
	await page.goto(instance().url + HOME[lang]);
	if (desktop) {
		await page.evaluate(() => document.fonts.ready);
		await page.evaluate(() =>
			window.scrollTo(0, document.body.scrollHeight)
		);
		await page.clock.runFor(8_500);
		const card = page.locator('[data-linker-genie-peek]');
		const list = page.locator('[data-linker-genie-peek-attach-list]');
		await expect(
			card,
			'the home card with its list suggestion'
		).toBeVisible();
		await expect(list).toBeVisible();
		await shot(page, `${tag}-0-card`);
		await page.clock.resume();
		await list.click();
		await expect(card).toBeHidden();
	} else {
		await page.evaluate(() =>
			window.dispatchEvent(
				new CustomEvent('linker-genie-ask', {
					detail: { attach: true, list: true },
				})
			)
		);
	}
	await expect(page.locator('.linker-genie-app__composer')).toBeVisible({
		timeout: 30_000,
	});
	await expect(
		page.getByRole('button', { name: WORDS[lang].choose })
	).toBeVisible();
	await shot(page, `${tag}-1-prompt`);
}

async function send(page: Page): Promise<void> {
	const votes = page.locator('.linker-genie-app__votes');
	const before = await votes.count();
	await expect(page.locator('.linker-genie-app__send')).toBeEnabled({
		timeout: 15_000,
	});
	await page.locator('.linker-genie-app__send').click();
	await expect
		.poll(async () => votes.count(), { timeout: 60_000 })
		.toBeGreaterThan(before);
}

/**
 * The answer is complete and its card is in view: the local 1.2s reveal has
 * ended and, when the card grew the transcript, the jump button is taken.
 */
async function settle(page: Page): Promise<void> {
	await expect(page.locator('.linker-genie-reply__show')).toHaveCount(0, {
		timeout: 10_000,
	});
	const jump = page.locator('.linker-genie-jump');
	if (await jump.isVisible().catch(() => false)) {
		await jump.click();
	}
}

// Each run starts with a fresh hourly upload allowance (Attachments::LIMIT):
// the CSV test sends one file per language and width, and a second run within
// the hour must not meet the limit it does not test.
test.beforeEach(() => {
	wp([
		'db',
		'query',
		"DELETE FROM wp_options WHERE option_name LIKE 'linker\\_tools\\_limit\\_genie\\_upload.%'",
	]);
});

for (const lang of ['en', 'de'] as Lang[]) {
	for (const width of [1440, 390]) {
		test(`parts list ${lang} ${width}`, async ({ page }) => {
			const words = WORDS[lang];
			const tag = `${lang}-${width}`;
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await arriveForList(page, lang, tag);

			// The 20-row list, pasted: matched, unclear and missing rows.
			await page.fill('#linker-genie-input', LIST[lang]);
			await send(page);
			await settle(page);
			const card = page.locator('.linker-genie-parts');
			await expect(card).toBeVisible({ timeout: 30_000 });
			await expect(card.locator('.linker-genie-parts__title')).toHaveText(
				words.title
			);
			await expect(
				card.locator('.linker-genie-parts__row--matched')
			).toHaveCount(16);
			await expect(
				card.locator('.linker-genie-parts__row--uncertain')
			).toHaveCount(2);
			await expect(
				card.locator('.linker-genie-parts__row--missing')
			).toHaveCount(2);
			await expect(card.getByText(words.match)).toBeVisible();
			await expect(card.getByText(words.missing).first()).toBeVisible();
			await expect(card.getByText(words.ask)).toBeVisible();
			await shot(page, `${tag}-2-parts`);
			await cardShots(page, `${tag}-2-parts-card`);

			// The first unclear row is answered one at a time.
			await card.getByRole('button', { name: 'GW7K-HCA-20' }).click();
			await expect(
				page.locator('.linker-genie-app__message--user').last()
			).toHaveText(words.answer.replace('%d', '17'));
			await expect(
				page.locator('.linker-genie-parts__row--matched')
			).toHaveCount(17);
			await expect(
				page.locator('.linker-genie-parts__row--uncertain')
			).toHaveCount(1);
			await shot(page, `${tag}-3-parts-one-answered`);
			await cardShots(page, `${tag}-3-parts-card`);

			// The second: the family's single-phase and three-phase models.
			await page.getByRole('button', { name: 'H2-15K-T3' }).click();
			await settle(page);
			await expect(page.locator('.linker-genie-parts__add')).toBeVisible({
				timeout: 60_000,
			});
			await expect(
				page.locator('.linker-genie-parts__row--uncertain')
			).toHaveCount(0);
			await shot(page, `${tag}-4-parts-ready`);
			await cardShots(page, `${tag}-4-parts-card`);

			// One click: every confirmed row into the solution draft.
			await page
				.getByRole('button', {
					name: words.addButton,
				})
				.click();
			await expect(
				page.locator('.linker-genie-parts__add')
			).toContainText(words.added);
			await shot(page, `${tag}-5-parts-added`);

			// The draft really holds them. #254 renames the German draft page;
			// a snapshot taken before its migration still answers the old one.
			const draft =
				lang === 'de' &&
				(
					await page.request.get(
						instance().url + '/de/loesungsentwurf/'
					)
				).ok()
					? '/de/loesungsentwurf/'
					: DRAFT[lang];
			await page.goto(instance().url + draft);
			await expect(page.getByText('SAJ H2-10K-T3').first()).toBeVisible({
				timeout: 30_000,
			});
			await shot(page, `${tag}-6-draft`);
		});

		test(`parts csv ${lang} ${width}`, async ({ page }) => {
			const tag = `${lang}-${width}-csv`;
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await arriveForList(page, lang, tag);
			const picker = page.locator('.linker-genie-app input[type="file"]');
			await picker.setInputFiles({
				name: 'parts.csv',
				mimeType: 'text/csv',
				buffer: Buffer.from(CSV[lang]),
			});
			await send(page);
			await settle(page);
			await expect(
				page.locator('.linker-genie-parts__row--matched')
			).toHaveCount(16, { timeout: 30_000 });
			await expect(
				page.locator('.linker-genie-parts__row--missing')
			).toHaveCount(2);
			await shot(page, `${tag}-1-csv-parts`);

			// The same list as an .xlsx workbook.
			await newConversation(page, lang);
			await picker.setInputFiles(join(FIXTURES, 'list.xlsx'));
			await send(page);
			await settle(page);
			await expect(
				page.locator('.linker-genie-parts__row--matched')
			).toHaveCount(16, { timeout: 30_000 });
			await expect(
				page.locator('.linker-genie-parts__row--missing')
			).toHaveCount(2);
			await shot(page, `${tag}-1-xlsx-parts`);

			// A photographed handwritten list (#236's vision channel).
			await newConversation(page, lang);
			await picker.setInputFiles(join(FIXTURES, 'list-handwritten.png'));
			await send(page);
			await settle(page);
			// The transcription of a photo varies a little; the clear models and
			// the two states are the stable evidence, and the card itself (the
			// screenshot) is the row-by-row record.
			await expect(
				page.locator('.linker-genie-parts__row--matched').first()
			).toBeVisible({ timeout: 60_000 });
			expect(
				await page.locator('.linker-genie-parts__row--matched').count()
			).toBeGreaterThanOrEqual(2);
			// At least one of the two unambiguous model lines was transcribed and
			// matched; the screenshot is the row-by-row record of the rest.
			const statuses = await page
				.locator(
					'.linker-genie-parts__row--matched .linker-genie-parts__status'
				)
				.allInnerTexts();
			expect(
				statuses.some(
					(line) =>
						line.includes('H2-10K-T3') || line.includes('DTSU666')
				)
			).toBe(true);
			expect(
				await page
					.locator('.linker-genie-parts__row--uncertain')
					.count()
			).toBeGreaterThanOrEqual(1);
			expect(
				await page.locator('.linker-genie-parts__row--missing').count()
			).toBeGreaterThanOrEqual(1);
			await shot(page, `${tag}-1-photo-parts`);

			// An Excel file that is no workbook: a failed list, with the picker
			// offered again (not a photo picker).
			await newConversation(page, lang);
			await picker.setInputFiles({
				name: 'broken.xlsx',
				mimeType:
					'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
				buffer: Buffer.from('PK\u0003\u0004not a workbook'),
			});
			await send(page);
			await expect(page.getByText(WORDS[lang].unreadable)).toBeVisible({
				timeout: 60_000,
			});
			await expect(
				page.getByRole('button', { name: WORDS[lang].choose })
			).toBeVisible();
			await page
				.locator('.linker-genie-attachment')
				.first()
				.scrollIntoViewIfNeeded();
			await shot(page, `${tag}-1-bad-list`);
		});
	}
}
