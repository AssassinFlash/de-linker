/** The configurator identifies its sources on a reopened project with a persisted revision. */
/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';
import { reopenProject, startSolarProject } from '../lib/planner-entry';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

type Lang = 'en' | 'de';

/** The reviewed EN / formal-DE identity copy (system-identity-copy, the .po). */
const CONTRACT = {
	en: {
		configurator: '/solution-configurator/',
		product: 'Solution Configurator',
		owner: 'by Linker',
		summary: 'About this tool',
		role: 'You can reopen saved projects and restore available drafts.',
		boundary:
			'All design views use the same project geometry. Source records retain the declared accuracy and permissions; a displayed model provides no engineering approval.',
		credits: 'Software and data credits',
		/** The whole block, so nothing inside it can drift unnoticed. */
		block: 'Solution Configurator by Linker Linker brings your inputs into an editable project for solar and storage planning. About this tool You can reopen saved projects and restore available drafts. All design views use the same project geometry. Source records retain the declared accuracy and permissions; a displayed model provides no engineering approval. Software and data credits Interface and project data: React, TanStack Query and Ajv. 3D views: Three.js and React Three Fiber. Map display: MapLibre GL JS. Street map: OpenFreeMap. © OpenMapTiles; © OpenStreetMap contributors. OpenFreeMap privacy policy',
		links: [
			['React', 'https://react.dev/'],
			['TanStack Query', 'https://tanstack.com/query'],
			['Ajv', 'https://ajv.js.org'],
			['Three.js', 'https://threejs.org/'],
			[
				'React Three Fiber',
				'https://r3f.docs.pmnd.rs/getting-started/introduction',
			],
			['MapLibre GL JS', 'https://maplibre.org/maplibre-gl-js/docs/'],
			['OpenFreeMap', 'https://openfreemap.org/'],
			['© OpenMapTiles', 'https://www.openmaptiles.org/'],
			[
				'© OpenStreetMap contributors',
				'https://www.openstreetmap.org/copyright',
			],
			['OpenFreeMap privacy policy', 'https://openfreemap.org/privacy/'],
		],
	},
	de: {
		configurator: '/de/loesungskonfigurator/',
		product: 'Lösungskonfigurator',
		owner: 'von Linker',
		summary: 'Über dieses Werkzeug',
		role: 'Gespeicherte Projekte können Sie erneut öffnen und vorhandene Entwürfe wiederherstellen.',
		// Written in German, not translated word for word: it keeps both
		// promises (the recorded source data stays as declared, the display is
		// no professional approval).
		boundary:
			'Alle Entwurfsansichten verwenden dieselbe Projektgeometrie. Die erfassten Angaben zur Quellengenauigkeit und zu Nutzungsrechten bleiben unverändert. Die Darstellung ersetzt keine fachtechnische Freigabe.',
		credits: 'Software und Datenquellen',
		block: 'Lösungskonfigurator von Linker Linker bündelt Ihre Angaben in einem bearbeitbaren Projekt für die PV- und Speicherplanung. Über dieses Werkzeug Gespeicherte Projekte können Sie erneut öffnen und vorhandene Entwürfe wiederherstellen. Alle Entwurfsansichten verwenden dieselbe Projektgeometrie. Die erfassten Angaben zur Quellengenauigkeit und zu Nutzungsrechten bleiben unverändert. Die Darstellung ersetzt keine fachtechnische Freigabe. Software und Datenquellen Oberfläche und Projektdaten: React, TanStack Query und Ajv. 3D-Ansichten: Three.js und React Three Fiber. Kartendarstellung: MapLibre GL JS. Straßenkarte: OpenFreeMap. © OpenMapTiles; © OpenStreetMap-Mitwirkende. Datenschutzhinweise von OpenFreeMap',
		links: [
			['React', 'https://react.dev/'],
			['TanStack Query', 'https://tanstack.com/query'],
			['Ajv', 'https://ajv.js.org'],
			['Three.js', 'https://threejs.org/'],
			[
				'React Three Fiber',
				'https://r3f.docs.pmnd.rs/getting-started/introduction',
			],
			['MapLibre GL JS', 'https://maplibre.org/maplibre-gl-js/docs/'],
			['OpenFreeMap', 'https://openfreemap.org/'],
			['© OpenMapTiles', 'https://www.openmaptiles.org/'],
			[
				'© OpenStreetMap-Mitwirkende',
				'https://www.openstreetmap.org/copyright',
			],
			[
				'Datenschutzhinweise von OpenFreeMap',
				'https://openfreemap.org/privacy/',
			],
		],
	},
} as const;

