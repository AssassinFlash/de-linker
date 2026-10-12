/*
 * Evidence for fix/configurator-c-fidelity: the Solution Configurator's input
 * screen against the archived variant C prototype, at 1440 and 390, EN and DE,
 * plus the measurements the checklist in ../EVIDENCE.md cites.
 *
 *   node cfg-c-fidelity.mjs <out-dir>
 *
 * Designt basis (read-only): the prototype checkout's
 * plugins/linker-tools/src/configurator/prototype/proto-configurator.css served
 * at http://127.0.0.1:8981/linker-planner/?variant=C&view=inputs (instance t111).
 * The production page is the real app on instance t109:
 *   EN http://127.0.0.1:8969/linker-planner/
 *   DE http://127.0.0.1:8969/de/linker-planner/
 * Same browser, viewport, and wait protocol (fonts.ready + a full scroll +
 * image decode) for both sides, so the numbers are comparable.
 *
 * The DE page exists here as an instance-local twin of page 3302 (Polylang,
 * slug linker-planner, language de). The live site serves /de/linker-planner/
 * too. This instance holds no German LiveCanvas partials, so the DE page
 * renders without the site header/footer; the app region is the compared
 * surface (see ../EVIDENCE.md).
 */
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-cfg-c';
const proto = 'http://127.0.0.1:8981/linker-planner/?variant=C&view=inputs';
const prodEn = 'http://127.0.0.1:8969/linker-planner/';
const prodDe = 'http://127.0.0.1:8969/de/linker-planner/';

const out = process.argv[ 2 ];
if ( ! out ) {
	throw new Error( 'usage: node cfg-c-fidelity.mjs <out-dir>' );
}

await mkdir( out, { recursive: true } );

const { chromium } = createRequire( repo + '/plugins/linker-tools/package.json' )(
	'playwright'
);
const browser = await chromium.launch( { channel: 'chromium' } );

async function settle( page ) {
	await page.waitForTimeout( 1800 );
	await page.evaluate( async () => {
		await document.fonts.ready;
		const step = () => new Promise( ( r ) => setTimeout( r, 25 ) );
		for ( let t = 0; t < document.body.scrollHeight + 500; t += 600 ) {
			window.scrollTo( 0, t );
			await step();
		}
		window.scrollTo( 0, 0 );
		const vis = [ ...document.images ].filter( ( i ) => i.checkVisibility() );
		await Promise.all( vis.map( ( i ) => i.decode().catch( () => {} ) ) );
	} );
	await page.waitForTimeout( 600 );
}

// One shape for both sides: the prototype's selector first, the app's second.
// Built with eval so the serialized function Playwright sends to the browser
// is self-contained (a string argument would evaluate to a function object
// and serialize to nothing).
const MEASURE = ( protos ) => eval( `() => {
	const read = ( sel ) => {
		const el = document.querySelector( sel );
		if ( ! el ) return null;
		const cs = getComputedStyle( el );
		const r = el.getBoundingClientRect();
		return {
			sel,
			box: [ Math.round( r.x ), Math.round( r.y + scrollY ), Math.round( r.width ), Math.round( r.height ) ],
			bg: cs.backgroundColor,
			color: cs.color,
			border: cs.borderTopWidth + ' ' + cs.borderTopStyle + ' ' + cs.borderTopColor,
			radius: cs.borderTopLeftRadius + ' / ' + cs.borderBottomRightRadius,
			padding: cs.padding,
			font: cs.fontSize + ' ' + cs.fontWeight,
			letterSpacing: cs.letterSpacing,
			textTransform: cs.textTransform,
			shadow: cs.boxShadow,
		};
	};
	return Object.fromEntries( Object.entries( ${ JSON.stringify( protos ) } ).map( ( [ k, sel ] ) => [ k, read( sel ) ] ) );
}` );

const PROTO_SELECTORS = {
	card: '.pc-card',
	cardBody: '.pc-body',
	headTitle: '.pc-h h2',
	headStep: '.pc-h-sub',
	chip: '.pc-fieldset > legend span',
	choice: '.pc-check',
	footer: '.pc-footer',
	submit: '.pc-next',
};

const PROD_SELECTORS = {
	card: '.linker-screen',
	cardBody: '.linker-screen',
	headTitle: '.linker-block__title',
	headStep: '.linker-block__step',
	chip: '.linker-group > legend',
	choice: '.linker-segments__tab',
	footer: '.linker-form__submit',
	submit: '.linker-form__submit .linker-button--primary',
};

const report = {};

async function capture( url, name, width, height, { element = null } = {} ) {
	const ctx = await browser.newContext( {
		viewport: { width, height },
		deviceScaleFactor: 1,
	} );
	const page = await ctx.newPage();
	await page.goto( `${ url }${ url.includes( '?' ) ? '&' : '?' }cbq=${ Date.now() }`, {
		waitUntil: 'domcontentloaded',
	} );
	await settle( page );
	await page.screenshot( { path: `${ out }/${ name }-viewport.png` } );
	await page.screenshot( { path: `${ out }/${ name }-full.png`, fullPage: true } );
	if ( element ) {
		await page.locator( element ).screenshot( { path: `${ out }/${ name }-app.png` } );
	}
	console.log( 'shot', name );
	await ctx.close();
}

async function measure( url, width, height, selectors ) {
	const ctx = await browser.newContext( {
		viewport: { width, height },
		deviceScaleFactor: 1,
	} );
	const page = await ctx.newPage();
	await page.goto( `${ url }${ url.includes( '?' ) ? '&' : '?' }cbq=${ Date.now() }`, {
		waitUntil: 'domcontentloaded',
	} );
	await settle( page );
	const data = await page.evaluate( MEASURE( selectors ) );
	await ctx.close();
	return data;
}

