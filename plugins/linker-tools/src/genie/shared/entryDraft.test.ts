import { afterEach, expect, test, vi } from 'vitest';
import { entryScope, ENTRY_KEY, readEntryRecovery } from './entryDraft';
afterEach( () => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
	sessionStorage.clear();
} );
test( 'the native auxiliary request is bounded and coalesces only pending guest epoch reads', async () => {
	vi.useFakeTimers();
	const fetcher = vi.fn(
		( _url: unknown, init: RequestInit ) =>
			new Promise( ( _resolve, reject ) =>
				init.signal?.addEventListener( 'abort', () =>
					reject( new DOMException( 'aborted', 'AbortError' ) )
				)
			)
	);
	vi.stubGlobal( 'fetch', fetcher );
	const config = { restUrl: '/wp-json/', restNonce: 'current' };
	const first = entryScope( config );
	const second = entryScope( config );
	expect( first ).toBe( second );
	expect( fetcher ).toHaveBeenCalledTimes( 1 );
	const rejected = first.catch( ( error: Error ) => error );
	await vi.advanceTimersByTimeAsync( 5000 );
	expect( ( ( await rejected ) as Error ).message ).toBe( 'aborted' );
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( {
			ok: true,
			json: async () => ( { scope: 'a'.repeat( 64 ) } ),
		} ) )
	);
	await expect( entryScope( config ) ).resolves.toBe( 'a'.repeat( 64 ) );
} );
test( 'only matching verified scope can read recovery text', () => {
	sessionStorage.setItem(
		ENTRY_KEY,
		JSON.stringify( {
			v: 1,
			scope: 'old',
			entries: [],
			claimed: [],
			composer: { text: 'private', missing: [] },
		} )
	);
	expect( readEntryRecovery( 'current' ).composer ).toBeNull();
	expect( sessionStorage.getItem( ENTRY_KEY ) ).toBeNull();
} );
