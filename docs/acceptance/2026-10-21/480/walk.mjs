/**
 * Local snapshot walk for #480: the six roof-step behaviours of the
 * Solution Configurator's Roof detail step (R05, R06, R08, R10, R11, R13).
 *
 * Guest only: opens /solution-configurator/ and /de/loesungskonfigurator/,
 * fills the postcode, opens the roof step, clicks the Triftstraße 5 roof,
 * toggles a plane, applies the roof, reopens and closes it, draws planes,
 * and drives the four failure states. Nothing is submitted: no calculation,
 * no inquiry, no registration, no mail.
 *
 * Instance: `just sync w480` (WordPress 9252, engine 9253) with snapshot
 * 20261021-1023. Run: node walk.mjs
 */
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
	new URL( '../../../../tests/e2e/package.json', import.meta.url )
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = join(here, 'shots');
mkdirSync(shotsDir, { recursive: true });

const ORIGIN = 'http://127.0.0.1:9252';
const ENGINE = 'http://127.0.0.1:9253';

// The fixture of R04/R05/R10: Triftstraße 5, 80538 München. The first click
// lands on it when the map (centre 48.1401, 11.5885, zoom 17) is offset by
// this many CSS pixels; the roof step's click tolerance is 3 m.
const TRIFT = { latitude: 48.140278, longitude: 11.588411, address: 'Triftstraße 5' };
const PLACE = { latitude: 48.1401, longitude: 11.5885 };

const COPIES = {
	en: {
		url: '/solution-configurator/',
		open: 'No PV figure yet? Estimate from the roof',
		use: 'Use this roof',
		change: 'Change roof',
		manual: 'Enter kWp instead',
		close: 'Close roof step',
		draw: 'Draw plane',
		drawing: 'Click the corners',
		refused: 'too large or outside Germany',
		none: 'No building at this point',
		unavailable: 'No official building model is available here',
		error: 'The roof could not be loaded',
		north: 'faces north',
		steep: 'steeper than 60°',
	},
	de: {
		url: '/de/loesungskonfigurator/',
		open: 'Noch keine PV-Leistung? Aus dem Dach abschätzen',
		use: 'Dieses Dach übernehmen',
		change: 'Dach ändern',
		manual: 'Stattdessen kWp eingeben',
		close: 'Dachauswahl schließen',
		draw: 'Fläche zeichnen',
		drawing: 'Klicken Sie die Ecken',
		refused: 'zu groß oder liegt außerhalb Deutschlands',
		none: 'An dieser Stelle steht kein Gebäude',
		unavailable: 'Hier ist kein amtliches Gebäudemodell verfügbar',
		error: 'Das Dach konnte nicht geladen werden',
		north: 'nach Norden ausgerichtet',
		steep: 'steiler als 60°',
	},
};

const record = {
	ticket: 480,
	instance: 'w480',
	origin: ORIGIN,
	engine: ENGINE,
	snapshot: '20261021-1023',
	startedAt: new Date().toISOString(),
	viewport: [1440, 390],
	writes: { posts: [], inquiry: false, registration: false, mail: false },
	engineProbes: {},
	cases: [],
};

function save() {
	writeFileSync( join( here, 'record.json' ), JSON.stringify( record, null, 2 ) );
}

function sleep( ms ) {
	return new Promise( ( resolve ) => setTimeout( resolve, ms ) );
}

async function dismissConsent( page ) {
	try {
		const accept = page.locator( '[data-cky-tag="accept-button"]' );
		await accept.waitFor( { state: 'visible', timeout: 4000 } );
		await accept.evaluate( ( button ) => button.click() );
		await page.locator( '.cky-consent-container' ).waitFor( {
			state: 'hidden',
			timeout: 3000,
		} );
	} catch {
		// Already chosen, or this page has no banner.
	}
}

