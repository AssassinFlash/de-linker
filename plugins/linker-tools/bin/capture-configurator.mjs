/**
 * Screenshots for the visual acceptance of the Solution Configurator
 * (docs/acceptance/protocol.md, part C): each screen and the roof step, in
 * English and German, at 1440 and 390 px, from a running Storybook: the full
 * page, and the report on its own.
 *
 *     node bin/capture-configurator.mjs <storybook url> <folder>
 *
 * Files are named <page>-<viewport>-<lang>-<state>.png.
 */
import { chromium } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import { roofClick } from '../tests/e2e/map-offset.mjs';

const recorded = ( name ) =>
	JSON.parse(
		readFileSync(
			new URL(
				`../tests/fixtures/configurator/${ name }.json`,
				import.meta.url
			)
		)
	);
// The building the recorded roof answer reads, from the opening map's centre.
const ROOF = roofClick( recorded( 'place-80538' ), recorded( 'roof-en' ) );

const [ base = 'http://localhost:6006', folder = 'artifacts/capture' ] =
	process.argv.slice( 2 );

const SHOTS = [
	[ 'inputs', 'app--inputs', 'empty' ],
	[ 'inputs', 'app--inputs', 'roof-applied' ],
	[ 'solution', 'app--solution', 'proposal' ],
	[ 'report', 'app--solution', 'report' ],
	[ 'solution', 'app--added-to-draft', 'added' ],
	[ 'solution', 'app--draft-not-confirmed', 'unverified' ],
	[ 'solution', 'app--computing', 'computing' ],
	[ 'solution', 'app--no-candidate', 'no-candidate' ],
	[ 'solution', 'app--unavailable', 'error' ],
	[ 'commercial', 'app--commercial-inputs', 'empty' ],
	[ 'commercial', 'app--commercial-sized', 'sized' ],
	[ 'commercial', 'app--commercial-indicative', 'indicative' ],
	[ 'utility', 'app--utility', 'form' ],
	[ 'roof', 'roof-step--munich', 'outline' ],
];

// States photographed as one part of the page rather than the whole page.
const PART = {
	report: 'section[aria-labelledby="linker-report-title"]',
};

// What each state shows once it is ready to be photographed.
const READY = {
	proposal: ( page ) => page.getByRole( 'article' ).first().waitFor(),
	report: ( page ) => page.getByRole( 'article' ).first().waitFor(),
	added: ( page ) =>
		page.locator( '.linker-card__status--added' ).first().waitFor(),
	unverified: ( page ) =>
		page.locator( '.linker-card__status--unverified' ).first().waitFor(),
	computing: ( page ) => page.locator( '.linker-spinner' ).waitFor(),
	'no-candidate': ( page ) => page.locator( '.linker-empty--none' ).waitFor(),
	error: ( page ) => page.locator( '.linker-empty--error' ).waitFor(),
	sized: ( page ) => page.getByRole( 'table' ).waitFor(),
	indicative: ( page ) => page.locator( '.linker-figures--key' ).waitFor(),
	'roof-applied': async ( page ) => {
		await page.locator( '#linker-plz' ).fill( '80538' );
		await page.locator( '#linker-roof-summary button' ).click();
		await READY.outline( page );
		await page.locator( '.linker-roof__actions button' ).click();
		await page.locator( '#linker-roof-summary p' ).waitFor();
	},
	outline: async ( page ) => {
		const map = page.getByRole( 'application' );
		await map.locator( 'canvas' ).waitFor();
		await map.scrollIntoViewIfNeeded();
		const box = await map.boundingBox();
		await page.mouse.click(
			box.x + box.width / 2 + ROOF.x,
			box.y + box.height / 2 + ROOF.y
		);
		await page.getByRole( 'checkbox' ).first().waitFor();
		// The aerial tiles of the fitted view come from the state's WMS.
		await page.waitForLoadState( 'networkidle' );
	},
};

// Product images load lazily from de-linker.com; a full-page photograph
// needs all of them, so they are asked for at once and awaited.
async function imagesLoaded( page ) {
	await page.evaluate( () =>
		document
			.querySelectorAll( 'img[loading="lazy"]' )
			.forEach( ( image ) => ( image.loading = 'eager' ) )
	);
	await page
		.waitForFunction(
			() =>
				[ ...document.images ].every(
					( image ) => image.complete && image.naturalWidth > 0
				),
			undefined,
			{ timeout: 20000 }
		)
		.catch( () => undefined );
}

mkdirSync( folder, { recursive: true } );
const browser = await chromium.launch();
for ( const [ name, id, state ] of SHOTS ) {
	for ( const locale of [ 'en', 'de' ] ) {
		for ( const width of [ 1440, 390 ] ) {
			const page = await browser.newPage( {
				viewport: { width, height: width > 500 ? 900 : 844 },
				deviceScaleFactor: width > 500 ? 1 : 2,
			} );
			await page.goto(
				`${ base }/iframe.html?id=configurator-${ id }&viewMode=story&globals=locale:${ locale }`
			);
			await page.locator( '.linker-configurator' ).first().waitFor();
			await READY[ state ]?.( page );
			await imagesLoaded( page );
			await page.waitForTimeout( 400 ); // web font and layout settle
			const file = join(
				folder,
				`${ name }-${ width }-${ locale }-${ state }.png`
			);
			if ( PART[ state ] ) {
				await page
					.locator( PART[ state ] )
					.screenshot( { path: file } );
			} else {
				await page.screenshot( { path: file, fullPage: true } );
			}
			process.stdout.write( `${ file }\n` );
			await page.close();
		}
	}
}
await browser.close();
