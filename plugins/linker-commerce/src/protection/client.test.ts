import { afterEach, expect, test, vi } from 'vitest';
import { ProtectionClient } from './client';
import type { TurnstileOptions } from './types';

afterEach( () => {
	vi.unstubAllGlobals();
	vi.useRealTimers();
	delete window.turnstile;
	document.body.replaceChildren();
} );

function fixture( api = 'https://example.test/wp-json/linker/v1/protection' ) {
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
		queueMicrotask( () => received.callback( 'synthetic-token' ) );
		return 'widget-id';
	} );
	window.turnstile = { render, reset: vi.fn(), remove: vi.fn() };
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
	[ 286.8, 'compact' ],
	[ 299.9, 'compact' ],
	[ 300, 'flexible' ],
	[ 326, 'flexible' ],
	[ 0, 'flexible' ],
] as const )(
	'a mount width of %s selects %s when rendering',
	async ( width, expected ) => {
		const f = fixture();
		vi.spyOn( f.container, 'getBoundingClientRect' ).mockReturnValue( {
			width,
		} as DOMRect );
		await expect( f.client.proof( 'genie', f.container ) ).resolves.toBe(
			'server-proof'
		);
		expect( f.options().size ).toBe( expected );
		expect( f.fetch ).toHaveBeenCalledTimes( 2 );
		f.client.reset( 'genie' );
	}
);

test( 'a running narrow challenge keeps its size, then a new retry measures its mount again', async () => {
	const f = fixture();
	let width = 286.8;
	vi.spyOn( f.container, 'getBoundingClientRect' ).mockImplementation(
		() => ( { width } ) as DOMRect
	);
	let options: TurnstileOptions;
	f.render.mockImplementation( ( _container, received ) => {
		options = received;
		return 'widget-id';
	} );
	const first = f.client.proof( 'genie', f.container );
	const failure = first.catch( ( error: unknown ) => error );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	expect( options!.size ).toBe( 'compact' );
	width = 326;
	expect( f.client.proof( 'genie', f.container ) ).toBe( first );
	expect( f.render ).toHaveBeenCalledOnce();
	options![ 'error-callback' ]( '110100' );
	expect( await failure ).toEqual(
		new Error( 'verification_widget_110100' )
	);
	f.render.mockImplementation( ( _container, received ) => {
		options = received;
		queueMicrotask( () => received.callback( 'provider-token' ) );
		return 'new-widget-id';
	} );
	await expect( f.client.proof( 'genie', f.container ) ).resolves.toBe(
		'server-proof'
	);
	expect( options!.size ).toBe( 'flexible' );
	expect( f.fetch ).toHaveBeenCalledTimes( 3 );
	f.client.reset( 'genie' );
} );

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
		appearance: 'always',
		size: 'flexible',
		retry: 'auto',
		'retry-interval': 8000,
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

test( 'a provider expiry publishes its own state instead of the generic failure', async () => {
	const f = fixture();
	const states: string[] = [];
	f.container.addEventListener( 'linker:protection', ( event ) =>
		states.push( ( event as CustomEvent ).detail.state )
	);
	f.render.mockImplementation( ( _container, options ) => {
		queueMicrotask( () => options[ 'expired-callback' ]() );
		return 'expiring-widget';
	} );
	await expect( f.client.proof( 'inquiry', f.container ) ).rejects.toThrow(
		'verification_expired'
	);
	// `failed` in the same tick would hide the accurate state from every
	// listener, leaving `expired` unreachable in ProtectionState.
	expect( states ).toEqual( [ 'checking', 'expired' ] );
	expect( f.container.dataset.linkerVerificationState ).toBe( 'expired' );
	expect( f.client.ready( 'inquiry', f.container ) ).toBe( '' );
} );

test( 'completed proof removes its widget and ignores its late expiry', async () => {
	const f = fixture();
	const states: string[] = [];
	f.container.addEventListener( 'linker:protection', ( event ) =>
		states.push( ( event as CustomEvent ).detail.state )
	);
	const proof = await f.client.proof( 'design', f.container );
	const old = f.options();

	expect( f.client.complete( 'design', proof ) ).toBe( true );
	expect( f.client.ready( 'design', f.container ) ).toBe( '' );
	expect( window.turnstile?.remove ).toHaveBeenCalledOnce();
	old[ 'expired-callback' ]();
	expect( states ).toEqual( [ 'checking', 'ready' ] );

	await f.client.proof( 'design', f.container );
	expect( f.fetch ).toHaveBeenCalledTimes( 4 );
	expect( f.render ).toHaveBeenCalledTimes( 2 );
	f.client.reset( 'design' );
} );