async function quiet( page ) {
	await page
		.addStyleTag( {
			content:
				'*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}' +
				'.linker-roof,.linker-roof__status,.linker-roof__total,#linker-roof-summary{scroll-margin-top:12rem}',
		} )
		.catch( () => {} );
}

/**
 * Screenshots for one state at 1440 and 390, named per
 * `docs/acceptance/protocol.md`: `<page>-<viewport>-<lang>-<state>.png`.
 * An element capture hides the sticky site header and step rail by
 * visibility only, so the captured list is not cut by the chrome.
 */
async function shoot( page, state, lang, selector, extra = {} ) {
	const taken = [];
	for ( const vp of [
		{ width: 1440, height: 900, tag: '1440' },
		{ width: 390, height: 844, tag: '390' },
	] ) {
		await page.setViewportSize( { width: vp.width, height: vp.height } );
		if ( selector ) {
			const target = page.locator( selector ).first();
			if ( await target.count() ) {
				await target
					.evaluate( ( el ) =>
						el.scrollIntoView( { block: 'start', inline: 'nearest' } )
					)
					.catch( () => {} );
			}
		}
		await sleep( 650 );
		const name = `roof-${ vp.tag }-${ lang }-${ state }.png`;
		await page.screenshot( { path: join( shotsDir, name ), fullPage: false } );
		taken.push( `shots/${ name }` );
		if ( extra.element ) {
			const el = page.locator( extra.element ).first();
			if ( await el.count() ) {
				await page.evaluate( () => {
					const style = document.createElement( 'style' );
					style.id = 'w480-capture-chrome';
					style.textContent =
						'#lc-header,nav.linker-steps{visibility:hidden!important}';
					document.head.appendChild( style );
				} );
				const elName = `roof-${ vp.tag }-${ lang }-${ state }-panel.png`;
				await el
					.screenshot( { path: join( shotsDir, elName ) } )
					.catch( async () => {
						await page.screenshot( {
							path: join( shotsDir, elName ),
							fullPage: false,
						} );
					} );
				await page.evaluate( () =>
					document.getElementById( 'w480-capture-chrome' )?.remove()
				);
				taken.push( `shots/${ elName }` );
			}
		}
	}
	await page.setViewportSize( { width: 1440, height: 900 } );
	await sleep( 400 );
	return taken;
}

/** "14" / "6.44" / "6,44" -> 14 / 6.44 without guessing the locale. */
function toNumber( text ) {
	if ( text === null || text === undefined ) {
		return null;
	}
	const value = String( text ).replace( /\s/g, '' );
	if ( value.includes( ',' ) && value.includes( '.' ) ) {
		return Number( value.replace( /\./g, '' ).replace( ',', '.' ) );
	}
	if ( value.includes( ',' ) ) {
		return Number( value.replace( ',', '.' ) );
	}
	return Number( value );
}

/** Every fact the roof step shows, as it stands. */
async function roofFacts( page ) {
	return page.evaluate( () => {
		const text = ( el ) =>
			el ? el.innerText.replace( /\s+/g, ' ' ).trim() : null;
		const total = document.querySelector( '.linker-roof__total' );
		const match = total
			? /([\d.,]+)\s+modules?\D+([\d.,]+)\s+kWp/i.exec(
					total.innerText
			  )
			: null;
		return {
			status: text( document.querySelector( '.linker-roof__status' ) ),
			total: text( total ),
			modulesRaw: match ? match[ 1 ] : null,
			kwpRaw: match ? match[ 2 ] : null,
			planes: Array.from(
				document.querySelectorAll( '.linker-planes li' )
			).map( ( li ) => ( {
				excluded: li.classList.contains( 'linker-planes__excluded' ),
				text: text( li ),
				checked: li.querySelector( 'input' )?.checked ?? null,
				disabled: li.querySelector( 'input' )?.disabled ?? null,
			} ) ),
			summary: document
				.querySelector( '#linker-roof-summary' )
				?.innerText.replace( /\s+/g, ' ' )
				.trim() ?? null,
			roofButtons: Array.from(
				document.querySelectorAll( '#linker-roof-summary button' )
			).map( ( b ) => b.innerText.trim() ),
			kwpField: {
				value: document.querySelector( '#linker-kwp' )?.value ?? null,
				readOnly: document.querySelector( '#linker-kwp' )?.readOnly ?? null,
			},
			roofOpen: !! document.querySelector( '.linker-roof' ),
			lang: document.documentElement.lang,
			url: location.href,
		};
	} ).then( ( facts ) => ( {
		...facts,
		modules: toNumber( facts.modulesRaw ),
		kwp: toNumber( facts.kwpRaw ),
	} ) );
}

