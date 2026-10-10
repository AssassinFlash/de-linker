/**
 * Screenshots for the visual acceptance of the Solution Configurator
 * (docs/acceptance/protocol.md, part C) from a running local instance: each
 * screen, the roof step and the report's PDF, in English and German, at 1440
 * and 390 px. The instance must be snapshot-loaded (AGENTS.md §2) and serving
 * its engine (`just serve`), and the planner pages must print the
 * configurator's mount point (the t14 instance's mu-plugin stand-in; #12's
 * site chrome later).
 *
 *     node bin/capture-configurator.mjs <instance base url> <folder>
 *
 * Screenshots are named <page>-<viewport>-<lang>-<state>.png, the two PDFs the
 * report view downloads land beside them as report-<lang>.pdf. Selectors are
 * ids and roles, never the wording, so one script drives both languages.
 */
import { chromium } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';
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
// The building the roof step should read, from the opening map's centre.
const ROOF = roofClick( recorded( 'place-80538' ), recorded( 'roof-en' ) );
const CSV = new URL(
	'../tests/fixtures/configurator/load-profile-15min.csv',
	import.meta.url
).pathname;

const [ base = 'http://127.0.0.1:8903', folder = 'artifacts/capture' ] =
	process.argv.slice( 2 );
const PAGES = {
	en: `${ base }/linker-planner/`,
	de: `${ base }/de/linker-planer/`,
};
const VIEWPORTS = [
	[ '1440', { width: 1440, height: 900 }, 1 ],
	[ '390', { width: 390, height: 844 }, 2 ],
];

// The theme's pages animate on scroll; a full-page screenshot scrolls, and a
// half-finished animation shows as clipped or doubled content. The camera
// freezes motion, so what it stitches is the settled page.
async function freezeMotion( page ) {
	await page.emulateMedia( { reducedMotion: 'reduce' } );
	await page.addStyleTag( {
		content:
			'*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}',
	} );
}

// Product images load lazily; a full-page photograph needs all of them, so
// they are asked for at once and awaited.
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
	await page.waitForTimeout( 400 ); // web font and layout settle
}

/**
 * The form that yields the released three-phase 10 kWp system of the ticket.
 *
 * @param {import('@playwright/test').Page} page The page with the app mounted.
 */
async function fillResidential( page ) {
	await page.locator( '#linker-plz' ).fill( '80538' );
	await page.locator( '#linker-annual' ).fill( '5000' );
	await page.locator( '#linker-kwp' ).fill( '10' );
	await page.locator( '#linker-phase-3' ).check();
}

async function submitResidential( page ) {
	await page
		.locator( '#linker-panel-residential button[type=submit]' )
		.click();
}

async function openRoof( page ) {
	await page.locator( '#linker-plz' ).fill( '80538' );
	await page.locator( '#linker-roof-summary button' ).click();
	const map = page.getByRole( 'application' );
	await map.locator( 'canvas' ).waitFor();
	await map.scrollIntoViewIfNeeded();
	const box = await map.boundingBox();
	await page.mouse.click(
		box.x + box.width / 2 + ROOF.x,
		box.y + box.height / 2 + ROOF.y
	);
	await page.getByRole( 'checkbox' ).first().waitFor();
	// The aerial tiles paint on the map's canvas; the network settles first.
	await page.waitForLoadState( 'networkidle' );
	await page.waitForTimeout( 1500 );
}

