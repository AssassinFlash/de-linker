// @vitest-environment jsdom
/** Actual ordinary producers; native identity, history and model HTTP are explicit fixtures. */
import {
	act,
	fireEvent,
	render,
	screen,
	waitFor,
	cleanup,
} from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { App, resetTurnLane } from './App';
import { readConfig, type GenieConfig } from './config';
import { sendTurn, TurnError } from './api/turn';
import { FailureJournal, failureBucketKey } from './shared/ownedFailure';
import { rememberEntry, ENTRY_KEY } from './shared/entryDraft';
import { startHero } from '../hero/controller';
vi.mock( './api/turn', async ( original ) => {
	const actual = await original< typeof import( './api/turn' ) >();
	return { ...actual, sendTurn: vi.fn() };
} );
const CONFIG: GenieConfig = {
	surface: 'helper',
	locale: 'en',
	pageType: 'home',
	productId: 0,
	turnUrl: '/wp-json/linker-ai/v1/genie/turn',
	threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
	conversationsUrl: '/wp-json/linker-ai/v1/genie/conversations',
	voteUrl: '/wp-json/linker-ai/v1/genie/turn',
	restUrl: '/wp-json/',
	restNonce: 'n',
	disclosure: 'You are chatting with an AI system.',
	accountUrl: '/my-account/',
	workspaceUrl: '/genie/',
	prompts: [],
	page: { type: 'home', url: '/', title: 'Home page' },
	signedIn: false,
	retentionDays: 90,
	mailStarted: '100.sig',
	mailStartedNonce: 'sig',
	contactUrl: '/wp-json/linker-ai/v1/genie/contact',
	inquiryUrl: '/wp-json/linker-ai/v1/genie/inquiry',
};

const HERO = `
<section class="hero-cinematic">
  <div class="hero-stage">
    <p class="hero-badge">Solar &amp; battery storage</p>
    <h1 class="hero-title">Linking Value.</h1>
    <p class="hero-subtitle">We link storage systems.</p>
    <div class="hero-dialog">
      <textarea class="hero-prompt" placeholder="Search equipment models, battery pairings, or datasheets..." rows="2"></textarea>
      <div class="hero-dialog-footer">
        <button type="button" data-linker-assistant-open="nameplate">Identify by nameplate photo</button>
        <button type="button" data-linker-assistant-open="attach">Attach</button>
        <button type="button" data-linker-assistant-open="voice">Voice</button>
        <a class="hero-send" href="/linker-advisor/">Send</a>
      </div>
    </div>
    <div class="hero-capsules">
      <a class="hero-capsule" href="/linker-advisor/">10 kW storage systems</a>
    </div>
    <p class="hero-footnote">On file.</p>
  </div>
</section>`;

let principal = 'A';
let rejected = false;
let scopeUnavailable = false;
let stop = () => {};
const text = 'Private A engineering quotation';
const fileText = '%PDF-1.4\nPRIVATE-A-BOM-COSTS';
const filename = 'A-private-costs.pdf';
const captures: Array< {
	principal: string;
	request: Parameters< typeof sendTurn >[ 0 ];
} > = [];
beforeEach( () => {
	sessionStorage.clear();
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	resetTurnLane();
	principal = 'A';
	rejected = false;
	scopeUnavailable = false;
	captures.length = 0;
	vi.mocked( sendTurn )
		.mockReset()
		.mockImplementation( async ( request ) => {
			captures.push( { principal, request } );
			if ( principal === 'A' ) {
				throw new Error( 'upstream' );
			}
			return {
				meta: null,
				blocks: [
					{
						type: 'text',
						text: 'Answer for current principal',
						refs: [],
					},
				],
				done: true,
			};
		} );
	vi.stubGlobal(
		'fetch',
		vi.fn( async ( url ) => {
			if (
				String( url ).includes( 'entry-context' ) &&
				scopeUnavailable
			) {
				return { ok: false, status: 503 };
			}
			if ( String( url ).includes( 'entry-context' ) ) {
				return {
					ok: true,
					json: async () => ( {
						scope: (
							{ A: 'a', B: 'b' }[ principal ] ?? 'c'
						).repeat( 64 ),
					} ),
				};
			}
			if ( String( url ).endsWith( '/conversations' ) ) {
				return {
					ok: true,
					json: async () => ( { conversations: [], current_id: 0 } ),
				};
			}
			return rejected
				? { ok: false, status: 403 }
				: {
						ok: true,
						json: async () => ( { messages: [], stream: '' } ),
					};
		} )
	);
} );
afterEach( () => {
	stop();
	cleanup();
	document.body.innerHTML = '';
	sessionStorage.clear();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieNativeScope;
	resetTurnLane();
} );
function config() {
	const mount = document.createElement( 'div' );
	mount.dataset.surface = 'workspace';
	mount.dataset.restNonce = 'nonce-' + principal;
	return readConfig( mount );
}
function workspace() {
	document.body.innerHTML = '';
	const ui = render( <App config={ config() } /> );
	return {
		field: () =>
			screen.getByRole< HTMLTextAreaElement >( 'textbox', {
				name: 'Ask Genie',
			} ),
		stop: () => ui.unmount(),
	};
}
function dock() {
	document.body.innerHTML = '';
	const ui = render( <App config={ { ...config(), surface: 'helper' } } /> );
	act( () => window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) ) );
	return {
		field: () =>
			screen.getByRole< HTMLTextAreaElement >( 'textbox', {
				name: 'Ask Genie',
			} ),
		stop: () => ui.unmount(),
	};
}

function home() {
	document.body.innerHTML = HERO;
	const hero = document.querySelector< HTMLElement >( '.hero-cinematic' )!;
	const end = startHero( hero, {
		config: { ...CONFIG, restNonce: 'nonce-' + principal },
	} );
	return {
		field: () =>
			hero.querySelector< HTMLTextAreaElement >( '.hero-prompt' )!,
		stop: end,
	};
}

