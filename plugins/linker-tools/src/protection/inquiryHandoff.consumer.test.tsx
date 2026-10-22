// @vitest-environment jsdom
/** Actual App/startHero inquiry callers keep accepted text and its native owner together. */
import {
	act,
	cleanup,
	fireEvent,
	render,
	screen,
	waitFor,
} from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { App, resetTurnLane } from '../genie/App';
import { readConfig } from '../genie/config';
import { sendTurn, TurnError } from '../genie/api/turn';
import type { Dictation } from '../genie/shared/dictation';
import { startHero } from '../hero/controller';
import { restoreInquiry } from './inquiryHandoff';

vi.mock( '../genie/api/turn', async ( original ) => {
	const actual = await original< typeof import( '../genie/api/turn' ) >();
	return { ...actual, sendTurn: vi.fn() };
} );
const scopeA = 'a'.repeat( 64 );
const scopeB = 'b'.repeat( 64 );
const prefix = 'linker-genie-inquiry-handoff:v2:';
const originalText = 'Private accepted A fallback text';
const nextText = 'Newly accepted current draft text';
const originalUrl = window.location.href;
let principal: 'A' | 'B';
let stop = () => {};

beforeEach( () => {
	sessionStorage.clear();
	for ( const key of [
		'__linkerGenieFailureJournal',
		'__linkerGenieNativeScope',
	] ) {
		delete ( window as unknown as Record< string, unknown > )[ key ];
	}
	resetTurnLane();
	principal = 'A';
	vi.mocked( sendTurn )
		.mockReset()
		.mockRejectedValueOnce(
			new TurnError( 429, 'linker_admission_quota' )
		);
	vi.stubGlobal(
		'fetch',
		vi.fn( async ( url ) => {
			if ( String( url ).includes( '/entry-context' ) ) {
				return {
					ok: true,
					json: async () => ( {
						scope: principal === 'A' ? scopeA : scopeB,
					} ),
				};
			}
			if ( String( url ).endsWith( '/conversations' ) ) {
				return {
					ok: true,
					json: async () => ( { conversations: [], current_id: 0 } ),
				};
			}
			if ( String( url ).endsWith( '/conversation' ) ) {
				return {
					ok: true,
					json: async () => ( { messages: [], stream: '' } ),
				};
			}
			throw new Error( `Unexpected HTTP consumer: ${ String( url ) }` );
		} )
	);
} );
afterEach( async () => {
	await act( async () => stop() );
	stop = () => {};
	cleanup();
	document.body.innerHTML = '';
	sessionStorage.clear();
	window.history.replaceState( null, '', originalUrl );
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	resetTurnLane();
} );
async function rejectedCaller( surface: 'dock' | 'home' ) {
	const mount = document.createElement( 'div' );
	mount.dataset.restNonce = 'native-browser-nonce';
	mount.dataset.requestPageUrl = '/proforma-request/';
	const config = readConfig( mount );
	if ( surface === 'dock' ) {
		const ui = render( <App config={ config } /> );
		stop = ui.unmount;
		await act( async () =>
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
		);
	} else {
		document.body.innerHTML =
			'<section class="hero-cinematic"><div class="hero-stage"><div class="hero-dialog"><textarea class="hero-prompt" placeholder="Ask Genie"></textarea><div class="hero-dialog-footer"><a class="hero-send" href="/genie/">Send</a></div></div></div></section>';
		await act( async () => {
			stop = startHero(
				document.querySelector< HTMLElement >( '.hero-cinematic' )!,
				{ config }
			);
		} );
	}
	const field = () =>
		surface === 'home'
			? document.querySelector< HTMLTextAreaElement >( '.hero-prompt' )!
			: screen.getByRole< HTMLTextAreaElement >( 'textbox', {
					name: 'Ask Genie',
				} );
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	fireEvent.input( field(), { target: { value: originalText } } );
	await act( async () =>
		fireEvent.click(
			surface === 'home'
				? document.querySelector( '.hero-send' )!
				: screen.getByRole( 'button', { name: 'Send' } )
		)
	);
	const link = await screen.findByRole( 'link', { name: 'Send an inquiry' } );
	link.addEventListener( 'click', ( event ) => event.preventDefault() );
	expect( link ).toHaveAttribute( 'href', '/proforma-request/' );
	expect( field().value ).toBe( originalText );
	return { field, link, config };
}
/**
 * Native input/click without RTL's per-event act flush; no React private fields.
 * @param field The real composer textarea.
 * @param value The browser input value.
 */