const STATES = {
	'inputs-empty': {
		page: 'inputs',
		async prepare() {},
	},
	'roof-outline': {
		page: 'roof',
		async prepare( page ) {
			await openRoof( page );
		},
	},
	'inputs-roof-applied': {
		page: 'inputs',
		async prepare( page ) {
			await openRoof( page );
			await page.locator( '.linker-roof__actions button' ).click();
			await page.locator( '#linker-roof-summary p' ).waitFor();
		},
	},
	'solution-computing': {
		page: 'solution',
		async prepare( page ) {
			// The engine never answers, so the busy state cannot resolve mid-shot.
			await page.route( '**/design/residential', () => {
				// The handler never fulfills: the request stays pending.
			} );
			await fillResidential( page );
			await submitResidential( page );
			await page.locator( '.linker-spinner' ).waitFor();
		},
	},
	'solution-proposal': {
		page: 'solution',
		async prepare( page ) {
			await fillResidential( page );
			await submitResidential( page );
			await page.getByRole( 'article' ).first().waitFor();
		},
	},
	'report-report': {
		page: 'report',
		part: 'section[aria-labelledby="linker-report-title"]',
		async prepare( page ) {
			await STATES[ 'solution-proposal' ].prepare( page );
		},
	},
	'solution-added': {
		page: 'solution',
		async prepare( page ) {
			await STATES[ 'solution-proposal' ].prepare( page );
			await page
				.getByRole( 'button', {
					name: /solution draft|Lösungsentwurf/,
				} )
				.click();
			await page
				.locator( '.linker-card__status--added' )
				.first()
				.waitFor();
		},
	},
	'solution-no-candidate': {
		page: 'solution',
		async prepare( page ) {
			await page.locator( '#linker-plz' ).fill( '80538' );
			await page.locator( '#linker-annual' ).fill( '2500' );
			await page.locator( '#linker-kwp' ).fill( '6' );
			await page.locator( '#linker-phase-1' ).check();
			await submitResidential( page );
			await page.locator( '.linker-empty--none' ).waitFor();
		},
	},
	'solution-saved': {
		page: 'solution',
		async prepare( page ) {
			await page.route( '**/linker/v1/solutions', ( route ) =>
				route.fulfill( {
					status: 201,
					contentType: 'application/json',
					body: JSON.stringify( {
						id: 61,
						url: '/my-account/solutions/61/',
					} ),
				} )
			);
			await STATES[ 'solution-proposal' ].prepare( page );
			await page
				.locator( '.linker-actions button.linker-button--secondary' )
				.click();
			await page.locator( '.linker-actions__status a' ).waitFor();
		},
	},
	'solution-error': {
		page: 'solution',
		async prepare( page ) {
			await page.route( '**/design/residential', ( route ) =>
				route.abort()
			);
			await fillResidential( page );
			await submitResidential( page );
			await page.locator( '.linker-empty--error' ).waitFor();
		},
	},
	'commercial-empty': {
		page: 'commercial',
		async prepare( page ) {
			await page.locator( '#linker-tab-commercial' ).click();
			await page.locator( '#linker-ci-plz' ).waitFor();
		},
	},
	'commercial-sized': {
		page: 'commercial',
		async prepare( page ) {
			await page.locator( '#linker-tab-commercial' ).click();
			await page.locator( '#linker-ci-plz' ).fill( '80538' );
			await page.locator( '#linker-ci-grid' ).fill( '100' );
			await page.locator( '#linker-ci-annual' ).fill( '250000' );
			await page.locator( '#linker-ci-goal-peak_shaving' ).check();
			await page.locator( '#linker-ci-peak' ).fill( '70' );
			await page.locator( '#linker-ci-target' ).fill( '50' );
			await page.setInputFiles( '#linker-ci-profile', CSV );
			await page
				.locator( '#linker-panel-commercial button[type=submit]' )
				.click();
			await page.getByRole( 'table' ).waitFor();
		},
	},
	'commercial-indicative': {
		page: 'commercial',
		async prepare( page ) {
			await page.locator( '#linker-tab-commercial' ).click();
			await page.locator( '#linker-ci-plz' ).fill( '80538' );
			await page.locator( '#linker-ci-grid' ).fill( '100' );
			await page.locator( '#linker-ci-annual' ).fill( '250000' );
			await page.locator( '#linker-ci-goal-self_consumption' ).check();
			await page.locator( '#linker-ci-pv' ).fill( '150' );
			await page
				.locator( '#linker-panel-commercial button[type=submit]' )
				.click();
			await page.locator( '.linker-figures--key' ).waitFor();
		},
	},
	'utility-form': {
		page: 'utility',
		async prepare( page ) {
			await page.locator( '#linker-tab-utility' ).click();
			await page.locator( '#linker-utility-title' ).waitFor();
		},
	},
};

async function shot( browser, url, viewport, scale, file, state ) {
	const context = await browser.newContext( {
		viewport,
		deviceScaleFactor: scale,
	} );
	const page = await context.newPage();
	await page.goto( url, { waitUntil: 'networkidle' } );
	await freezeMotion( page );
	await page.locator( '.linker-configurator' ).waitFor();
	await state.prepare( page );
	await imagesLoaded( page );
	// A page wider than its viewport would photograph a stretched canvas; that
	// is a defect of the page (or of this script), never a state to archive.
	const width = await page.evaluate(
		() => document.scrollingElement.scrollWidth
	);
	if ( width > viewport.width ) {
		throw new Error(
			`${ file }: the page is ${ width } px wide at a ${ viewport.width } px viewport`
		);
	}
	if ( state.part ) {
		await page.locator( state.part ).screenshot( { path: file } );
	} else {
		await page.screenshot( {
			path: file,
			fullPage: true,
			animations: 'disabled',
		} );
	}
	await context.close();
	process.stdout.write( `${ file }\n` );
}

