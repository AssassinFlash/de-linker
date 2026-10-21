/**
 * Ticket #479: the configurator interaction walk on the local snapshot.
 *
 * Six behaviours, each in EN and DE at 1440 and 390:
 *   C08  ArrowLeft / ArrowRight move between the three application radios
 *   C22  a real but unknown postcode (26124, Oldenburg) -> the engine's 422
 *        field=plz copy; a yield-service 503 -> the service copy. The 503 is
 *        produced by stub503.py behind the site's own EngineProxy: the browser
 *        request is real, only the engine behind the proxy is the stub.
 *   C28  Add all: Store API 500 -> retry cards; a short readback -> unverified
 *        cards; a readback that recovers within SETTLE_READS -> added. The
 *        card/order states, the number of post-add cart reads and the gaps
 *        between them are recorded (SETTLE_MS = 250, SETTLE_READS = 3).
 *   C30  guest save: no login, the save answers the page's language URL
 *        (?lang=, #477) and keeps the solution in the WooCommerce session
 *        (the guest's claim cookie). Both saves are then claimed by one
 *        login and listed on the account page in both languages.
 *   C31  save failure: POST linker/v1/solutions 500 -> the failure copy.
 *   C57  hand-entered kWp, no roof -> the report's 35-degree-south sentence
 *        (limit.default_orientation), EN and DE.
 *
 * No product code is changed. The walk writes only its own guest session and
 * draft, expects the one WP-CLI test user the run command creates and deletes
 * it with the solutions the claim created, and points the option
 * `linker_engine_url` at the 503 stub for the two 503 screens before
 * restoring the real engine. No mail, no inquiry, no registration.
 *
 * Instance: `just up walk479`, `just pull load walk479 latest`,
 * `just present walk479`, `just serve walk479` (see README.md).
 *
 * Run: node walk.mjs <one-time-login-url> [user-login]
 */
import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';

