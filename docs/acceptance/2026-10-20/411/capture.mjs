/**
 * #411's failure states, captured on a local instance with the live snapshot.
 *
 * The four states the ticket names:
 *   upstream  - a 502 after the question, question back in the field, Try again
 *   truncated - a stream without `done`, question in the thread, file chip kept
 *   omitted-single, omitted-plural - the reload record names the files the
 *               tab could not keep
 *
 * Every state is reached through the shipped code: the two live turns go
 * through the real dock and its turn route (intercepted with Playwright, as
 * the campaign harness does), the omitted-file notices come from a record
 * sessionStorage cannot hold, seeded before the page loads.
 *
 *   node capture.mjs --wp http://127.0.0.1:<port> [--out <dir>]
 *
 * The output directory is this one by default. Playwright is loaded from
 * tests/e2e's node_modules.
 */
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname( fileURLToPath( import.meta.url ) );

const args = process.argv.slice( 2 );
let WP = 'http://127.0.0.1:9215';
let OUT = here;
for ( let i = 0; i < args.length; i += 1 ) {
	if ( args[ i ] === '--wp' ) {
		WP = args[ i + 1 ];
		i += 1;
	} else if ( args[ i ] === '--out' ) {
		OUT = args[ i + 1 ];
		i += 1;
	}
}
mkdirSync( OUT, { recursive: true } );

const playwrightPkg = join( here, '../../../../tests/e2e/package.json' );
const { chromium } = createRequire( playwrightPkg )( 'playwright' );

const WIDTHS = [
	{ name: '1440', width: 1440, height: 900 },
	{ name: '390', width: 390, height: 844 },
];
const LANGS = [
	{ name: 'en', path: '/' },
	{ name: 'de', path: '/de/' },
];

const COPY = {
	en: {
		failure: 'Genie did not answer. Please try again.',
		single:
			'Attach datasheet.pdf again. It could not be kept for another try.',
		plural:
			'Attach these files again. They could not be kept for another try.',
		retry: 'Try again',
		question: 'Which wallbox fits?',
	},
	de: {
		failure: 'Genie hat nicht geantwortet. Bitte versuchen Sie es erneut.',
		single:
			'Bitte hängen Sie datasheet.pdf erneut an. Die Datei konnte für einen weiteren Versuch nicht gespeichert werden.',
		plural:
			'Bitte hängen Sie diese Dateien erneut an. Sie konnten für einen weiteren Versuch nicht gespeichert werden.',
		retry: 'Erneut versuchen',
		question: 'Welche Wallbox passt?',
	},
};

/** The proxy's answer shape: `{ conversation_id, stream }`. */
function thread( messages = [] ) {
	return {
		conversation_id: messages.length > 0 ? 7 : 0,
		messages,
		stream: '',
	};
}

/** A stream the service never finished: no `done`. */
const TRUNCATED_STREAM =
	'event: meta\n' +
	'data: {"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n' +
	'event: block\n' +
	'data: {"type":"text","text":"This partial answer must not render.","refs":[]}\n\n';

const ATTACHMENT_PDF = Buffer.from( '%PDF-1.4\n%%EOF\n' );

function record( kind, text, question, omitted ) {
	return {
		v: 1,
		kind,
		text,
		question,
		uploads: [],
		omitted,
	};
}

const STATES = [
	{
		name: 'upstream',
		record: null,
		turn: {
			status: 502,
			body: {
				code: 'linker_genie_upstream',
				message: 'The service did not answer.',
			},
		},
		async drive( page, copy ) {
			await ask( page, copy.question );
			await page
				.locator(
					'#linker-genie-mount .linker-genie-app__error[role="alert"]'
				)
				.filter( { hasText: copy.failure } )
				.waitFor( { state: 'visible', timeout: 30000 } );
			await page
				.getByRole( 'button', { name: copy.retry } )
				.waitFor( { state: 'visible' } );
		},
	},
	{
		name: 'truncated',
		record: null,
		turn: {
			status: 200,
			body: { conversation_id: 7, stream: TRUNCATED_STREAM },
		},
		async drive( page, copy ) {
			await open( page, { attach: true } );
			const picker = page.locator(
				'#linker-genie-mount .linker-genie-app input[type="file"]'
			);
			await picker.waitFor( { state: 'attached', timeout: 30000 } );
			await picker.setInputFiles( {
				name: 'datasheet.pdf',
				mimeType: 'application/pdf',
				buffer: ATTACHMENT_PDF,
			} );
			await page
				.locator(
					'#linker-genie-mount .linker-genie-app__attachment-name'
				)
				.filter( { hasText: 'datasheet.pdf' } )
				.waitFor( { state: 'visible', timeout: 30000 } );
			const field = page.locator( '#linker-genie-mount .linker-genie-app textarea' );
			await field.fill( copy.question );
			const send = page.locator( '#linker-genie-mount .linker-genie-app__send' );
			await send.waitFor( { state: 'visible' } );
			await expectEnabled( send );
			await send.click();
			await page
				.locator(
					'#linker-genie-mount .linker-genie-app__error[role="alert"]'
				)
				.filter( { hasText: copy.failure } )
				.waitFor( { state: 'visible', timeout: 30000 } );
			await page
				.locator( '#linker-genie-mount .linker-genie-app__thread' )
				.filter( { hasText: copy.question } )
				.waitFor( { state: 'visible' } );
			const partial = await page
				.getByText( 'This partial answer must not render.' )
				.count();
			if ( partial > 0 ) {
				throw new Error( 'the truncated stream rendered a partial answer' );
			}
		},
	},
	{
		name: 'omitted-single',
		record: record(
			'upstream',
			'Check this datasheet',
			'Check this datasheet\nAttached: datasheet.pdf',
			[ 'datasheet.pdf' ]
		),
		async drive( page, copy ) {
			await open( page, { refresh: true } );
			const alert = page.locator(
				'#linker-genie-mount .linker-genie-app__error[role="alert"]'
			);
			await alert.waitFor( { state: 'visible', timeout: 30000 } );
			await alert
				.filter( { hasText: copy.single } )
				.waitFor( { state: 'visible', timeout: 30000 } );
			const field = page.locator( '#linker-genie-mount .linker-genie-app textarea' );
			await field.waitFor( { state: 'visible' } );
			if ( ( await field.inputValue() ) !== 'Check this datasheet' ) {
				throw new Error( 'the upstream record did not restore the words' );
			}
		},
	},
	{
		name: 'omitted-plural',
		record: record(
			'upstream',
			'Check these files',
			'Check these files\nAttached: datasheet.pdf\nAttached: nameplate.jpg',
			[ 'datasheet.pdf', 'nameplate.jpg' ]
		),
		async drive( page, copy ) {
			await open( page, { refresh: true } );
			const alert = page.locator(
				'#linker-genie-mount .linker-genie-app__error[role="alert"]'
			);
			await alert.waitFor( { state: 'visible', timeout: 30000 } );
			await alert
				.filter( { hasText: copy.plural } )
				.waitFor( { state: 'visible', timeout: 30000 } );
			// The plural notice does not list the names.
			const text = await alert.innerText();
			if ( text.includes( 'datasheet.pdf' ) || text.includes( 'nameplate.jpg' ) ) {
				throw new Error( 'the plural notice lists names' );
			}
		},
	},
];

