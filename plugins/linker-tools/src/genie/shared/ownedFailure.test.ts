import { beforeEach, expect, test } from 'vitest';
import { FailureJournal, failureBucketKey } from './ownedFailure';
import { FAILURE_KEY, type FailureState, type FailureStore } from './failure';

const A = 'a'.repeat( 64 );
const B = 'b'.repeat( 64 );
let data: Map< string, string >;
let store: FailureStore;
beforeEach( () => {
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	data = new Map();
	store = {
		getItem: ( key ) => data.get( key ) ?? null,
		setItem: ( key, value ) => {
			data.set( key, value );
		},
		removeItem: ( key ) => {
			data.delete( key );
		},
	};
} );
function journal( scope = A, persistent = true ) {
	return new FailureJournal( store, { scope, persistent } );
}
function state( text: string ): FailureState {
	return {
		phase: 'failed',
		kind: 'upstream',
		draft: { text, question: text, uploads: [], omitted: [] },
	};
}
test( 'scope buckets preserve A while B writes; returning A chooses only its native bucket', () => {
	const a = journal().begin( state( 'A private' ) );
	const before = data.get( failureBucketKey( A ) );
	journal( B ).begin( state( 'B private' ) );
	expect( data.get( failureBucketKey( A ) ) ).toBe( before );
	expect( journal().candidate()?.record.text ).toBe( 'A private' );
	expect( journal( B ).candidate()?.record.text ).toBe( 'B private' );
	expect( journal( 'c'.repeat( 64 ) ).candidate() ).toBeNull();
	expect( journal( B ).consume( a.cursor ) ).toBe( false );
} );
test( 'consuming active A2 selects A1 by explicit insertion order; late A2 cannot change A3', () => {
	const first = journal().begin( state( 'A1' ) );
	const second = journal().begin( state( 'A2' ) );
	expect( journal().consume( second.cursor ) ).toBe( true );
	const restored = journal().candidate();
	expect( restored?.record.text ).toBe( 'A1' );
	expect( restored?.cursor.owner ).toEqual( first.cursor.owner );
	const third = journal().begin( state( 'A3' ) );
	expect( journal().consume( second.cursor ) ).toBe( false );
	expect( journal().candidate()?.cursor ).toEqual( third.cursor );
} );
test( 'raw and revision CAS rejects stale mutation even when another attempt belongs to same scope', () => {
	const first = journal().begin( state( 'A1' ) );
	journal().begin( state( 'A2' ) );
	const before = data.get( failureBucketKey( A ) );
	expect(
		journal().save( { ...first.state, kind: 'truncated' }, first.cursor )
			.conflict
	).toBe( true );
	expect( journal().consume( first.cursor ) ).toBe( false );
	expect( data.get( failureBucketKey( A ) ) ).toBe( before );
} );
test( 'unknown v1 bytes are inactive and never overwritten, even beside new v2 failure', () => {
	const legacy = JSON.stringify( {
		v: 1,
		kind: 'upstream',
		...state( 'unknown' ).draft,
	} );
	data.set( FAILURE_KEY, legacy );
	expect( journal().candidate() ).toBeNull();
	expect( journal().begin( state( 'new' ) ).durable ).toBe( true );
	expect( journal().candidate()?.record.text ).toBe( 'new' );
	expect( data.get( FAILURE_KEY ) ).toBe( legacy );
} );
test( 'scoped v1 migrates only when no current v2 exists and only after exact readback', () => {
	const legacy = JSON.stringify( {
		v: 1,
		kind: 'upstream',
		...state( 'scoped old' ).draft,
		entryId: 'source',
		entryScope: A,
	} );
	data.set( FAILURE_KEY, legacy );
	expect( journal( B ).candidate() ).toBeNull();
	expect( data.get( FAILURE_KEY ) ).toBe( legacy );
	journal().begin( state( 'current v2' ) );
	expect( journal().candidate()?.record.text ).toBe( 'current v2' );
	expect( data.get( FAILURE_KEY ) ).toBe( legacy );
	data.delete( failureBucketKey( A ) );
	expect( journal().candidate()?.record.text ).toBe( 'scoped old' );
	expect( data.has( FAILURE_KEY ) ).toBe( false );
} );
test( 'failed read is not empty and failed exact readback cannot acknowledge or consume legacy', () => {
	const legacy = JSON.stringify( {
		v: 1,
		kind: 'upstream',
		...state( 'old' ).draft,
		entryId: 'source',
		entryScope: A,
	} );
	data.set( FAILURE_KEY, legacy );
	let readsFail = true;
	const writing = store.setItem;
	store.getItem = ( key ) => {
		if ( readsFail ) {
			throw new Error( 'blocked' );
		}
		return data.get( key ) ?? null;
	};
	expect( journal().begin( state( 'new' ) ).durable ).toBe( false );
	expect( data.size ).toBe( 1 );
	readsFail = false;
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	store.setItem = ( key, value ) => {
		writing( key, value );
		data.set( key, value + ' ' );
	};
	expect( () => journal().candidate() ).toThrow(
		'failure-migration-storage'
	);
	expect( data.get( FAILURE_KEY ) ).toBe( legacy );
} );
test( 'minimal write quota failure retains current mount bytes and never removes unknown legacy', () => {
	data.set( FAILURE_KEY, 'private unknown raw' );
	store.setItem = () => {
		throw new Error( 'quota' );
	};
	const failed = journal().begin(
		state( 'editable and retryable in memory' )
	);
	expect( failed.durable ).toBe( false );
	expect( failed.conflict ).toBe( false );
	expect( failed.state.draft?.text ).toBe(
		'editable and retryable in memory'
	);
	expect( data.get( FAILURE_KEY ) ).toBe( 'private unknown raw' );
	expect( journal( A, false ).candidate()?.record.text ).toBe(
		'editable and retryable in memory'
	);
	expect( journal( B, false ).candidate() ).toBeNull();
} );