for ( const [ label, width, height ] of [
	[ '1440', 1440, 900 ],
	[ '390', 390, 844 ],
] ) {
	await capture( proto, `proto-c-inputs-${ label }`, width, height );
	await capture( prodEn, `prod-en-inputs-${ label }`, width, height, {
		element: '.linker-configurator',
	} );
	await capture( prodDe, `prod-de-inputs-${ label }`, width, height, {
		element: '.linker-configurator',
	} );
	report[ `proto-${ label }` ] = await measure(
		proto,
		width,
		height,
		PROTO_SELECTORS
	);
	report[ `prod-en-${ label }` ] = await measure(
		prodEn,
		width,
		height,
		PROD_SELECTORS
	);
	report[ `prod-de-${ label }` ] = await measure(
		prodDe,
		width,
		height,
		PROD_SELECTORS
	);
}

/* D2 — after a model change the Solution title is fully clear of the pinned
   rail (the assertion Steps.test.tsx holds in jsdom, run here in the browser
   on the real page; the 32px gap and the 89px sticky top are that test's). */
{
	const ctx = await browser.newContext( {
		viewport: { width: 390, height: 844 },
		deviceScaleFactor: 1,
	} );
	const page = await ctx.newPage();
	await page.goto( `${ prodEn }?cbq=${ Date.now() }`, {
		waitUntil: 'domcontentloaded',
	} );
	await page.waitForTimeout( 2200 );
	await page.locator( '#linker-plz' ).fill( '80538' );
	await page.locator( '#linker-annual' ).fill( '5000' );
	await page.locator( '#linker-kwp' ).fill( '10' );
	await page.locator( 'button:has-text("Calculate system")' ).click();
	await page.waitForTimeout( 4500 );
	const select = page.locator( '.linker-section select' ).last();
	await select.selectOption( { index: 1 } );
	await page.waitForTimeout( 5000 );
	report.d2 = await page.evaluate( () => {
		const rail = document.querySelector( '.linker-steps' );
		const title = document.querySelector( '#linker-solution-title' );
		const box = ( el ) => {
			const r = el.getBoundingClientRect();
			return {
				top: Math.round( r.top ),
				bottom: Math.round( r.bottom ),
				height: Math.round( r.height ),
			};
		};
		return {
			viewport: innerHeight,
			rail: { ...box( rail ), position: getComputedStyle( rail ).position, top: getComputedStyle( rail ).top },
			title: box( title ),
			gap: Math.round(
				title.getBoundingClientRect().top - rail.getBoundingClientRect().bottom
			),
			fullyVisible:
				title.getBoundingClientRect().top >= 0 &&
				title.getBoundingClientRect().bottom <= innerHeight,
			sectionHeldBySticky: ( () => {
				const held = [];
				for ( let n = title.parentElement; n; n = n.parentElement ) {
					const p = getComputedStyle( n ).position;
					if ( p === 'sticky' || p === 'fixed' ) held.push( n.className );
				}
				return held;
			} )(),
		};
	} );
	await page.screenshot( { path: `${ out }/d2-after-model-change-390.png` } );
	console.log( 'shot d2' );
	await ctx.close();
}

/* Same-scale side-by-side sheets: the prototype's frame left, the app right.
   Written as a file and opened over file:// so the images load (a data/about:
   document cannot read file:// images). */
async function sheet( name, left, right, width, height ) {
	const html = `<!doctype html><meta charset="utf-8"><style>
			body { margin: 0; background: #fff; font: 600 12px system-ui, sans-serif; }
			main { display: flex; gap: 24px; padding: 12px; }
			figure { margin: 0; }
			figcaption { padding: 4px 0 8px; }
			img { display: block; width: ${ width }px; border: 1px solid #dfe7ec; }
		</style>
		<main>
			<figure><figcaption>SRC prototype C</figcaption><img src="file://${ left }"></figure>
			<figure><figcaption>REP ${ name }</figcaption><img src="file://${ right }"></figure>
		</main>`;
	const file = `${ out }/.sheet-${ name }.html`;
	await writeFile( file, html );
	const ctx = await browser.newContext( {
		viewport: { width: width * 2 + 24, height: height + 44 },
		deviceScaleFactor: 1,
	} );
	const page = await ctx.newPage();
	await page.goto( `file://${ file }`, { waitUntil: 'load' } );
	await page.waitForTimeout( 700 );
	await page.screenshot( { path: `${ out }/cmp-${ name }.png`, fullPage: true } );
	console.log( 'sheet', name );
	await ctx.close();
}

await sheet(
	'1440-en-app',
	`${ out }/proto-c-inputs-1440-viewport.png`,
	`${ out }/prod-en-inputs-1440-app.png`,
	1440,
	900
);
await sheet(
	'390-en-app',
	`${ out }/proto-c-inputs-390-viewport.png`,
	`${ out }/prod-en-inputs-390-app.png`,
	390,
	844
);
await sheet(
	'1440-de-app',
	`${ out }/proto-c-inputs-1440-viewport.png`,
	`${ out }/prod-de-inputs-1440-app.png`,
	1440,
	900
);
await sheet(
	'390-de-app',
	`${ out }/proto-c-inputs-390-viewport.png`,
	`${ out }/prod-de-inputs-390-app.png`,
	390,
	844
);

await writeFile(
	`${ out }/measurements.json`,
	JSON.stringify( report, null, 1 )
);
await browser.close();
console.log( 'done' );