const require = createRequire(
	process.env.LINKER_E2E_PACKAGE ||
		'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = join(here, 'shots');
mkdirSync(shotsDir, { recursive: true });

const REPO = join( here, '../../../..' );
const INSTANCE = 'walk479';
const ORIGIN = 'http://127.0.0.1:9258';
const ENGINE = 'http://127.0.0.1:9259';
const STUB_PORT = 9333;
const USER = process.argv[3] || 'walk479';
const LOGIN_URL = process.argv[2] || '';

const PAGES = {
	en: '/solution-configurator/',
	de: '/de/loesungskonfigurator/',
};
const ACCOUNT = {
	en: '/my-account/saved-solutions/',
	de: '/de/mein-konto/gespeicherte-loesungen/',
};
const LOCALES = { en: 'en-GB', de: 'de-DE' };
const ADD_RE = /Add all to solution draft|Alles zum Lösungsentwurf hinzufügen/;
const SAVE_RE = /Save solution|Lösung speichern/;

const UNKNOWN_PLZ = '26124';
const KNOWN_PLZ = { en: '80538', de: '80331' };

const EXPECTED = {
	unknownPlz: {
		en: 'We do not know this postcode. Check it and try again.',
		de: 'Diese Postleitzahl ist uns nicht bekannt. Prüfen Sie sie und versuchen Sie es erneut.',
	},
	yieldUnavailable: {
		en: 'The yield service did not answer. Try again in a minute.',
		de: 'Der Ertragsdienst hat nicht geantwortet. Versuchen Sie es in einer Minute erneut.',
	},
	addRetry: {
		en: 'Not added. Try again.',
		de: 'Nicht hinzugefügt. Versuchen Sie es erneut.',
	},
	addUnverified: {
		en: 'Sent, but the draft does not show it yet. Please check.',
		de: 'Gesendet, aber im Entwurf noch nicht sichtbar. Bitte prüfen Sie den Entwurf.',
	},
	orderPartial: {
		en: 'Some products are not confirmed in your solution draft. See the cards above.',
		de: 'Einige Produkte sind in Ihrem Lösungsentwurf nicht bestätigt. Einzelheiten stehen in den Karten oben.',
	},
	orderComplete: {
		en: 'All products are in your solution draft.',
		de: 'Alle Produkte sind in Ihrem Lösungsentwurf.',
	},
	saveFailed: {
		en: 'The solution could not be saved. Try again.',
		de: 'Die Lösung konnte nicht gespeichert werden. Versuchen Sie es erneut.',
	},
	saved: {
		en: 'Saved to your account.',
		de: 'In Ihrem Konto gespeichert.',
	},
	orientation: {
		en: 'Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).',
		de: 'Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).',
	},
};

const record = {
	ticket: 479,
	kind: 'local snapshot walkthrough',
	instance: INSTANCE,
	origin: ORIGIN,
	startedAt: new Date().toISOString(),
	mailSent: false,
	inquirySent: false,
	registered: false,
	forbiddenPosts: [],
	posts: [],
	rows: {},
	cleanup: {},
};

function writeRecord() {
	writeFileSync( join( here, 'record.json' ), JSON.stringify( record, null, 2 ) );
}

function sleep( ms ) {
	return new Promise( ( resolve ) => setTimeout( resolve, ms ) );
}

function runWp( args ) {
	const output = execFileSync( 'just', [ 'wp', INSTANCE, ...args ], {
		cwd: REPO,
		encoding: 'utf8',
		timeout: 120000,
	} );
	const lines = output.trim().split( '\n' );
	return lines[ lines.length - 1 ].trim();
}

/**
 * Counters that must not move because of this walk: the instance's mail files
 * (the local mu-plugin writes one .eml per wp_mail call), HPOS orders,
 * saved solutions and customers. The run command creates the one WP-CLI test
 * user before this script; it is excluded from the customer count and deleted
 * at the end. The two guest saves and the claimed solutions are created and
 * removed inside the walk.
 */
function instanceCounts() {
	const count = ( args ) => Number( runWp( args ) );
	let mailFiles = -1;
	try {
		mailFiles = readdirSync(
			join( homedir(), 'de-linker-local', INSTANCE, 'mail' )
		).filter( ( name ) => name.endsWith( '.eml' ) ).length;
	} catch {
		mailFiles = -1;
	}
	return {
		// HPOS is enabled on this snapshot: shop_order posts are empty while
		// the real orders live in wp_wc_orders (66 on arrival).
		orders: count( [
			'db',
			'query',
			'SELECT COUNT(*) FROM wp_wc_orders',
			'--skip-column-names',
		] ),
		mailFiles,
		solutions: count( [
			'post',
			'list',
			'--post_type=linker_solution',
			'--format=count',
		] ),
		customers: count( [
			'db',
			'query',
			"SELECT COUNT(*) FROM wp_users u JOIN wp_usermeta m ON m.user_id = u.ID AND m.meta_key = 'wp_capabilities' "
				+ `WHERE m.meta_value LIKE '%customer%' AND u.user_login <> '${ USER }'`,
			'--skip-column-names',
		] ),
	};
}

function sourceConstants() {
	const store = readFileSync(
		join( REPO, 'plugins/linker-tools/src/configurator/api/store.ts' ),
		'utf8'
	);
	const settleMs = /const SETTLE_MS = (\d+)/.exec( store );
	const settleReads = /const SETTLE_READS = (\d+)/.exec( store );
	return {
		settleMs: settleMs ? Number( settleMs[ 1 ] ) : null,
		settleReads: settleReads ? Number( settleReads[ 1 ] ) : null,
	};
}

function gazetteerFacts() {
	const table = gunzipSync(
		readFileSync( join( REPO, 'services/engine/data/plz_de.csv.gz' ) )
	)
		.toString( 'utf8' )
		.trim()
		.split( '\n' );
	const wanted = `${ UNKNOWN_PLZ },`;
	return {
		file: 'services/engine/data/plz_de.csv.gz',
		rows: table.length - 1,
		containsUnknown: table.slice( 1 ).some( ( line ) => line.startsWith( wanted ) ),
	};
}

async function buildFacts( page ) {
	const src = await page.evaluate( () => {
		const script = [ ...document.scripts ]
			.map( ( node ) => node.src )
			.find( ( url ) => url.includes( 'configurator.js' ) );
		return script || '';
	} );
	if ( ! src ) {
		return { src: '', ver: '', sha256: '', bytes: 0 };
	}
	const text = await ( await fetch( src ) ).text();
	return {
		src,
		ver: new URL( src ).searchParams.get( 'ver' ),
		sha256: createHash( 'sha256' ).update( text ).digest( 'hex' ),
		bytes: Buffer.byteLength( text ),
	};
}

async function dismissConsent( page ) {
	const accept = page.locator( '[data-cky-tag="accept-button"]' );
	try {
		await accept.waitFor( { state: 'visible', timeout: 2500 } );
		await accept.evaluate( ( button ) => button.click() );
		await page
			.locator( '.cky-consent-container' )
			.waitFor( { state: 'hidden', timeout: 3000 } )
			.catch( () => {} );
	} catch {
		// Already chosen on this context, or the page has no banner.
	}
}

async function quiet( page ) {
	await page
		.addStyleTag( {
			content:
				'*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}',
		} )
		.catch( () => {} );
}

function watchPosts( page, label ) {
	page.on( 'request', ( request ) => {
		if ( request.method() !== 'POST' ) {
			return;
		}
		const path = request.url().replace( ORIGIN, '' ).split( '?' )[ 0 ];
		record.posts.push( { label, path } );
		if (
			/\/checkout|proforma-request|proforma-anfrage|wp-login\.php|\/register|contact-form|wc\/store\/v1\/checkout/.test(
				request.url()
			)
		) {
			record.forbiddenPosts.push( { label, path } );
		}
	} );
}

async function newPage( browser, lang, label ) {
	const context = await browser.newContext( {
		viewport: { width: 1440, height: 900 },
		locale: LOCALES[ lang ],
		userAgent: 'de-linker-walk-479/1.0',
		reducedMotion: 'reduce',
	} );
	const page = await context.newPage();
	watchPosts( page, label );
	return { context, page };
}

async function openConfigurator( page, lang ) {
	const response = await page.goto( ORIGIN + PAGES[ lang ], {
		waitUntil: 'domcontentloaded',
		timeout: 60000,
	} );
	await dismissConsent( page );
	await quiet( page );
	await page.locator( '#linker-plz' ).waitFor( {
		state: 'visible',
		timeout: 30000,
	} );
	return response ? response.status() : 0;
}

async function fillResidential( page, plz ) {
	await page.locator( '#linker-plz' ).fill( plz );
	await page.locator( '#linker-annual' ).fill( '4500' );
	await page.locator( '#linker-kwp' ).fill( '10' );
	await page.locator( '#linker-phase-3' ).check();
	await page.locator( '#linker-backup' ).selectOption( 'none' );
}

async function calculate( page, plz ) {
	await fillResidential( page, plz );
	const requestWait = page.waitForRequest(
		( request ) =>
			request.url().includes( '/engine/design/residential' ) &&
			request.method() === 'POST',
		{ timeout: 30000 }
	);
	const responseWait = page.waitForResponse(
		( response ) =>
			response.url().includes( '/engine/design/residential' ) &&
			response.request().method() === 'POST',
		{ timeout: 180000 }
	);
	const t0 = Date.now();
	await page
		.locator( '#linker-inputs-section form button[type="submit"]' )
		.click();
	const request = await requestWait;
	const response = await responseWait;
	const ms = Date.now() - t0;
	let body = null;
	try {
		body = await response.json();
	} catch {
		body = null;
	}
	let postData = null;
	try {
		postData = JSON.parse( request.postData() || 'null' );
	} catch {
		postData = null;
	}
	await page.waitForTimeout( 400 );
	return {
		status: response.status(),
		requestUrl: request.url(),
		postData,
		body,
		ms,
	};
}

async function radioState( page ) {
	return page.evaluate( () => ( {
		focus: document.activeElement?.id || '',
		checked: [
			...document.querySelectorAll( '[role="radio"]' ),
		]
			.filter( ( node ) => node.getAttribute( 'aria-checked' ) === 'true' )
			.map( ( node ) => node.id ),
		labels: [
			...document.querySelectorAll(
				'[role="radio"] .linker-segments__label'
			),
		].map( ( node ) => node.textContent.trim() ),
		tabIndex: [
			...document.querySelectorAll( '[role="radio"]' ),
		].map( ( node ) => node.tabIndex ),
		panel: document.querySelector( '[id^="linker-panel-"]' )?.id || '',
	} ) );
}

async function cardStates( page ) {
	return page.evaluate( () =>
		[ ...document.querySelectorAll( '.linker-card' ) ].map( ( card ) => ( {
			state: card.dataset.state || '',
			title:
				card.querySelector( '.linker-card__title' )?.innerText.trim() ||
				'',
			text:
				card
					.querySelector( '.linker-card__status' )
					?.innerText.replace( /\s+/g, ' ' )
					.trim() || '',
		} ) )
	);
}

async function actionState( page ) {
	return page.evaluate( () => ( {
		text:
			document
				.querySelector( '.linker-actions__status' )
				?.innerText.replace( /\s+/g, ' ' )
				.trim() || '',
		href:
			document
				.querySelector( '.linker-actions__status a' )
				?.getAttribute( 'href' ) || '',
		buttons: [
			...document.querySelectorAll( '.linker-actions button' ),
		].map( ( button ) => ( {
			label: button.innerText.trim(),
			disabled: button.disabled,
			busy: button.getAttribute( 'aria-busy' ),
		} ) ),
	} ) );
}

async function solutionsOnPage( page ) {
	return page.evaluate( () => ( {
		url: location.href,
		lang: document.documentElement.lang,
		title: document.title,
		rows: [
			...document.querySelectorAll( '.linker-account-solution' ),
		].map( ( row ) => row.innerText.replace( /\s+/g, ' ' ).trim() ),
		empty:
			document
				.querySelector( '.linker-empty' )
				?.innerText.replace( /\s+/g, ' ' )
				.trim() || '',
		heading:
			document.querySelector( 'h1' )?.innerText.replace( /\s+/g, ' ' ).trim() ||
			'',
	} ) );
}

async function shoot( page, base, target ) {
	const taken = [];
	for ( const viewport of [
		{ width: 1440, height: 900, tag: '1440' },
		{ width: 390, height: 844, tag: '390' },
	] ) {
		await page.setViewportSize( {
			width: viewport.width,
			height: viewport.height,
		} );
		try {
			if ( target ) {
				const locator =
					typeof target === 'string'
						? page.locator( target ).first()
						: target;
				if ( await locator.count() ) {
					// Center the state: at 390 the mobile navigation is fixed
					// at the bottom, and a target scrolled only just into view
					// can sit behind it.
					await locator.evaluate( ( element ) =>
						element.scrollIntoView( {
							block: 'center',
							inline: 'nearest',
						} )
					);
				}
			}
		} catch {
			// A target the state does not render: keep the viewport as it is.
		}
		await page.waitForTimeout( 350 );
		const name = `${ base }-${ viewport.tag }.png`;
		await page.screenshot( { path: join( shotsDir, name ) } );
		taken.push( `shots/${ name }` );
	}
	await page.setViewportSize( { width: 1440, height: 900 } );
	return taken;
}

async function emptyDraft( page ) {
	return page.evaluate( async () => {
		const base = '/wp-json/wc/store/v1';
		const read = await fetch( `${ base }/cart`, { credentials: 'include' } );
		let nonce = read.headers.get( 'Nonce' ) || '';
		const cart = await read.json();
		const removed = [];
		for ( const item of cart.items || [] ) {
			const response = await fetch( `${ base }/cart/remove-item`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json', Nonce: nonce },
				body: JSON.stringify( { key: item.key } ),
			} );
			nonce = response.headers.get( 'Nonce' ) || nonce;
			removed.push( { id: item.id, status: response.status } );
		}
		const after = await fetch( `${ base }/cart`, { credentials: 'include' } );
		const body = await after.json();
		return {
			removed,
			remaining: ( body.items || [] ).length,
			left: ( body.items || [] ).map( ( item ) => ( {
				id: item.id,
				quantity: item.quantity,
			} ) ),
		};
	} );
}