async function restoreRetainedDraft() {
	const button = await screen.findByRole( 'button', {
		name: 'Restore unsent draft',
	} );
	await act( async () => fireEvent.click( button ) );
}
async function verifyReturnedEditorExchange(
	field: () => HTMLTextAreaElement
) {
	await restoreRetainedDraft();
	expect( field().value ).toBe( 'A1 submitted original' );
	await restoreRetainedDraft();
	expect( field().value ).toBe( 'A2 newly accepted question' );
	expect(
		document.querySelector( '.linker-genie-app__attachment' )?.textContent
	).toContain( filename );
}
async function finishImmediateConsumerWork() {
	await act( async () => {} );
}
async function tryOnlyVisibleRecovery() {
	const retry = screen.queryByRole( 'button', { name: 'Try again' } );
	if ( retry ) {
		await act( async () => fireEvent.click( retry ) );
	}
}
function expectCurrentNativeScopeWasRead() {
	expect(
		vi
			.mocked( fetch )
			.mock.calls.some(
				( [ url, options ] ) =>
					String( url ).includes( 'entry-context' ) &&
					new Headers( options?.headers ).get( 'X-WP-Nonce' ) ===
						'nonce-' + principal
			)
	).toBe( true );
}
for ( const surface of [ 'workspace', 'home' ] as const ) {
	for ( const next of [ 'B', 'guest' ] as const ) {
		for ( const blocked of [ false, true ] ) {
			test( `ordinary text stays with its owner: ${ surface } A→${ next }, ${ blocked ? '403' : 'empty' } history`, async () => {
				let ui = surface === 'workspace' ? workspace() : home();
				stop = ui.stop;
				if ( surface === 'workspace' ) {
					act( () =>
						window.dispatchEvent(
							new CustomEvent( 'linker-genie-open' )
						)
					);
				}
				await finishImmediateConsumerWork();
				fireEvent.input( ui.field(), { target: { value: text } } );
				await act( async () =>
					fireEvent.click(
						surface === 'home'
							? document.querySelector( '.hero-send' )!
							: screen.getByRole( 'button', { name: 'Send' } )
					)
				);
				await screen.findByText(
					'Genie did not answer. Please try again.'
				);
				expect( captures ).toHaveLength( 1 );
				ui.stop();
				cleanup();
				resetTurnLane();
				principal = next;
				rejected = blocked;
				ui = surface === 'workspace' ? workspace() : home();
				stop = ui.stop;
				await finishImmediateConsumerWork();
				expect( ui.field().value ).toBe( '' );
				expect( document.body.textContent ).not.toContain( text );
				await tryOnlyVisibleRecovery();
				expect( captures ).toHaveLength( 1 );
				expectCurrentNativeScopeWasRead();
			} );
		}
	}
}
for ( const target of [ 'workspace', 'home' ] as const ) {
	for ( const blocked of [ false, true ] ) {
		test( `ordinary prepared PDF stays with its owner: home A→${ target } guest, ${ blocked ? '403' : 'empty' } history`, async () => {
			let ui = home();
			stop = ui.stop;
			await finishImmediateConsumerWork();
			const file = new File( [ fileText ], filename, {
				type: 'application/pdf',
			} );
			await act( async () =>
				fireEvent.change(
					document.querySelector( 'input[type=file]' )!,
					{ target: { files: [ file ] } }
				)
			);
			await screen.findByText(
				'Genie did not answer. Please try again.'
			);
			expect( captures ).toHaveLength( 1 );
			expect( captures[ 0 ]!.request.uploads![ 0 ]!.name ).toBe(
				filename
			);
			expect( atob( captures[ 0 ]!.request.uploads![ 0 ]!.data ) ).toBe(
				fileText
			);
			ui.stop();
			cleanup();
			resetTurnLane();
			principal = 'guest';
			rejected = blocked;
			ui = target === 'workspace' ? workspace() : home();
			stop = ui.stop;
			await finishImmediateConsumerWork();
			expect( ui.field().value ).not.toContain( filename );
			expect( document.body.textContent ).not.toContain( filename );
			await tryOnlyVisibleRecovery();
			expect( captures ).toHaveLength( 1 );
			expectCurrentNativeScopeWasRead();
		} );
	}
}

async function askWorkspace( question: string ) {
	await waitFor( () =>
		expect(
			screen.getByRole< HTMLTextAreaElement >( 'textbox', {
				name: 'Ask Genie',
			} ).disabled
		).toBe( false )
	);
	fireEvent.change( screen.getByRole( 'textbox', { name: 'Ask Genie' } ), {
		target: { value: question },
	} );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
}
const answer = {
	meta: null,
	blocks: [
		{ type: 'text' as const, text: 'Current authorized answer', refs: [] },
	],
};

test( 'ordinary same-owner failure has an explicit verified Restore; no marketing metadata is invented', async () => {
	let ui = workspace();
	stop = ui.stop;
	await askWorkspace( text );
	await screen.findByText( 'Genie did not answer. Please try again.' );
	ui.stop();
	cleanup();
	resetTurnLane();
	ui = workspace();
	stop = ui.stop;
	await screen.findByRole( 'button', { name: 'Restore unsent draft' } );
	expect( ui.field().value ).toBe( '' );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	expect( ui.field().value ).toBe( text );
	expect( captures ).toHaveLength( 1 );
	const buckets = Object.keys( sessionStorage ).filter( ( key ) =>
		key.startsWith( 'linker-genie-turn-failure:v2:' )
	);
	const encoded = sessionStorage.getItem( buckets[ 0 ]! )!;
	expect( encoded ).toContain( '"owner"' );
	expect( encoded ).not.toContain( 'entryId' );
	expect( sessionStorage.getItem( 'linker-genie-turn-failure' ) ).toBeNull();
} );

test( 'A1 survives A2 failure then successful retry, fresh mount can explicitly restore A1', async () => {
	let ui = workspace();
	stop = ui.stop;
	await askWorkspace( 'A1 separate engineering question' );
	await screen.findByText( 'Genie did not answer. Please try again.' );
	await askWorkspace( 'A2 separate engineering question' );
	await waitFor( () => expect( captures ).toHaveLength( 2 ) );
	vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await screen.findByText( 'Current authorized answer' );
	ui.stop();
	cleanup();
	resetTurnLane();
	ui = workspace();
	stop = ui.stop;
	await screen.findByRole( 'button', { name: 'Restore unsent draft' } );
	expect(
		document.querySelector( '[data-genie-owned-recovery]' )?.textContent
	).toContain( 'A1 separate engineering question' );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	expect( ui.field().value ).toBe( 'A1 separate engineering question' );
} );

