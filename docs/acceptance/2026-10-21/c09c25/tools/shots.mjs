/*
 * Evidence for fix/437-c09-c25: the step rail's current step (C09) and the
 * currently-unavailable stock state on the proposal cards (C25), at 1440 and
 * 390, EN and DE.
 *
 *   node tools/shots.mjs        (Storybook on http://localhost:6006)
 *
 * The states are driven through the configurator's Storybook stories: the
 * engine's recorded answers stand in for the engine, and the story's own play
 * function fills and calculates. The German run uses the toolbar locale, the
 * same catalog the page receives from WordPress.
 *
 * Every shot is taken after fonts.ready and a settle delay. The rail's
 * current item is read from the DOM at the moment of the shot and written to
 * checks.txt beside the images.
 */

import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname( fileURLToPath( import.meta.url ) );
const repo = resolve( here, '../../../../..' );
const out = resolve( here, '..' );
const base = process.env.STORYBOOK_URL ?? 'http://localhost:6006';

const { chromium } = createRequire( repo + '/plugins/linker-tools/package.json' )(
	'playwright'
);

const viewports = [
	{ name: '1440', width: 1440, height: 900 },
	{ name: '390', width: 390, height: 844 },
];
const locales = [ 'en', 'de' ];
const checks = [];

function story( id, locale ) {
	return `${ base }/iframe.html?id=configurator-app--${ id }&viewMode=story&globals=locale:${ locale }`;
}

async function settle( page ) {
	await page.evaluate( async () => {
		await document.fonts.ready;
		const visible = [ ...document.images ].filter( ( image ) =>
			image.checkVisibility()
		);
		await Promise.all(
			visible.map( ( image ) => image.decode().catch( () => undefined ) )
		);
	} );
	await page.waitForTimeout( 400 );
}

async function current( page ) {
	return page.evaluate(
		() =>
			document.querySelector( '.linker-steps .is-current' )?.textContent ??
			null
	);
}

async function record( page, shot, expected, fullPage = false ) {
	const rail = await current( page );
	const bar = await page.evaluate(
		() =>
			document.querySelector(
				'.linker-mobile-nav [aria-current="step"]'
			)?.textContent ?? null
	);
	checks.push(
		`${ shot }: rail=${ JSON.stringify( rail ) } bar=${ JSON.stringify(
			bar
		) }${ fullPage ? ' (full page, rail at the document top)' : '' }`
	);
	if ( expected && ! ( rail ?? '' ).startsWith( expected ) ) {
		throw new Error( `${ shot }: rail ${ rail } does not start ${ expected }` );
	}
	await page.screenshot( {
		path: `${ out }/${ shot }.png`,
		fullPage,
		animations: 'disabled',
	} );
}

async function scrolledTo( page, id ) {
	await page.evaluate( ( section ) => {
		document
			.getElementById( section )
			?.scrollIntoView( { block: 'start' } );
	}, id );
	await page.waitForTimeout( 500 );
}

const browser = await chromium.launch( { channel: 'chromium' } );
await mkdir( out, { recursive: true } );
try {
	for ( const locale of locales ) {
		for ( const viewport of viewports ) {
			const page = await browser.newPage( {
				viewport: { width: viewport.width, height: viewport.height },
			} );
			const tag = `${ viewport.name }-${ locale }`;

			// 01 Inputs: nothing calculated yet.
			await page.goto( story( 'inputs', locale ) );
			await page.locator( '.linker-steps' ).waitFor();
			await settle( page );
			await record( page, `rail-01-inputs-${ tag }`, '01' );

			// 02 Solution: after the calculation the rail leaves the inputs;
			// on a wide screen the rail is only visible at the top, so the
			// shot returns there with the calculated system in place.
			await page.goto( story( 'solution', locale ) );
			await page.getByRole( 'article' ).first().waitFor();
			await settle( page );
			if ( viewport.width > 860 ) {
				// The rail has scrolled away; the shot returns to the top with
				// the calculated system in place.
				await page.evaluate( () => window.scrollTo( 0, 0 ) );
				await page.waitForTimeout( 400 );
			} else {
				// The story's click scrolled before the web font landed, so the
				// steady state is staged here: the Solution is in view and the
				// bar reads the same section as the rail.
				await scrolledTo( page, 'linker-solution-section' );
				await settle( page );
			}
			await record( page, `rail-02-solution-${ tag }`, '02' );

			// 03 Design report: its section has been reached. On a wide screen
			// the rail has scrolled away; the full page shows it at the top.
			await scrolledTo( page, 'linker-report-section' );
			await record(
				page,
				`rail-03-report-${ tag }`,
				'03',
				viewport.width > 860
			);

			// C25: the product cards, in stock and currently unavailable.
			for ( const [ shot, id ] of [
				[ 'in', 'solution' ],
				[ 'out', 'solution-unavailable' ],
			] ) {
				await page.goto( story( id, locale ) );
				await page.getByRole( 'article' ).first().waitFor();
				await page.evaluate( () =>
					document
						.querySelector( '.linker-cards' )
						?.scrollIntoView( { block: 'start' } )
				);
				// The rail pins under the site header; Storybook has no header,
				// so lift the cards clear of the rail's 89px top.
				if ( viewport.width <= 860 ) {
					await page.evaluate( () => window.scrollBy( 0, -190 ) );
				}
				await page.waitForTimeout( 500 );
				await settle( page );
				await record( page, `stock-residential-${ shot }-${ tag }` );
				checks.push(
					`stock-residential-${ shot }-${ tag }: labels=${ JSON.stringify(
						await page.locator( '.linker-card__badge' ).allTextContents()
					) }`
				);
			}

			for ( const [ shot, id ] of [
				[ 'in', 'commercial-sized' ],
				[ 'out', 'commercial-unavailable' ],
			] ) {
				await page.goto( story( id, locale ) );
				await page.getByRole( 'article' ).first().waitFor();
				await page.evaluate( () =>
					document
						.querySelector( '.linker-cards' )
						?.scrollIntoView( { block: 'start' } )
				);
				// The rail pins under the site header; Storybook has no header,
				// so lift the cards clear of the rail's 89px top.
				if ( viewport.width <= 860 ) {
					await page.evaluate( () => window.scrollBy( 0, -190 ) );
				}
				await page.waitForTimeout( 500 );
				await settle( page );
				await record( page, `stock-commercial-${ shot }-${ tag }` );
				checks.push(
					`stock-commercial-${ shot }-${ tag }: labels=${ JSON.stringify(
						await page.locator( '.linker-card__badge' ).allTextContents()
					) }`
				);
			}

			await page.close();
		}
	}
	await writeFile( `${ out }/checks.txt`, checks.join( '\n' ) + '\n' );
	console.log( checks.join( '\n' ) );
} finally {
	await browser.close();
}
