// @vitest-environment jsdom

/**
 * The product card's actions and status line (ticket #232 review round 1,
 * item 4): one hook for the dock and the hero.
 */

/**
 * External dependencies
 */
import { act, renderHook } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { saveSolution } from '../../configurator/api/solutions';
import type { storeClient } from '../../configurator/api/store';
import { useCardActions } from './cardActions';

vi.mock( '../../configurator/api/solutions', () => ( {
	saveSolution: vi.fn(),
} ) );

function store() {
	return {
		addAll: vi.fn( async ( _lines, onStatus ) => onStatus( 5, 'added' ) ),
	} as unknown as ReturnType< typeof storeClient >;
}

function hook( client = store() ) {
	return renderHook( () =>
		useCardActions( {
			restUrl: '/wp-json/',
			restNonce: 'n',
			locale: 'en',
			store: client,
		} )
	);
}

beforeEach( () => {
	vi.mocked( saveSolution ).mockReset();
} );

test( 'a card starts idle', () => {
	const { result } = hook();
	expect( result.current.statusFor( 5 ) ).toEqual( {
		state: 'idle',
		text: '',
	} );
} );

test( 'adding to the draft shows the settled status in the card', async () => {
	const client = store();
	const { result } = hook( client );

	await act( async () => {
		await result.current.addToDraft( 5 );
	} );

	expect( client.addAll ).toHaveBeenCalledWith(
		[ { productId: 5, quantity: 1 } ],
		expect.any( Function )
	);
	expect( result.current.statusFor( 5 ) ).toEqual( {
		state: 'added',
		text: 'In your solution draft.',
	} );
} );

test( 'saving a solution reports the saved card', async () => {
	vi.mocked( saveSolution ).mockResolvedValue( {
		id: 9,
		url: '/solution/9/',
	} );
	const { result } = hook();

	await act( async () => {
		await result.current.saveCardSolution( 5, 'SAJ H2-10K-T3' );
	} );

	expect( saveSolution ).toHaveBeenCalledWith(
		'/wp-json/',
		'n',
		expect.objectContaining( {
			kind: 'residential',
			title: 'SAJ H2-10K-T3',
			lines: [ { productId: 5, quantity: 1 } ],
		} )
	);
	expect( result.current.statusFor( 5 ) ).toEqual( {
		state: 'added',
		text: 'Saved to your account.',
	} );
} );

test( 'a failed save asks for a retry', async () => {
	vi.mocked( saveSolution ).mockRejectedValue( new Error( 'save 500' ) );
	const { result } = hook();

	await act( async () => {
		await result.current.saveCardSolution( 5, 'SAJ H2-10K-T3' );
	} );

	expect( result.current.statusFor( 5 ) ).toEqual( {
		state: 'retry',
		text: 'Not saved. Try again.',
	} );
} );
