import { afterEach, expect, test, vi } from 'vitest';
import { FAILURE_KEY } from './failure';
import { verifiedEntryFailure } from './entryFailure';
const config = { restUrl: '/wp-json/', restNonce: 'current' };
const first = {
	v: 1,
	kind: 'upstream',
	text: 'Private A',
	question: 'Private A',
	uploads: [],
	omitted: [],
	entryId: 'source-a',
	entryScope: 'a'.repeat( 64 ),
};
afterEach( () => {
	vi.unstubAllGlobals();
	sessionStorage.clear();
} );
test( 'a delayed reader cannot reconcile or delete a newer failure owner', async () => {
	sessionStorage.setItem( FAILURE_KEY, JSON.stringify( first ) );
	let release!: ( value: unknown ) => void;
	vi.stubGlobal(
		'fetch',
		vi.fn(
			() =>
				new Promise( ( resolve ) => {
					release = resolve;
				} )
		)
	);
	const checked = verifiedEntryFailure( config, sessionStorage );
	const later = JSON.stringify( {
		...first,
		text: 'New B',
		question: 'New B',
		entryId: 'source-b',
		entryScope: 'b'.repeat( 64 ),
	} );
	sessionStorage.setItem( FAILURE_KEY, later );
	release( { ok: true, json: async () => ( { scope: 'b'.repeat( 64 ) } ) } );
	expect( await checked ).toBeNull();
	expect( sessionStorage.getItem( FAILURE_KEY ) ).toBe( later );
} );
test( 'identity lookup failure hides scoped text and retains its exact recovery record', async () => {
	const raw = JSON.stringify( first );
	sessionStorage.setItem( FAILURE_KEY, raw );
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( { ok: false } ) )
	);
	expect( await verifiedEntryFailure( config, sessionStorage ) ).toBeNull();
	expect( sessionStorage.getItem( FAILURE_KEY ) ).toBe( raw );
} );
test( 'a verified mismatch removes only the captured scoped failure, legacy recovery remains unchanged', async () => {
	sessionStorage.setItem( FAILURE_KEY, JSON.stringify( first ) );
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( {
			ok: true,
			json: async () => ( { scope: 'b'.repeat( 64 ) } ),
		} ) )
	);
	expect( await verifiedEntryFailure( config, sessionStorage ) ).toBeNull();
	expect( sessionStorage.getItem( FAILURE_KEY ) ).toBeNull();
	const { entryId: _id, entryScope: _scope, ...legacy } = first;
	sessionStorage.setItem( FAILURE_KEY, JSON.stringify( legacy ) );
	expect(
		( await verifiedEntryFailure( config, sessionStorage ) )?.record?.text
	).toBe( 'Private A' );
} );

test( 'transport cannot reuse a scope read that started before the principal changed', async () => {
	const { entryScope } = await import( './entryDraft' );
	let release!: ( value: unknown ) => void;
	vi.stubGlobal(
		'fetch',
		vi
			.fn()
			.mockImplementationOnce(
				() =>
					new Promise( ( resolve ) => {
						release = resolve;
					} )
			)
			.mockResolvedValueOnce( {
				ok: true,
				json: async () => ( { scope: 'b'.repeat( 64 ) } ),
			} )
	);
	const old = entryScope( config );
	sessionStorage.setItem( FAILURE_KEY, JSON.stringify( first ) );
	expect( await verifiedEntryFailure( config, sessionStorage ) ).toBeNull();
	release( { ok: true, json: async () => ( { scope: 'a'.repeat( 64 ) } ) } );
	await old;
} );
