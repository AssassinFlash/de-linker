/** Accepted asynchronous checkpoints cannot reopen an attempt already promoted to a send. */
import { beforeEach, expect, test } from 'vitest';
import { FailureJournal, failureBucketKey } from './ownedFailure';
import type { FailureState } from './failure';

beforeEach( () => {
	sessionStorage.clear();
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
} );
test( 'a pending attempt rejects a late editing checkpoint without allocating another attempt or changing bytes', () => {
	const scope = 'a'.repeat( 64 );
	const journal = new FailureJournal( sessionStorage, {
		scope,
		persistent: true,
	} );
	const editing: FailureState = {
		phase: 'editing',
		kind: null,
		draft: {
			editing: true,
			text: 'Original editor',
			question: 'Original editor',
			uploads: [],
			omitted: [],
		},
	};
	const first = journal.begin( editing );
	const pending = journal.save(
		{
			...first.state,
			phase: 'pending',
			draft: { ...first.state.draft!, editing: false },
		},
		first.cursor
	);
	expect( pending.conflict ).toBe( false );
	const raw = sessionStorage.getItem( failureBucketKey( scope ) );
	const checkpoint = journal.begin(
		{
			...editing,
			draft: {
				...editing.draft!,
				text: 'Late heard words',
				question: 'Late heard words',
			},
		},
		first.cursor.owner
	);
	expect( checkpoint.conflict ).toBe( true );
	expect( checkpoint.cursor.owner ).toEqual( first.cursor.owner );
	expect( sessionStorage.getItem( failureBucketKey( scope ) ) ).toBe( raw );
	expect( Object.keys( JSON.parse( raw! ).records ) ).toEqual( [
		first.cursor.owner.attempt,
	] );
} );
