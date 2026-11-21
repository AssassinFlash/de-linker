import { expect, test, type Locator, type Page } from '@playwright/test';
import { instance } from '../lib/instance';

const routes = {
	en: '/solution-configurator/',
	de: '/de/loesungskonfigurator/',
};
const tabs = {
	en: ['Compare', 'Equipment', 'Roof', 'Project', 'Inquiry'],
	de: ['Vergleichen', 'Geräte', 'Dach', 'Projekt', 'Anfrage'],
};
const queries = [
	'?compare=preliminary',
	'?view=equipment',
	'?step=roof',
	'?view=project',
	'?view=inquiry',
];
const views = ['compare', 'equipment', 'roof', 'project', 'inquiry'];

async function reviewFromEntry(
	page: Page,
	link: Locator,
	target: URL,
	language: keyof typeof routes
) {
	const query = target.search;
	await expect(link).toHaveAttribute('href', target.pathname + query);
	await link.click();
	if (query !== '?view=inquiry') await expect(page).toHaveURL(target.href);
	const workspace = page.locator('[data-linker-planner]');
	const directions = workspace.locator('.sc-direction-comparison tbody tr');
	const form = page.locator('form.linker-inquiry-form:visible');
	const actions = ['Open the link from the homepage'];
	try {
		if (query === '?step=roof') {
			await expect(
				workspace.locator('[name="location_label"]')
			).toBeVisible();
			await workspace
				.getByRole('link', {
					name:
						language === 'en'
							? 'Compare options'
							: 'Optionen vergleichen',
					exact: true,
				})
				.click();
			actions.push('Compare options without a roof plan');
		} else if (query === '?projects=1') {
			await expect(workspace.locator('.sc-saved-projects')).toBeVisible();
			await workspace
				.getByRole('link', {
					name: language === 'en' ? 'New project' : 'Neues Projekt',
					exact: true,
				})
				.click();
			actions.push('Start a new comparison');
		} else if (['', '?view=equipment', '?view=project'].includes(query)) {
			if (query === '?view=equipment')
				await expect(
					workspace.locator('details.sc-project-equipment')
				).toHaveJSProperty('open', true);
			const details = workspace
				.locator('form')
				.filter({ has: page.locator('select[name="system_scope"]') });
			await expect(details).toBeVisible();
			await details
				.getByRole('button', {
					name:
						language === 'en'
							? 'Compare systems'
							: 'Systeme vergleichen',
					exact: true,
				})
				.click();
			actions.push('Submit the project form for comparison');
		}
		if (query !== '?view=inquiry') {
			await expect(directions.first()).toBeVisible();
			await directions.first().getByRole('button').click();
			actions.push('Choose the solution');
		}
		await expect(form).toBeVisible({ timeout: 45_000 });
		expect(actions, target.href).toHaveLength(
			query === '?view=inquiry'
				? 1
				: query === '?compare=preliminary' ||
					  query === '?scope=storage_addition'
					? 2
					: 3
		);
		await expect(page.locator('html')).toHaveAttribute(
			'lang',
			new RegExp('^' + language)
		);
	} finally {
		const project = new URL(page.url()).searchParams.get('project');
		if (project) {
			await page.goto(target.origin + target.pathname + '?projects=1');
			const row = page.getByRole('listitem').filter({
				has: page.locator('[id="sc-project-' + project + '"]'),
			});
			await row
				.getByRole('button', {
					name:
						language === 'en'
							? /^Delete project /
							: /^Projekt .* löschen$/,
				})
				.click();
			await row
				.getByRole('group')
				.getByRole('button', {
					name:
						language === 'en'
							? 'Delete project'
							: 'Projekt löschen',
					exact: true,
				})
				.click();
			await expect(row).toHaveCount(0);
		}
	}
}