test( 'old completion and callbacks cannot retire or overwrite a newer scoped attempt', async () => {
	const f = fixture();
	const states: string[] = [];
	f.container.addEventListener( 'linker:protection', ( event ) =>
		states.push( ( event as CustomEvent ).detail.state )
	);
	const first = await f.client.proof( 'design', f.container );
	const old = f.options();
	f.client.reset( 'design' );
	f.fetch.mockResolvedValueOnce( {
		ok: true,
		json: async () => ( { site_key: 'public', prepare: 'new-stamp' } ),
	} );
	f.fetch.mockResolvedValueOnce( {
		ok: true,
		json: async () => ( { proof: 'new-proof', ttl: 300 } ),
	} );
	await f.client.proof( 'design', f.container );

	expect( f.client.complete( 'report_pdf', 'new-proof' ) ).toBe( false );
	expect( f.client.complete( 'design', first ) ).toBe( false );
	old[ 'expired-callback' ]();
	old[ 'error-callback' ]();
	old[ 'error-callback' ]( '300030' );
	old[ 'before-interactive-callback' ]();
	expect( f.client.ready( 'design', f.container ) ).toBe( 'new-proof' );
	expect( states ).toEqual( [ 'checking', 'ready', 'checking', 'ready' ] );
	expect( window.turnstile?.remove ).toHaveBeenCalledTimes( 1 );
	f.client.reset( 'design' );
} );

test( 'an old successful response cannot cancel a newer challenge still in progress', async () => {
	const f = fixture();
	const first = await f.client.proof( 'design', f.container );
	const old = f.options();
	f.client.reset( 'design' );
	let current: TurnstileOptions | undefined;
	f.render.mockImplementation( ( _container, options ) => {
		current = options;
		return 'new-widget';
	} );
	const work = f.client.proof( 'design', f.container );
	await vi.waitFor( () => expect( current ).toBeDefined() );
	expect( f.client.complete( 'design', first ) ).toBe( false );
	old[ 'expired-callback' ]();
	expect( window.turnstile?.remove ).toHaveBeenCalledTimes( 1 );
	current!.callback( 'new-token' );
	await expect( work ).resolves.toBe( 'server-proof' );
	expect( f.fetch ).toHaveBeenCalledTimes( 4 );
	f.client.reset( 'design' );
} );

test.each( [ 'expired-callback', 'error-callback' ] as const )(
	'%s before proof use still fails without validation',
	async ( callback ) => {
		const f = fixture();
		f.render.mockImplementation( ( _container, options ) => {
			queueMicrotask( () => options[ callback ]() );
			return 'failed-widget';
		} );
		await expect( f.client.proof( 'design', f.container ) ).rejects.toThrow(
			callback === 'expired-callback'
				? 'verification_expired'
				: 'verification_widget'
		);
		expect( f.fetch ).toHaveBeenCalledTimes( 1 );
		expect( f.client.ready( 'design', f.container ) ).toBe( '' );
	}
);

test( 'a nonretryable configuration error stays failed and retains only its fixed diagnostic', async () => {
	const f = fixture();
	f.render.mockImplementation( ( _container, options ) => {
		queueMicrotask( () => options[ 'error-callback' ]( '110100' ) );
		return 'invalid-widget';
	} );
	await expect(
		f.client.proof( 'registration', f.container )
	).rejects.toThrow( 'verification_widget_110100' );
	expect( f.fetch ).toHaveBeenCalledOnce();
	expect( window.turnstile?.remove ).toHaveBeenCalledOnce();
	expect( f.container.dataset.linkerVerificationError ).toBe( '110100' );
	expect( f.container.dataset.linkerVerificationState ).toBe( 'failed' );
} );

test( 'an unsupported client cannot obtain a proof or dispatch validation', async () => {
	const f = fixture();
	f.render.mockImplementation( ( _container, options ) => {
		queueMicrotask( () => options[ 'unsupported-callback' ]() );
		return 'unsupported-widget';
	} );
	await expect(
		f.client.proof( 'registration', f.container )
	).rejects.toThrow( 'verification_unsupported' );
	expect( f.fetch ).toHaveBeenCalledOnce();
	expect( f.container.dataset.linkerVerificationState ).toBe( 'failed' );
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
	window.turnstile = { render: f.render, reset: vi.fn(), remove: vi.fn() };
	await expect( f.client.proof( 'inquiry', f.container ) ).resolves.toBe(
		'server-proof'
	);
	f.client.reset( 'inquiry' );
} );