/* C08 ------------------------------------------------------------------- */

async function walkC08( browser ) {
	const row = {};
	for ( const lang of [ 'en', 'de' ] ) {
		const { context, page } = await newPage( browser, lang, 'C08' );
		try {
			await openConfigurator( page, lang );
			await page.locator( '#linker-tab-residential' ).focus();
			const states = [ await radioState( page ) ];
			for ( const key of [ 'ArrowRight', 'ArrowRight', 'ArrowRight', 'ArrowLeft' ] ) {
				await page.keyboard.press( key );
				await page.waitForTimeout( 250 );
				states.push( { key, ...( await radioState( page ) ) } );
			}
			row[ lang ] = {
				states,
				shots: await shoot( page, `c08-arrows-${ lang }`, '.linker-segments' ),
			};
		} finally {
			await context.close();
		}
	}
	record.rows.C08 = row;
	writeRecord();
}

/* C22 ------------------------------------------------------------------- */

async function walkC22Unknown( browser ) {
	const row = {};
	for ( const lang of [ 'en', 'de' ] ) {
		const { context, page } = await newPage( browser, lang, 'C22-unknown' );
		try {
			await openConfigurator( page, lang );
			const answer = await calculate( page, UNKNOWN_PLZ );
			await page.locator( '.linker-empty--error' ).waitFor( {
				state: 'visible',
				timeout: 30000,
			} );
			row[ lang ] = {
				answer: {
					status: answer.status,
					body: answer.body,
					requestUrl: answer.requestUrl,
					ms: answer.ms,
				},
				copy: await page
					.locator( '.linker-empty--error' )
					.innerText()
					.then( ( text ) => text.replace( /\s+/g, ' ' ).trim() ),
				retry: await page.evaluate( () =>
					[
						...document.querySelectorAll(
							'.linker-empty--error button'
						),
					].map( ( button ) => button.innerText.trim() )
				),
				expected: EXPECTED.unknownPlz[ lang ],
				shots: await shoot(
					page,
					`c22-unknown-plz-${ lang }`,
					'.linker-empty--error'
				),
			};
		} finally {
			await context.close();
		}
	}
	record.rows.C22 = record.rows.C22 || {};
	record.rows.C22.unknownPostcode = row;
	writeRecord();
}

