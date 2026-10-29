/// <reference types="vite/client" />
/** The real Commerce client, resource adapter and Genie transport together. */
import { webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, expect, test, vi } from 'vitest';
import { sendTurn, TURN_VERIFICATION_TIMEOUT_MS } from './turn';

// A runtime boundary, as on the actual page. Do not merge the two plugins'
// independent Window type declarations into either production compilation.
const commerceModules = import.meta.glob(
	'../../../../linker-commerce/src/protection/client.ts',
	{ eager: true }
);
const { ProtectionClient } = Object.values( commerceModules )[ 0 ] as {
	ProtectionClient: new (
		config: NonNullable< Window[ 'linkerPublicProtectionConfig' ] >
	) => NonNullable< Window[ 'linkerPublicProtection' ] >;
};

interface Widget {
	callback: ( token: string ) => void;
	'error-callback': ( code: string ) => void;
	'before-interactive-callback': () => void;
}

const question = 'Customer question retained';
const answer = JSON.stringify( {
	stream:
		'event: block\ndata: {"type":"text","text":"Answer","refs":[]}\n\n' +
		'event: done\ndata: {"ok":true}\n\n',
} );

afterEach( () => {
	window.linkerPublicProtection?.reset( 'genie' );
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	Reflect.deleteProperty( window, 'turnstile' );
	document.body.replaceChildren();
	vi.useRealTimers();
	vi.unstubAllGlobals();
} );

function fixture( challenge: ( options: Widget ) => void ) {
	vi.useFakeTimers();
	vi.stubGlobal( 'crypto', webcrypto );
	// The mounted Genie surface: its own slot for the widget the proof lives in
	// (#548). Without it the turn would be an ordinary request with one 90-second
	// limit for everything, which is not the path this test is about.
	document.body.innerHTML = `<main><form><textarea>${ question }</textarea></form><div data-linker-resource-verification-slot hidden></div></main>`;
	const form = document.querySelector( 'form' )!;
	// jsdom has no layout; this is the real resource adapter's visible form.
	form.getClientRects = () => ( { length: 1 } ) as DOMRectList;
	const slot = document.querySelector< HTMLElement >(
		'[data-linker-resource-verification-slot]'
	)!;
	const config = {
		api: 'https://site.test/wp-json/linker/v1/protection',
		nonce: 'synthetic',
		mode: 'enforce',
		language: 'en' as const,
	};
	window.linkerPublicProtectionConfig = config;
	window.linkerPublicProtection = new ProtectionClient( config );
	const validation = vi.fn(
		async ( url: string ) =>
			new Response(
				JSON.stringify(
					url.includes( '/prepare' )
						? {
								site_key: 'synthetic-public',
								prepare: 'synthetic-stamp',
							}
						: { proof: 'signed-proof', ttl: 300 }
				)
			)
	);
	vi.stubGlobal( 'fetch', validation );
	let nativeRetry: ReturnType< typeof setTimeout > | undefined;
	const remove = vi.fn( () => clearTimeout( nativeRetry ) );
	const render = vi.fn( ( _container: HTMLElement, options: Widget ) => {
		challenge( options );
		return 'native-widget';
	} );
	Object.assign( window, { turnstile: { render, remove } } );
	const transport = vi.fn< typeof fetch >( async ( _input, init ) => {
		expect( new Headers( init?.headers ).get( 'X-Linker-Proof' ) ).toBe(
			'signed-proof'
		);
		return new Response( answer );
	} );
	let outcome: unknown;
	const pending = sendTurn( {
		turnUrl: 'https://site.test/wp-json/linker-ai/v1/genie/turn',
		nonce: 'synthetic',
		locale: 'en',
		messages: [ { role: 'user', content: question } ],
		page: { type: 'tool' },
		fetcher: transport,
		verification: {
			slot: () => slot,
			signal: new AbortController().signal,
			challenge: true,
			onDispatch: () => undefined,
		},
	} ).then(
		( value ) => {
			outcome = value;
		},
		( error: unknown ) => {
			outcome = error;
		}
	);
	return {
		validation,
		transport,
		render,
		remove,
		pending,
		outcome: () => outcome,
		retry: ( callback: () => void ) => {
			nativeRetry = setTimeout( callback, 8000 );
		},
	};
}