test( 'unknown ownerless v1 is byte-identical and inactive beside a new ordinary failure', async () => {
	const old = JSON.stringify( {
		v: 1,
		kind: 'upstream',
		text: 'Unattributed private text',
		question: 'Unattributed private text',
		uploads: [],
		omitted: [ 'unattributed.pdf' ],
	} );
	sessionStorage.setItem( 'linker-genie-turn-failure', old );
	const ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	expect( document.body.textContent ).not.toContain(
		'Unattributed private text'
	);
	expect( document.body.textContent ).not.toContain( 'unattributed.pdf' );
	await askWorkspace( 'New explicitly owned question' );
	await screen.findByText( 'Genie did not answer. Please try again.' );
	expect( sessionStorage.getItem( 'linker-genie-turn-failure' ) ).toBe( old );
} );

for ( const method of [ 'getItem', 'setItem' ] as const ) {
	test( `ordinary current mount remains usable with ${ method } denied, warns and retries without claiming old bytes`, async () => {
		const old = 'opaque legacy private bytes';
		sessionStorage.setItem( 'linker-genie-turn-failure', old );
		const original = Storage.prototype.getItem;
		vi.spyOn( Storage.prototype, method ).mockImplementation( () => {
			throw new Error( 'blocked' );
		} );
		const ui = workspace();
		stop = ui.stop;
		await askWorkspace( 'Memory only question' );
		await screen.findByText( 'Genie did not answer. Please try again.' );
		await screen.findByText(
			'This question could not be saved. It may be lost if you refresh or leave this page.'
		);
		vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			)
		);
		await screen.findByText( 'Current authorized answer' );
		expect(
			original.call( sessionStorage, 'linker-genie-turn-failure' )
		).toBe( old );
	} );
}

for ( const outcome of [
	'success',
	'refusal',
	'conflict',
	'upstream',
] as const ) {
	test( `in-place identity change quarantines A and ignores late ${ outcome } settlement/finally`, async () => {
		let resolve!: ( value: typeof answer ) => void;
		let reject!: ( reason: unknown ) => void;
		vi.mocked( sendTurn ).mockImplementationOnce(
			() =>
				new Promise( ( done, fail ) => {
					resolve = done;
					reject = fail;
				} )
		);
		const ui = workspace();
		stop = ui.stop;
		await askWorkspace( text );
		await waitFor( () => expect( resolve ).toBeTypeOf( 'function' ) );
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( ui.field().value ).toBe( '' );
		expect( document.body.textContent ).not.toContain( text );
		await act( async () => {
			if ( outcome === 'success' ) {
				resolve( answer );
			} else {
				reject(
					outcome === 'upstream'
						? new Error( 'upstream' )
						: new TurnError(
								outcome === 'conflict' ? 409 : 413,
								outcome === 'conflict'
									? 'linker_genie_turn_conflict'
									: 'linker_genie_attachment_size'
							)
				);
			}
		} );
		expect( document.body.textContent ).not.toContain( text );
		expect( document.body.textContent ).not.toContain(
			'Current authorized answer'
		);
		vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
		await askWorkspace( 'B own new question' );
		await screen.findByText( 'Current authorized answer' );
	} );
}

test( 'a real PDF FileReader completing after an in-place identity change cannot paint or transport its old bytes', async () => {
	const original = FileReader.prototype.readAsArrayBuffer;
	let finish!: () => void;
	vi.spyOn( FileReader.prototype, 'readAsArrayBuffer' ).mockImplementation(
		function ( this: FileReader, file: Blob ) {
			finish = () => original.call( this, file );
		}
	);
	const mounted = render(
		<App config={ { ...config(), surface: 'helper' } } />
	);
	act( () => window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) ) );
	stop = () => mounted.unmount();
	await finishImmediateConsumerWork();
	const file = new File( [ fileText ], filename, {
		type: 'application/pdf',
	} );
	await act( async () =>
		fireEvent.change( document.querySelector( 'input[type=file]' )!, {
			target: { files: [ file ] },
		} )
	);
	expect( finish ).toBeTypeOf( 'function' );
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( document.body.textContent ).not.toContain( filename );
	await act( async () => finish() );
	await new Promise( ( resolve ) => setTimeout( resolve, 0 ) );
	expect( document.body.textContent ).not.toContain( filename );
	vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
	await askWorkspace( 'B has no attachment' );
	const request = vi.mocked( sendTurn ).mock.calls.at( -1 )?.[ 0 ];
	expect( request?.uploads ).toEqual( [] );
} );

test( 'native lookup pending accepts no ordinary input, outage Retry makes a usable editor with zero automatic turn', async () => {
	let release!: ( value: unknown ) => void;
	vi.stubGlobal(
		'fetch',
		vi.fn(
			() =>
				new Promise( ( resolve ) => {
					release = resolve;
				} )
		)
	);
	const ui = workspace();
	stop = ui.stop;
	expect( ui.field().disabled ).toBe( true );
	fireEvent.input( ui.field(), {
		target: { value: 'Must not be accepted while unowned' },
	} );
	expect( ui.field().value ).toBe( '' );
	await act( async () => release( { ok: false, status: 503 } ) );
	await screen.findByRole( 'button', { name: 'Try again' } );
	expect( captures ).toHaveLength( 0 );
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( {
			ok: true,
			json: async () => ( {
				scope: 'a'.repeat( 64 ),
				messages: [],
				conversations: [],
			} ),
		} ) )
	);
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await waitFor( () => expect( ui.field().disabled ).toBe( false ) );
	expect( captures ).toHaveLength( 0 );
	await askWorkspace( 'Explicit question after verification' );
	await waitFor( () => expect( captures ).toHaveLength( 1 ) );
} );

test( 'ordinary Send native outage retains the owned question and has a usable auxiliary Retry then one explicit transport', async () => {
	const ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	scopeUnavailable = true;
	await askWorkspace( 'Same owner auxiliary outage' );
	await screen.findByText( 'Genie could not load.' );
	expect( ui.field().value ).toBe( '' );
	expect( captures ).toHaveLength( 0 );
	scopeUnavailable = false;
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await waitFor( () =>
		expect( ui.field().value ).toBe( 'Same owner auxiliary outage' )
	);
	vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await screen.findByText( 'Current authorized answer' );
	expect( sendTurn ).toHaveBeenCalledOnce();
} );