async function startStub() {
	const child = spawn(
		'python3',
		[ '-I', join( here, 'stub503.py' ), String( STUB_PORT ) ],
		{ stdio: [ 'ignore', 'pipe', 'pipe' ] }
	);
	const lines = [];
	child.stdout.on( 'data', ( chunk ) => {
		lines.push(
			...String( chunk )
				.split( '\n' )
				.map( ( line ) => line.trim() )
				.filter( Boolean )
		);
	} );
	child.stderr.on( 'data', ( chunk ) => {
		lines.push( `stderr: ${ String( chunk ).trim() }` );
	} );
	for ( let attempt = 0; attempt < 50; attempt++ ) {
		try {
			const response = await fetch( `http://127.0.0.1:${ STUB_PORT }/health` );
			if ( response.ok ) {
				break;
			}
		} catch {
			// Not listening yet.
		}
		await sleep( 100 );
	}
	return { child, lines };
}

async function walkC22Unavailable( browser ) {
	const before = runWp( [ 'option', 'get', 'linker_engine_url' ] );
	const stub = await startStub();
	record.rows.C22 = record.rows.C22 || {};
	record.rows.C22.yield503 = {
		optionBefore: before,
		stub: {
			script: 'stub503.py',
			port: STUB_PORT,
			answer: 'POST /design/residential -> 503 detail.error=yield_unavailable',
		},
		languages: {},
	};
	try {
		const during = runWp( [
			'option',
			'update',
			'linker_engine_url',
			`http://127.0.0.1:${ STUB_PORT }`,
		] );
		record.rows.C22.yield503.optionDuring = {
			update: during,
			value: runWp( [ 'option', 'get', 'linker_engine_url' ] ),
		};
		for ( const lang of [ 'en', 'de' ] ) {
			const { context, page } = await newPage(
				browser,
				lang,
				'C22-yield-503'
			);
			try {
				await openConfigurator( page, lang );
				const answer = await calculate( page, KNOWN_PLZ[ lang ] );
				await page.locator( '.linker-empty--error' ).waitFor( {
					state: 'visible',
					timeout: 30000,
				} );
				record.rows.C22.yield503.languages[ lang ] = {
					answer: {
						status: answer.status,
						body: answer.body,
						requestUrl: answer.requestUrl,
						ms: answer.ms,
					},
					copy: await page
						.locator( '.linker-empty--error' )
						.innerText()
						.then( ( text ) =>
							text.replace( /\s+/g, ' ' ).trim()
						),
					expected: EXPECTED.yieldUnavailable[ lang ],
					shots: await shoot(
						page,
						`c22-yield-503-${ lang }`,
						'.linker-empty--error'
					),
				};
			} finally {
				await context.close();
			}
		}
	} finally {
		const restored = runWp( [
			'option',
			'update',
			'linker_engine_url',
			ENGINE,
		] );
		record.rows.C22.yield503.optionAfter = {
			update: restored,
			value: runWp( [ 'option', 'get', 'linker_engine_url' ] ),
		};
		stub.child.kill( 'SIGTERM' );
		await sleep( 300 );
		record.rows.C22.yield503.stub.requests = stub.lines.filter( ( line ) =>
			line.includes( 'POST /design/residential' )
		).length;
		record.rows.C22.yield503.stub.log = stub.lines;
		writeRecord();
	}
}

