import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { nativeScope, invalidateNativeScope, TAB_KEY } from './nativeScope';
const config = { restUrl: '/wp-json/', restNonce: 'native' };
const stateKey = '__linkerGenieNativeScope';
beforeEach( () => {
	delete ( window as unknown as Record< string, unknown > )[ stateKey ];
	sessionStorage.clear();
} );
afterEach( () => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	delete ( window as unknown as Record< string, unknown > )[ stateKey ];
} );
function reply( scope = 'a'.repeat( 64 ) ) {
	return { ok: true, json: async () => ( { scope } ) };
}
test( 'independent bundles share only a cold pending bootstrap; fresh sends each read native identity', async () => {
	let release!: ( value: ReturnType< typeof reply > ) => void;
	const fetcher = vi
		.fn()
		.mockImplementationOnce(
			() =>
				new Promise( ( resolve ) => {
					release = resolve;
				} )
		)
		.mockResolvedValue( reply() );
	vi.stubGlobal( 'fetch', fetcher );
	const first = nativeScope( config );
	vi.resetModules();
	const secondBundle = await import( './nativeScope' );
	const second = secondBundle.nativeScope( config );
	expect( second ).toBe( first );
	expect( fetcher ).toHaveBeenCalledTimes( 1 );
	release( reply() );
	await expect( second ).resolves.toEqual( {
		scope: 'a'.repeat( 64 ),
		persistent: true,
	} );
	await Promise.all( [
		nativeScope( config, true ),
		secondBundle.nativeScope( config, true ),
	] );
	expect( fetcher ).toHaveBeenCalledTimes( 3 );
} );
for ( const method of [ 'getItem', 'setItem' ] as const ) {
	test( `native scope stays usable with a window-shared memory tab when ${ method } throws`, async () => {
		vi.spyOn( Storage.prototype, method ).mockImplementation( () => {
			throw new Error( 'storage blocked' );
		} );
		const tabs: string[] = [];
		vi.stubGlobal(
			'fetch',
			vi.fn( async ( _url, init ) => {
				tabs.push( JSON.parse( init.body ).tab );
				return reply();
			} )
		);
		expect( ( await nativeScope( config ) ).persistent ).toBe( false );
		vi.resetModules();
		const other = await import( './nativeScope' );
		expect( ( await other.nativeScope( config, true ) ).persistent ).toBe(
			false
		);
		expect( tabs[ 0 ] ).toBe( tabs[ 1 ] );
		expect( tabs[ 0 ] ).toBeTruthy();
	} );
}
test( 'known lifecycle invalidation rejects a late bootstrap instead of rebinding old input', async () => {
	let release!: ( value: ReturnType< typeof reply > ) => void;
	vi.stubGlobal(
		'fetch',
		vi.fn(
			() =>
				new Promise( ( resolve ) => {
					release = resolve;
				} )
		)
	);
	const read = nativeScope( config );
	invalidateNativeScope();
	release( reply() );
	await expect( read ).rejects.toThrow( 'entry-context' );
} );
test( 'persisted tab ID is read back and reused without exposing tokens', async () => {
	sessionStorage.setItem( TAB_KEY, 'existing-tab' );
	const fetcher = vi.fn<
		(
			url: unknown,
			init?: RequestInit
		) => Promise< ReturnType< typeof reply > >
	>( async () => reply() );
	vi.stubGlobal( 'fetch', fetcher );
	await nativeScope( config );
	expect( fetcher.mock.calls[ 0 ]?.[ 1 ] ).toMatchObject( {
		cache: 'no-store',
		credentials: 'same-origin',
		body: JSON.stringify( { tab: 'existing-tab' } ),
	} );
} );