/** The map's visible box, clipped to the viewport. */
async function mapBox( page ) {
	const box = await page.locator( '.linker-roof__map' ).boundingBox();
	if ( ! box ) {
		return null;
	}
	const viewport = await page.evaluate( () => ( {
		width: innerWidth,
		height: innerHeight,
	} ) );
	return {
		x: box.x,
		y: Math.max( box.y, 0 ),
		width: box.width,
		height: Math.min( box.y + box.height, viewport.height ) - Math.max( box.y, 0 ),
		raw: box,
	};
}

/**
 * Clicks the map until the status names Triftstraße 5. The map's exact
 * projection differs by a few pixels between loads; a handful of offsets
 * around the projected point is enough.
 */
async function selectTriftstrasse( page ) {
	const offsets = [
		[ -17, -50 ],
		[ -23, -50 ],
		[ -10, -55 ],
		[ -30, -45 ],
		[ 0, -60 ],
		[ -17, -35 ],
	];
	for ( const [ dx, dy ] of offsets ) {
		const box = await mapBox( page );
		await page.mouse.click(
			box.x + box.width / 2 + dx,
			box.y + box.height / 2 + dy
		);
		for ( let i = 0; i < 8; i++ ) {
			await sleep( 250 );
			const status = await page
				.locator( '.linker-roof__status' )
				.innerText()
				.catch( () => '' );
			if ( status.includes( TRIFT.address ) ) {
				return { clicked: [ dx, dy ], status };
			}
			if ( ! status.startsWith( 'Click the roof' ) && ! status.includes( 'Luftbild' ) ) {
				break;
			}
		}
	}
	return { clicked: null, status: await page.locator( '.linker-roof__status' ).innerText() };
}

/** Opens the roof step from a closed form. `plz` is filled first. */
async function openRoof( page, copy, plz = '80538', button = copy.open ) {
	if ( plz !== '80538' ) {
		await page.fill( '#linker-plz', plz );
	}
	await page
		.locator( '#linker-roof-summary button', { hasText: button } )
		.first()
		.click();
	await page.waitForSelector( '.linker-roof', { timeout: 20000 } );
	// The map opens once `/geo/plz` answers; the click handler exists with the map.
	for ( let i = 0; i < 40; i++ ) {
		const text = await page
			.locator( '.linker-roof__status' )
			.innerText()
			.catch( () => '' );
		if ( ! /Loading the aerial image|Luftbild wird geladen/i.test( text ) ) {
			break;
		}
		await sleep( 250 );
	}
	await sleep( 2200 );
	await page
		.locator( '.linker-roof' )
		.evaluate( ( el ) => el.scrollIntoView( { block: 'start' } ) );
	await sleep( 500 );
	return copy;
}

async function closeRoof( page ) {
	await page.locator( '.linker-roof__header button' ).click();
	await page.waitForSelector( '.linker-roof', { state: 'detached', timeout: 10000 } );
	await sleep( 300 );
}

/**
 * Records every sentence the status element shows, in order, including ones a
 * poll would miss and a sentence that comes back after another one (the
 * refusal is replaced by the finishing click's selection).
 */
