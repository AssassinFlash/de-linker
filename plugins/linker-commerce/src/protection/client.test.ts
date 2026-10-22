import { afterEach, expect, test, vi } from 'vitest';
import { ProtectionClient } from './client';
import type { TurnstileOptions } from './types';

afterEach( () => {
	vi.unstubAllGlobals();
	vi.useRealTimers();
	delete window.turnstile;
	document.body.replaceChildren();
} );

function fixture(
	api = 'https://example.test/wp-json/linker/v1/protection',
	autoResolve = true
) {
	const container = document.createElement( 'div' );
	document.body.append( container );
	const client = new ProtectionClient( {
		api,
		nonce: 'nonce',
		mode: 'enforce',
		language: 'de',
	} );
	let options: TurnstileOptions;
	const render = vi.fn( ( _container, received: TurnstileOptions ) => {
		options = received;
		if ( autoResolve ) {
			queueMicrotask( () => received.callback( 'synthetic-token' ) );
		}
		return 'widget-id';
	} );
	window.turnstile = { render, remove: vi.fn() };
	const fetch = vi.fn<
		(
			url: string,
			input: RequestInit
		) => Promise< { ok: boolean; json: () => Promise< unknown > } >
	>( async ( url ) => ( {
		ok: true,
		json: async () =>
			url.includes( 'prepare' )
				? { site_key: 'public-key', prepare: 'prepare-stamp' }
				: {
						proof: 'server-proof',
						expires: Math.floor( Date.now() / 1000 ) + 300,
						ttl: 300,
					},
	} ) );
	vi.stubGlobal( 'fetch', fetch );
	return { client, container, render, fetch, options: () => options };
}

test.each( [
	'https://example.test/wp-json/linker/v1/protection',
	'https://example.test/?rest_route=%2Flinker%2Fv1%2Fprotection',
] )( 'lazy, scoped proof and concurrent reuse for %s', async ( api ) => {
	const f = fixture( api );
	expect( f.fetch ).not.toHaveBeenCalled();
	expect( f.render ).not.toHaveBeenCalled();
	const first = f.client.warm( 'inquiry', f.container );
	expect( f.client.proof( 'inquiry', f.container ) ).toBe( first );
	await expect( first ).resolves.toBe( 'server-proof' );
	await expect( f.client.proof( 'inquiry', f.container ) ).resolves.toBe(
		'server-proof'
	);
	expect( f.fetch ).toHaveBeenCalledTimes( 2 );
	expect( f.render ).toHaveBeenCalledTimes( 1 );
	expect( f.options() ).toMatchObject( {
		action: 'inquiry',
		language: 'de',
		appearance: 'interaction-only',
	} );
	const [ url, input ] = f.fetch.mock.calls[ 1 ] as unknown as [
		string,
		RequestInit,
	];
	const endpoint = new URL( url );
	expect(
		endpoint.searchParams.get( 'rest_route' ) || endpoint.pathname
	).toContain( '/protection/verify' );
	expect( JSON.parse( input.body as string ) ).toEqual( {
		action: 'inquiry',
		prepare: 'prepare-stamp',
		token: 'synthetic-token',
	} );
	f.client.reset( 'inquiry' );
} );

test( 'only an interactive current challenge scrolls into view', async () => {
	const f = fixture( undefined, false );
	const scroll = vi.fn();
	f.container.scrollIntoView = scroll;
	const pending = f.client.proof( 'report_pdf', f.container );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	expect( scroll ).not.toHaveBeenCalled();
	expect( f.options() ).toHaveProperty(
		'before-interactive-callback',
		expect.any( Function )
	);
	const interactive = Reflect.get(
		f.options(),
		'before-interactive-callback'
	) as () => void;
	// A wall-clock jump is not a provider expiry or the running challenge timer.
	vi.spyOn( Date, 'now' ).mockReturnValue( Date.now() + 120001 );
	interactive();
	f.options().callback( 'synthetic-token' );
	await expect( pending ).resolves.toBe( 'server-proof' );
	interactive();
	expect( scroll ).toHaveBeenCalledExactlyOnceWith( {
		block: 'center',
		inline: 'nearest',
	} );
	f.client.reset( 'report_pdf' );
} );

test( 'cancelled, replaced and disconnected challenges cannot scroll the visitor', async () => {
	const f = fixture( undefined, false );
	const scroll = vi.fn();
	f.container.scrollIntoView = scroll;
	const first = f.client.proof( 'report_pdf', f.container );
	const cancelled = first.catch( ( error: unknown ) => error );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	const staleInteractive = Reflect.get(
		f.options(),
		'before-interactive-callback'
	) as () => void;
	f.client.reset( 'report_pdf' );
	expect( await cancelled ).toEqual( new Error( 'verification_cancelled' ) );
	const next = f.client.proof( 'report_pdf', f.container );
	const nextCancelled = next.catch( ( error: unknown ) => error );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledTimes( 2 ) );
	expect( staleInteractive ).toBeTypeOf( 'function' );
	staleInteractive();
	f.container.remove();
	const interactive = Reflect.get(
		f.options(),
		'before-interactive-callback'
	) as () => void;
	interactive();
	expect( scroll ).not.toHaveBeenCalled();
	f.client.reset( 'report_pdf' );
	expect( await nextCancelled ).toEqual(
		new Error( 'verification_cancelled' )
	);
} );

test( 'failed validation leaves form input intact and a fresh attempt can recover', async () => {
	const f = fixture();
	const input = document.createElement( 'textarea' );
	input.value = 'Customer inquiry retained';
	f.container.append( input );
	f.fetch.mockResolvedValueOnce( {
		ok: true,
		json: async () => ( { site_key: 'public', prepare: 'stamp' } ),
	} );
	f.fetch.mockResolvedValueOnce( { ok: false, json: async () => ( {} ) } );
	await expect( f.client.proof( 'inquiry', f.container ) ).rejects.toThrow(
		'verification_http_'
	);
	expect( input.value ).toBe( 'Customer inquiry retained' );
	await expect( f.client.proof( 'inquiry', f.container ) ).resolves.toBe(
		'server-proof'
	);
	expect( f.render ).toHaveBeenCalledTimes( 2 );
	f.client.reset( 'inquiry' );
} );

test( 'expiry requires a new scoped proof and never reuses the completed one', async () => {
	const f = fixture();
	await f.client.proof( 'inquiry', f.container );
	f.options()[ 'expired-callback' ]();
	await expect( f.client.proof( 'inquiry', f.container ) ).resolves.toBe(
		'server-proof'
	);
	expect( f.fetch ).toHaveBeenCalledTimes( 4 );
	f.client.reset( 'inquiry' );
} );

test( 'provider script failure is retryable and never sends a token to validation', async () => {
	const f = fixture();
	delete window.turnstile;
	const attempt = f.client.proof( 'inquiry', f.container );
	const failure = attempt.catch( ( error: unknown ) => error );
	await vi.waitFor( () =>
		expect(
			document.querySelector( 'script[src*="challenges.cloudflare.com"]' )
		).not.toBeNull()
	);
	document
		.querySelector< HTMLScriptElement >(
			'script[src*="challenges.cloudflare.com"]'
		)
		?.dispatchEvent( new Event( 'error' ) );
	expect( await failure ).toEqual( new Error( 'verification_script' ) );
	expect( f.fetch ).toHaveBeenCalledTimes( 1 );
	window.turnstile = { render: f.render, remove: vi.fn() };
	await expect( f.client.proof( 'inquiry', f.container ) ).resolves.toBe(
		'server-proof'
	);
	f.client.reset( 'inquiry' );
} );
