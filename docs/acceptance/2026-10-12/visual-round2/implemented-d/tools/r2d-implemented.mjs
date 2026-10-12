/*
 * Measures the two owner-approved configurator proposals (owner ruling
 * 2026-10-12, D1 + D2; ledger and trialled CSS:
 * docs/acceptance/2026-10-12/visual-round2/proposals/README.md) on the t109
 * instance after they were implemented in
 * plugins/linker-tools/src/configurator/configurator.css (served from the
 * committed build/configurator.css).
 *
 * Same browser, viewport, URL and wait protocol as the proposal round's
 * /tmp/r2-trials.mjs, so the "after" numbers are directly comparable to that
 * round's measurements.json. The "before" variant injects the two rules'
 * pre-implementation values (the base rules' rendering: one-column rows,
 * scrolling step nav) so this run measures its own baseline instead of
 * trusting the recorded one.
 *
 *   node r2d-implemented.mjs <out-dir>
 */
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-r2d';
const out = process.argv[ 2 ];
if ( ! out ) {
	throw new Error( 'usage: node r2d-implemented.mjs <out-dir>' );
}
await mkdir( out, { recursive: true } );

const { chromium } = createRequire(
	repo + '/plugins/linker-tools/package.json'
)( 'playwright' );
const browser = await chromium.launch( { channel: 'chromium' } );
const PLAN = 'http://127.0.0.1:8969/linker-planner/';

// The pre-implementation values of exactly the two accepted proposals: the
// base rules' rendering at those viewports.
const BEFORE_CSS = `@media (min-width:1200px){
  [data-linker-app="configurator"] .linker-report__rows{grid-template-columns:none;column-gap:normal;align-items:normal}
}
@media (max-width:860px){
  [data-linker-app="configurator"] .linker-steps{position:static;top:auto;z-index:auto;background:none;backdrop-filter:none;padding:0;margin:0 0 var(--proto-space-5,1.5rem)}
}`;

async function runFlow( page ) {
	await page.waitForTimeout( 2200 );
	await page.locator( '#linker-plz' ).fill( '80538' );
	await page.locator( '#linker-annual' ).fill( '5000' );
	await page.locator( '#linker-kwp' ).fill( '10' );
	await page.locator( 'button:has-text("Calculate system")' ).click();
	await page.waitForTimeout( 3500 );
}

async function settle( page ) {
	await page.waitForTimeout( 1600 );
	await page.evaluate( async () => {
		await document.fonts.ready;
		const step = () => new Promise( ( r ) => setTimeout( r, 25 ) );
		for ( let t = 0; t < document.body.scrollHeight + 500; t += 600 ) {
			window.scrollTo( 0, t );
			await step();
		}
		const vis = [ ...document.images ].filter( ( i ) =>
			i.checkVisibility()
		);
		await Promise.all( vis.map( ( i ) => i.decode().catch( () => {} ) ) );
	} );
	await page.waitForTimeout( 700 );
}

// Page-side helpers get inlined into every measure function's source, so the
// serialized function Playwright sends to the browser is self-contained.
const PRELUDE = `
const box = ( sel ) => { const el = document.querySelector(sel); if (!el) return null; const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)]; };
const rectNow = ( sel ) => { const el = document.querySelector(sel); if (!el) return null; const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; };
`;
const measure = ( body ) => eval( `() => { ${ PRELUDE } return (${ body })(); }` );

// D1: the design report's label/value rows at 1440 — per-block geometry and
// computed grid, plus the three areas the proposal leaves untouched (solution
// section, Stückliste table, assumptions section) for a before=after check of
// their own layout (heights; their page positions shift as the page shortens).
const D1 = measure( () => ( {
	vw: innerWidth,
	pageH: document.body.scrollHeight,
	rowsBlocks: [
		...document.querySelectorAll(
			'[data-linker-app="configurator"] .linker-report__rows'
		),
	].map( ( d ) => {
		const r = d.getBoundingClientRect();
		const cs = getComputedStyle( d );
		return {
			section: d
				.closest( 'section' )
				?.getAttribute( 'aria-labelledby' ),
			h: Math.round( r.height ),
			w: Math.round( r.width ),
			rows: d.children.length,
			display: cs.display,
			columns: cs.gridTemplateColumns,
			columnGap: cs.columnGap,
			alignItems: cs.alignItems,
		};
	} ),
	reportTotalH: Math.round(
		[
			...document.querySelectorAll(
				'[data-linker-app="configurator"] .linker-report__rows'
			),
		].reduce(
			( s, d ) => s + d.getBoundingClientRect().height,
			0
		)
	),
	firstTwoRowBoxes: [
		...document.querySelectorAll(
			'[data-linker-app="configurator"] .linker-report__rows'
		),
	][ 0 ]
		? [
				...document.querySelectorAll(
					'[data-linker-app="configurator"] .linker-report__rows'
				)[ 0 ].children,
			].slice( 0, 2 ).map( ( c ) => {
				const r = c.getBoundingClientRect();
				return [ Math.round( r.x ), Math.round( r.y + scrollY ), Math.round( r.width ), Math.round( r.height ) ];
			} )
		: null,
	solution: box( 'section[aria-labelledby="linker-solution-title"]' ),
	bom: box( 'section[aria-labelledby="linker-report-bom"]' ),
	bomTable: box(
		'section[aria-labelledby="linker-report-bom"] .linker-table'
	),
	assumptions: box(
		'section[aria-labelledby="linker-report-assumptions"]'
	),
} ) );