/**
 * The PDF of the report view, with the installer's logo on it.
 *
 * @param {import('@playwright/test').Browser} browser A browser over the running instance.
 * @param {'en'|'de'}                          locale  The page's language.
 */
async function pdf( browser, locale ) {
	const context = await browser.newContext( {
		viewport: VIEWPORTS[ 0 ][ 1 ],
	} );
	const page = await context.newPage();
	await page.goto( PAGES[ locale ], { waitUntil: 'networkidle' } );
	await STATES[ 'solution-proposal' ].prepare( page );
	const logo = join( folder, `logo-${ locale }.png` );
	writeFileSync( logo, logoPng() );
	await page.setInputFiles( '#linker-logo', logo );
	await page.locator( '.linker-report__logo' ).waitFor();
	const [ download ] = await Promise.all( [
		page.waitForEvent( 'download' ),
		page.locator( '.linker-report__download button[type=button]' ).click(),
	] );
	await download.saveAs( join( folder, `report-${ locale }.pdf` ) );
	await context.close();
	process.stdout.write( `report-${ locale }.pdf\n` );
}

/** A PNG the report can print as the installer's logo: a white L on two blues. */
function logoPng() {
	const width = 240;
	const height = 96;
	const rows = [];
	const color = ( x, y ) => {
		if ( x < 44 || ( y > height - 40 && x < 150 ) ) {
			return [ 255, 255, 255 ];
		}
		return x > 150 ? [ 19, 184, 166 ] : [ 11, 31, 51 ];
	};
	for ( let y = 0; y < height; y++ ) {
		const row = Buffer.alloc( 1 + width * 3 );
		for ( let x = 0; x < width; x++ ) {
			row.set( color( x, y ), 1 + x * 3 );
		}
		rows.push( row );
	}
	const ihdr = Buffer.alloc( 13 );
	ihdr.writeUInt32BE( width, 0 );
	ihdr.writeUInt32BE( height, 4 );
	ihdr[ 8 ] = 8; // bit depth
	ihdr[ 9 ] = 2; // truecolour
	const chunk = ( type, data ) => {
		const body = Buffer.concat( [ Buffer.from( type, 'ascii' ), data ] );
		const length = Buffer.alloc( 4 );
		length.writeUInt32BE( data.length );
		const crc = Buffer.alloc( 4 );
		// The chunk's CRC as the unsigned 32 bits PNG asks for.
		// eslint-disable-next-line no-bitwise
		crc.writeUInt32BE( crc32( body ) >>> 0 );
		return Buffer.concat( [ length, body, crc ] );
	};
	return Buffer.concat( [
		Buffer.from( [ 0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a ] ),
		chunk( 'IHDR', ihdr ),
		chunk( 'IDAT', deflateSync( Buffer.concat( rows ) ) ),
		chunk( 'IEND', Buffer.alloc( 0 ) ),
	] );
}

// A PNG carries a CRC-32 of every chunk; its arithmetic is bitwise by definition.
/* eslint-disable no-bitwise */
const CRC_TABLE = Array.from( { length: 256 }, ( _, n ) => {
	let c = n;
	for ( let k = 0; k < 8; k++ ) {
		c = c & 1 ? 0xedb88320 ^ ( c >>> 1 ) : c >>> 1;
	}
	return c >>> 0;
} );

function crc32( buffer ) {
	let crc = 0xffffffff;
	for ( const byte of buffer ) {
		crc = CRC_TABLE[ ( crc ^ byte ) & 0xff ] ^ ( crc >>> 8 );
	}
	return crc ^ 0xffffffff;
}
/* eslint-enable no-bitwise */

mkdirSync( folder, { recursive: true } );
const browser = await chromium.launch();
for ( const [ locale, url ] of Object.entries( PAGES ) ) {
	for ( const [ label, viewport, scale ] of VIEWPORTS ) {
		for ( const [ state, definition ] of Object.entries( STATES ) ) {
			await shot(
				browser,
				url,
				viewport,
				scale,
				join(
					folder,
					`${ definition.page }-${ label }-${ locale }-${ state.split( '-' ).slice( 1 ).join( '-' ) }.png`
				),
				definition
			);
		}
	}
	await pdf( browser, locale );
}
await browser.close();