for ( const surface of [ 'workspace', 'home' ] as const ) {
	test( `unsent ${ surface } text remains with A while B is blank, original fresh A explicitly restores editing with zero turns`, async () => {
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'A unsent design brief' },
		} );
		expect( ui.field().value ).toBe( 'A unsent design brief' );
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( ui.field().value ).toBe( '' );
		expect( document.body.textContent ).not.toContain(
			'A unsent design brief'
		);
		principal = 'A';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		await screen.findByRole( 'button', { name: 'Restore unsent draft' } );
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Restore unsent draft' } )
			)
		);
		expect( ui.field().value ).toBe( 'A unsent design brief' );
		expect( document.body.textContent ).not.toContain(
			'Genie did not answer.'
		);
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}

test( 'unsent ordinary PDF and text survive helper Close/open as editing, then A→B→A without leaking or auto-send', async () => {
	const mounted = render(
		<App config={ { ...config(), surface: 'helper' } } />
	);
	stop = () => mounted.unmount();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	const field = () =>
		screen.getByRole< HTMLTextAreaElement >( 'textbox', {
			name: 'Ask Genie',
		} );
	await waitFor( () => expect( field().disabled ).toBe( false ) );
	fireEvent.input( field(), { target: { value: 'Unsent PDF context A' } } );
	await act( async () =>
		fireEvent.change( document.querySelector( 'input[type=file]' )!, {
			target: {
				files: [
					new File( [ fileText ], filename, {
						type: 'application/pdf',
					} ),
				],
			},
		} )
	);
	await screen.findByRole( 'button', {
		name: 'Remove attachment ' + filename,
	} );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) )
	);
	const closed = JSON.parse(
		sessionStorage.getItem(
			'linker-genie-turn-failure:v2:' + 'a'.repeat( 64 )
		)!
	);
	const retained = closed.records[ closed.active ].record;
	expect( retained.editing ).toBe( true );
	expect( retained.entryId ).toBeUndefined();
	expect( retained.uploads[ 0 ].name ).toBe( filename );
	expect( atob( retained.uploads[ 0 ].data ) ).toBe( fileText );
	// Closing the dock is a leaving boundary even though React remains mounted.
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	expect( field().value ).toBe( 'Unsent PDF context A' );
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( field().value ).toBe( '' );
	expect( document.body.textContent ).not.toContain( filename );
	principal = 'A';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await screen.findByRole( 'button', { name: 'Restore unsent draft' } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	expect( field().value ).toBe( 'Unsent PDF context A' );
	await screen.findByRole( 'button', {
		name: 'Remove attachment ' + filename,
	} );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'failed editing persistence keeps an A-scoped window copy, shows warning only when A restores, never exposes it to B', async () => {
	const ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	fireEvent.input( ui.field(), {
		target: { value: 'Private memory editing A' },
	} );
	const write = vi
		.spyOn( Storage.prototype, 'setItem' )
		.mockImplementation( () => {
			throw new Error( 'quota' );
		} );
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( ui.field().value ).toBe( '' );
	expect( document.body.textContent ).not.toContain(
		'Private memory editing A'
	);
	principal = 'A';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await screen.findByRole( 'button', { name: 'Restore unsent draft' } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	expect( ui.field().value ).toBe( 'Private memory editing A' );
	await screen.findByText(
		'This question could not be saved. It may be lost if you refresh or leave this page.'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
	await askWorkspace( 'Private memory editing A' );
	await screen.findByText( 'Genie did not answer. Please try again.' );
	vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await screen.findByText( 'Current authorized answer' );
	expect( sendTurn ).toHaveBeenCalledTimes( 2 );
	write.mockRestore();
} );

for ( const surface of [ 'workspace', 'home' ] as const ) {
	test( `same account rotated native session cannot recover ${ surface } text`, async () => {
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'Prior account session private note' },
		} );
		principal = 'A-rotated';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( ui.field().value ).toBe( '' );
		expect( document.body.textContent ).not.toContain(
			'Prior account session private note'
		);
		expect(
			screen.queryByRole( 'button', { name: 'Restore unsent draft' } )
		).toBeNull();
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}
test( 'ordinary unsent text survives New conversation as explicit editing recovery without an automatic model turn', async () => {
	const ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	fireEvent.input( ui.field(), {
		target: { value: 'A accepted project note before New' },
	} );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'New conversation' } )
		)
	);
	await screen.findByRole( 'button', { name: 'Restore unsent draft' } );
	expect( ui.field().value ).toBe( '' );
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	expect( ui.field().value ).toBe( 'A accepted project note before New' );
	expect( document.body.textContent ).not.toContain(
		'Genie did not answer.'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );
test( 'ordinary editing missing-file recovery requires reselect or explicit Remove and sends no phantom attachment', async () => {
	const original = FileReader.prototype.readAsArrayBuffer;
	let finish!: () => void;
	vi.spyOn( FileReader.prototype, 'readAsArrayBuffer' ).mockImplementation(
		function ( this: FileReader, file: Blob ) {
			finish = () => original.call( this, file );
		}
	);
	const mounted = render(
		<App config={ { ...config(), surface: 'helper' } } />
	);
	let ui = {
		field: () =>
			screen.getByRole< HTMLTextAreaElement >( 'textbox', {
				name: 'Ask Genie',
			} ),
		stop: () => mounted.unmount(),
	};
	stop = ui.stop;
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await finishImmediateConsumerWork();
	fireEvent.input( ui.field(), {
		target: { value: 'A preparing PDF context' },
	} );
	fireEvent.change( document.querySelector( 'input[type=file]' )!, {
		target: {
			files: [
				new File( [ fileText ], filename, { type: 'application/pdf' } ),
			],
		},
	} );
	expect( finish ).toBeTypeOf( 'function' );
	await act( async () => {
		stop();
		cleanup();
	} );
	ui = workspace();
	stop = ui.stop;
	await screen.findByRole( 'button', { name: 'Restore unsent draft' } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	expect( ui.field().value ).toBe( 'A preparing PDF context' );
	expect(
		screen.getByText( `Select ${ filename } again before sending.` )
	).toBeTruthy();
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Remove' } ) )
	);
	expect(
		screen.queryByText( `Select ${ filename } again before sending.` )
	).toBeNull();
	vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await screen.findByText( 'Current authorized answer' );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]?.[ 0 ].uploads ).toEqual(
		[]
	);
	await act( async () => finish() );
	expect( document.body.textContent ).not.toContain( filename );
} );

