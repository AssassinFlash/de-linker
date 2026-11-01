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

const commerceModules = import.meta.glob(
	'../../../linker-commerce/src/protection/client.ts',
	{ eager: true }
);
const { ProtectionClient } = Object.values( commerceModules )[ 0 ] as {
	ProtectionClient: new (
		config: NonNullable< Window[ 'linkerPublicProtectionConfig' ] >
	) => NonNullable< Window[ 'linkerPublicProtection' ] >;
};

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
	window.linkerPublicProtection?.reset( 'genie' );
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	Reflect.deleteProperty( window, 'turnstile' );
	Reflect.deleteProperty( document, 'visibilityState' );
	vi.useRealTimers();
	document.body.replaceChildren();
	sessionStorage.clear();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	resetTurnLane();
} );

test.each( [
	[ 'new', 'timeout' ],
	[ 'new', 'cancel' ],
	[ 'delete', 'timeout' ],
] as const )(
	'sending during a pending %s conversation preserves the question through verification %s',
	async ( operation, outcome ) => {
		let interactive!: () => void;
		let complete!: ( token: string ) => void;
		const selection = deferred< Response >();
		let opened = false;
		const history = [ { id: 547, title: 'Earlier conversation' } ];
		const widgets = [ deferred< void >(), deferred< void >() ];
		let rendered = 0;
		const renderWidget = vi.fn(
			(
				_node: HTMLElement,
				options: {
					callback: ( token: string ) => void;
					'before-interactive-callback': () => void;
				}
			) => {
				interactive = options[ 'before-interactive-callback' ];
				complete = options.callback;
				widgets[ rendered++ ]?.resolve();
				return 'synthetic-widget';
			}
		);
		Object.assign( window, {
			turnstile: { render: renderWidget, remove: vi.fn() },
		} );
		const config = {
			api: 'https://site.test/proof',
			nonce: 'synthetic',
			mode: 'enforce',
			language: 'de' as const,
		};
		const sentBodies: string[] = [];
		const turn = vi.fn(
			async () =>
				new Response(
					JSON.stringify( {
						stream: `event: block\ndata: ${ JSON.stringify( { type: 'text', text: answer, refs: [] } ) }\n\nevent: done\ndata: {"ok":true}\n\n`,
					} )
				)
		);
		vi.stubGlobal(
			'fetch',
			vi.fn< typeof fetch >( async ( url, init ) => {
				const path = String( url );
				if ( path.includes( '/entry-context' ) ) {
					return new Response( JSON.stringify( { scope: scopeA } ) );
				}
				if (
					path.endsWith( '/conversations' ) &&
					init?.method === 'POST'
				) {
					return selection.promise;
				}
				if (
					path.endsWith( '/conversations/547' ) &&
					init?.method === 'DELETE'
				) {
					return selection.promise;
				}
				if ( path.endsWith( '/conversations' ) ) {
					return new Response(
						JSON.stringify( {
							conversations: history,
							current_id: opened ? 548 : 547,
						} )
					);
				}
				if (
					path.includes( '/conversation?' ) ||
					path.endsWith( '/conversation' )
				) {
					return new Response(
						JSON.stringify( {
							conversation_id: opened ? 548 : 547,
							messages: opened
								? []
								: [
										{
											role: 'user',
											content: 'Previous question',
										},
									],
							stream: '',
						} )
					);
				}
				if ( path.includes( '/prepare?' ) ) {
					return new Response(
						JSON.stringify( {
							site_key: 'synthetic',
							prepare: 'synthetic',
						} )
					);
				}
				if ( path.includes( '/verify?' ) ) {
					return new Response(
						JSON.stringify( { proof: 'synthetic', ttl: 300 } )
					);
				}
				if ( path.endsWith( '/genie/turn' ) ) {
					if ( ! opened ) {
						return new Response( '', { status: 503 } );
					}
					sentBodies.push( String( init?.body ) );
					return turn();
				}
				throw new Error( `Unexpected fixture HTTP: ${ path }` );
			} )
		);
		const mount = document.createElement( 'div' );
		mount.dataset.surface = 'workspace';
		mount.dataset.locale = 'de';
		mount.dataset.restNonce = 'synthetic';
		const ui = render( <App config={ readConfig( mount ) } /> );
		stop = ui.unmount;
		await screen.findByText( 'Previous question' );
		fireEvent.input( field(), {
			target: { value: 'Previous unsent question' },
		} );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
		);
		await waitFor( () =>
			expect( field() ).toHaveValue( 'Previous unsent question' )
		);
		if ( operation === 'new' ) {
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', { name: 'New conversation' } )
				)
			);
		} else {
			fireEvent.click(
				await screen.findByRole( 'button', {
					name: 'Delete conversation: Earlier conversation',
				} )
			);
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', { name: 'Delete' } )
				)
			);
		}
		await waitFor( () =>
			expect(
				vi
					.mocked( fetch )
					.mock.calls.some( ( [ url, init ] ) =>
						operation === 'new'
							? String( url ).endsWith( '/conversations' ) &&
								init?.method === 'POST'
							: String( url ).endsWith( '/conversations/547' ) &&
								init?.method === 'DELETE'
					)
			).toBe( true )
		);
		expect( field() ).not.toBeDisabled();
		window.linkerPublicProtectionConfig = config;
		window.linkerPublicProtection = new ProtectionClient( config );
		vi.useFakeTimers();
		fireEvent.input( field(), { target: { value: question } } );
		await act( async () => {
			fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
		} );
		expect(
			new FailureJournal( sessionStorage, {
				scope: scopeA,
				persistent: true,
			} ).candidate()?.record
		).toMatchObject( { text: question } );
		opened = true;
		await act( async () =>
			selection.resolve(
				new Response(
					JSON.stringify( {
						conversation_id: 548,
						current_id: operation === 'delete' ? 0 : 548,
						conversations: history,
					} )
				)
			)
		);
		expect(
			new FailureJournal( sessionStorage, {
				scope: scopeA,
				persistent: true,
			} ).candidate()?.record
		).toMatchObject( { text: question } );
		await act( () => widgets[ 0 ].promise );
		expect( renderWidget ).toHaveBeenCalledOnce();
		await act( async () => interactive() );
		expect( screen.getByText( question ) ).toBeVisible();
		expect( screen.getByText( 'Checking verification…' ) ).toBeVisible();
		expect( turn ).not.toHaveBeenCalled();
		if ( outcome === 'timeout' ) {
			Object.defineProperty( document, 'visibilityState', {
				configurable: true,
				value: 'hidden',
			} );
			await act( async () =>
				document.dispatchEvent( new Event( 'visibilitychange' ) )
			);
			await act( async () => {
				await vi.advanceTimersByTimeAsync( 120_001 );
			} );
			Object.defineProperty( document, 'visibilityState', {
				configurable: true,
				value: 'visible',
			} );
			await act( async () => {
				document.dispatchEvent( new Event( 'visibilitychange' ) );
				window.dispatchEvent( new Event( 'focus' ) );
			} );
		} else {
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', {
						name: 'Cancel verification',
					} )
				)
			);
		}
		expect( field() ).toHaveValue( question );
		expect(
			screen
				.queryAllByRole( 'alert' )
				.some( ( alert ) =>
					alert.textContent?.includes(
						'Verification could not be completed'
					)
				)
		).toBe( outcome === 'timeout' );
		expect( turn ).not.toHaveBeenCalled();
		await act( async () => {
			fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
		} );
		await act( () => widgets[ 1 ].promise );
		expect( renderWidget ).toHaveBeenCalledTimes( 2 );
		await act( async () => complete( 'synthetic-token' ) );
		expect( screen.getByText( answer ) ).toBeVisible();
		expect( turn ).toHaveBeenCalledOnce();
		expect( JSON.parse( sentBodies[ 0 ] ).messages ).toEqual( [
			{ role: 'user', content: question },
		] );
		expect(
			new FailureJournal( sessionStorage, {
				scope: scopeA,
				persistent: true,
			} ).candidate()
		).toBeNull();
	}
);

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
