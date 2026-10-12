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
 *
 * Every comparison sheet is cut out of two full-page screenshots taken at
 * deviceScaleFactor 1, at the same viewport width, and rendered without any
 * CSS width or height on the images: both panels are therefore 1 image
 * pixel per CSS pixel, and the only difference between the two crops of a
 * sheet is where they start vertically. Nothing in a sheet is rescaled, so
 * an element measured on one panel can be compared with an element measured
 * on the other directly (sheet captions carry the crop rectangles).
 */
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-cfg-c';
const proto = 'http://127.0.0.1:8981/linker-planner/?variant=C&view=inputs';
const prodEn = 'http://127.0.0.1:8969/linker-planner/';
const prodDe = 'http://127.0.0.1:8969/de/linker-planner/';

const given = process.argv[ 2 ];
if ( ! given ) {
	throw new Error( 'usage: node cfg-c-fidelity.mjs <out-dir>' );
}
// Absolute: the sheets are opened over file://, which a relative path breaks.
const out = resolve( given );

await mkdir( out, { recursive: true } );
await mkdir( `${ out }/before`, { recursive: true } );

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
	input: '.pc-field input',
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
	input: '.linker-field input',
	footer: '.linker-form__submit',
	submit: '.linker-form__submit .linker-button--primary',
	// The phone layout pins the rail (D2); its box is recorded so a page whose
	// site header is missing locally can be told apart from one that has it.
	steps: '.linker-steps',
};

const report = {};

/* One navigation per side: the boxes are read from the same page load that is
   screenshotted, so a measurement and the pixels it describes cannot drift
   apart. */
async function capture( url, name, width, height, selectors ) {
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
	await page.screenshot( { path: `${ out }/${ name }-viewport.png` } );
	await page.screenshot( { path: `${ out }/${ name }-full.png`, fullPage: true } );
	console.log( 'shot', name );
	await ctx.close();
	return data;
}

for ( const [ label, width, height ] of [
	[ '1440', 1440, 900 ],
	[ '390', 390, 844 ],
] ) {
	report[ `proto-${ label }` ] = await capture(
		proto,
		`proto-c-inputs-${ label }`,
		width,
		height,
		PROTO_SELECTORS
	);
	report[ `prod-en-${ label }` ] = await capture(
		prodEn,
		`prod-en-inputs-${ label }`,
		width,
		height,
		PROD_SELECTORS
	);
	report[ `prod-de-${ label }` ] = await capture(
		prodDe,
		`prod-de-inputs-${ label }`,
		width,
		height,
		PROD_SELECTORS
	);
}

/* The card's footer strip reaches the card's border while it ends the card,
   and stands clear of the roof step (or its loading line) while it does not.
   Both are geometry, so both are measured: `flush` is the strip's bottom
   against the section's bottom in the closed state (0px of canvas between
   them, over the card's own 1px border), `roof.gap` the strip's bottom edge
   against the roof panel's top edge with the roof step open. A negative gap
   would mean the panel overlaps the strip (the state the review found: the
   strip's -pad bottom margin collapsing into the panel's own top margin). */