test( 'a verified live editor can offer the previous retained attempt without changing active or its raw bytes', () => {
	const first = journal().begin( state( 'Earlier failed question' ) );
	const current = journal().begin( {
		phase: 'editing',
		kind: null,
		draft: {
			text: 'Current editable question',
			question: 'Current editable question',
			editing: true,
			uploads: [],
			omitted: [],
		},
	} );
	const before = data.get( failureBucketKey( A ) );
	expect( journal().candidate()?.cursor.owner.attempt ).toBe(
		current.cursor.owner.attempt
	);
	expect(
		journal().candidate( current.cursor.owner.attempt )?.cursor.owner
			.attempt
	).toBe( first.cursor.owner.attempt );
	expect( data.get( failureBucketKey( A ) ) ).toBe( before );
} );
test( 'consuming a newer memory-only attempt makes its older durable owner reachable while preserving another principal', () => {
	journal().begin( state( 'A durable earlier question' ) );
	const write = store.setItem;
	store.setItem = () => {
		throw new Error( 'quota' );
	};
	const second = journal().begin( state( 'A memory newer question' ) );
	journal( B ).begin( state( 'B independent memory question' ) );
	expect( second.durable ).toBe( false );
	expect( journal().candidate()?.record.text ).toBe(
		'A memory newer question'
	);
	expect( journal().consume( second.cursor ) ).toBe( true );
	expect( journal().candidate()?.record.text ).toBe(
		'A durable earlier question'
	);
	expect( journal( B ).candidate()?.record.text ).toBe(
		'B independent memory question'
	);
	expect( journal().consume( second.cursor ) ).toBe( false );
	store.setItem = write;
} );

test( 'a write without exact readback retains a scoped memory owner and cannot acknowledge a durable copy', () => {
	const write = store.setItem;
	store.setItem = ( key, value ) => {
		write( key, value + ' ' );
	};
	const result = journal().begin(
		state( 'Question whose write did not read back exactly' )
	);
	expect( result.durable ).toBe( false );
	expect( result.conflict ).toBe( false );
	expect( result.cursor.memory ).toBe( true );
	expect( journal().candidate()?.record.text ).toBe(
		'Question whose write did not read back exactly'
	);
	expect( journal( B ).candidate() ).toBeNull();
} );

test( 'review repair: consuming a memory revision also removes its precise older durable counterpart', () => {
	const first = journal().begin( {
		...state( 'Old durable editor' ),
		phase: 'editing',
		kind: null,
		draft: { ...state( 'Old durable editor' ).draft!, editing: true },
	} );
	const other = journal().begin( state( 'Other retained attempt' ) );
	const write = store.setItem;
	store.setItem = () => {
		throw new Error( 'quota' );
	};
	const update = journal().begin(
		{
			...state( 'Latest memory editor' ),
			phase: 'editing',
			kind: null,
			draft: { ...state( 'Latest memory editor' ).draft!, editing: true },
		},
		first.cursor.owner
	);
	expect( update.cursor.memory ).toBe( true );
	store.setItem = write;
	expect( journal().consume( update.cursor ) ).toBe( true );
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	expect( journal().candidate()?.cursor.owner.attempt ).toBe(
		other.cursor.owner.attempt
	);
	const raw = data.get( failureBucketKey( A ) )!;
	expect( raw ).not.toContain( 'Old durable editor' );
} );
test( 'review repair: invalid proposed editing record cannot poison an existing readable bucket', () => {
	const first = journal().begin( state( 'Readable original question' ) );
	const before = data.get( failureBucketKey( A ) );
	const invalid = journal().begin( {
		phase: 'editing',
		kind: null,
		draft: {
			editing: true,
			text: '',
			question: '',
			uploads: [],
			omitted: [ 'missing.pdf' ],
		},
	} );
	expect( invalid.conflict ).toBe( true );
	expect( data.get( failureBucketKey( A ) ) ).toBe( before );
	expect( journal().candidate()?.cursor.owner.attempt ).toBe(
		first.cursor.owner.attempt
	);
} );