test( 'a retryable 300030 keeps the same visible check and sends exactly once after validation', async () => {
	const f = fixture( ( options ) => {
		queueMicrotask( () => options[ 'error-callback' ]( '300030' ) );
		f.retry( () => options.callback( 'valid-native-token' ) );
	} );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	await vi.advanceTimersByTimeAsync( 0 );
	expect( f.outcome() ).toBeUndefined();
	expect( f.remove ).not.toHaveBeenCalled();
	expect( f.transport ).not.toHaveBeenCalled();
	const widget = document.querySelector< HTMLElement >(
		'[data-linker-resource-verification="genie"]'
	)!;
	expect( widget.dataset.linkerVerificationState ).toBe( 'retrying' );
	expect( widget.dataset.linkerVerificationError ).toBe( '300030' );
	expect( widget.hidden ).toBe( false );
	expect( document.querySelector( '[role="status"]' ) ).toHaveTextContent(
		'Verification is being retried. No request has been sent in this attempt.'
	);
	await vi.advanceTimersByTimeAsync( 8000 );
	await f.pending;
	expect( f.outcome() ).toMatchObject( {
		blocks: [ { type: 'text', text: 'Answer' } ],
	} );
	expect( f.validation ).toHaveBeenCalledTimes( 2 );
	expect( f.transport ).toHaveBeenCalledOnce();
	expect( document.querySelector( 'textarea' ) ).toHaveValue( question );
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'human interaction can use 110 seconds before the unchanged response window begins', async () => {
	const f = fixture( ( options ) => {
		queueMicrotask( () => options[ 'before-interactive-callback' ]() );
		setTimeout( () => options.callback( 'valid-human-token' ), 110_000 );
	} );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	await vi.advanceTimersByTimeAsync( 90_001 );
	expect( f.outcome() ).toBeUndefined();
	expect( f.transport ).not.toHaveBeenCalled();
	expect( document.querySelector( '[role="status"]' ) ).toHaveTextContent(
		'No request has been sent in this attempt. Please complete the verification.'
	);
	await vi.advanceTimersByTimeAsync( 20_000 );
	await f.pending;
	expect( f.outcome() ).toMatchObject( {
		blocks: [ { type: 'text', text: 'Answer' } ],
	} );
	expect( f.transport ).toHaveBeenCalledOnce();
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'repeated provider failures retain input but cannot extend the challenge deadline or dispatch', async () => {
	let repeated: ReturnType< typeof setInterval >;
	const f = fixture( ( options ) => {
		queueMicrotask( () => options[ 'error-callback' ]( '300030' ) );
		repeated = setInterval(
			() => options[ 'error-callback' ]( '300030' ),
			8000
		);
	} );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	await vi.advanceTimersByTimeAsync( 119_000 );
	expect( f.outcome() ).toBeUndefined();
	await vi.advanceTimersByTimeAsync( 1000 );
	await f.pending;
	clearInterval( repeated! );
	expect( f.outcome() ).toEqual( new Error( 'verification_timeout' ) );
	expect( f.remove ).toHaveBeenCalledOnce();
	expect( f.validation ).toHaveBeenCalledOnce();
	expect( f.transport ).not.toHaveBeenCalled();
	expect( document.querySelector( 'textarea' ) ).toHaveValue( question );
	// The mounted Genie surface owns this failure: the adapter collapses its
	// slot and the shell's own banner is the one thing the customer reads,
	// rather than a second detached status left in the document.
	expect(
		document.querySelector( '[data-linker-resource-verification-slot]' )
	).toHaveProperty( 'hidden', true );
	expect( document.querySelector( '[role="status"]' ) ).toBeNull();
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'the verification bound and the shared client lifetime are one number', () => {
	// The Commerce client owns the terms of this bound (src/protection/client.ts:
	// three network steps plus one challenge window). Keeping a second run-time
	// configuration here would let a change there silently shorten or lengthen
	// Genie's preparation.
	const client = readFileSync(
		join(
			dirname( fileURLToPath( import.meta.url ) ),
			'../../../../linker-commerce/src/protection/client.ts'
		),
		'utf8'
	);
	const constant = ( name: string ) => {
		const match = new RegExp(
			`const\\s+${ name }\\s*=\\s*([\\d_]+)\\s*;`
		).exec( client );
		expect( match, `${ name } in the Commerce client` ).not.toBeNull();
		return Number( match![ 1 ].replace( /_/g, '' ) );
	};
	expect( TURN_VERIFICATION_TIMEOUT_MS ).toBe(
		3 * constant( 'NETWORK_MS' ) + constant( 'CHALLENGE_MS' )
	);
} );