test.each( [ '110600', '110620', '200500' ] )(
	'official retryable %s uses its reset/auto contract within the same attempt',
	async ( code ) => {
		vi.useFakeTimers();
		const f = fixture();
		let options: TurnstileOptions;
		f.render.mockImplementation( ( _container, received ) => {
			options = received;
			queueMicrotask( () => received[ 'error-callback' ]( code ) );
			if ( code === '200500' ) {
				setTimeout(
					() => received.callback( 'native-retry-token' ),
					8000
				);
			}
			return 'retry-widget';
		} );
		const reset = vi.fn( () => options.callback( 'native-reset-token' ) );
		window.turnstile!.reset = reset;
		const work = f.client.proof( 'registration', f.container );
		await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
		expect( f.container.dataset.linkerVerificationState ).toBe(
			'retrying'
		);
		expect( f.fetch ).toHaveBeenCalledOnce();
		expect( window.turnstile?.remove ).not.toHaveBeenCalled();
		await vi.advanceTimersByTimeAsync( 8000 );
		await expect( work ).resolves.toBe( 'server-proof' );
		expect( f.fetch ).toHaveBeenCalledTimes( 2 );
		expect( f.render ).toHaveBeenCalledOnce();
		expect( reset.mock.calls ).toEqual(
			code === '200500' ? [] : [ [ 'retry-widget' ] ]
		);
		expect( vi.getTimerCount() ).toBe( 0 );
		f.client.reset( 'registration' );
	}
);

test( 'one native challenge retry can still produce a real verified proof', async () => {
	const f = fixture();
	let options: TurnstileOptions;
	f.render.mockImplementation( ( _container, received ) => {
		options = received;
		return 'retry-widget';
	} );
	const work = f.client.proof( 'genie', f.container );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	options![ 'error-callback' ]( '300030' );
	options![ 'before-interactive-callback' ]();
	options![ 'error-callback' ]( '300030' );
	options!.callback( 'provider-retry-token' );
	await expect( work ).resolves.toBe( 'server-proof' );
	expect( f.fetch ).toHaveBeenCalledTimes( 2 );
	expect( JSON.parse( f.fetch.mock.calls[ 1 ][ 1 ].body as string ) ).toEqual(
		{
			action: 'genie',
			prepare: 'prepare-stamp',
			token: 'provider-retry-token',
		}
	);
	applySingleCompletion( f.client, f.container );
} );

test( 'a different challenge diagnostic is not treated as the same repeated failure', async () => {
	const f = fixture();
	let options: TurnstileOptions;
	f.render.mockImplementation( ( _container, received ) => {
		options = received;
		return 'retry-widget';
	} );
	const work = f.client.proof( 'genie', f.container );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	options![ 'error-callback' ]( '300030' );
	options![ 'error-callback' ]( '600010' );
	expect( f.container.dataset.linkerVerificationState ).toBe( 'retrying' );
	options!.callback( 'provider-retry-token' );
	await expect( work ).resolves.toBe( 'server-proof' );
	applySingleCompletion( f.client, f.container );
} );

test( 'two challenge execution failures without interaction stop the wait across timeout callbacks', async () => {
	vi.useFakeTimers();
	const f = fixture();
	let options: TurnstileOptions;
	f.render.mockImplementation( ( _container, received ) => {
		options = received;
		return 'retry-widget';
	} );
	const work = f.client.proof( 'genie', f.container );
	const failure = work.catch( ( error: unknown ) => error );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	options![ 'error-callback' ]( '300030' );
	expect( f.container.dataset.linkerVerificationState ).toBe( 'retrying' );
	options![ 'error-callback' ]( '300030' );
	expect( f.container.dataset.linkerVerificationState ).toBe( 'retrying' );
	expect( window.turnstile?.remove ).not.toHaveBeenCalled();
	await vi.advanceTimersByTimeAsync( 8000 );
	options![ 'timeout-callback' ]();
	options![ 'error-callback' ]( '300030' );
	expect( await failure ).toEqual(
		new Error( 'verification_widget_300030' )
	);
	expect( f.container.dataset.linkerVerificationState ).toBe( 'failed' );
	expect( window.turnstile?.remove ).toHaveBeenCalledOnce();
	expect( f.fetch ).toHaveBeenCalledOnce();
	expect( vi.getTimerCount() ).toBe( 0 );
	options!.callback( 'too-late' );
	await Promise.resolve();
	expect( f.fetch ).toHaveBeenCalledOnce();
	expect( f.client.ready( 'genie', f.container ) ).toBe( '' );
	f.render.mockImplementation( ( _container, received ) => {
		queueMicrotask( () => received.callback( 'recovered-provider-token' ) );
		return 'recovered-widget';
	} );
	await expect( f.client.proof( 'genie', f.container ) ).resolves.toBe(
		'server-proof'
	);
	expect( f.fetch ).toHaveBeenCalledTimes( 3 );
	applySingleCompletion( f.client, f.container );
} );

