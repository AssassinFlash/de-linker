import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { DraftContext } from './draftContext';
const A = 'a'.repeat( 64 );
const B = 'b'.repeat( 64 );
let scope = A;
let changed = vi.fn< () => void >();
let context: DraftContext;
beforeEach( () => {
	sessionStorage.clear();
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieNativeScope;
	scope = A;
	changed = vi.fn< () => void >();
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( { ok: true, json: async () => ( { scope } ) } ) )
	);
	context = new DraftContext(
		{ restUrl: '/wp-json/', restNonce: 'native' },
		changed
	);
} );
afterEach( () => {
	context.dispose();
	vi.unstubAllGlobals();
} );
test( 'first byte has no owner until native verification; every later authorize is a separate fresh read', async () => {
	expect( context.capture() ).toBeNull();
	await context.verify( false );
	const lease = context.capture();
	expect( lease?.scope ).toBe( A );
	await expect( context.authorize( lease ) ).resolves.toBe( true );
	await expect( context.authorize( lease ) ).resolves.toBe( true );
	expect( fetch ).toHaveBeenCalledTimes( 3 );
} );
test( 'in-progress same-owner revalidation quarantines settlements, then permits only the unchanged epoch', async () => {
	await context.verify( false );
	const lease = context.capture();
	let release!: () => void;
	vi.stubGlobal(
		'fetch',
		vi.fn(
			() =>
				new Promise( ( resolve ) => {
					release = () =>
						resolve( {
							ok: true,
							json: async () => ( { scope: A } ),
						} );
				} )
		)
	);
	const pending = context.verify();
	expect( context.capture() ).toBeNull();
	let settled = false;
	const settlement = context.settle( lease ).then( ( value ) => {
		settled = value;
	} );
	await Promise.resolve();
	expect( settled ).toBe( false );
	release();
	await pending;
	await settlement;
	expect( settled ).toBe( true );
} );
test( 'same account with a rotated native session is a different owner, and late A cannot settle or unlock B', async () => {
	await context.verify( false );
	const lease = context.capture();
	scope = B;
	await expect( context.authorize( lease ) ).resolves.toBe( false );
	expect( changed ).toHaveBeenCalledOnce();
	await expect( context.settle( lease ) ).resolves.toBe( false );
	expect( context.capture()?.scope ).toBe( B );
} );
test( 'temporary native outage blocks but retains its owner for a working retry; a thread switch invalidates it', async () => {
	await context.verify( false );
	const lease = context.capture();
	vi.mocked( fetch ).mockRejectedValueOnce( new Error( 'offline' ) );
	await expect( context.authorize( lease ) ).resolves.toBe( false );
	expect( context.phase ).toBe( 'unavailable' );
	expect( context.identity?.scope ).toBe( A );
	await context.verify();
	expect( context.valid( lease ) ).toBe( true );
	context.invalidate();
	expect( context.valid( lease ) ).toBe( false );
	context.dispose();
	expect( context.capture() ).toBeNull();
} );