async function observeStatus( page ) {
	await page.evaluate( () => {
		window.__roofStatusObserver?.disconnect();
		window.__roofStatuses = [];
		const target = document.querySelector( '.linker-roof__status' );
		if ( ! target ) {
			return;
		}
		const started = performance.now();
		const read = () =>
			( target.innerText || '' ).replace( /\s+/g, ' ' ).trim();
		let last = '';
		if ( read() ) {
			last = read();
			window.__roofStatuses.push( { t: 0, text: last } );
		}
		window.__roofStatusObserver = new MutationObserver( () => {
			const line = read();
			if ( line && line !== last ) {
				last = line;
				window.__roofStatuses.push( {
					t: Math.round( performance.now() - started ),
					text: line,
				} );
			}
		} );
		window.__roofStatusObserver.observe( target, {
			childList: true,
			subtree: true,
			characterData: true,
		} );
	} );
}

async function statusesSeen( page ) {
	return page.evaluate( () => window.__roofStatuses || [] );
}

/**
 * Draws a rectangle inside the map's visible area and finishes it: first with
 * a click on the first corner (the app's own instruction), and if that leaves
 * the polygon open, with a double click on the last corner.
 *
 * The Draw button is clicked without scrolling (the bottom of the panel is
 * out of view), then the map itself is brought to the top of the viewport so
 * every corner lands on the canvas, not on the sticky site header.
 */
async function drawRectangle( page, copy, { x, top, width, height } ) {
	// A real pointer click; Playwright scrolls the bottom-of-panel button into
	// view, then the map is brought back to the top for the corners.
	await page.locator( '.linker-roof__draw button' ).click();
	await sleep( 600 );
	await page
		.locator( '.linker-roof__map' )
		.evaluate( ( el ) => el.scrollIntoView( { block: 'start' } ) );
	await sleep( 600 );
	const box = await mapBox( page );
	const x0 = box.x + box.width * x;
	const y0 = box.y + top;
	const x1 = x0 + box.width * width;
	const y1 = y0 + height;
	const points = [
		[ x0, y0 ],
		[ x1, y0 ],
		[ x1, y1 ],
		[ x0, y1 ],
	];
	for ( const [ px, py ] of points ) {
		await page.mouse.click( px, py );
		await sleep( 300 );
	}
	await page.mouse.click( x0, y0 );
	let finishedBy = 'first-corner click';
	for ( let i = 0; i < 8; i++ ) {
		await sleep( 250 );
		const status = await page
			.locator( '.linker-roof__status' )
			.innerText()
			.catch( () => '' );
		if ( ! status.includes( copy.drawing ) ) {
			return { finishedBy, points, map: box };
		}
	}
	await page.mouse.dblclick( x1, y1 );
	finishedBy = 'double click on the last corner';
	await sleep( 2000 );
	return { finishedBy, points, map: box };
}

async function drawQuestions( page ) {
	return page.evaluate( () => {
		const questions = document.querySelectorAll( '.linker-planes li' );
		return {
			planeCount: questions.length,
			// The draw form's defaults are 35° / south; no LoD2 plane of the
			// fixture has that tilt, so the row is the drawn plane.
			hasDrawn: Array.from( questions ).some( ( li ) =>
				/(tilt|Neigung) 35°/.test( li.innerText )
			),
			rows: Array.from( questions ).map( ( li ) =>
				li.innerText.replace( /\s+/g, ' ' ).trim()
			),
		};
	} );
}

/** Polls the status for two seconds and keeps every distinct sentence. */
async function statusTrace( page, ms = 2200 ) {
	const seen = [];
	const until = Date.now() + ms;
	while ( Date.now() < until ) {
		const text = await page
			.locator( '.linker-roof__status' )
			.innerText()
			.catch( () => '' );
		const flat = text.replace( /\s+/g, ' ' ).trim();
		if ( flat && ! seen.includes( flat ) ) {
			seen.push( flat );
		}
		await sleep( 100 );
	}
	return seen;
}