/* C28 ------------------------------------------------------------------- */

async function runAddCase( page, mode, lines, expectedStates, shortReads ) {
	const fullItems = lines.map( ( line ) => ( {
		id: line.id,
		quantity: line.quantity,
		key: `stub-${ line.id }`,
	} ) );
	const shortItems = fullItems
		.map( ( item ) => ( { ...item, quantity: item.quantity - 1 } ) )
		.filter( ( item ) => item.quantity > 0 );
	// Mixed: the first line's write fails, the second lands; the readback
	// shows only the second, so one card is retry and one added while the
	// order is partial — the inventory's "only part written" input.
	const failedId = lines[ 0 ]?.id;
	const mixedItems = fullItems.filter( ( item ) => item.id !== failedId );
	const observed = { addPosts: 0, cartReads: [] };
	const addHandler = async ( route ) => {
		observed.addPosts += 1;
		let body = {};
		try {
			body = JSON.parse( route.request().postData() || '{}' );
		} catch {
			body = {};
		}
		const fails =
			mode === 'retry' || ( mode === 'mixed' && body.id === failedId );
		if ( fails ) {
			return route.fulfill( {
				status: 500,
				contentType: 'application/json',
				body: JSON.stringify( {
					code: 'stub_500',
					message: 'injected Store API 500',
				} ),
			} );
		}
		return route.fulfill( {
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify( { items: [] } ),
		} );
	};
	const cartHandler = async ( route ) => {
		if ( route.request().method() !== 'GET' ) {
			return route.continue();
		}
		observed.cartReads.push( Date.now() );
		if ( mode === 'retry' ) {
			return route.continue();
		}
		const read = observed.cartReads.length;
		if ( read === 1 ) {
			return route.continue();
		}
		const short = mode === 'short' && read - 1 <= shortReads;
		return route.fulfill( {
			status: 200,
			contentType: 'application/json',
			headers: { Nonce: 'stub-nonce' },
			body: JSON.stringify( {
				items:
					mode === 'mixed'
						? mixedItems
						: short
							? shortItems
							: fullItems,
			} ),
		} );
	};
	await page.route( '**/wc/store/v1/cart/add-item', addHandler );
	await page.route( '**/wc/store/v1/cart', cartHandler );
	try {
		await page.getByRole( 'button', { name: ADD_RE } ).click();
		await page.waitForTimeout( 60 );
		await page
			.waitForFunction(
				( expected ) => {
					const cards = [
						...document.querySelectorAll( '.linker-card' ),
					];
					return (
						cards.length > 0 &&
						cards.every( ( card ) =>
							expected.includes( card.dataset.state )
						)
					);
				},
				expectedStates,
				{ timeout: 20000 }
			)
			.catch( () => {} );
		// The card states land while "Add all" is still busy; the order's own
		// message (complete / partial) renders when the click has finished.
		await page
			.waitForFunction(
				() => {
					const button = document.querySelector(
						'.linker-actions button'
					);
					return button && ! button.disabled;
				},
				null,
				{ timeout: 10000 }
			)
			.catch( () => {} );
		await page.waitForTimeout( 100 );
	} finally {
		await page.unroute( '**/wc/store/v1/cart/add-item', addHandler );
		await page.unroute( '**/wc/store/v1/cart', cartHandler );
	}
	const gaps = observed.cartReads
		.slice( 1 )
		.map( ( time, index, all ) => time - all[ index - 1 ] )
		.slice( 1 );
	return {
		mode,
		cardStates: await cardStates( page ),
		action: await actionState( page ),
		addPosts: observed.addPosts,
		cartReads: observed.cartReads.length,
		postAddReads: Math.max( 0, observed.cartReads.length - 1 ),
		postAddGapsMs: gaps,
	};
}