async function open( page, detail ) {
	await page.evaluate(
		( payload ) =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-ask', { detail: payload } )
			),
		detail
	);
	await page
		.locator( '#linker-genie-mount .linker-genie-app textarea' )
		.waitFor( { state: 'visible', timeout: 30000 } );
}

async function ask( page, message ) {
	await page.evaluate(
		( text ) =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-ask', {
					detail: { message: text },
				} )
			),
		message
	);
	await page
		.locator( '#linker-genie-mount .linker-genie-app textarea' )
		.waitFor( { state: 'attached', timeout: 30000 } );
}

async function expectEnabled( locator ) {
	for ( let i = 0; i < 50; i += 1 ) {
		if ( await locator.isEnabled() ) {
			return;
		}
		await new Promise( ( resolve ) => setTimeout( resolve, 200 ) );
	}
	throw new Error( 'the send button never armed' );
}

/**
 * The live site's cookie banner would cover the dock in every screenshot.
 * Accepting it is what a visitor does before using the page.
 *
 * @param page The page.
 */
async function dismissConsent( page ) {
	const accept = page.locator( '[data-cky-tag="accept-button"]' );
	try {
		await accept.waitFor( { state: 'visible', timeout: 5000 } );
		await accept.evaluate( ( button ) => button.click() );
		await page
			.locator( '.cky-consent-container' )
			.waitFor( { state: 'hidden', timeout: 5000 } );
	} catch {
		// A later visit in the same context: the choice is already stored.
	}
}

async function main() {
	const browser = await chromium.launch( { headless: true } );
	const written = [];
	try {
		for ( const state of STATES ) {
			for ( const lang of LANGS ) {
				for ( const viewport of WIDTHS ) {
					const context = await browser.newContext( {
						viewport: {
							width: viewport.width,
							height: viewport.height,
						},
					} );
					const page = await context.newPage();
					await page.route(
						'**/wp-json/linker-ai/v1/genie/conversation',
						( route ) =>
							route.fulfill( {
								status: 200,
								contentType: 'application/json',
								body: JSON.stringify( thread() ),
							} )
					);
					await page.route(
						'**/wp-json/linker-ai/v1/genie/conversations',
						( route ) =>
							route.fulfill( {
								status: 200,
								contentType: 'application/json',
								body: JSON.stringify( {
									current_id: 0,
									conversations: [],
								} ),
							} )
					);
					if ( state.turn ) {
						await page.route(
							'**/wp-json/linker-ai/v1/genie/turn',
							( route ) =>
								route.fulfill( {
									status: state.turn.status,
									contentType: 'application/json',
									body: JSON.stringify( state.turn.body ),
								} )
						);
					}
					if ( state.record ) {
						await page.addInitScript( ( stored ) => {
							window.sessionStorage.setItem(
								'linker-genie-turn-failure',
								JSON.stringify( stored )
							);
						}, state.record );
					}
					await page.goto( WP + lang.path, {
						waitUntil: 'domcontentloaded',
						timeout: 60000,
					} );
					await dismissConsent( page );
					await page.evaluate( () => document.fonts.ready );
					await state.drive( page, COPY[ lang.name ] );
					await page.waitForTimeout( 300 );
					const file = join(
						OUT,
						`live-${ state.name }-${ viewport.name }-${ lang.name }.png`
					);
					await page.screenshot( { path: file } );
					written.push( file );
					await context.close();
				}
			}
		}
	} finally {
		await browser.close();
	}
	console.log( written.join( '\n' ) );
}

await main();
