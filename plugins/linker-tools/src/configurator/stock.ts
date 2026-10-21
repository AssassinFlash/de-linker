/**
 * The stock state a customer reads on a proposal card: available or currently
 * unavailable, never a quantity (AGENTS.md 2026-10-11: WooCommerce is the only
 * stock authority, and a customer is told the status, not the count).
 *
 * A part with no store entry leaves the answer unknown: the card then draws no
 * badge rather than guessing.
 */

/**
 * WordPress dependencies
 */
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { CardBadge } from '../shared/ProductCard';
import type { StoreProduct } from './types';

export function stockBadge(
	parts: ( StoreProduct | undefined )[]
): CardBadge | null {
	const known = parts.filter(
		( part ): part is StoreProduct => part !== undefined
	);
	if ( known.length === 0 || known.length !== parts.length ) {
		return null;
	}
	return known.every( ( part ) => part.is_in_stock )
		? { tone: 'ok', text: __( 'In stock', 'linker-tools' ) }
		: {
				tone: 'warn',
				text: __( 'Currently unavailable', 'linker-tools' ),
			};
}