async function walkC28( browser ) {
	const row = {};
	const settle = sourceConstants();
	record.settle = settle;
	for ( const lang of [ 'en', 'de' ] ) {
		const { context, page } = await newPage( browser, lang, 'C28' );
		try {
			await openConfigurator( page, lang );
			const design = await calculate( page, KNOWN_PLZ[ lang ] );
			await page.locator( '.linker-cards' ).waitFor( {
				state: 'visible',
				timeout: 30000,
			} );
			const lines = ( design.body?.selected?.lines || [] )
				.filter(
					( line ) => line.product && Number.isInteger( line.product.id )
				)
				.map( ( line ) => ( {
					id: line.product.id,
					model: line.product.model || '',
					quantity: line.quantity,
				} ) );
			const cases = {};

			const retry = await runAddCase(
				page,
				'retry',
				lines,
				[ 'retry' ],
				0
			);
			cases.retry = {
				...retry,
				expectedCard: EXPECTED.addRetry[ lang ],
				expectedOrder: EXPECTED.orderPartial[ lang ],
				shots: await shoot(
					page,
					`c28-add-retry-${ lang }`,
					'.linker-actions'
				),
			};

			const mixed = await runAddCase(
				page,
				'mixed',
				lines,
				[ 'retry', 'added' ],
				0
			);
			cases.mixed = {
				...mixed,
				expectedCard: null,
				expectedOrder: EXPECTED.orderPartial[ lang ],
				shots: await shoot(
					page,
					`c28-add-mixed-${ lang }`,
					'.linker-actions'
				),
			};

			const unverified = await runAddCase(
				page,
				'short',
				lines,
				[ 'unverified' ],
				99
			);
			cases.unverified = {
				...unverified,
				expectedCard: EXPECTED.addUnverified[ lang ],
				expectedOrder: EXPECTED.orderPartial[ lang ],
				shots: await shoot(
					page,
					`c28-add-unverified-${ lang }`,
					'.linker-actions'
				),
			};

			const settled = await runAddCase(
				page,
				'short',
				lines,
				[ 'added' ],
				settle.settleReads
			);
			cases.settled = {
				...settled,
				expectedCard: null,
				expectedOrder: EXPECTED.orderComplete[ lang ],
				shots: await shoot(
					page,
					`c28-add-settled-${ lang }`,
					'.linker-actions'
				),
			};

			row[ lang ] = { designStatus: design.status, lines, cases };
		} finally {
			await context.close();
		}
	}
	record.rows.C28 = row;
	writeRecord();
}

/* C31 ------------------------------------------------------------------- */

async function walkC31( browser ) {
	const row = {};
	for ( const lang of [ 'en', 'de' ] ) {
		const { context, page } = await newPage( browser, lang, 'C31' );
		try {
			await openConfigurator( page, lang );
			const design = await calculate( page, KNOWN_PLZ[ lang ] );
			await page.locator( '.linker-cards' ).waitFor( {
				state: 'visible',
				timeout: 30000,
			} );
			const handler = async ( route ) =>
				route.fulfill( {
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify( {
						code: 'stub_500',
						message: 'injected save failure',
					} ),
				} );
			await page.route( '**/linker/v1/solutions*', handler );
			let saveRequest = '';
			let saveStatus = 0;
			try {
				const requestWait = page.waitForRequest(
					( request ) =>
						request.url().includes( '/linker/v1/solutions' ) &&
						request.method() === 'POST',
					{ timeout: 30000 }
				);
				const responseWait = page.waitForResponse(
					( response ) =>
						response.url().includes( '/linker/v1/solutions' ) &&
						response.request().method() === 'POST',
					{ timeout: 60000 }
				);
				await page
					.getByRole( 'button', { name: SAVE_RE } )
					.click();
				saveRequest = ( await requestWait ).url();
				saveStatus = ( await responseWait ).status();
				await page.waitForFunction(
					( expected ) =>
						(
							document.querySelector( '.linker-actions__status' )
								?.innerText || ''
						).includes( expected ),
					EXPECTED.saveFailed[ lang ],
					{ timeout: 30000 }
				);
			} finally {
				await page.unroute( '**/linker/v1/solutions*', handler );
			}
			row[ lang ] = {
				designStatus: design.status,
				saveRequest,
				saveStatus,
				action: await actionState( page ),
				expected: EXPECTED.saveFailed[ lang ],
				shots: await shoot(
					page,
					`c31-save-failed-${ lang }`,
					'.linker-actions'
				),
			};
		} finally {
			await context.close();
		}
	}
	record.rows.C31 = row;
	writeRecord();
}

/* C57 ------------------------------------------------------------------- */

