import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { resourceAction, resourceFetch } from './request';
import { resourceRefusalReason } from '../genie/shared/resourceFailure';

beforeEach( () => {
	vi.stubGlobal( 'crypto', webcrypto );
	document.body.innerHTML =
		'<main><form><textarea>Keep this project question</textarea><button>Send</button></form></main>';
	window.linkerPublicProtectionConfig = {
		api: 'https://site.test/wp-json/linker/v1/protection',
		nonce: 'synthetic',
		mode: 'enforce',
		language: 'en',
	};
	window.linkerPublicProtection = {
		proof: vi.fn( async () => 'synthetic-proof' ),
		reset: vi.fn(),
	};
} );

afterEach( () => {
	delete window.linkerPublicProtectionConfig;
	delete window.linkerPublicProtection;
	vi.unstubAllGlobals();
} );

test( 'reads never create proof/model work; selecting history uses a write scope', async () => {
	const fetcher = vi.fn< typeof fetch >( async () => new Response( '{}' ) );
	await resourceFetch(
		fetcher,
		'https://site.test/wp-json/linker-ai/v1/genie/conversation'
	);
	expect( window.linkerPublicProtection?.proof ).not.toHaveBeenCalled();
	expect(
		resourceAction(
			'https://site.test/wp-json/linker-ai/v1/genie/conversations',
			'POST',
			'{"id":12}'
		)
	).toBe( 'conversation_write' );
	expect(
		resourceAction(
			'https://site.test/WP-JSON/linker-ai/v1/GENIE/TURN',
			'POST'
		)
	).toBe( 'genie' );
	expect(
		resourceAction(
			'https://site.test/?rest_route=/linker-ai/v1/engine/roof/pack',
			'POST'
		)
	).toBe( 'roof' );
} );

test( 'an ambiguous retry retains UUID; a successful explicit action gets a new UUID', async () => {
	const complete = vi.fn( () => true );
	window.linkerPublicProtection!.complete = complete;
	const seen: string[] = [];
	let calls = 0;
	const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
		seen.push(
			new Headers( init?.headers ).get( 'X-Linker-Operation' ) ?? ''
		);
		expect( new Headers( init?.headers ).get( 'X-Linker-Proof' ) ).toBe(
			'synthetic-proof'
		);
		if ( calls++ === 0 ) {
			throw new TypeError( 'synthetic lost reply' );
		}
		return new Response( '{}' );
	} );
	const input = {
		method: 'POST',
		body: '{"messages":[{"role":"user","content":"synthetic retry"}]}',
	};
	const url = 'https://site.test/wp-json/linker-ai/v1/genie/turn';
	await expect( resourceFetch( fetcher, url, input ) ).rejects.toThrow(
		'lost reply'
	);
	expect( complete ).not.toHaveBeenCalled();
	await resourceFetch( fetcher, url, input );
	await resourceFetch( fetcher, url, input );
	expect( complete.mock.calls ).toEqual( [
		[ 'genie', 'synthetic-proof' ],
		[ 'genie', 'synthetic-proof' ],
	] );
	expect( seen[ 0 ] ).toBe( seen[ 1 ] );
	expect( seen[ 2 ] ).not.toBe( seen[ 1 ] );
	expect( input ).toEqual( {
		method: 'POST',
		body: '{"messages":[{"role":"user","content":"synthetic retry"}]}',
	} );
} );

test.each( [ 'design/residential', 'roof/pack', 'report/pdf' ] )(
	'only actual successful %s completion clears its verification status',
	async ( route ) => {
		window.linkerPublicProtection!.proof = vi.fn(
			async ( action, container ) => {
				container.dispatchEvent(
					new CustomEvent( 'linker:protection', {
						detail: { action, state: 'expired' },
					} )
				);
				return 'synthetic-proof';
			}
		);
		const complete = vi.fn( () => true );
		window.linkerPublicProtection!.complete = complete;
		const url = `https://site.test/wp-json/linker-ai/v1/engine/${ route }`;
		await resourceFetch(
			vi.fn( async () => new Response( '{}' ) ),
			url,
			{
				method: 'POST',
				body: '{}',
			}
		);
		expect( complete ).toHaveBeenCalledWith(
			resourceAction( url, 'POST' ),
			'synthetic-proof'
		);
		expect( document.querySelector( '[role="status"]' )?.textContent ).toBe(
			''
		);
	}
);

