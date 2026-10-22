import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { resourceFetch } from './request';

interface WidgetCallbacks {
	callback: ( token: string ) => void;
	'expired-callback': () => void;
	'error-callback': () => void;
}

type Config = NonNullable< Window[ 'linkerPublicProtectionConfig' ] >;
type Client = NonNullable< Window[ 'linkerPublicProtection' ] >;

// Load the actual shared client without merging the plugins' ambient declarations.
// Only the provider and HTTP boundaries are replaced; neither plugin is mocked.
const { ProtectionClient } = await vi.importActual< {
	ProtectionClient: new ( config: Config ) => Client;
} >( '../../../linker-commerce/src/protection/client' );

const widgets: WidgetCallbacks[] = [];
const verifications: string[] = [];

beforeEach( () => {
	vi.stubGlobal( 'crypto', webcrypto );
	document.body.innerHTML =
		'<main><form><textarea>Keep this project</textarea></form></main>';
	window.linkerPublicProtectionConfig = {
		api: 'https://site.test/wp-json/linker/v1/protection',
		nonce: 'synthetic',
		mode: 'enforce',
		language: 'en',
	};
	Object.assign( window, {
		turnstile: {
			render: ( _container: HTMLElement, options: WidgetCallbacks ) => {
				widgets.push( options );
				return `widget-${ widgets.length }`;
			},
			remove: vi.fn(),
		},
	} );
	vi.stubGlobal(
		'fetch',
		vi.fn< typeof fetch >( async ( input ) => {
			const url = String( input );
			verifications.push( url );
			if ( url.includes( '/prepare?' ) ) {
				return new Response(
					JSON.stringify( {
						site_key: 'synthetic',
						prepare: 'stamp',
					} )
				);
			}
			if ( url.includes( '/verify?' ) ) {
				return new Response(
					JSON.stringify( { proof: 'server-proof', ttl: 300 } )
				);
			}
			throw new Error( 'Unexpected HTTP boundary' );
		} )
	);
	window.linkerPublicProtection = new ProtectionClient(
		window.linkerPublicProtectionConfig
	);
} );

afterEach( () => {
	window.linkerPublicProtection?.reset( 'design' );
	widgets.length = 0;
	verifications.length = 0;
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	Reflect.deleteProperty( window, 'turnstile' );
	vi.unstubAllGlobals();
} );

test( 'idle proof expiry clears the old resource status and the next call verifies afresh', async () => {
	const url =
		'https://site.test/wp-json/linker-ai/v1/engine/design/residential';
	const init = { method: 'POST', body: '{"project":"expiry"}' };
	const fetcher = vi.fn< typeof fetch >( async () => new Response( '{}' ) );
	const first = resourceFetch( fetcher, url, init );
	await vi.waitFor( () => expect( widgets ).toHaveLength( 1 ) );
	widgets[ 0 ].callback( 'synthetic-token' );
	await first;
	await resourceFetch( fetcher, url, init );
	expect( widgets ).toHaveLength( 1 );
	expect( verifications ).toHaveLength( 2 );
	const widget = document.querySelector(
		'[data-linker-resource-verification="design"]'
	)!;
	const status = widget.previousElementSibling!;
	expect( status.textContent ).toBe( '' );
	widgets[ 0 ][ 'expired-callback' ]();
	expect( status.textContent ).toBe( '' );
	expect( fetcher ).toHaveBeenCalledTimes( 2 );
	const fresh = resourceFetch( fetcher, url, init );
	await vi.waitFor( () => expect( widgets ).toHaveLength( 2 ) );
	widgets[ 1 ].callback( 'fresh-token' );
	await fresh;
	expect( verifications ).toHaveLength( 4 );
	expect( status.textContent ).toBe( '' );
	expect( document.querySelector( 'textarea' )?.value ).toBe(
		'Keep this project'
	);
} );

test.each( [
	[ 'error-callback', 'verification_widget' ],
	[ 'expired-callback', 'verification_expired' ],
] as const )(
	'active %s stays visible and a fresh retry preserves input',
	async ( callback, reason ) => {
		const url =
			'https://site.test/wp-json/linker-ai/v1/engine/design/residential';
		const init = { method: 'POST', body: '{"project":"failed-retry"}' };
		const fetcher = vi.fn< typeof fetch >(
			async () => new Response( '{}' )
		);
		const first = resourceFetch( fetcher, url, init );
		const failed = first.catch( ( failure: unknown ) => failure );
		await vi.waitFor( () => expect( widgets ).toHaveLength( 1 ) );
		widgets[ 0 ][ callback ]();
		expect( await failed ).toEqual( new Error( reason ) );
		expect( fetcher ).not.toHaveBeenCalled();
		expect(
			document.querySelector( '[role="status"]' )?.textContent
		).toContain( 'Verification could not be completed.' );
		const retry = resourceFetch( fetcher, url, init );
		await vi.waitFor( () => expect( widgets ).toHaveLength( 2 ) );
		widgets[ 1 ].callback( 'retry-token' );
		await retry;
		expect( fetcher ).toHaveBeenCalledOnce();
		expect( document.querySelector( '[role="status"]' )?.textContent ).toBe(
			''
		);
		expect( document.querySelector( 'textarea' )?.value ).toBe(
			'Keep this project'
		);
	}
);