async function runCase( browser, lang ) {
	const copy = COPIES[ lang ];
	const result = { lang, url: copy.url, steps: {}, shots: [] };
	const context = await browser.newContext( {
		viewport: { width: 1440, height: 900 },
	} );
	const page = await context.newPage();
	const network = [];
	// Every POST the page makes, so the no-write claim is recorded, not asserted.
	const posts = [];
	page.on( 'request', ( request ) => {
		if ( request.method() === 'POST' ) {
			posts.push( {
				url: request.url(),
				path: request.url().replace( ORIGIN, '' ),
				status: null,
			} );
		}
		if ( request.url().includes( '/engine/roof/' ) ) {
			const body = request.postData();
			network.push( {
				method: request.method(),
				path: request.url().split( '/engine/' )[ 1 ],
				body: body ? JSON.parse( body ) : null,
			} );
		}
	} );
	page.on( 'response', async ( response ) => {
		if ( response.request().method() === 'POST' ) {
			const entry = [ ...posts ]
				.reverse()
				.find(
					( item ) =>
						item.url === response.url() && item.status === null
				);
			if ( entry ) {
				entry.status = response.status();
			}
		}
		if ( response.url().includes( '/engine/roof/' ) ) {
			const path = response.url().split( '/engine/' )[ 1 ];
			let body = null;
			try {
				body = await response.json();
			} catch {
				body = null;
			}
			// Keep the answer's contract, not every module polygon.
			const summary =
				path === 'roof/outline' && body
					? {
							found: body.found,
							address: body.address,
							building_id: body.building_id,
							planes: body.planes?.length,
							modules: body.modules,
							kwp: body.kwp,
					  }
					: path === 'roof/pack' && body
					? {
							id: body.id,
							area_m2: body.area_m2,
							usable: body.usable,
							excluded_reason: body.excluded_reason,
							modules: body.modules,
							kwp: body.kwp,
					  }
					: body;
			network.push( {
				response: path,
				status: response.status(),
				body: summary,
			} );
		}
	} );

	await page.goto( ORIGIN + copy.url, { waitUntil: 'domcontentloaded' } );
	await dismissConsent( page );
	await quiet( page );
	await page.waitForSelector( '#linker-plz', { timeout: 20000 } );
	await page.fill( '#linker-plz', '80538' );

	// R10 + R05: the LoD2 roof with usable and excluded planes.
	await openRoof( page, copy );
	const selected = await selectTriftstrasse( page );
	result.steps.select = selected;
	const baseline = await roofFacts( page );
	result.steps.baseline = baseline;
	result.shots.push(
		...( await shoot( page, 'r10-excluded', lang, '.linker-roof', {
			element: '.linker-planes',
		} ) )
	);

	const enabled = page.locator( '.linker-planes input:not([disabled])' );
	const first = enabled.first();
	const checkedLabel = await first.evaluate( ( input ) =>
		input.closest( 'li' ).innerText.replace( /\s+/g, ' ' ).trim()
	);
	await first.click();
	await sleep( 400 );
	const unchecked = await roofFacts( page );
	result.shots.push(
		...( await shoot( page, 'r05-unchecked', lang, '.linker-roof__total' ) )
	);
	await page
		.locator( '.linker-planes input:not([disabled])' )
		.first()
		.click();
	await sleep( 400 );
	const rechecked = await roofFacts( page );
	result.shots.push(
		...( await shoot( page, 'r05-rechecked', lang, '.linker-roof__total' ) )
	);
	result.steps.r05 = {
		checkbox: checkedLabel,
		initial: { modules: baseline.modules, kwp: baseline.kwp },
		unchecked: { modules: unchecked.modules, kwp: unchecked.kwp },
		rechecked: { modules: rechecked.modules, kwp: rechecked.kwp },
		changed: unchecked.modules !== baseline.modules || unchecked.kwp !== baseline.kwp,
		restored:
			rechecked.modules === baseline.modules && rechecked.kwp === baseline.kwp,
	};
	result.steps.r10 = {
		excluded: baseline.planes
			.filter( ( plane ) => plane.excluded )
			.map( ( plane ) => plane.text ),
		north: baseline.planes.filter( ( plane ) => plane.text.includes( copy.north ) ),
		steep: baseline.planes.filter( ( plane ) => plane.text.includes( copy.steep ) ),
	};

	// R08: apply, change, close, enter kWp instead.
	await page.locator( '.linker-roof__actions button' ).click();
	await sleep( 700 );
	const applied = await roofFacts( page );
	result.steps.r08 = {
		applied,
	};
	result.shots.push(
		...( await shoot( page, 'r08-applied', lang, '#linker-roof-summary' ) )
	);
	await page
		.locator( '#linker-roof-summary button', { hasText: copy.change } )
		.click();
	await page.waitForSelector( '.linker-roof', { timeout: 20000 } );
	await sleep( 2600 );
	const changed = await roofFacts( page );
	result.steps.r08.change = { reopened: changed.roofOpen, status: changed.status };
	result.shots.push(
		...( await shoot( page, 'r08-change-roof', lang, '.linker-roof__header' ) )
	);
	await closeRoof( page );
	const afterClose = await roofFacts( page );
	result.steps.r08.afterClose = {
		roofOpen: afterClose.roofOpen,
		summary: afterClose.summary,
		kwp: afterClose.kwpField,
	};
	await page
		.locator( '#linker-roof-summary button', { hasText: copy.manual } )
		.click();
	await sleep( 500 );
	const manual = await roofFacts( page );
	result.steps.r08.manual = {
		summary: manual.summary,
		kwp: manual.kwpField,
		roofOpen: manual.roofOpen,
	};
	result.shots.push(
		...( await shoot( page, 'r08-manual', lang, '#linker-roof-summary' ) )
	);

	// R13: open, select a roof in the step, close without adopting: the form
	// keeps its manual kWp and the in-step selection is discarded.
	const manualValue = manual.kwpField.value;
	await openRoof( page, copy );
	await selectTriftstrasse( page );
	const inStep = await roofFacts( page );
	await closeRoof( page );
	const afterR13 = await roofFacts( page );
	result.steps.r13 = {
		opened: inStep.roofOpen,
		inStepSelection: {
			status: inStep.status,
			modules: inStep.modules,
			kwp: inStep.kwp,
			planes: inStep.planes.length,
		},
		closed: ! afterR13.roofOpen,
		summary: afterR13.summary,
		before: manualValue,
		after: afterR13.kwpField,
		kept: afterR13.kwpField.value === manualValue && afterR13.kwpField.readOnly === false,
	};
	result.shots.push(
		...( await shoot( page, 'r13-closed', lang, '#linker-roof-summary' ) )
	);

	// R06: draw a plane, then one beyond MAX_DRAWN_PLANE_M2.
	await openRoof( page, copy );
	await selectTriftstrasse( page );
	await sleep( 600 );
	network.length = 0;
	const beforeDraw = await roofFacts( page );
	await observeStatus( page );
	const smallDraw = await drawRectangle( page, copy, {
		x: 0.2,
		top: 120,
		width: 0.32,
		height: 140,
	} );
	await sleep( 2500 );
	const afterDraw = await roofFacts( page );
	result.steps.r06 = {
		before: {
			modules: beforeDraw.modules,
			kwp: beforeDraw.kwp,
			planes: beforeDraw.planes.length,
		},
		after: {
			status: afterDraw.status,
			modules: afterDraw.modules,
			kwp: afterDraw.kwp,
			planes: afterDraw.planes.length,
			questions: await drawQuestions( page ),
		},
		finishedBy: smallDraw.finishedBy,
		statuses: await statusesSeen( page ),
		network: network.filter( ( item ) => item.path || item.response ),
	};
	result.shots.push(
		...( await shoot( page, 'r06-drawn-attempt', lang, '.linker-roof__status' ) )
	);

	// Beyond 3000 m²: zoom out so the visible map covers more than the bound,
	// then draw a rectangle that is larger than the bound on the ground.
	const zoomOut = page.locator( '.maplibregl-ctrl-zoom-out' );
	for ( let i = 0; i < 3; i++ ) {
		await zoomOut.click();
		await sleep( 900 );
	}
	await observeStatus( page );
	network.length = 0;
	const beforeBig = await roofFacts( page );
	const bigDraw = await drawRectangle( page, copy, {
		x: 0.12,
		top: 110,
		width: 0.55,
		height: 280,
	} );
	await sleep( 2500 );
	const afterBig = await roofFacts( page );
	result.steps.r06.refused = {
		before: { planes: beforeBig.planes.length },
		finishedBy: bigDraw.finishedBy,
		statuses: await statusesSeen( page ),
		status: afterBig.status,
		planes: afterBig.planes.length,
		modules: afterBig.modules,
		kwp: afterBig.kwp,
		network: network.filter( ( item ) => item.path || item.response ),
	};
	result.shots.push(
		...( await shoot( page, 'r06-refused-attempt', lang, '.linker-roof__status' ) )
	);
	await closeRoof( page );

	// R11: no building, LoD2 unavailable, map load failure.
	const emptyOffsets = [
		[ 180, -120 ],
		[ 120, -100 ],
		[ 60, 160 ],
		[ -150, -150 ],
	];
	let noBuilding = null;
	for ( const [ dx, dy ] of emptyOffsets ) {
		await openRoof( page, copy );
		const box = await mapBox( page );
		await page.mouse.click( box.x + box.width / 2 + dx, box.y + box.height / 2 + dy );
		const trace = await statusTrace( page, 2200 );
		if ( trace.some( ( line ) => line.includes( copy.none ) ) ) {
			noBuilding = { offset: [ dx, dy ], trace, facts: await roofFacts( page ) };
			result.shots.push(
				...( await shoot( page, 'r11-no-building', lang, '.linker-roof__status' ) )
			);
			await closeRoof( page );
			break;
		}
		await closeRoof( page );
	}
	result.steps.r11 = { noBuilding };

	await openRoof( page, copy, '06108' );
	const lod2Box = await mapBox( page );
	await page.mouse.click(
		lod2Box.x + lod2Box.width / 2,
		lod2Box.y + lod2Box.height / 2
	);
	const lod2Trace = await statusTrace( page, 2500 );
	result.steps.r11.lod2 = { trace: lod2Trace, facts: await roofFacts( page ) };
	result.shots.push(
		...( await shoot(
			page,
			'r11-lod2-unavailable',
			lang,
			'.linker-roof__status'
		) )
	);
	await closeRoof( page );

	await page.fill( '#linker-plz', '99999' );
	await page
		.locator( '#linker-roof-summary button', { hasText: copy.open } )
		.first()
		.click();
	await page.waitForSelector( '.linker-roof', { timeout: 20000 } );
	await sleep( 2500 );
	const errorTrace = await statusTrace( page, 2000 );
	result.steps.r11.mapError = { trace: errorTrace, facts: await roofFacts( page ) };
	result.shots.push(
		...( await shoot( page, 'r11-map-error', lang, '.linker-roof' ) )
	);
	await closeRoof( page );

	result.posts = posts;
	result.finishedAt = new Date().toISOString();
	await context.close();
	return result;
}