for ( const mode of [ 'attach', 'voice' ] as const ) {
	test( `first home ${ mode } intent opens native loading and resumes only an explicit action after Retry`, async () => {
		scopeUnavailable = true;
		const start = vi.fn();
		vi.stubGlobal(
			'SpeechRecognition',
			class {
				start = start;
				stop() {}
			}
		);
		const ui = home();
		stop = ui.stop;
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', {
					name: mode === 'attach' ? 'Attach' : 'Voice',
				} )
			)
		);
		await screen.findByRole( 'button', { name: 'Try again' } );
		expect( ui.field().disabled ).toBe( true );
		expect( sendTurn ).not.toHaveBeenCalled();
		expect( start ).not.toHaveBeenCalled();
		scopeUnavailable = false;
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			)
		);
		await waitFor( () => expect( ui.field().disabled ).toBe( false ) );
		await screen.findByRole( 'button', {
			name: mode === 'attach' ? 'Choose a file' : 'Dictate',
		} );
		expect( start ).not.toHaveBeenCalled();
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}
for ( const outcome of [
	'success',
	'refusal',
	'conflict',
	'upstream',
] as const ) {
	test( `homepage controller ignores late A ${ outcome } after native B replaces its context`, async () => {
		let resolve!: ( value: typeof answer ) => void;
		let reject!: ( error: unknown ) => void;
		vi.mocked( sendTurn ).mockImplementationOnce(
			() =>
				new Promise( ( done, fail ) => {
					resolve = done;
					reject = fail;
				} )
		);
		const ui = home();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), { target: { value: text } } );
		await act( async () =>
			fireEvent.click( document.querySelector( '.hero-send' )! )
		);
		await waitFor( () => expect( resolve ).toBeTypeOf( 'function' ) );
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( ui.field().value ).toBe( '' );
		expect( document.body.textContent ).not.toContain( text );
		await act( async () => {
			if ( outcome === 'success' ) {
				resolve( answer );
			} else {
				reject(
					outcome === 'upstream'
						? new Error( 'upstream' )
						: new TurnError(
								outcome === 'conflict' ? 409 : 413,
								outcome === 'conflict'
									? 'linker_genie_turn_conflict'
									: 'linker_genie_attachment_size'
							)
				);
			}
		} );
		expect( document.body.textContent ).not.toContain( text );
		expect( document.body.textContent ).not.toContain(
			'Current authorized answer'
		);
		vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
		await waitFor( () => expect( ui.field().disabled ).toBe( false ) );
		fireEvent.input( ui.field(), {
			target: { value: 'B current home question' },
		} );
		await act( async () =>
			fireEvent.click( document.querySelector( '.hero-send' )! )
		);
		await screen.findAllByText( 'Current authorized answer' );
	} );
}

for ( const surface of [ 'workspace', 'home' ] as const ) {
	test( `a completed ${ surface } answer and live announcement are quarantined on native principal change`, async () => {
		vi.mocked( sendTurn ).mockResolvedValueOnce( {
			meta: null,
			blocks: [
				{
					type: 'text',
					text: 'A private approved engineering answer',
					refs: [],
				},
			],
		} );
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'A private completed question' },
		} );
		await act( async () =>
			fireEvent.click(
				surface === 'home'
					? document.querySelector( '.hero-send' )!
					: screen.getByRole( 'button', { name: 'Send' } )
			)
		);
		await screen.findAllByText( 'A private approved engineering answer' );
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( document.body.textContent ).not.toContain(
			'A private approved engineering answer'
		);
		expect( document.body.textContent ).not.toContain(
			'A private completed question'
		);
	} );
}

test( 'explicitly emptying an accepted editor consumes only its editing snapshot before New', async () => {
	const ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	fireEvent.input( ui.field(), {
		target: { value: 'Text subsequently removed by its owner' },
	} );
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	fireEvent.input( ui.field(), { target: { value: '' } } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'New conversation' } )
		)
	);
	expect( ui.field().value ).toBe( '' );
	expect(
		screen.queryByRole( 'button', { name: 'Restore unsent draft' } )
	).toBeNull();
	expect( document.body.textContent ).not.toContain(
		'Text subsequently removed by its owner'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

for ( const surface of [ 'workspace', 'home' ] as const ) {
	test( `pagehide checkpoints accepted ${ surface } editor before document navigation without turning it into a model failure`, async () => {
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'Accepted note before document navigation' },
		} );
		await act( async () =>
			window.dispatchEvent( new Event( 'pagehide' ) )
		);
		const bucket = JSON.parse(
			sessionStorage.getItem(
				'linker-genie-turn-failure:v2:' + 'a'.repeat( 64 )
			)!
		);
		expect( bucket.records[ bucket.active ].record.editing ).toBe( true );
		expect( bucket.records[ bucket.active ].record.text ).toBe(
			'Accepted note before document navigation'
		);
		expect(
			bucket.records[ bucket.active ].record.entryId
		).toBeUndefined();
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}