async function footer( url, width, height ) {
	const ctx = await browser.newContext( {
		viewport: { width, height },
		deviceScaleFactor: 1,
	} );
	const page = await ctx.newPage();
	await page.goto( `${ url }?cbq=${ Date.now() }`, {
		waitUntil: 'domcontentloaded',
	} );
	await page.waitForTimeout( 2200 );
	const read = () =>
		page.evaluate( () => {
			const section = document
				.querySelector( '#linker-inputs-title' )
				.closest( '.linker-section' );
			const strip = section.querySelector( '.linker-form__submit' );
			const roof = section.querySelector( '.linker-roof' );
			const form = section.querySelector( '.linker-form' );
			const s = strip.getBoundingClientRect();
			const sec = section.getBoundingClientRect();
			const margin = getComputedStyle( strip );
			const box = ( r ) => ( {
				top: Math.round( r.top ),
				bottom: Math.round( r.bottom ),
				height: Math.round( r.height ),
			} );
			return {
				stripMargin: `${ margin.marginTop } ${ margin.marginRight } ${ margin.marginBottom }`,
				strip: box( s ),
				form: box( form.getBoundingClientRect() ),
				section: box( sec ),
				sectionPadBottom: getComputedStyle( section ).paddingBottom,
				flush: Math.round( sec.bottom - s.bottom ),
				formEndsSection:
					section.lastElementChild === form,
				roof: roof
					? {
							...box( roof.getBoundingClientRect() ),
							marginTop: getComputedStyle( roof ).marginTop,
					  }
					: null,
				gap: roof
					? Math.round(
							roof.getBoundingClientRect().top - s.bottom
					  )
					: null,
				overlaps: roof
					? roof.getBoundingClientRect().top < s.bottom
					: false,
				viewport: innerHeight,
			};
		} );
	const closed = await read();
	await page.locator( '#linker-plz' ).fill( '80538' );
	await page
		.getByRole( 'button', {
			name: /Estimate from the roof|Vom Dach schätzen/,
		} )
		.click();
	await page.waitForSelector( '.linker-roof', { timeout: 30000 } ).catch( () => {} );
	await page.waitForTimeout( 4000 );
	const open = await read();
	// The strip's bottom edge and the panel's top edge, at native scale.
	const band = await page.evaluate( () => {
		const section = document
			.querySelector( '#linker-inputs-title' )
			.closest( '.linker-section' );
		const s = section.querySelector( '.linker-form__submit' ).getBoundingClientRect();
		const r = section.querySelector( '.linker-roof' ).getBoundingClientRect();
		return { edge: Math.round( s.bottom + scrollY ), gap: Math.round( r.top - s.bottom ) };
	} );
	await page.evaluate(
		( y ) => window.scrollTo( 0, Math.max( 0, y - 300 ) ),
		band.edge
	);
	await page.waitForTimeout( 400 );
	await page.screenshot( { path: `${ out }/roof-gap-${ width }.png` } );
	console.log( 'shot roof-gap', width, JSON.stringify( band ) );
	await ctx.close();
	return { closed, open, band };
}

report[ 'footer-1440' ] = await footer( prodEn, 1440, 900 );
report[ 'footer-390' ] = await footer( prodEn, 390, 844 );
console.log( 'footer 1440', JSON.stringify( report[ 'footer-1440' ] ) );
console.log( 'footer 390', JSON.stringify( report[ 'footer-390' ] ) );

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

/* Side-by-side sheets: both panels are crops of full-page screenshots taken at
   the same viewport width and deviceScaleFactor 1, shown at their intrinsic
   size (`object-fit` is left alone and the images carry no width or height), so
   one image pixel is one CSS pixel on either side. The crop window is the
   viewport's width, starts `pad` above the app card's top edge and is as tall
   as the viewport — captions name the rectangle. Written as a file and opened
   over file:// so the images load (a data/about: document cannot read
   file:// images). */