test( 'review repair: memory counterpart consumption fails closed while durable storage is unavailable', () => {
	const first = journal().begin( {
		...state( 'Original durable' ),
		phase: 'editing',
		kind: null,
		draft: { ...state( 'Original durable' ).draft!, editing: true },
	} );
	const write = store.setItem;
	store.setItem = () => {
		throw new Error( 'quota' );
	};
	const updated = journal().begin(
		{
			...state( 'Latest memory' ),
			phase: 'editing',
			kind: null,
			draft: { ...state( 'Latest memory' ).draft!, editing: true },
		},
		first.cursor.owner
	);
	expect( journal().consume( updated.cursor ) ).toBe( false );
	expect( journal().candidate()?.record.text ).toBe( 'Latest memory' );
	expect( data.get( failureBucketKey( A ) ) ).toContain( 'Original durable' );
	store.setItem = write;
	expect( journal( B ).consume( updated.cursor ) ).toBe( false );
	expect( journal().consume( updated.cursor ) ).toBe( true );
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	expect( journal().candidate() ).toBeNull();
} );
test( 'review repair: stale memory cursor cannot remove the durable counterpart of a newer memory revision', () => {
	const first = journal().begin( {
		...state( 'Original durable' ),
		phase: 'editing',
		kind: null,
		draft: { ...state( 'Original durable' ).draft!, editing: true },
	} );
	const write = store.setItem;
	store.setItem = () => {
		throw new Error( 'quota' );
	};
	const second = journal().begin(
		{
			...state( 'Second memory' ),
			phase: 'editing',
			kind: null,
			draft: { ...state( 'Second memory' ).draft!, editing: true },
		},
		first.cursor.owner
	);
	journal().begin(
		{
			...state( 'Third memory' ),
			phase: 'editing',
			kind: null,
			draft: { ...state( 'Third memory' ).draft!, editing: true },
		},
		first.cursor.owner
	);
	store.setItem = write;
	const raw = data.get( failureBucketKey( A ) );
	expect( journal().consume( second.cursor ) ).toBe( false );
	expect( data.get( failureBucketKey( A ) ) ).toBe( raw );
	expect( journal().candidate()?.record.text ).toBe( 'Third memory' );
} );

test( 'review repair: unreadable durable storage cannot make an invalid proposal shadow a valid owner', () => {
	const first = journal().begin( {
		...state( 'Still valid durable editor' ),
		phase: 'editing',
		kind: null,
		draft: {
			...state( 'Still valid durable editor' ).draft!,
			editing: true,
		},
	} );
	const read = store.getItem;
	store.getItem = () => {
		throw new Error( 'unavailable' );
	};
	const invalid = journal().begin(
		{
			phase: 'editing',
			kind: null,
			draft: {
				editing: true,
				text: '',
				question: '',
				uploads: [],
				omitted: [ 'missing.pdf' ],
			},
		},
		first.cursor.owner
	);
	expect( invalid.conflict ).toBe( true );
	store.getItem = read;
	expect( journal().candidate()?.record.text ).toBe(
		'Still valid durable editor'
	);
} );

test( 'review get fallback: a temporary get failure retains trusted old durable evidence for exact consumption', () => {
	const first = journal().begin( {
		...state( 'Durable before read failure' ),
		phase: 'editing',
		kind: null,
		draft: {
			...state( 'Durable before read failure' ).draft!,
			editing: true,
		},
	} );
	const read = store.getItem;
	store.getItem = () => {
		throw new Error( 'temporary get failure' );
	};
	const update = journal().begin(
		{
			...state( 'Latest accepted during read failure' ),
			phase: 'editing',
			kind: null,
			draft: {
				...state( 'Latest accepted during read failure' ).draft!,
				editing: true,
			},
		},
		first.cursor.owner
	);
	expect( update.cursor.memory ).toBe( true );
	store.getItem = read;
	expect( journal().consume( update.cursor ) ).toBe( true );
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	expect( journal().candidate() ).toBeNull();
} );
test( 'review get fallback: no trusted counterpart cannot be mistaken for a proven absent durable attempt', () => {
	const write = store.setItem;
	store.setItem = ( key, value ) => write( key, value + ' ' );
	const memory = journal().begin( state( 'An unacknowledged disk write' ) );
	expect( memory.cursor.memory ).toBe( true );
	store.setItem = write;
	const before = data.get( failureBucketKey( A ) );
	expect( journal().consume( memory.cursor ) ).toBe( false );
	expect( data.get( failureBucketKey( A ) ) ).toBe( before );
	expect( journal().candidate()?.record.text ).toBe(
		'An unacknowledged disk write'
	);
} );