for ( const surface of [ 'workspace', 'home' ] as const ) {
	for ( const outcome of [ 'refusal', 'conflict' ] as const ) {
		test( `review repair: ${ surface } returned ${ outcome } preserves its editing owner without another keystroke`, async () => {
			vi.mocked( sendTurn ).mockRejectedValueOnce(
				new TurnError(
					outcome === 'conflict' ? 409 : 413,
					outcome === 'conflict'
						? 'linker_genie_turn_conflict'
						: 'linker_genie_attachment_size'
				)
			);
			let ui = surface === 'home' ? home() : workspace();
			stop = ui.stop;
			await finishImmediateConsumerWork();
			fireEvent.input( ui.field(), {
				target: { value: 'Original accepted returned question' },
			} );
			await act( async () =>
				fireEvent.click(
					surface === 'home'
						? document.querySelector( '.hero-send' )!
						: screen.getByRole( 'button', { name: 'Send' } )
				)
			);
			await waitFor( () =>
				expect( ui.field().value ).toBe(
					'Original accepted returned question'
				)
			);
			await act( async () =>
				window.dispatchEvent( new Event( 'pagehide' ) )
			);
			const stored = new FailureJournal( sessionStorage, {
				scope: 'a'.repeat( 64 ),
				persistent: true,
			} ).candidate();
			expect( stored?.record.editing ).toBe( true );
			expect( stored?.record.text ).toBe(
				'Original accepted returned question'
			);
			await act( async () => {
				ui.stop();
				cleanup();
			} );
			principal = 'B';
			ui = surface === 'home' ? home() : workspace();
			stop = ui.stop;
			await finishImmediateConsumerWork();
			expect( ui.field().value ).toBe( '' );
			principal = 'A';
			await act( async () =>
				window.dispatchEvent( new Event( 'focus' ) )
			);
			await restoreRetainedDraft();
			expect( ui.field().value ).toBe(
				'Original accepted returned question'
			);
			expect( sendTurn ).toHaveBeenCalledTimes( 1 );
		} );
	}
	test( `review repair: ${ surface } accepts A2 while A1 is pending and checkpoints A2 on identity change`, async () => {
		let resolve!: ( value: typeof answer ) => void;
		vi.mocked( sendTurn ).mockImplementationOnce(
			() =>
				new Promise( ( done ) => {
					resolve = done;
				} )
		);
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'A1 pending question' },
		} );
		await act( async () =>
			fireEvent.click(
				surface === 'home'
					? document.querySelector( '.hero-send' )!
					: screen.getByRole( 'button', { name: 'Send' } )
			)
		);
		await waitFor( () => expect( resolve ).toBeTypeOf( 'function' ) );
		expect( ui.field().disabled ).toBe( false );
		fireEvent.input( ui.field(), {
			target: { value: 'A2 accepted while waiting' },
		} );
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( ui.field().value ).toBe( '' );
		const bucket = JSON.parse(
			sessionStorage.getItem( failureBucketKey( 'a'.repeat( 64 ) ) )!
		) as { records: Record< string, { record: { text: string } } > };
		expect(
			Object.values( bucket.records ).map(
				( entry ) => entry.record.text
			)
		).toContain( 'A2 accepted while waiting' );
		await act( async () => resolve( answer ) );
		principal = 'A';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		await restoreRetainedDraft();
		expect( ui.field().value ).toBe( 'A2 accepted while waiting' );
	} );
	test( `review repair: ${ surface } missing-only editor exchanges both retained attempts without corrupting storage`, async () => {
		const journal = new FailureJournal( sessionStorage, {
			scope: 'a'.repeat( 64 ),
			persistent: true,
		} );
		journal.begin( {
			phase: 'failed',
			kind: 'upstream',
			draft: {
				text: 'Earlier retained question',
				question: 'Earlier retained question',
				uploads: [],
				omitted: [],
			},
		} );
		journal.begin( {
			phase: 'editing',
			kind: null,
			draft: {
				editing: true,
				text: '',
				question: 'pending.pdf',
				uploads: [],
				omitted: [ 'pending.pdf' ],
			},
		} );
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await restoreRetainedDraft();
		await screen.findByText( 'Select pending.pdf again before sending.' );
		if ( surface === 'workspace' ) {
			await act( async () =>
				window.dispatchEvent(
					new CustomEvent( 'linker-genie-open', {
						detail: { refresh: true },
					} )
				)
			);
		} else {
			scopeUnavailable = true;
			await act( async () =>
				window.dispatchEvent( new Event( 'focus' ) )
			);
			scopeUnavailable = false;
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', { name: 'Try again' } )
				)
			);
		}

		await restoreRetainedDraft();
		expect( () => journal.candidate() ).not.toThrow();
		expect( ui.field().value ).toBe( 'Earlier retained question' );
		await restoreRetainedDraft();
		await screen.findByText( 'Select pending.pdf again before sending.' );
	} );
	test( `review repair: ${ surface } visibility-only resume revalidates and hidden checkpoints accepted text`, async () => {
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'Private A before hide' },
		} );
		Object.defineProperty( document, 'visibilityState', {
			configurable: true,
			value: 'hidden',
		} );
		await act( async () =>
			document.dispatchEvent( new Event( 'visibilitychange' ) )
		);
		principal = 'B';
		Object.defineProperty( document, 'visibilityState', {
			configurable: true,
			value: 'visible',
		} );
		await act( async () =>
			document.dispatchEvent( new Event( 'visibilitychange' ) )
		);
		expect( ui.field().value ).toBe( '' );
		expect( document.body.textContent ).not.toContain(
			'Private A before hide'
		);
		expect(
			new FailureJournal( sessionStorage, {
				scope: 'a'.repeat( 64 ),
				persistent: true,
			} ).candidate()?.record.text
		).toBe( 'Private A before hide' );
	} );
	test( `review repair: ${ surface } new text after explicitly emptying a checkpoint gets a new recoverable attempt`, async () => {
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'First accepted note' },
		} );
		await act( async () =>
			window.dispatchEvent( new Event( 'pagehide' ) )
		);
		const first = new FailureJournal( sessionStorage, {
			scope: 'a'.repeat( 64 ),
			persistent: true,
		} ).candidate()!;
		fireEvent.input( ui.field(), { target: { value: '' } } );
		await act( async () =>
			window.dispatchEvent( new Event( 'pagehide' ) )
		);
		fireEvent.input( ui.field(), {
			target: { value: 'Second original owner note' },
		} );
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( ui.field().value ).toBe( '' );
		principal = 'A';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		await restoreRetainedDraft();
		expect( ui.field().value ).toBe( 'Second original owner note' );
		expect(
			new FailureJournal( sessionStorage, {
				scope: 'a'.repeat( 64 ),
				persistent: true,
			} ).candidate()?.cursor.owner.attempt
		).not.toBe( first.cursor.owner.attempt );
	} );
}

test( 'review repair: late A marketing completion cannot consume a B durable source', async () => {
	let resolve!: ( value: typeof answer ) => void;
	vi.mocked( sendTurn ).mockImplementationOnce(
		() =>
			new Promise( ( done ) => {
				resolve = done;
			} )
	);
	const ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	const a = {
		id: 'A-source-attempt',
		scope: 'a'.repeat( 64 ),
		mode: 'compose' as const,
		text: 'A delayed marketing question',
		sourcePath: '/residential/',
	};
	expect( rememberEntry( a ) ).toBe( true );
	await act( async () =>
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', { detail: { entry: a } } )
		)
	);
	await waitFor( () => expect( resolve ).toBeTypeOf( 'function' ) );
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	const b = {
		id: 'B-source-attempt',
		scope: 'b'.repeat( 64 ),
		mode: 'attach' as const,
		text: 'B new durable source question',
		sourcePath: '/commercial/',
	};
	expect( rememberEntry( b ) ).toBe( true );
	const before = sessionStorage.getItem( ENTRY_KEY );
	await act( async () => resolve( answer ) );
	expect( sessionStorage.getItem( ENTRY_KEY ) ).toBe( before );
} );