test( 'an old response cannot clear the status of a newer proof', async () => {
	window.linkerPublicProtection!.proof = vi.fn(
		async ( action, container ) => {
			container.dispatchEvent(
				new CustomEvent( 'linker:protection', {
					detail: { action, state: 'checking' },
				} )
			);
			return 'old-proof';
		}
	);
	window.linkerPublicProtection!.complete = vi.fn( () => false );
	await resourceFetch(
		vi.fn( async () => new Response( '{}' ) ),
		'https://site.test/wp-json/linker-ai/v1/engine/report/pdf',
		{ method: 'POST', body: '{}' }
	);
	expect( document.querySelector( '[role="status"]' )?.textContent ).toBe(
		'Checking verification…'
	);
} );

test.each( [ 400, 409, 429, 502, 503 ] )(
	'HTTP %i refusal never completes a proof',
	async ( status ) => {
		const complete = vi.fn( () => true );
		window.linkerPublicProtection!.complete = complete;
		await resourceFetch(
			vi.fn( async () => new Response( '{}', { status } ) ),
			'https://site.test/wp-json/linker-ai/v1/engine/design/residential',
			{ method: 'POST', body: JSON.stringify( { status } ) }
		);
		expect( complete ).not.toHaveBeenCalled();
	}
);

test( 'a failed proof performs no resource request and leaves the composer untouched', async () => {
	window.linkerPublicProtection!.proof = vi.fn( async () => {
		throw new Error( 'verification_expired' );
	} );
	const fetcher = vi.fn< typeof fetch >();
	await expect(
		resourceFetch(
			fetcher,
			'https://site.test/wp-json/linker-ai/v1/genie/turn',
			{ method: 'POST', body: '{}' }
		)
	).rejects.toThrow( 'verification_expired' );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( document.querySelector( 'textarea' )?.value ).toBe(
		'Keep this project question'
	);
	expect(
		resourceRefusalReason( new Error( 'verification_expired' ) )
	).toContain( 'inquiry' );
} );

test( 'a definite service refusal allows the next explicit operation UUID', async () => {
	const ids: string[] = [];
	const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
		ids.push( new Headers( init?.headers ).get( 'X-Linker-Operation' )! );
		return new Response( '{}', {
			status: 503,
			headers: { 'X-Linker-Resource-Outcome': 'failed' },
		} );
	} );
	const url =
		'https://site.test/wp-json/linker-ai/v1/engine/design/residential';
	const input = { method: 'POST', body: '{"synthetic":true}' };
	await resourceFetch( fetcher, url, input );
	await resourceFetch( fetcher, url, input );
	expect( ids[ 0 ] ).not.toBe( ids[ 1 ] );
} );

test.each( [ 502, 503 ] )(
	'an ambiguous business gateway %i keeps the logical UUID',
	async ( status ) => {
		const ids: string[] = [];
		const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
			ids.push(
				new Headers( init?.headers ).get( 'X-Linker-Operation' )!
			);
			return new Response( '<html>synthetic gateway</html>', { status } );
		} );
		const url = 'https://site.test/wp-json/linker-ai/v1/genie/inquiry';
		const input = {
			method: 'POST',
			body: JSON.stringify( { message: `gateway ${ status }` } ),
		};
		await resourceFetch( fetcher, url, input );
		await resourceFetch( fetcher, url, input );
		expect( ids[ 0 ] ).toBe( ids[ 1 ] );
	}
);

