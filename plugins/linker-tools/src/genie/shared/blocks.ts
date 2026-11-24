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
 * Controls below a reply, shared by live and restored turns.
 *
 * @param blocks The turn after its document links have been authorized and labeled.
 */
export function controlsOf( blocks: Block[] ): Block[] {
	const links = new Set< string >();
	return blocks.filter( ( block ) => {
		if ( block.type === 'document' ) {
			if ( ! block.url || ! block.label ) {
				return false;
			}
			const [ file, page ] = block.url.split( '#' );
			const key = JSON.stringify( [
				block.document_id ?? file,
				page,
				block.label,
			] );
			if ( links.has( key ) ) {
				return false;
			}
			links.add( key );
			return true;
		}
		return (
			block.type === 'ask' ||
			block.type === 'parts' ||
			( block.type === 'action' && block.name !== 'open_configurator' )
		);
	} );
}

/**
 * The price lines of the turn's cards, as the service filled them (#242).
 *
 * @param blocks The turn's blocks.
 */
export function pricesOf( blocks: Block[] ): CardPrice[] {
	const lines = new Map< number, CardPrice >();
	for ( const block of blocks ) {
		if ( block.type === 'cards' ) {
			for ( const price of block.prices ?? [] ) {
				lines.set( price.product_id, price );
			}
		}
	}
	return [ ...lines.values() ];
}

/**
 * All products in this turn, preserving the order in which the answer showed them.
 * @param blocks
 */
export function cardIdsOf( blocks: Block[] ): number[] {
	return [
		...new Set(
			blocks.flatMap( ( block ) =>
				block.type === 'cards' ? block.product_ids : []
			)
		),
	];
}

/**
 * Each comparison is bounded by the set the answer asked to compare.
 * @param blocks
 */
export function comparisonsOf( blocks: Block[] ): CompareBlock[] {
	return blocks.filter(
		( block ): block is CompareBlock => block.type === 'compare'
	);
}

/**
 * The unit counts displayed and signed for individual product cards.
 * @param blocks Current normalized turn blocks.
 */
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
		if (
			( block.type === 'cards' || block.type === 'compare' ) &&
			block.quantities
		) {
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
			.filter(
				( block ): block is CardsBlock | CompareBlock =>
					block.type === 'cards' || block.type === 'compare'
			)
			.map( ( block ) => block.draft_proofs ?? {} )
	);
}