for ( const surface of [ 'dock', 'home' ] as const ) {
	for ( const outcome of [
		'success',
		'refusal',
		'conflict',
		'upstream',
		'resource',
	] as const ) {
		test( `review repair: ${ surface } A1 ${ outcome } preserves the accepted A2 text and actually prepared PDF`, async () => {
			let resolve!: ( value: typeof answer ) => void;
			let reject!: ( error: unknown ) => void;
			vi.mocked( sendTurn ).mockImplementationOnce(
				() =>
					new Promise( ( done, fail ) => {
						resolve = done;
						reject = fail;
					} )
			);
			const ui = surface === 'home' ? home() : dock();
			stop = ui.stop;
			await finishImmediateConsumerWork();
			fireEvent.input( ui.field(), {
				target: { value: 'A1 submitted original' },
			} );
			await act( async () =>
				fireEvent.click(
					surface === 'home'
						? document.querySelector( '.hero-send' )!
						: screen.getByRole( 'button', { name: 'Send' } )
				)
			);
			await waitFor( () => expect( resolve ).toBeTypeOf( 'function' ) );
			fireEvent.input( ui.field(), {
				target: { value: 'A2 newly accepted question' },
			} );
			fireEvent.change( document.querySelector( 'input[type=file]' )!, {
				target: {
					files: [
						new File( [ fileText ], filename, {
							type: 'application/pdf',
						} ),
					],
				},
			} );
			await waitFor( () => {
				expect(
					document.querySelector( '.linker-genie-app__attachment' )
				).not.toBeNull();
				expect( screen.queryByText( 'Preparing file…' ) ).toBeNull();
			} );
			await act( async () => {
				if ( outcome === 'success' ) {
					resolve( answer );
				} else if ( outcome === 'resource' ) {
					reject( new TurnError( 429, 'linker_admission_quota' ) );
				} else {
					reject(
						outcome === 'upstream'
							? new Error( 'upstream' )
							: new TurnError(
									outcome === 'conflict' ? 409 : 413,
									outcome === 'conflict'
										? 'linker_genie_turn_conflict'
										: 'linker_genie_attachment_size'
								)
					);
				}
			} );
			expect( ui.field().value ).toBe( 'A2 newly accepted question' );
			expect(
				document.querySelector( '.linker-genie-app__attachment' )
					?.textContent
			).toContain( filename );
			await act( async () =>
				window.dispatchEvent( new Event( 'pagehide' ) )
			);
			const bucket = JSON.parse(
				sessionStorage.getItem( failureBucketKey( 'a'.repeat( 64 ) ) )!
			) as {
				records: Record<
					string,
					{
						record: {
							text: string;
							editing?: boolean;
							uploads: Array< { name: string; data: string } >;
						};
					}
				>;
			};
			const drafts = Object.values( bucket.records ).map(
				( item ) => item.record
			);
			const next = drafts.find(
				( item ) => item.text === 'A2 newly accepted question'
			);
			expect( next?.editing ).toBe( true );
			expect( next?.uploads[ 0 ]?.data ).toBe( btoa( fileText ) );
			expect(
				drafts.find( ( item ) => item.text === 'A1 submitted original' )
					?.editing
			).toBe(
				outcome === 'refusal' ||
					outcome === 'conflict' ||
					outcome === 'resource'
					? true
					: undefined
			);
			if (
				outcome === 'refusal' ||
				outcome === 'conflict' ||
				outcome === 'resource'
			) {
				await verifyReturnedEditorExchange( ui.field );
			}
		} );
	}
}

for ( const surface of [ 'workspace', 'home' ] as const ) {
	test( `review repair: ${ surface } owned omitted-only upstream record is readable but never an empty send`, async () => {
		const journal = new FailureJournal( sessionStorage, {
			scope: 'a'.repeat( 64 ),
			persistent: true,
		} );
		const pending = journal.begin( {
			phase: 'pending',
			kind: null,
			draft: {
				text: '',
				question: 'Attached: missing.pdf',
				uploads: [],
				omitted: [ 'missing.pdf' ],
			},
		} );
		const failed = journal.save(
			{ ...pending.state, phase: 'failed', kind: 'upstream' },
			pending.cursor
		);
		expect( failed.conflict ).toBe( false );
		expect( journal.candidate()?.record.question ).toBe( '' );
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await restoreRetainedDraft();
		expect( ui.field().value ).toBe( '' );
		await screen.findByText(
			/Attach missing\.pdf again\. It could not be kept for another try\./
		);
		const retry = screen.getByRole( 'button', { name: 'Try again' } );
		await act( async () => fireEvent.click( retry ) );
		expect( sendTurn ).not.toHaveBeenCalled();
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( document.body.textContent ).not.toContain( 'missing.pdf' );
	} );
}
test( 'review repair: actual homepage manual model exit claims native editing ownership', async () => {
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		...answer,
		attachments: [
			{
				id: 'att1',
				name: 'nameplate.jpg',
				kind: 'nameplate',
				match: 'unreadable',
				brand: null,
				model: null,
				products: [],
			},
		],
	} );
	const ui = home();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	fireEvent.input( ui.field(), {
		target: { value: 'Identify this device' },
	} );
	await act( async () =>
		fireEvent.click( document.querySelector( '.hero-send' )! )
	);
	const type = await screen.findByRole( 'button', {
		name: 'Type the model',
	} );
	await act( async () => fireEvent.click( type ) );
	expect( ui.field().value ).toBe( 'My device is the ' );
	await act( async () => window.dispatchEvent( new Event( 'pagehide' ) ) );
	expect(
		new FailureJournal( sessionStorage, {
			scope: 'a'.repeat( 64 ),
			persistent: true,
		} ).candidate()?.record.text
	).toBe( 'My device is the ' );
} );