function nativeInput( field: HTMLTextAreaElement, value: string ) {
	const setter = Object.getOwnPropertyDescriptor(
		HTMLTextAreaElement.prototype,
		'value'
	)!.set!;
	setter.call( field, value );
	field.dispatchEvent( new Event( 'input', { bubbles: true } ) );
}
function nativeClick( link: HTMLElement ) {
	link.dispatchEvent(
		new MouseEvent( 'click', { bubbles: true, cancelable: true } )
	);
}
/**
 * Original Standards scheduled-once native-response/pre-React-commit window.
 * No React state or DraftContext internals are mutated; input/click are DOM events.
 * @param action Native DOM action before React commits the new identity.
 */
async function afterNativeBSettles( action: () => void ) {
	const original = vi.mocked( fetch ).getMockImplementation()!;
	let scheduled = false;
	let acted = false;
	let actionError: unknown;
	vi.mocked( fetch ).mockImplementation( async ( url, options ) => {
		if ( String( url ).includes( '/entry-context' ) && principal === 'B' ) {
			return {
				ok: true,
				json: async () => {
					if ( ! scheduled ) {
						scheduled = true;
						queueMicrotask( () =>
							queueMicrotask( () =>
								queueMicrotask( () => {
									acted = true;
									try {
										action();
									} catch ( error ) {
										actionError = error;
									}
								} )
							)
						);
					}
					return { scope: scopeB };
				},
			} as Response;
		}
		return original( url, options );
	} );
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( scheduled ).toBe( true );
	expect( acted ).toBe( true );
	if ( actionError ) {
		throw actionError;
	}
}

for ( const surface of [ 'dock', 'home' ] as const ) {
	test( `${ surface }: explicit inquiry navigation restores current accepted text through the native receiver`, async () => {
		const ui = await rejectedCaller( surface );
		await act( async () => fireEvent.click( ui.link ) );
		expect(
			JSON.parse( sessionStorage.getItem( prefix + scopeA )! )
		).toMatchObject( { scope: scopeA, message: originalText } );
		window.history.pushState( null, '', '/proforma-request/' );
		const nativeField = document.createElement( 'textarea' );
		nativeField.id = 'inquiry-message';
		document.body.append( nativeField );
		await restoreInquiry( ui.config );
		expect( nativeField.value ).toBe( originalText );
		expect( sessionStorage.getItem( prefix + scopeA ) ).toBeNull();
		expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	} );
}
test( 'dock: old A inquiry link cannot stage A text after native B is ready without an editor', async () => {
	const ui = await rejectedCaller( 'dock' );
	await afterNativeBSettles( () => {
		expect( ui.link.isConnected ).toBe( true );
		nativeClick( ui.link );
	} );
	expect( sessionStorage.getItem( prefix + scopeB ) ).toBeNull();
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );
test( 'dock: B accepts a new editor before React commits, but the old A handler cannot bind its closure text to B', async () => {
	let onStart = () => {};
	const sessions: NativeRecognition[] = [];
	class NativeRecognition implements Dictation {
		lang = '';
		onresult: Dictation[ 'onresult' ] = null;
		onend: Dictation[ 'onend' ] = null;
		onerror: Dictation[ 'onerror' ] = null;
		constructor() {
			sessions.push( this );
		}
		start() {
			onStart();
		}
		stop() {}
	}
	vi.stubGlobal( 'SpeechRecognition', NativeRecognition );
	const ui = await rejectedCaller( 'dock' );
	let connectedAtStart = false;
	onStart = () => {
		// Production Dictate has synchronously accepted B's editor before native start().
		connectedAtStart = ui.link.isConnected;
		nativeClick( ui.link );
	};
	await afterNativeBSettles( () =>
		nativeClick( screen.getByRole( 'button', { name: 'Dictate' } ) )
	);
	expect( connectedAtStart ).toBe( true );
	expect( sessions ).toHaveLength( 1 );
	expect( sessionStorage.getItem( prefix + scopeB ) ).toBeNull();
} );

test( 'dock: same-owner DOM edits never transfer the superseded question', async () => {
	const ui = await rejectedCaller( 'dock' );
	await act( async () => {
		nativeInput( ui.field(), nextText );
		nativeClick( ui.link );
	} );
	const raw = sessionStorage.getItem( prefix + scopeA );
	expect( [ null, nextText ] ).toContain(
		raw === null ? null : JSON.parse( raw ).message
	);
	expect( ui.field().value ).toBe( nextText );
} );
test( 'home: current same-owner live prompt/version wins before a React commit', async () => {
	const ui = await rejectedCaller( 'home' );
	await act( async () => {
		nativeInput( ui.field(), nextText );
		nativeClick( ui.link );
	} );
	expect(
		JSON.parse( sessionStorage.getItem( prefix + scopeA )! )
	).toMatchObject( { scope: scopeA, message: nextText } );
} );
