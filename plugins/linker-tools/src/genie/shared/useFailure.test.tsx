// @vitest-environment jsdom

/**
 * The shared failure hook (ticket #411): the record both surfaces send from,
 * and the one retry its state machine allows.
 */

/**
 * External dependencies
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { Upload } from '../attachments/prepare';
import type { FailureDraft } from './failure';
import { useFailure } from './useFailure';

const PDF: Upload = {
	name: 'datasheet.pdf',
	type: 'application/pdf',
	data: 'JVBERi0=',
};

const DRAFT: FailureDraft = {
	text: 'Check this datasheet',
	question: 'Check this datasheet\nAttached: datasheet.pdf',
	uploads: [ PDF ],
	omitted: [],
};

afterEach( () => {
	sessionStorage.clear();
} );

function files( uploads: Upload[] ) {
	return {
		uploads,
		restore: vi.fn(),
		clear: vi.fn(),
	};
}

test( 'a truncated failure offers one retry and leaves the record on the composer', () => {
	const { result } = renderHook( () => useFailure( files( [ PDF ] ) ) );

	act( () => {
		result.current.commitFailure( { type: 'send', draft: DRAFT } );
		result.current.commitFailure( { type: 'truncated' } );
	} );
	expect( result.current.failureState.current.phase ).toBe( 'failed' );
	expect( result.current.failureState.current.kind ).toBe( 'truncated' );

	const opened = result.current.openRetry( [
		{ role: 'user', content: DRAFT.question },
	] );
	expect( opened ).toEqual( { draft: DRAFT, kind: 'truncated' } );
	// The retry already left `failed`: a second click sends nothing.
	expect(
		result.current.openRetry( [
			{ role: 'user', content: DRAFT.question },
		] )
	).toBeNull();
	expect(
		result.current.previewRetry( DRAFT, 'truncated', [] )
	).toMatchObject( { question: DRAFT.question, uploads: [ PDF ] } );
} );

test( 'an upstream retry with no words left puts the failure back', () => {
	const { result } = renderHook( () => useFailure( files( [] ) ) );
	const draft: FailureDraft = {
		text: '',
		question: 'Attached: datasheet.pdf',
		uploads: [],
		omitted: [ 'datasheet.pdf' ],
	};

	act( () => {
		result.current.commitFailure( { type: 'send', draft } );
		result.current.commitFailure( { type: 'upstream' } );
	} );

	let payload: unknown;
	act( () => {
		payload = result.current.payloadOrRestore( draft, 'upstream', [] );
	} );
	expect( payload ).toBeNull();
	expect( result.current.failureState.current.phase ).toBe( 'failed' );
} );

test( 'an older entry completion or file edit cannot erase a newer failure owner', () => {
	const prior = {
		...DRAFT,
		entryId: 'entry-a',
		entryScope: 'a'.repeat( 64 ),
	};
	const current = {
		...DRAFT,
		entryId: 'entry-b',
		entryScope: 'b'.repeat( 64 ),
		text: 'Current owner B',
		question: 'Current owner B',
	};
	const older = renderHook( () => useFailure( files( [ PDF ] ) ) );
	act( () =>
		older.result.current.commitFailure( { type: 'send', draft: prior } )
	);
	const newer = renderHook( () => useFailure( files( [] ) ) );
	act( () =>
		newer.result.current.commitFailure( { type: 'send', draft: current } )
	);
	const raw = sessionStorage.getItem( 'linker-genie-turn-failure' );
	act( () => older.result.current.commitFailure( { type: 'answered' } ) );
	expect( sessionStorage.getItem( 'linker-genie-turn-failure' ) ).toBe( raw );
} );