/** Collapses the wrapping differences of two widths onto one comparable line. */
const flat = (text: string): string => text.replace(/\s+/g, ' ').trim();

/** A saved project, created through the interface, with the identity below it. */
async function savedProject(page: Page, lang: Lang): Promise<void> {
	const words = CONTRACT[lang];
	await page.goto(instance().url + words.configurator, {
		waitUntil: 'networkidle',
	});
	const title = `Identity ${lang} e2e`;
	await startSolarProject(page, lang, title);
	const projectId = new URL(page.url()).searchParams.get('project');
	const project = await reopenProject(page, lang, title);
	expect(project.id).toBe(projectId);
	expect(project.revision).toBeGreaterThan(0);
}

/** Expands the disclosure the way a customer does. */
async function openIdentity(page: Page, lang: Lang): Promise<void> {
	const words = CONTRACT[lang];
	await expect(page.locator('.lp-tool-identity')).toHaveCount(1);
	await expect(page.locator('.lp-tool-about summary')).toHaveText(
		words.summary
	);
	await page.locator('.lp-tool-about summary').click();
	await expect(page.locator('.lp-tool-about')).toHaveAttribute('open', '');
	// Nothing around the block pushes the page sideways at either width.
	const overflow = await page.evaluate(
		() =>
			document.documentElement.scrollWidth -
			document.documentElement.clientWidth
	);
	expect(overflow, 'no horizontal page overflow').toBe(0);
	const box = await page.locator('.lp-tool-identity').boundingBox();
	expect(box, 'the identity block has a laid-out box').toBeTruthy();
	expect(box!.width).toBeGreaterThan(0);
	expect(box!.height).toBeGreaterThan(0);
}

for (const lang of ['en', 'de'] as const) {
	for (const [width, height] of [
		[1440, 1000],
		[390, 844],
	] as const) {
		test(`${lang} ${width}: the identity block names the product, withholds approval and links all ten sources`, async ({
			page,
		}) => {
			const words = CONTRACT[lang];
			await page.setViewportSize({ width, height });
			await savedProject(page, lang);
			await openIdentity(page, lang);

			const identity = page.locator('.lp-tool-identity');
			await expect(
				identity.locator('.lp-tool-product strong')
			).toHaveText(words.product);
			await expect(identity.locator('.lp-tool-product span')).toHaveText(
				words.owner
			);
			await expect(
				identity.locator('.lp-tool-about > div')
			).toContainText(words.role);
			// The boundary sentence is the contract's core: a displayed model
			// is not an engineering approval.
			await expect(identity.locator('.lp-tool-boundary')).toHaveText(
				words.boundary
			);
			await expect(
				identity.getByRole('heading', { name: words.credits })
			).toBeVisible();
			// The block as one text, wrapping normalised: same words, same
			// order, nothing added or dropped between the two widths.
			expect(flat(await identity.innerText())).toBe(flat(words.block));

			const links = await identity
				.locator('a')
				.evaluateAll((anchors) =>
					anchors.map((anchor) => [
						anchor.textContent?.trim() ?? '',
						anchor.getAttribute('href') ?? '',
						anchor.getAttribute('rel') ?? '',
						anchor.getAttribute('target') ?? '',
					])
				);
			expect(
				links,
				'ten credited sources, in the reviewed order'
			).toEqual(
				words.links.map(([label, href]) => [
					label,
					href,
					'noopener noreferrer',
					'_blank',
				])
			);
		});
	}
}