for ( const surface of [ 'workspace', 'home' ] as const ) {
	test( `review repair: ${ surface } transient scope outage during A1 settlement preserves accepted A2`, async () => {
		let done!: ( value: typeof answer ) => void;
		vi.mocked( sendTurn ).mockImplementationOnce(
			() =>
				new Promise( ( resolve ) => {
					done = resolve;
				} )
		);
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'A1 awaiting answer' },
		} );
		await act( async () =>
			fireEvent.click(
				surface === 'home'
					? document.querySelector( '.hero-send' )!
					: screen.getByRole( 'button', { name: 'Send' } )
			)
		);
		await waitFor( () => expect( done ).toBeTypeOf( 'function' ) );
		fireEvent.input( ui.field(), {
			target: { value: 'A2 stays during temporary lookup failure' },
		} );
		scopeUnavailable = true;
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		await act( async () => done( answer ) );
		scopeUnavailable = false;
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		expect( ui.field().value ).toBe(
			'A2 stays during temporary lookup failure'
		);
		expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	} );
	test( `review repair: ${ surface } Retry retains an accepted replacement under its own editor attempt`, async () => {
		let ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'Original failed A1' },
		} );
		await act( async () =>
			fireEvent.click(
				surface === 'home'
					? document.querySelector( '.hero-send' )!
					: screen.getByRole( 'button', { name: 'Send' } )
			)
		);
		await screen.findByText( 'Genie did not answer. Please try again.' );
		fireEvent.input( ui.field(), {
			target: { value: 'Accepted replacement A2 before Retry' },
		} );
		vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			)
		);
		await screen.findAllByText( 'Current authorized answer' );
		await act( async () => {
			ui.stop();
			cleanup();
		} );
		ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await restoreRetainedDraft();
		expect( ui.field().value ).toBe(
			'Accepted replacement A2 before Retry'
		);
		expect( sendTurn ).toHaveBeenCalledTimes( 2 );
	} );
}

for ( const surface of [ 'workspace', 'home' ] as const ) {
	test( `review repair: ${ surface } emptying non-active A2 cannot revive its consumed attempt after A1 returns`, async () => {
		let reject!: ( error: unknown ) => void;
		vi.mocked( sendTurn ).mockImplementationOnce(
			() =>
				new Promise( ( _done, fail ) => {
					reject = fail;
				} )
		);
		const ui = surface === 'home' ? home() : workspace();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		fireEvent.input( ui.field(), {
			target: { value: 'A1 returned preserved' },
		} );
		await act( async () =>
			fireEvent.click(
				surface === 'home'
					? document.querySelector( '.hero-send' )!
					: screen.getByRole( 'button', { name: 'Send' } )
			)
		);
		await waitFor( () => expect( reject ).toBeTypeOf( 'function' ) );
		fireEvent.input( ui.field(), {
			target: { value: 'A2 deliberately removed' },
		} );
		await act( async () =>
			reject( new TurnError( 413, 'linker_genie_attachment_size' ) )
		);
		expect( ui.field().value ).toBe( 'A2 deliberately removed' );
		fireEvent.input( ui.field(), { target: { value: '' } } );
		await act( async () =>
			window.dispatchEvent( new Event( 'pagehide' ) )
		);
		const raw = sessionStorage.getItem(
			failureBucketKey( 'a'.repeat( 64 ) )
		)!;
		expect( raw ).not.toContain( 'A2 deliberately removed' );
		expect( raw ).toContain( 'A1 returned preserved' );
		fireEvent.input( ui.field(), {
			target: { value: 'A3 accepted after removal' },
		} );
		principal = 'B';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		principal = 'A';
		await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
		await restoreRetainedDraft();
		expect( ui.field().value ).toBe( 'A3 accepted after removal' );
	} );
}

test( 'review get fallback: actual App read-failure editing recovery consumed after an answer cannot revive its old disk text', async () => {
	let ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	fireEvent.input( ui.field(), {
		target: { value: 'Original durable question before read failure' },
	} );
	await act( async () => window.dispatchEvent( new Event( 'pagehide' ) ) );
	fireEvent.input( ui.field(), {
		target: { value: 'Latest accepted editor while storage read fails' },
	} );
	const get = vi
		.spyOn( Storage.prototype, 'getItem' )
		.mockImplementation( () => {
			throw new Error( 'temporary get failure' );
		} );
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( ui.field().value ).toBe( '' );
	get.mockRestore();
	principal = 'A';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await restoreRetainedDraft();
	expect( ui.field().value ).toBe(
		'Latest accepted editor while storage read fails'
	);
	vi.mocked( sendTurn ).mockResolvedValueOnce( answer );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await screen.findAllByText( 'Current authorized answer' );
	await act( async () => {
		ui.stop();
		cleanup();
	} );
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	ui = workspace();
	stop = ui.stop;
	await finishImmediateConsumerWork();
	expect( ui.field().value ).toBe( '' );
	expect( document.body.textContent ).not.toContain(
		'Original durable question before read failure'
	);
	expect(
		screen.queryByRole( 'button', { name: 'Restore unsent draft' } )
	).toBeNull();
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

for ( const changed of [ false, true ] ) {
	test( `review dictation end: actual homepage rejects an old ${ changed ? 'principal' : 'same-owner session' } end without losing the current stop handle`, async () => {
		class Recognition {
			onend: ( () => void ) | null = null;
			onerror: ( () => void ) | null = null;
			onresult: null = null;
			lang = '';
			start = vi.fn();
			stop = vi.fn();
			constructor() {
				sessions.push( this );
			}
		}
		const sessions: Recognition[] = [];
		vi.stubGlobal( 'SpeechRecognition', Recognition );
		const ui = home();
		stop = ui.stop;
		await finishImmediateConsumerWork();
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) )
		);
		expect( sessions ).toHaveLength( 1 );
		if ( changed ) {
			principal = 'B';
			await act( async () =>
				window.dispatchEvent( new Event( 'focus' ) )
			);
		} else {
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', { name: 'Voice' } )
				)
			);
		}
		expect( sessions[ 0 ]!.stop ).toHaveBeenCalledTimes( 1 );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) )
		);
		expect( sessions ).toHaveLength( 2 );
		await act( async () => sessions[ 0 ]!.onend?.() );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) )
		);
		expect( sessions[ 1 ]!.stop ).toHaveBeenCalledTimes( 1 );
		expect( sessions ).toHaveLength( 2 );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) )
		);
		expect( sessions ).toHaveLength( 3 );
		await act( async () => sessions[ 1 ]!.onerror?.() );
		await act( async () => sessions[ 2 ]!.onend?.() );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) )
		);
		expect( sessions ).toHaveLength( 4 );
		await act( async () => ui.stop() );
		expect( sessions[ 3 ]!.stop ).toHaveBeenCalledTimes( 1 );
	} );
}