async function sheet( name, left, right, width, label ) {
	const figure = ( spec, caption ) => `
			<figure>
				<figcaption>${ caption }</figcaption>
				<div class="crop" data-y="${ spec.y }" style="width:${ width }px;height:${ spec.height }px">
					<img src="file://${ spec.img }" style="margin-left:${ -spec.x }px;margin-top:${ -spec.y }px">
				</div>
			</figure>`;
	const html = `<!doctype html><meta charset="utf-8"><style>
			body { margin: 0; background: #fff; font: 600 12px/1.4 system-ui, sans-serif; color: #172636; }
			main { display: flex; flex-wrap: nowrap; gap: 16px; padding: 12px; align-items: flex-start; }
			figure { margin: 0; flex: none; }
			figcaption { padding: 2px 0 6px; }
			.crop { overflow: hidden; flex: none; border: 1px solid #dfe7ec; background: #eef1f3; }
			.crop img { display: block; margin: 0; max-width: none; max-height: none; }
		</style>
		<main>${ figure(
			left,
			`SRC prototype C · 1:1 crop of proto-c-inputs-${ label }-full.png (x=${ left.x } y=${ left.y } w=${ width })`
		) }${ figure(
			right,
			`REP ${ name } · 1:1 crop of prod-${ name.split( '-' )[ 1 ] }-inputs-${ label }-full.png (x=${
				right.x
			} y=${ right.y } w=${ width })`
		) }</main>`;
	const file = `${ tmpdir() }/cfg-c-sheet-${ name }.html`;
	await writeFile( file, html );
	const ctx = await browser.newContext( {
		viewport: { width: width * 2 + 80, height: 900 },
		deviceScaleFactor: 1,
	} );
	const page = await ctx.newPage();
	await page.goto( `file://${ file }`, { waitUntil: 'load' } );
	await page.waitForTimeout( 400 );
	// Trim each crop to the pixels its screenshot actually has, and trim both
	// to the same height so the two panels line up.
	const check = await page.evaluate( () => {
		const crops = [ ...document.querySelectorAll( '.crop' ) ].map( ( crop ) => {
			const img = crop.querySelector( 'img' );
			const y = Number( crop.dataset.y );
			return {
				crop,
				img,
				scale: img.getBoundingClientRect().width / img.naturalWidth,
				height: Math.min(
					Number.parseFloat( crop.style.height ),
					img.naturalHeight - y
				),
			};
		} );
		const height = Math.min( ...crops.map( ( c ) => c.height ) );
		crops.forEach( ( c ) => {
			c.crop.style.height = `${ height }px`;
		} );
		return {
			scales: crops.map( ( c ) => c.scale ),
			natural: crops.map( ( c ) => [ c.img.naturalWidth, c.img.naturalHeight ] ),
			height,
			shown: crops.map( ( c ) => [
				c.img.getBoundingClientRect().width,
				Number.parseFloat( c.crop.style.height ),
			] ),
			// Where each panel sits in the sheet page, i.e. in the PNG: the
			// pixels of a cmp-*.png are the crops, so anyone can measure a
			// panel without guessing the sheet's layout.
			panels: crops.map( ( c ) => {
				const r = c.crop.getBoundingClientRect();
				return {
					x: Math.round( r.x + 1 ),
					y: Math.round( r.y + 1 ),
					width: Math.round( r.width - 2 ),
					height: Math.round( r.height - 2 ),
					src: c.img.getAttribute( 'src' ).replace( 'file://', '' ),
					from: [ 0, Number( c.crop.dataset.y ) ],
				};
			} ),
		};
	} );
	if ( check.scales.some( ( s ) => Math.abs( s - 1 ) > 0.001 ) ) {
		throw new Error(
			`sheet ${ name } rescales an image: ${ check.scales.join( ', ' ) }`
		);
	}
	report.sheets = report.sheets ?? {};
	report.sheets[ name ] = { ...check, imgScale: check.scales };
	await page.screenshot( { path: `${ out }/cmp-${ name }.png`, fullPage: true } );
	console.log(
		'sheet',
		name,
		'1:1',
		JSON.stringify( check.scales ),
		'height',
		check.height
	);
	await ctx.close();
}

/* The crop starts 24px above the app card's top edge, so both panels show the
   card's top border and its shadow. */
function crop( img, box, x, viewport ) {
	return { img, x, y: Math.max( 0, box[ 1 ] - 24 ), height: viewport };
}

for ( const [ label, width, height ] of [
	[ '1440', 1440, 900 ],
	[ '390', 390, 844 ],
] ) {
	const protoCard = report[ `proto-${ label }` ].card.box;
	const enCard = report[ `prod-en-${ label }` ].card.box;
	const deCard = report[ `prod-de-${ label }` ].card.box;
	await sheet(
		`${ label }-en-app`,
		crop( `${ out }/proto-c-inputs-${ label }-full.png`, protoCard, 0, height ),
		crop( `${ out }/prod-en-inputs-${ label }-full.png`, enCard, 0, height ),
		width,
		label
	);
	await sheet(
		`${ label }-de-app`,
		crop( `${ out }/proto-c-inputs-${ label }-full.png`, protoCard, 0, height ),
		crop( `${ out }/prod-de-inputs-${ label }-full.png`, deCard, 0, height ),
		width,
		label
	);
}

await writeFile(
	`${ out }/measurements.json`,
	JSON.stringify( report, null, 1 )
);
await browser.close();
console.log( 'done' );
