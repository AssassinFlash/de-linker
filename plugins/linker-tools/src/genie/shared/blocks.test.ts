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
import type { Block, DocumentBlock } from '../api/turn';
import {
	cardIdsOf,
	controlsOf,
	comparisonsOf,
	pricesOf,
	proofsOf,
	quantitiesOf,
} from './blocks';

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
	expect( cardIdsOf( BLOCKS ) ).toEqual( [ 4107, 2092 ] );
} );

test( 'the compare block names the products the table compares', () => {
	expect( comparisonsOf( BLOCKS ) ).toEqual( [ BLOCKS[ 2 ] ] );
} );

test( 'the price lines come with the cards block', () => {
	expect( pricesOf( BLOCKS ) ).toEqual( [
		{ product_id: 4107, text: '1.234,00 €' },
	] );
} );

test( 'no block means no ids and no prices', () => {
	expect( cardIdsOf( [ BLOCKS[ 0 ] ] ) ).toEqual( [] );
	expect( pricesOf( [ BLOCKS[ 0 ] ] ) ).toEqual( [] );
} );

test( 'reopening an unsigned turn shows the original action quantity without making a new proof', () => {
	const stored: Block[] = [
		{ type: 'cards', product_ids: [ 4107 ] },
		{
			type: 'action',
			name: 'add_to_draft',
			args: { product_id: 4107, quantity: 2 },
		},
		{ type: 'action', name: 'save_solution', args: {} },
	];
	expect( quantitiesOf( stored ) ).toEqual( { 4107: 2 } );
	expect( proofsOf( stored ) ).toEqual( {} );
} );

test( 'the same visible manual and page has one control across evidence chunks', () => {
	const page: DocumentBlock = {
		type: 'document',
		ref: 'passage-1',
		document_id: 'manual',
		url: '/cb2.pdf#page=4',
		label: 'CB2-100 · User manual (EN) · p. 4',
	};
	const shared = { ...page, ref: 'passage-2', evidence_product_id: 4103 };
	const otherPage = {
		...page,
		url: '/cb2.pdf#page=8',
		label: 'CB2-100 · User manual (EN) · p. 8',
	};
	const otherModel = { ...page, label: 'CB2-57 · User manual (EN) · p. 4' };
	const blocks = [
		{ ...page, url: null },
		page,
		shared,
		otherPage,
		otherModel,
	];
	expect( controlsOf( blocks ) ).toEqual( [ page, otherPage, otherModel ] );
	expect( blocks ).toHaveLength( 5 );
} );
