/**
 * The turn's card and comparison product ids, and its card price lines
 * (ticket #232 review round 1, item 4): one reader for the dock (App.tsx)
 * and the home hero (Hero.tsx).
 */

/**
 * Internal dependencies
 */
import type { Block, CardPrice, CardsBlock, CompareBlock } from '../api/turn';

/**
 * The price lines of the turn's cards, as the service filled them (#242).
 *
 * @param blocks The turn's blocks.
 */
export function pricesOf( blocks: Block[] ): CardPrice[] {
	for ( const block of blocks ) {
		if ( 'cards' === block.type ) {
			return block.prices ?? [];
		}
	}
	return [];
}

/**
 * The product ids of the turn's card or comparison block.
 *
 * @param blocks The turn's blocks.
 * @param kind   Which block.
 */
export function idsOf( blocks: Block[], kind: 'cards' | 'compare' ): number[] {
	for ( const block of blocks ) {
		if ( block.type === kind ) {
			return ( block as CardsBlock | CompareBlock ).product_ids;
		}
	}
	return [];
}

/** The unit counts displayed and signed for individual product cards. */
export function quantitiesOf( blocks: Block[] ): Record< string, number > {
	const quantities: Record< string, number > = {};
	for ( const block of blocks ) {
		if ( block.type === 'action' && block.name === 'add_to_draft' ) {
			const { product_id: id, quantity } = block.args;
			if (
				typeof id === 'number' &&
				typeof quantity === 'number' &&
				Number.isSafeInteger( quantity ) &&
				quantity > 0
			) {
				quantities[ id ] = quantity;
			}
		}
	}
	for ( const block of blocks ) {
		if ( block.type === 'cards' && block.quantities ) {
			for ( const id of block.product_ids ) {
				// WordPress omits a count from the live map when it cannot sign it.
				quantities[ id ] = block.quantities[ id ] ?? 0;
			}
		}
	}
	return quantities;
}

/**
 * Exact live product-card actions; history never creates replacement proofs.
 * @param blocks Current normalized turn blocks.
 */
export function proofsOf( blocks: Block[] ): Record< string, string > {
	return Object.assign(
		{},
		...blocks
			.filter( ( block ): block is CardsBlock => block.type === 'cards' )
			.map( ( block ) => block.draft_proofs ?? {} )
	);
}