async function walkC57( browser ) {
	const row = {};
	for ( const lang of [ 'en', 'de' ] ) {
		const { context, page } = await newPage( browser, lang, 'C57' );
		try {
			await openConfigurator( page, lang );
			const design = await calculate( page, KNOWN_PLZ[ lang ] );
			await page.locator( '.linker-cards' ).waitFor( {
				state: 'visible',
				timeout: 30000,
			} );
			const facts = await page.evaluate( ( sentence ) => {
				const section = document.querySelector(
					'#linker-report-assumptions'
				)?.parentElement;
				return {
					heading:
						section
							?.querySelector( 'h4' )
							?.innerText.trim() || '',
					paragraphs: [
						...( section?.querySelectorAll( 'p' ) || [] ),
					].map( ( p ) => p.innerText.replace( /\s+/g, ' ' ).trim() ),
					hasSentence: ( section?.innerText || '' ).includes(
						sentence
					),
				};
			}, EXPECTED.orientation[ lang ] );
			const target = page
				.locator( 'p', {
					hasText: EXPECTED.orientation[ lang ].slice( 0, 40 ),
				} )
				.first();
			row[ lang ] = {
				designStatus: design.status,
				requestKeys: Object.keys( design.postData || {} ),
				requestHasPlanes: Object.hasOwn(
					design.postData || {},
					'planes'
				),
				reportSections: ( design.body?.report?.sections || [] ).map(
					( section ) => section.id
				),
				expected: EXPECTED.orientation[ lang ],
				facts,
				shots: await shoot(
					page,
					`c57-report-orientation-${ lang }`,
					target
				),
			};
		} finally {
			await context.close();
		}
	}
	record.rows.C57 = row;
	writeRecord();
}

/* C30 ------------------------------------------------------------------- */

async function walkC30( browser ) {
	const row = { guest: {}, claim: {}, session: {}, cleanup: {} };
	const { context, page } = await newPage( browser, 'en', 'C30' );
	try {
		for ( const lang of [ 'en', 'de' ] ) {
			await openConfigurator( page, lang );
			const design = await calculate( page, KNOWN_PLZ[ lang ] );
			await page.locator( '.linker-cards' ).waitFor( {
				state: 'visible',
				timeout: 30000,
			} );
			await page.getByRole( 'button', { name: ADD_RE } ).click();
			await page.waitForFunction(
				( expected ) =>
					(
						document.querySelector( '.linker-actions__status' )
							?.innerText || ''
					).includes( expected ),
				EXPECTED.orderComplete[ lang ],
				{ timeout: 60000 }
			);
			const before = await context.cookies();
			const requestWait = page.waitForRequest(
				( request ) =>
					request.url().includes( '/linker/v1/solutions' ) &&
					request.method() === 'POST',
				{ timeout: 30000 }
			);
			const responseWait = page.waitForResponse(
				( response ) =>
					response.url().includes( '/linker/v1/solutions' ) &&
					response.request().method() === 'POST',
				{ timeout: 90000 }
			);
			await page.getByRole( 'button', { name: SAVE_RE } ).click();
			const request = await requestWait;
			const response = await responseWait;
			const answer = await response.json().catch( () => null );
			const headers = await response.allHeaders();
			await page.waitForFunction(
				( expected ) =>
					(
						document.querySelector( '.linker-actions__status' )
							?.innerText || ''
					).includes( expected ),
				EXPECTED.saved[ lang ],
				{ timeout: 30000 }
			);
			const after = await context.cookies();
			const woo = ( cookies ) =>
				cookies
					.filter(
						( cookie ) =>
							/^wp_woocommerce_session_|^woocommerce_cart_hash$|^woocommerce_items_in_cart$/.test(
								cookie.name
							)
					)
					.map( ( cookie ) => ( {
						name: cookie.name.replace(
							/^wp_woocommerce_session_.*$/,
							'wp_woocommerce_session_*'
						),
						domain: cookie.domain,
						path: cookie.path,
						expires: cookie.expires,
					} ) );
			row.guest[ lang ] = {
				designStatus: design.status,
				lines: ( design.body?.selected?.lines || [] )
					.filter( ( line ) => line.product )
					.map( ( line ) => ( {
						id: line.product.id,
						model: line.product.model,
						quantity: line.quantity,
					} ) ),
				saveRequest: request.url(),
				saveStatus: response.status(),
				saveAnswer: answer,
				setCookieHeader:
					headers[ 'set-cookie' ] ||
					headers[ 'Set-Cookie' ] ||
					null,
				cookiesBefore: woo( before ),
				cookiesAfter: woo( after ),
				action: await actionState( page ),
				expected: EXPECTED.saved[ lang ],
				shots: await shoot(
					page,
					`c30-guest-saved-${ lang }`,
					'.linker-actions__status'
				),
			};
		}

		row.cleanup.draft = await emptyDraft( page );
		row.session.beforeLogin = {
			kept: runWp( [
				'db',
				'query',
				"SELECT COUNT(*) FROM wp_woocommerce_sessions WHERE session_value LIKE '%linker_saved_solutions%'",
				'--skip-column-names',
			] ),
			en: runWp( [
				'db',
				'query',
				"SELECT COUNT(*) FROM wp_woocommerce_sessions WHERE session_value LIKE '%80538%'",
				'--skip-column-names',
			] ),
			de: runWp( [
				'db',
				'query',
				"SELECT COUNT(*) FROM wp_woocommerce_sessions WHERE session_value LIKE '%80331%'",
				'--skip-column-names',
			] ),
		};

		if ( LOGIN_URL ) {
			await page.goto( LOGIN_URL, {
				waitUntil: 'domcontentloaded',
				timeout: 60000,
			} );
			row.claim.loginLanding = page.url();
			await page.waitForTimeout( 800 );
			row.claim.languages = {};
			for ( const lang of [ 'en', 'de' ] ) {
				await page.goto( ORIGIN + ACCOUNT[ lang ], {
					waitUntil: 'domcontentloaded',
					timeout: 60000,
				} );
				await dismissConsent( page );
				await quiet( page );
				await page.waitForTimeout( 1200 );
				row.claim.languages[ lang ] = {
					page: await solutionsOnPage( page ),
					shots: await shoot(
						page,
						`c30-claimed-${ lang }`,
						'.linker-account-solution'
					),
				};
			}
			row.session.afterClaim = {
				kept: runWp( [
					'db',
					'query',
					"SELECT COUNT(*) FROM wp_woocommerce_sessions WHERE session_value LIKE '%linker_saved_solutions%'",
					'--skip-column-names',
				] ),
			};
		} else {
			row.claim = { skipped: 'no one-time login URL passed' };
		}
	} finally {
		await context.close();
	}

	// Delete this walk's test user and the solutions the claim created.
	try {
		const userId = runWp( [ 'user', 'get', USER, '--field=ID' ] );
		row.cleanup.userId = userId;
		const ids = runWp( [
			'post',
			'list',
			'--post_type=linker_solution',
			`--author=${ userId }`,
			'--format=ids',
		] );
		row.cleanup.solutionIds = ids;
		if ( ids ) {
			row.cleanup.deletedSolutions = ids
				.split( /\s+/ )
				.map( ( id ) =>
					runWp( [ 'post', 'delete', id, '--force' ] )
				);
		}
		row.cleanup.solutionsRemaining = runWp( [
			'post',
			'list',
			'--post_type=linker_solution',
			`--author=${ userId }`,
			'--format=count',
		] );
		row.cleanup.deletedUser = runWp( [ 'user', 'delete', userId, '--yes' ] );
		row.cleanup.userGone =
			runWp( [
				'db',
				'query',
				`SELECT COUNT(*) FROM wp_users WHERE user_login = '${ USER }'`,
				'--skip-column-names',
			] ) === '0';
	} catch ( failure ) {
		row.cleanup.error = String(
			failure && failure.message ? failure.message : failure
		);
	}

	record.rows.C30 = row;
	writeRecord();
}