test( 'a trusted pre-dispatch quota refusal permits a new explicit UUID', async () => {
	const ids: string[] = [];
	const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
		ids.push( new Headers( init?.headers ).get( 'X-Linker-Operation' )! );
		return new Response(
			JSON.stringify( { code: 'linker_admission_quota' } ),
			{ status: 429 }
		);
	} );
	const input = { method: 'POST', body: '{"message":"quota fixture"}' };
	const url = 'https://site.test/wp-json/linker-ai/v1/genie/contact';
	await resourceFetch( fetcher, url, input );
	await resourceFetch( fetcher, url, input );
	expect( ids[ 0 ] ).not.toBe( ids[ 1 ] );
} );

test.each( [ true, false ] )(
	'observe stays native when the Cloudflare client exists=%s',
	async ( available ) => {
		window.linkerPublicProtectionConfig!.mode = 'observe';
		const proof = vi.fn( async () => {
			throw new Error( 'synthetic outage' );
		} );
		window.linkerPublicProtection = available
			? { proof, reset: vi.fn() }
			: undefined;
		const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
			const headers = new Headers( init?.headers );
			expect( headers.get( 'X-WP-Nonce' ) ).toBe( 'native-nonce' );
			expect( headers.get( 'X-Linker-Operation' ) ).toMatch(
				/^[a-f0-9-]{36}$/
			);
			expect( headers.has( 'X-Linker-Proof' ) ).toBe( false );
			return new Response( '{}' );
		} );
		await resourceFetch(
			fetcher,
			'https://site.test/wp-json/linker-ai/v1/genie/turn',
			{
				method: 'POST',
				body: '{}',
				headers: { 'X-WP-Nonce': 'native-nonce' },
			}
		);
		expect( fetcher ).toHaveBeenCalledOnce();
		expect( proof ).not.toHaveBeenCalled();
	}
);

test( 'observe preserves native fetch when shadow UUID hashing is unavailable', async () => {
	window.linkerPublicProtectionConfig!.mode = 'observe';
	vi.stubGlobal( 'crypto', {
		subtle: {
			digest: async () => {
				throw new Error( 'synthetic hash unavailable' );
			},
		},
	} );
	const fetcher = vi.fn< typeof fetch >( async () => new Response( '{}' ) );
	await resourceFetch(
		fetcher,
		'https://site.test/wp-json/linker-ai/v1/genie/turn',
		{ method: 'POST', body: '{}' }
	);
	expect( fetcher ).toHaveBeenCalledOnce();
	expect( window.linkerPublicProtection?.proof ).not.toHaveBeenCalled();
} );

test.each( [ 'enforce', 'observe', 'off' ] )(
	'send witness follows actual transport in %s',
	async ( mode ) => {
		window.linkerPublicProtectionConfig!.mode = mode;
		const sent = vi.fn();
		const fetcher = vi.fn< typeof fetch >( async ( _input, init ) => {
			expect( sent.mock.calls ).toEqual(
				mode === 'enforce'
					? [
							[
								new Headers( init?.headers ).get(
									'X-Linker-Operation'
								),
							],
						]
					: []
			);
			return new Response( '{}' );
		} );
		await resourceFetch(
			fetcher,
			'/wp-json/linker-ai/v1/genie/turn',
			{ method: 'POST', body: JSON.stringify( { mode } ) },
			sent
		);
	}
);

test( 'failed verification never creates a live send witness', async () => {
	window.linkerPublicProtection!.proof = vi.fn( async () => {
		throw new Error( 'proof unavailable' );
	} );
	const sent = vi.fn();
	const fetcher = vi.fn< typeof fetch >();
	await expect(
		resourceFetch(
			fetcher,
			'/wp-json/linker-ai/v1/genie/turn',
			{ method: 'POST', body: '{}' },
			sent
		)
	).rejects.toThrow( 'proof unavailable' );
	expect( sent ).not.toHaveBeenCalled();
	expect( fetcher ).not.toHaveBeenCalled();
} );

test( 'signed Genie product-list writes retain the native draft and save admission scopes', () => {
	expect(
		resourceAction(
			'https://site.test/wp-json/linker-ai/v1/genie/draft',
			'POST'
		)
	).toBe( 'draft_write' );
	expect(
		resourceAction(
			'https://site.test/wp-json/linker-ai/v1/genie/solution',
			'POST'
		)
	).toBe( 'solution_save' );
} );