// D2: the step nav pinned under the header (89px) on phones once the
// single-page flow has scrolled into the solution/report.
const D2 = measure( () => {
	const el = document.querySelector( '.linker-steps' );
	if ( ! el ) {
		return null;
	}
	const cs = getComputedStyle( el );
	const r = el.getBoundingClientRect();
	return {
		vw: innerWidth,
		scrollY: Math.round( scrollY ),
		stepsViewportTop: Math.round( r.top ),
		stepsViewportRect: rectNow( '.linker-steps' ),
		stepsH: Math.round( r.height ),
		position: cs.position,
		top: cs.top,
		zIndex: cs.zIndex,
		background: cs.backgroundColor,
		backdropFilter: cs.backdropFilter,
		padding: cs.padding,
		margin: cs.margin,
	};
} );

const report = {};

async function shot( page, name, { fullPage = false } = {} ) {
	await page.screenshot( { path: `${ out }/${ name }.png`, fullPage } );
	console.log( 'shot', name );
}

// ---- D1: report rows two columns (planner, 1440) ----
{
	const ctx = await browser.newContext( {
		viewport: { width: 1440, height: 900 },
	} );
	const page = await ctx.newPage();
	await page.goto( PLAN + '?cbq=' + Date.now(), {
		waitUntil: 'domcontentloaded',
	} );
	await runFlow( page );
	await settle( page );
	// Same DOM for both variants: the injected pre-implementation values are
	// switched off by making their tag not apply, so nothing else moves.
	const beforeTag = await page.addStyleTag( { content: BEFORE_CSS } );
	await page.waitForTimeout( 900 );
	report[ 'D1-before' ] = await page.evaluate( D1 );
	await shot( page, 'D1_report-columns-1440-before', { fullPage: true } );
	await beforeTag.evaluate( ( el ) => {
		el.media = 'not all';
	} );
	await page.waitForTimeout( 900 );
	report[ 'D1-after' ] = await page.evaluate( D1 );
	await shot( page, 'D1_report-columns-1440-after', { fullPage: true } );
	await ctx.close();
}
// D1 guard: 1100 viewport untouched.
{
	const ctx = await browser.newContext( {
		viewport: { width: 1100, height: 900 },
	} );
	const page = await ctx.newPage();
	await page.goto( PLAN + '?cbq=' + Date.now(), {
		waitUntil: 'domcontentloaded',
	} );
	await runFlow( page );
	await settle( page );
	report[ 'D1-guard1100-after' ] = await page.evaluate( D1 );
	await page.addStyleTag( { content: BEFORE_CSS } );
	await page.waitForTimeout( 600 );
	report[ 'D1-guard1100-before' ] = await page.evaluate( D1 );
	await ctx.close();
}

// ---- D2: sticky step nav (planner, 390, scrolled into solution) ----
{
	const ctx = await browser.newContext( {
		viewport: { width: 390, height: 844 },
	} );
	const page = await ctx.newPage();
	await page.goto( PLAN + '?cbq=' + Date.now(), {
		waitUntil: 'domcontentloaded',
	} );
	await runFlow( page );
	await settle( page );
	await page.evaluate( () => window.scrollTo( 0, 2400 ) );
	await page.waitForTimeout( 800 );
	const beforeTag = await page.addStyleTag( { content: BEFORE_CSS } );
	await page.waitForTimeout( 900 );
	report[ 'D2-before' ] = await page.evaluate( D2 );
	await shot( page, 'D2_steps-sticky-390-before' );
	await beforeTag.evaluate( ( el ) => {
		el.media = 'not all';
	} );
	await page.waitForTimeout( 900 );
	report[ 'D2-after' ] = await page.evaluate( D2 );
	await shot( page, 'D2_steps-sticky-390-after' );
	// The phone keeps D1's rows single-column: the report as it renders at
	// 390 (the min-width:1200px rule cannot apply, recorded to prove it).
	report[ 'D2-rows390' ] = await page.evaluate( D1 );
	await ctx.close();
}
// D2 guard: desktop (1440) keeps the scrolling nav — not sticky, scrolled away.
{
	const ctx = await browser.newContext( {
		viewport: { width: 1440, height: 900 },
	} );
	const page = await ctx.newPage();
	await page.goto( PLAN + '?cbq=' + Date.now(), {
		waitUntil: 'domcontentloaded',
	} );
	await runFlow( page );
	await settle( page );
	await page.evaluate( () => window.scrollTo( 0, 2400 ) );
	await page.waitForTimeout( 800 );
	const beforeTag = await page.addStyleTag( { content: BEFORE_CSS } );
	await page.waitForTimeout( 600 );
	report[ 'D2-guard1440-before' ] = await page.evaluate( D2 );
	await beforeTag.evaluate( ( el ) => {
		el.media = 'not all';
	} );
	await page.waitForTimeout( 600 );
	report[ 'D2-guard1440-after' ] = await page.evaluate( D2 );
	await ctx.close();
}

await writeFile(
	out + '/measurements-implemented.json',
	JSON.stringify( report, null, 1 )
);
await browser.close();
