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
import type { Locale } from '../../configurator/types';
import { useCardActions } from './cardActions';

vi.mock( '../../configurator/api/solutions', () => ( {
	saveSolution: vi.fn(),
} ) );

function store() {
	return {
		addAll: vi.fn( async ( _lines, onStatus ) => onStatus( 5, 'added' ) ),
	} as unknown as ReturnType< typeof storeClient >;
}

function hook( client = store(), locale: Locale = 'en' ) {
	return renderHook( () =>
		useCardActions( {
			restUrl: '/wp-json/',
			restNonce: 'n',
			locale,
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
		} ),
		'en'
	);
	expect( result.current.statusFor( 5 ) ).toEqual( {
		state: 'added',
		text: 'Saved to your account.',
	} );
} );

test( 'a German card asks for the save in German', async () => {
	vi.mocked( saveSolution ).mockResolvedValue( {
		id: 9,
		url: '/de/mein-konto/gespeicherte-loesungen/#linker-solution-9',
	} );
	const { result } = hook( store(), 'de' );

	await act( async () => {
		await result.current.saveCardSolution( 5, 'SAJ H2-10K-T3' );
	} );

	expect( saveSolution ).toHaveBeenCalledWith(
		'/wp-json/',
		'n',
		expect.objectContaining( { kind: 'residential' } ),
		'de'
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

test( 'a parts list writes every row in one call and reports added', async () => {
	const client = {
		addAll: vi.fn( async ( _lines, onStatus ) => onStatus( 5, 'added' ) ),
	} as unknown as ReturnType< typeof storeClient >;
	const { result } = hook( client );

	let outcome: string = '';
	await act( async () => {
		outcome = await result.current.addPartsToDraft( [
			{ product_id: 5, quantity: 2 },
			{ product_id: 6, quantity: 1 },
		] );
	} );

	expect( client.addAll ).toHaveBeenCalledWith(
		[
			{ productId: 5, quantity: 2 },
			{ productId: 6, quantity: 1 },
		],
		expect.any( Function )
	);
	expect( outcome ).toBe( 'added' );
} );

test( "a parts list reports the rows' worst outcome", async () => {
	const client = {
		addAll: vi.fn( async ( _lines, onStatus ) => {
			onStatus( 5, 'added' );
			onStatus( 6, 'unverified' );
		} ),
	} as unknown as ReturnType< typeof storeClient >;
	const { result } = hook( client );

	let outcome: string = '';
	await act( async () => {
		outcome = await result.current.addPartsToDraft( [
			{ product_id: 5, quantity: 1 },
			{ product_id: 6, quantity: 1 },
		] );
	} );

	expect( outcome ).toBe( 'unverified' );
} );

test( 'a parts list retry outranks an unverified row', async () => {
	const client = {
		addAll: vi.fn( async ( _lines, onStatus ) => {
			onStatus( 5, 'unverified' );
			onStatus( 6, 'retry' );
		} ),
	} as unknown as ReturnType< typeof storeClient >;
	const { result } = hook( client );

	let outcome: string = '';
	await act( async () => {
		outcome = await result.current.addPartsToDraft( [
			{ product_id: 5, quantity: 1 },
			{ product_id: 6, quantity: 1 },
		] );
	} );

	expect( outcome ).toBe( 'retry' );
} );