/* main ------------------------------------------------------------------ */

const browser = await chromium.launch();
try {
	record.instance = { before: instanceCounts() };
	const instance = await newPage( browser, 'en', 'environment' );
	try {
		record.environment = { pages: {} };
		for ( const lang of [ 'en', 'de' ] ) {
			const status = await openConfigurator( instance.page, lang );
			if ( lang === 'en' ) {
				record.build = await buildFacts( instance.page );
			}
			record.environment.pages[ lang ] =
				await instance.page.evaluate( () => ( {
					url: location.href,
					lang: document.documentElement.lang,
					mount: !! document.querySelector(
						'[data-linker-app="configurator"]'
					),
					viewport: {
						width: window.innerWidth,
						height: window.innerHeight,
					},
				} ) );
			record.environment.pages[ lang ].status = status;
		}
	} finally {
		await instance.context.close();
	}
	record.gazetteer = gazetteerFacts();
	writeRecord();

	await walkC08( browser );
	await walkC22Unknown( browser );
	await walkC22Unavailable( browser );
	await walkC28( browser );
	await walkC31( browser );
	await walkC57( browser );
	await walkC30( browser );

	record.instance.after = instanceCounts();
	record.instance.engineOption = runWp( [
		'option',
		'get',
		'linker_engine_url',
	] );
	const before = record.instance.before;
	const after = record.instance.after;
	const counterKeys = [ 'orders', 'mailFiles', 'solutions', 'customers' ];
	record.assertions = {
		noForbiddenPosts: record.forbiddenPosts.length === 0,
		countersNumeric: counterKeys.every(
			( key ) =>
				Number.isFinite( before[ key ] ) &&
				Number.isFinite( after[ key ] )
		),
		mailReadable: before.mailFiles >= 0 && after.mailFiles >= 0,
		mailUnchanged: before.mailFiles === after.mailFiles,
		ordersUnchanged: before.orders === after.orders,
		solutionsUnchanged: before.solutions === after.solutions,
		customersUnchanged: before.customers === after.customers,
		engineOptionRestored: record.instance.engineOption === ENGINE,
	};
	const failed = Object.entries( record.assertions )
		.filter( ( [ , passes ] ) => ! passes )
		.map( ( [ name ] ) => name );
	if ( failed.length > 0 ) {
		throw new Error( `walk assertions failed: ${ failed.join( ', ' ) }` );
	}
} finally {
	record.finishedAt = new Date().toISOString();
	writeRecord();
	await browser.close();
}

console.log( JSON.stringify( record, null, 2 ) );