async function engineProbes() {
	const post = async ( path, body ) => {
		const response = await fetch( ENGINE + path, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify( body ),
		} );
		let json = null;
		try {
			json = await response.json();
		} catch {
			json = null;
		}
		return { status: response.status, body: json };
	};
	const get = async ( path ) => {
		const response = await fetch( ENGINE + path );
		let json = null;
		try {
			json = await response.json();
		} catch {
			json = null;
		}
		return { status: response.status, body: json };
	};
	const valid = await post( '/roof/pack', {
		polygon: [
			[ 11.5883, 48.1402 ],
			[ 11.5885, 48.1402 ],
			[ 11.5885, 48.1403 ],
			[ 11.5883, 48.1403 ],
		],
		tilt_deg: 35,
		azimuth_deg: 180,
	} );
	const tooLarge = await post( '/roof/pack', {
		polygon: [
			[ 11.58, 48.14 ],
			[ 11.62, 48.14 ],
			[ 11.62, 48.16 ],
			[ 11.58, 48.16 ],
		],
		tilt_deg: 35,
		azimuth_deg: 180,
	} );
	const outside = await post( '/roof/pack', {
		polygon: [
			[ 20.0, 60.0 ],
			[ 20.01, 60.0 ],
			[ 20.01, 60.01 ],
			[ 20.0, 60.01 ],
		],
		tilt_deg: 35,
		azimuth_deg: 180,
	} );
	const outsideLow = await post( '/roof/pack', {
		polygon: [
			[ 0.0, 40.0 ],
			[ 0.01, 40.0 ],
			[ 0.01, 40.01 ],
			[ 0.0, 40.01 ],
		],
		tilt_deg: 35,
		azimuth_deg: 180,
	} );
	// A bow tie is inside the bounds and passes the area bound but is not a
	// polygon the packer can use: roof_geometry, the third exclusion sentence.
	const geometry = await post( '/roof/pack', {
		polygon: [
			[ 11.5883, 48.1402 ],
			[ 11.5885, 48.1403 ],
			[ 11.5883, 48.1403 ],
			[ 11.5885, 48.1402 ],
		],
		tilt_deg: 35,
		azimuth_deg: 180,
	} );
	const lod2 = await post( '/roof/outline', {
		plz: '06108',
		locale: 'en',
		location: { latitude: 51.483, longitude: 11.972 },
	} );
	const unknown = await get( '/geo/plz/99999' );
	record.engineProbes = {
		packValid: {
			status: valid.status,
			modules: valid.body?.modules,
			kwp: valid.body?.kwp,
			area_m2: valid.body?.area_m2,
		},
		packTooLarge: {
			status: tooLarge.status,
			message: tooLarge.body?.detail?.[ 0 ]?.msg ?? null,
		},
		packOutsideGermany: {
			status: outside.status,
			constraints: ( outside.body?.detail ?? [] ).map(
				( item ) => `${ item.msg } (${ item.input })`
			),
		},
		packOutsideGermanyLow: {
			status: outsideLow.status,
			constraints: ( outsideLow.body?.detail ?? [] ).map(
				( item ) => `${ item.msg } (${ item.input })`
			),
		},
		packGeometry: {
			status: geometry.status,
			usable: geometry.body?.usable,
			excluded_reason: geometry.body?.excluded_reason,
			modules: geometry.body?.modules,
		},
		lod2Unavailable: {
			status: lod2.status,
			detail: lod2.body?.detail ?? null,
		},
		unknownPostcode: { status: unknown.status, detail: unknown.body?.detail ?? null },
	};
}

const browser = await chromium.launch();
try {
	await engineProbes();
	save();
	for ( const lang of [ 'en', 'de' ] ) {
		const result = await runCase( browser, lang );
		record.cases.push( result );
		record.writes.posts = record.cases.flatMap( ( item ) =>
			item.posts.map( ( post ) => ( { lang: item.lang, ...post } ) )
		);
		const written = record.writes.posts.map( ( post ) => post.path );
		record.writes.inquiry = written.some( ( path ) => /inquiry/i.test( path ) );
		record.writes.registration = written.some( ( path ) =>
			/register|user/i.test( path )
		);
		record.writes.mail = written.some( ( path ) => /mail|contact/i.test( path ) );
		save();
	}
	record.finishedAt = new Date().toISOString();
	save();
} finally {
	await browser.close();
}
