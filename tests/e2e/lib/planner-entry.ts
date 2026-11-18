import { expect, type Page } from '@playwright/test';

export const plannerWords = {
	en: {
		form: 'New project',
		name: 'Project name (optional)',
		details: 'Site details',
		roof: 'Solar installation and roof layout',
		purpose: 'Main purpose',
		grid: 'Grid connection',
		compare: 'Compare systems',
		saved: 'Saved projects',
		list: 'Your projects',
		back: 'Back to project',
		projects: 'Projects',
		open: 'Open project',
		nav: 'Project navigation',
		solar: 'Solar',
		energy: 'Energy use',
		steps: ['Project', 'Choose a solution', 'Review & inquire'],
	},
	de: {
		form: 'Neues Projekt',
		name: 'Projektname (optional)',
		details: 'Standortdetails',
		roof: 'PV-Anlage und Dachbelegung',
		purpose: 'Hauptziel',
		grid: 'Netzanschluss',
		compare: 'Systeme vergleichen',
		saved: 'Gespeicherte Projekte',
		list: 'Ihre Projekte',
		back: 'Zurück zum Projekt',
		projects: 'Projekte',
		open: 'Projekt öffnen',
		nav: 'Projektnavigation',
		solar: 'Photovoltaik',
		energy: 'Strombedarf',
		steps: ['Projekt', 'Lösung wählen', 'Prüfen und anfragen'],
	},
} as const;

type Lang = keyof typeof plannerWords;

function savedRow(page: Page, lang: Lang, title: string) {
	return page
		.getByRole('region', { name: plannerWords[lang].list })
		.getByRole('listitem')
		.filter({
			has: page.getByRole('heading', { name: title, exact: true }),
		});
}

export async function reopenProject(page: Page, lang: Lang, title: string) {
	const words = plannerWords[lang];
	await page
		.getByRole('button', { name: words.projects, exact: true })
		.click();
	const list = page.getByRole('region', { name: words.list });
	await expect(list).toBeVisible();
	await savedRow(page, lang, title)
		.getByRole('button', { name: words.open, exact: true })
		.click();
	await expect(
		page.getByRole('heading', { name: title, level: 1 })
	).toBeVisible();
	// A reload reads the persisted project even when the list reopened a cached copy.
	const [request] = await Promise.all([
		page.waitForRequest('**/rpc/projects/read'),
		page.reload(),
	]);
	await expect(
		page.getByRole('heading', { name: title, level: 1 })
	).toBeVisible();
	const response = await page.request.fetch(request);
	expect(response.ok()).toBe(true);
	return response.json();
}

export async function deleteOpenProject(page: Page, lang: Lang, title: string) {
	const words = plannerWords[lang];
	await page
		.getByRole('button', { name: words.projects, exact: true })
		.click();
	const row = savedRow(page, lang, title);
	await row
		.getByRole('button', {
			name:
				lang === 'en'
					? `Delete project ${title}`
					: `Projekt ${title} löschen`,
			exact: true,
		})
		.click();
	await row
		.getByRole('button', {
			name: lang === 'en' ? 'Delete project' : 'Projekt löschen',
			exact: true,
		})
		.click();
	await expect(row).toHaveCount(0, { timeout: 60_000 });
}

export async function fillSolarProject(page: Page, lang: Lang, title: string) {
	const words = plannerWords[lang];
	const form = page.getByRole('form', { name: words.form, exact: true });
	await form.getByText(words.details, { exact: true }).click();
	await form.getByLabel(words.name, { exact: true }).fill(title);
	await form
		.locator('select[name="system_scope"]')
		.selectOption('new_pv_storage');
	await form
		.getByRole('combobox', { name: words.purpose, exact: true })
		.selectOption('self');
	await page
		.getByRole('region', { name: words.energy, exact: true })
		.getByRole('combobox', { name: words.grid, exact: true })
		.selectOption('3');
}

export async function compareProject(page: Page, lang: Lang) {
	const words = plannerWords[lang];
	await page
		.getByRole('region', { name: words.energy, exact: true })
		.getByRole('button', { name: words.compare, exact: true })
		.click();
	await expect(page).toHaveURL(/project=[a-f0-9]{32}.*#sc-system$/, {
		timeout: 60_000,
	});
	await expect(
		page.getByRole('heading', {
			name:
				lang === 'en'
					? 'A system for this project'
					: 'Ein System für Ihr Projekt',
			exact: true,
		})
	).toBeVisible({ timeout: 90_000 });
}

export async function startSolarProject(page: Page, lang: Lang, title: string) {
	await fillSolarProject(page, lang, title);
	await compareProject(page, lang);
}
