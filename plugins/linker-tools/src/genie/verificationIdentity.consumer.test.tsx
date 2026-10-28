// @vitest-environment jsdom
/** Actual App, native DraftContext and protected turn transport share one owner. */
import { webcrypto } from 'node:crypto';
import {
	act,
	cleanup,
	fireEvent,
	render,
	screen,
	waitFor,
} from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { App, resetTurnLane } from './App';
import { readConfig } from './config';
import { FailureJournal } from './shared/ownedFailure';

const scopeA = 'a'.repeat( 64 );
const scopeB = 'b'.repeat( 64 );
const question = 'Original owner question awaiting public verification';
const answer = 'Answer dispatched for the verified original owner';
let stop = () => {};

function deferred< T >() {
	let resolve!: ( value: T ) => void;
	const promise = new Promise< T >( ( done ) => {
		resolve = done;
	} );
	return { promise, resolve };
}

beforeEach( () => {
	sessionStorage.clear();
	for ( const key of [
		'__linkerGenieFailureJournal',
		'__linkerGenieNativeScope',
	] ) {
		delete ( window as unknown as Record< string, unknown > )[ key ];
	}
	resetTurnLane();
	vi.stubGlobal( 'crypto', webcrypto );
} );

afterEach( () => {
	stop();
	stop = () => {};
	cleanup();
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	document.body.replaceChildren();
	sessionStorage.clear();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	resetTurnLane();
} );

const field = () =>
	screen.getByRole< HTMLTextAreaElement >( 'textbox', { name: 'Ask Genie' } );

async function fixture() {
	const proof = deferred< string >();
	const identity = deferred< string >();
	let freshIdentityPending = false;
	let pendingIdentityReads = 0;
	const turnTransport = vi.fn< typeof fetch >( async ( _url, init ) => {
		expect( new Headers( init?.headers ).get( 'X-Linker-Proof' ) ).toBe(
			'synthetic-public-proof'
		);
		expect( JSON.parse( String( init?.body ) ).messages ).toEqual( [
			{ role: 'user', content: question },
		] );
		return new Response(
			JSON.stringify( {
				stream:
					`event: block\ndata: ${ JSON.stringify( {
						type: 'text',
						text: answer,
						refs: [],
					} ) }\n\n` + 'event: done\ndata: {"ok":true}\n\n',
			} )
		);
	} );
	vi.stubGlobal(
		'fetch',
		vi.fn< typeof fetch >( async ( url, init ) => {
			const path = String( url );
			if ( path.includes( '/entry-context' ) ) {
				if ( freshIdentityPending ) {
					pendingIdentityReads += 1;
				}
				const scope = freshIdentityPending
					? await identity.promise
					: scopeA;
				return new Response( JSON.stringify( { scope } ) );
			}
			if ( path.endsWith( '/conversations' ) ) {
				return new Response(
					JSON.stringify( { conversations: [], current_id: 0 } )
				);
			}
			if ( path.endsWith( '/conversation' ) ) {
				return new Response(
					JSON.stringify( { messages: [], stream: '' } )
				);
			}
			if ( path.endsWith( '/genie/turn' ) ) {
				return turnTransport( url, init );
			}
			throw new Error(
				`Unexpected verification consumer HTTP: ${ path }`
			);
		} )
	);
	const client = {
		proof: vi.fn( () => proof.promise ),
		reset: vi.fn(),
		cancel: vi.fn( () => true ),
	};
	window.linkerPublicProtectionConfig = {
		api: '/wp-json/linker/v1/protection',
		nonce: 'synthetic-verification-nonce',
		mode: 'enforce',
		language: 'en',
	};
	window.linkerPublicProtection = client;
	const mountPoint = document.createElement( 'div' );
	mountPoint.dataset.restNonce = 'synthetic-native-owner';
	const ui = render( <App config={ readConfig( mountPoint ) } /> );
	stop = ui.unmount;
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	fireEvent.input( field(), { target: { value: question } } );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await waitFor( () => expect( client.proof ).toHaveBeenCalledOnce() );
	expect( turnTransport ).not.toHaveBeenCalled();
	// The native focus handler starts actual DraftContext.verify(true).
	freshIdentityPending = true;
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( pendingIdentityReads ).toBe( 1 );
	await act( async () => proof.resolve( 'synthetic-public-proof' ) );
	// Public proof is ready; the native identity read is deliberately unresolved.
	expect( turnTransport ).not.toHaveBeenCalled();
	return { identity, turnTransport };
}

test( 'proof finishing during a native identity check waits, then the same owner dispatches exactly once', async () => {
	const f = await fixture();
	await act( async () => f.identity.resolve( scopeA ) );
	await screen.findByText( answer );
	expect( f.turnTransport ).toHaveBeenCalledOnce();
} );

test( 'proof finishing during a native identity check cannot dispatch or transfer the old question to a new owner', async () => {
	const f = await fixture();
	await act( async () => f.identity.resolve( scopeB ) );
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	expect( f.turnTransport ).not.toHaveBeenCalled();
	expect( field() ).toHaveValue( '' );
	expect( screen.queryByText( question ) ).not.toBeInTheDocument();
	expect( screen.queryByText( answer ) ).not.toBeInTheDocument();
	await act( async () => window.dispatchEvent( new Event( 'pagehide' ) ) );
	expect(
		new FailureJournal( sessionStorage, {
			scope: scopeB,
			persistent: true,
		} ).candidate()
	).toBeNull();
} );