function applySingleCompletion(
	client: ProtectionClient,
	container: HTMLElement
) {
	expect( client.complete( 'genie', 'server-proof' ) ).toBe( true );
	expect( client.complete( 'genie', 'server-proof' ) ).toBe( false );
	expect( client.ready( 'genie', container ) ).toBe( '' );
}

test.each( [ 'prepare', 'verify' ] )(
	'%s network/JSON failure stays a pre-dispatch verification failure',
	async ( operation ) => {
		for ( const cause of [
			new TypeError( 'synthetic network failure' ),
			new SyntaxError( 'synthetic invalid response' ),
		] ) {
			const f = fixture();
			if ( operation === 'verify' ) {
				f.fetch.mockResolvedValueOnce( {
					ok: true,
					json: async () => ( {
						site_key: 'public',
						prepare: 'stamp',
					} ),
				} );
			}
			if ( cause instanceof SyntaxError ) {
				f.fetch.mockResolvedValueOnce( {
					ok: true,
					json: async () => {
						throw cause;
					},
				} );
			} else {
				f.fetch.mockRejectedValueOnce( cause );
			}
			const error = await f.client
				.proof( 'genie', f.container )
				.catch( ( failure: unknown ) => failure );
			expect( error ).toMatchObject( {
				message:
					cause instanceof SyntaxError
						? 'verification_response'
						: 'verification_network',
				cause,
			} );
			expect( f.client.ready( 'genie', f.container ) ).toBe( '' );
			expect( f.fetch ).toHaveBeenCalledTimes(
				operation === 'prepare' ? 1 : 2
			);
		}
	}
);

test( 'the verification network deadline is distinct from the model deadline', async () => {
	vi.useFakeTimers();
	const f = fixture();
	f.fetch.mockImplementationOnce(
		async ( _url, init ) =>
			new Promise( ( _resolve, reject ) => {
				init.signal!.addEventListener( 'abort', () =>
					reject(
						new DOMException(
							'synthetic network abort',
							'AbortError'
						)
					)
				);
			} )
	);
	const outcome = f.client
		.proof( 'genie', f.container )
		.catch( ( error: unknown ) => error );
	await vi.advanceTimersByTimeAsync( 15000 );
	expect( await outcome ).toMatchObject( {
		message: 'verification_network_timeout',
		cause: { name: 'AbortError' },
	} );
	expect( f.render ).not.toHaveBeenCalled();
	expect( f.fetch ).toHaveBeenCalledOnce();
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'closing a surface cancels only its widget and ignores a late challenge response', async () => {
	vi.useFakeTimers();
	const f = fixture();
	let options: TurnstileOptions;
	f.render.mockImplementation( ( _container, received ) => {
		options = received;
		return 'owned-widget';
	} );
	const outcome = f.client
		.proof( 'genie', f.container )
		.catch( ( error: unknown ) => error );
	await vi.waitFor( () => expect( f.render ).toHaveBeenCalledOnce() );
	expect( f.client.cancel( 'genie', document.createElement( 'div' ) ) ).toBe(
		false
	);
	expect( f.client.cancel( 'genie', f.container ) ).toBe( true );
	expect( await outcome ).toEqual( new Error( 'verification_cancelled' ) );
	options!.callback( 'late-provider-token' );
	await vi.advanceTimersByTimeAsync( 0 );
	expect( f.fetch ).toHaveBeenCalledOnce();
	expect( window.turnstile?.remove ).toHaveBeenCalledOnce();
	expect( vi.getTimerCount() ).toBe( 0 );
} );
