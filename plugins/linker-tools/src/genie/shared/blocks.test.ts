// @vitest-environment jsdom

/**
 * The turn's card ids and price lines (ticket #232 review round 1, item 4).
 */

/**
 * External dependencies
 */
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import type { Block } from '../api/turn';
import { idsOf, pricesOf } from './blocks';

const BLOCKS: Block[] = [
	{ type: 'text', text: 'These fit.', refs: [] },
	{
		type: 'cards',
		product_ids: [ 4107, 2092 ],
		prices: [ { product_id: 4107, text: '1.234,00 €' } ],
	},
	{ type: 'compare', product_ids: [ 4107, 2092 ] },
];

test( 'the cards block names the products the grid shows', () => {
	expect( idsOf( BLOCKS, 'cards' ) ).toEqual( [ 4107, 2092 ] );
} );

test( 'the compare block names the products the table compares', () => {
	expect( idsOf( BLOCKS, 'compare' ) ).toEqual( [ 4107, 2092 ] );
} );

test( 'the price lines come with the cards block', () => {
	expect( pricesOf( BLOCKS ) ).toEqual( [
		{ product_id: 4107, text: '1.234,00 €' },
	] );
} );

test( 'no block means no ids and no prices', () => {
	expect( idsOf( [ BLOCKS[ 0 ] ], 'cards' ) ).toEqual( [] );
	expect( pricesOf( [ BLOCKS[ 0 ] ] ) ).toEqual( [] );
} );
