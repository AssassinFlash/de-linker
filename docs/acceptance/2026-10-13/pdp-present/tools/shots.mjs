/**
 * Evidence shots for the PDP/configurator present fix (2026-10-13).
 *
 * Same browser, same viewports, same settle protocol for the local instance
 * and the live site: fonts ready, every image decoded, animations off. Each
 * shot is preceded by a marker read of the served HTML, so a page that did not
 * render the structure this run is about is reported, not photographed.
 *
 *   node docs/acceptance/2026-10-13/pdp-present/tools/shots.mjs <out-dir> [base-url]
 *
 * The default base URL is the review instance; pass another to shoot a
 * different instance of the same tree.
 */

import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-pdp-fix/plugins/linker-tools/package.json'
);
const { chromium } = require( 'playwright' );

const LOCAL = process.argv[ 3 ] ?? 'http://127.0.0.1:8975';
const LIVE = 'https://de-linker.com';
const PDP = '/product/goodwe-gw60k-sts-g10/';
const PDP_DE = '/de/produkt/goodwe-gw60k-sts-g10/';

const out = process.argv[ 2 ] ?? '.';
mkdirSync( out, { recursive: true } );

const shots = [
	{ name: 'pdp-en-1440', url: LOCAL + PDP, width: 1440, height: 1000, expect: 'sf-pdp' },
	{ name: 'pdp-en-390', url: LOCAL + PDP, width: 390, height: 844, expect: 'sf-pdp' },
	{ name: 'pdp-de-1440', url: LOCAL + PDP_DE, width: 1440, height: 1000, expect: 'sf-pdp' },
	{ name: 'pdp-de-390', url: LOCAL + PDP_DE, width: 390, height: 844, expect: 'sf-pdp' },
	{ name: 'pdp-live-en-1440', url: LIVE + PDP, width: 1440, height: 1000, expect: 'sf-pdp' },
	{ name: 'pdp-live-en-390', url: LIVE + PDP, width: 390, height: 844, expect: 'sf-pdp' },
	{ name: 'pdp-live-de-1440', url: LIVE + PDP_DE, width: 1440, height: 1000, expect: 'sf-pdp' },
	{ name: 'configurator-en-1440', url: LOCAL + '/linker-planner/', width: 1440, height: 1000, expect: 'data-linker-app="configurator"' },
	{ name: 'configurator-en-390', url: LOCAL + '/linker-planner/', width: 390, height: 844, expect: 'data-linker-app="configurator"' },
	{ name: 'configurator-de-1440', url: LOCAL + '/de/linker-planer/', width: 1440, height: 1000, expect: 'data-linker-app="configurator"' },
	{ name: 'shop-en-1440', url: LOCAL + '/shop/', width: 1440, height: 1000, expect: 'sf-catalog' },
	{ name: 'shop-en-390', url: LOCAL + '/shop/', width: 390, height: 844, expect: 'sf-catalog' },
];

/**
 * The geometry the ask judges the PDP by: the gallery's pair box and the
 * thumbnail strip (live: 813 px wide, 72 × 72 tiles), the section nav's
 * labels and the three sections that were missing.
 */
const measure = () => {
	const box = ( selector ) => {
		const element = document.querySelector( selector );
		if ( ! element ) {
			return null;
		}
		const rect = element.getBoundingClientRect();
		return { width: Math.round( rect.width ), height: Math.round( rect.height ) };
	};
	const thumb = document.querySelector( '.pdp-thumb' );
	const thumbRect = thumb ? thumb.getBoundingClientRect() : null;
	return {
		pair: box( '.pdp-gallery-pair' ),
		main: box( '.pdp-gallery-main' ),
		thumbs: box( '.pdp-thumbs' ),
		thumb: thumbRect ? { width: Math.round( thumbRect.width ), height: Math.round( thumbRect.height ) } : null,
		thumbCount: document.querySelectorAll( '[data-pdp-thumb]' ).length,
		nav: Array.from( document.querySelectorAll( '.pdp-section-link' ) ).map( ( link ) => link.textContent.trim() ),
		fit: box( '#fit' ),
		faqs: box( '.pdp-faqs' ),
		app: document.querySelector( '[data-linker-app="configurator"]' ) ? 'configurator' : null,
	};
};

const browser = await chromium.launch();
const report = [];

for ( const shot of shots ) {
	const context = await browser.newContext( {
		viewport: { width: shot.width, height: shot.height },
		deviceScaleFactor: 1,
		reducedMotion: 'reduce',
	} );
	const page = await context.newPage();
	let response = null;
	try {
		// The live pages carry third-party scripts that can keep the load event
		// from firing; the settle below is what the shot waits for there. The
		// local pages are fully ours and load to the end.
		response = await page.goto( shot.url, {
			waitUntil: shot.url.startsWith( LIVE ) ? 'domcontentloaded' : 'load',
			timeout: 60_000,
		} );
		await page.evaluate( async () => {
			await Promise.race( [
				( async () => {
					await document.fonts.ready;
					await Promise.all(
						Array.from( document.images ).map( ( image ) =>
							image.complete
								? Promise.resolve()
								: new Promise( ( resolve ) => {
										image.addEventListener( 'load', resolve, { once: true } );
										image.addEventListener( 'error', resolve, { once: true } );
								  } )
						)
					);
				} )(),
				new Promise( ( resolve ) => setTimeout( resolve, 15_000 ) ),
			] );
		} );
		await page.waitForTimeout( 400 );
		const html = await page.content();
		const file = join( out, `${ shot.name }.png` );
		await page.screenshot( { path: file, fullPage: false } );
		const geometry = shot.name.startsWith( 'shop' ) ? null : await page.evaluate( measure );
		report.push( {
			shot: shot.name,
			status: response ? response.status() : 0,
			file,
			marker: html.includes( shot.expect ),
			expected: shot.expect,
			geometry,
		} );
		console.log(
			`${ shot.name }: http ${ response ? response.status() : 0 }, ${ shot.expect } ${ html.includes( shot.expect ) ? 'present' : 'MISSING' }`
		);
	} catch ( error ) {
		report.push( { shot: shot.name, status: 0, file: null, marker: false, expected: shot.expect, error: String( error ) } );
		console.log( `${ shot.name }: FAILED ${ error }` );
	}
	await context.close();
}

await browser.close();
writeFileSync( join( out, 'shots.json' ), `${ JSON.stringify( report, null, 2 ) }\n` );
console.log( `report: ${ join( out, 'shots.json' ) }` );
const failed = report.filter( ( row ) => ! row.marker );
if ( failed.length > 0 ) {
	console.error( `markers missing: ${ failed.map( ( row ) => row.shot ).join( ', ' ) }` );
	process.exitCode = 1;
}
