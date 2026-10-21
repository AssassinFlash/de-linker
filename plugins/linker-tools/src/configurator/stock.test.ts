/**
 * The stock line on a proposal card: available, currently unavailable, or no
 * claim at all when the store data is missing (AGENTS.md 2026-10-11: the
 * customer reads a status, never a quantity).
 */

/**
 * External dependencies
 */
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import { stockBadge } from './stock';
import type { StoreProduct } from './types';

function product( available: boolean ): StoreProduct {
	return {
		id: 1,
		name: 'GoodWe GW10K-ETA-G20',
		permalink: '/product/gw10k/',
		images: [],
		is_in_stock: available,
	};
}

test( 'a product in stock reads In stock', () => {
	expect( stockBadge( [ product( true ) ] ) ).toEqual( {
		tone: 'ok',
		text: 'In stock',
	} );
} );

test( 'a product out of stock reads Currently unavailable', () => {
	expect( stockBadge( [ product( false ) ] ) ).toEqual( {
		tone: 'warn',
		text: 'Currently unavailable',
	} );
} );

test( 'a system is in stock only when every part is', () => {
	expect( stockBadge( [ product( true ), product( true ) ] ) ).toEqual( {
		tone: 'ok',
		text: 'In stock',
	} );
	expect( stockBadge( [ product( true ), product( false ) ] ) ).toEqual( {
		tone: 'warn',
		text: 'Currently unavailable',
	} );
} );

test( 'a part without a store entry draws no badge', () => {
	expect( stockBadge( [] ) ).toBeNull();
	expect( stockBadge( [ product( true ), undefined ] ) ).toBeNull();
} );