for (const language of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${language} ${width}: browse the homepage showcase and reach inquiry review from each view`, async ({
			page,
			baseURL,
		}) => {
			test.setTimeout(480_000);
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			const origin = baseURL ?? instance().url;
			const home = new URL(language === 'de' ? '/de/' : '/', origin);
			const entry = new URL(routes[language], origin);
			const section = page.locator('#configurator-showcase');
			const heroEntry = page.locator(
				'[data-linker-planner-entry="home-hero"] a'
			);
			const list = section.getByRole('tablist');
			const panel = section.getByRole('tabpanel');
			const homepageRequests: string[] = [];
			let onHome = true;
			page.on('request', (request) => {
				const path = new URL(request.url()).pathname;
				if (
					onHome &&
					/(?:\/planner\.js|\/projects\/list)\/?$/.test(path)
				)
					homepageRequests.push(path);
			});
			const openHome = async () => {
				onHome = true;
				await page.goto(home.href, { waitUntil: 'domcontentloaded' });
				await expect(heroEntry).toHaveAttribute(
					'href',
					new RegExp(routes[language] + '\\?compare=preliminary$')
				);
				await expect(page.locator('[data-linker-planner]')).toHaveCount(
					0
				);
				const dismiss = page.locator(
					'[data-cky-tag="reject-button"]:visible'
				);
				if (await dismiss.isVisible()) await dismiss.click();
				await expect(section).toBeVisible();
			};
			await openHome();
			await expect(
				page.locator(
					'#services ~ #configurator-showcase ~ #testimonials'
				)
			).toHaveCount(1);
			await expect(
				section.getByRole('heading', {
					name:
						language === 'en'
							? 'Design matched systems faster.'
							: 'Passende Systeme schneller planen.',
					exact: true,
				})
			).toBeVisible();
			await expect(list.getByRole('tab')).toHaveCount(5);
			async function visit(link: Locator, query: string, label: string) {
				const target = new URL(entry);
				target.search = query;
				expect(homepageRequests).toEqual([]);
				onHome = false;
				await test.step(label, () =>
					reviewFromEntry(page, link, target, language)
				);
			}
			for (const [i, label] of tabs[language].entries()) {
				if (i) await openHome();
				const tab = list.getByRole('tab', { name: label, exact: true });
				await tab.click();
				await expect(tab).toHaveAttribute('aria-selected', 'true');
				await expect(panel).toBeVisible();
				const img = panel.locator('img');
				await img.scrollIntoViewIfNeeded();
				const source = await img.evaluate(
					async (im: HTMLImageElement) => {
						await im.decode();
						return {
							src: new URL(im.currentSrc).pathname,
							width: im.naturalWidth,
						};
					}
				);
				expect(source.src).toContain(
					views[i] + '-' + language + '-' + width
				);
				expect(source.width).toBeGreaterThan(390);
				const notes = panel.locator('.showcase-notes > span');
				await expect(notes).toHaveCount(2);
				for (const note of await notes.all()) {
					if (width === 390) await expect(note).toBeHidden();
					else await expect(note).toBeVisible();
				}
				expect(
					await page.evaluate(
						() => document.documentElement.scrollWidth
					)
				).toBeLessThanOrEqual(width);
				await section.screenshot({
					path: test
						.info()
						.outputPath(
							views[i] + '-' + language + '-' + width + '.png'
						),
					animations: 'disabled',
				});
				await visit(
					panel.locator('figcaption a'),
					queries[i]!,
					label + ' view to review'
				);
			}
			await openHome();
			const first = list.getByRole('tab').first();
			await first.focus();
			await first.press('End');
			await expect(list.getByRole('tab').last()).toBeFocused();
			await list.getByRole('tab').last().press('Home');
			await expect(first).toBeFocused();
			await visit(
				section.getByRole('link', {
					name:
						language === 'en'
							? 'Launch Configurator'
							: 'Konfigurator starten',
					exact: true,
				}),
				'',
				'Launch from the homepage'
			);
			await openHome();
			await visit(
				section.getByRole('link', {
					name:
						language === 'en'
							? /Outline a roof first/
							: /Direkt mit dem Dach starten/,
				}),
				'?step=roof',
				'Start with the roof'
			);
			if (width === 1440) {
				for (const [index, query] of [
					'?scope=storage_addition',
					'?compare=preliminary',
					'?projects=1',
				].entries()) {
					await openHome();
					await visit(
						section.locator('.showcase-shortcuts nav a').nth(index),
						query,
						'Desktop shortcut ' + query
					);
				}
			} else {
				await openHome();
				await expect(
					section.locator('.showcase-shortcuts')
				).toBeHidden();
			}
			expect(homepageRequests).toEqual([]);
		});
	}
}
