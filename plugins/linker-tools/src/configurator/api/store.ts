/**
 * WooCommerce Store API: product display data and the solution draft (the cart).
 *
 * "Add all" adds each line, then reads the draft back and compares quantities:
 * a line counts as added only when the draft shows it (docs/specs/14 "走 Store
 * API 并读回"). A line the draft already holds at the scheme quantity is not
 * sent again: the live planner records a written line and leaves it out of the
 * next add, and the Store API adds onto an existing line rather than setting
 * it. Product display data is asked for in the page's language (`?lang=`,
 * linker-i18n's RestLang; the default is English).
 */

/**
 * Internal dependencies
 */
import type { Locale, StoreProduct } from '../types';

type Fetch = typeof fetch;

export type AddStatus = 'pending' | 'added' | 'unverified' | 'retry';

export interface DraftLine {
	productId: number;
	quantity: number;
}

interface Cart {
	nonce: string;
	quantities: Map< number, number >;
}

export interface StoreClient {
	products: ( ids: number[], locale: Locale ) => Promise< StoreProduct[] >;
	addAll: (
		lines: DraftLine[],
		onStatus: ( productId: number, status: AddStatus ) => void
	) => Promise< boolean >;
}

function quantities( items: { id: number; quantity: number }[] ) {
	const out = new Map< number, number >();
	for ( const item of items ) {
		out.set( item.id, ( out.get( item.id ) ?? 0 ) + item.quantity );
	}
	return out;
}

export function storeClient(
	restUrl: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): StoreClient {
	const base = `${ restUrl }wc/store/v1`;

	async function cart(): Promise< Cart > {
		const response = await fetcher( `${ base }/cart`, {
			credentials: 'same-origin',
		} );
		if ( ! response.ok ) {
			throw new Error( `cart ${ response.status }` );
		}
		const body = await response.json();
		return {
			nonce: response.headers.get( 'Nonce' ) ?? '',
			quantities: quantities( body.items ?? [] ),
		};
	}

	return {
		async products( ids, locale ) {
			if ( ids.length === 0 ) {
				return [];
			}
			const query =
				`include=${ ids.join( ',' ) }&per_page=${ ids.length }` +
				`&lang=${ locale }`;
			const response = await fetcher( `${ base }/products?${ query }`, {
				credentials: 'same-origin',
			} );
			return response.ok ? response.json() : [];
		},

		async addAll( lines, onStatus ) {
			lines.forEach( ( line ) => onStatus( line.productId, 'pending' ) );
			let before: Cart;
			try {
				before = await cart();
			} catch {
				lines.forEach( ( line ) =>
					onStatus( line.productId, 'retry' )
				);
				return false;
			}
			const sent = new Set< number >();
			const held = new Set< number >();
			for ( const line of lines ) {
				const already = before.quantities.get( line.productId ) ?? 0;
				if ( already >= line.quantity ) {
					held.add( line.productId );
					continue;
				}
				try {
					const response = await fetcher( `${ base }/cart/add-item`, {
						method: 'POST',
						credentials: 'same-origin',
						headers: {
							'Content-Type': 'application/json',
							Nonce: before.nonce,
						},
						body: JSON.stringify( {
							id: line.productId,
							quantity: line.quantity - already,
						} ),
					} );
					if ( response.ok ) {
						sent.add( line.productId );
					} else {
						onStatus( line.productId, 'retry' );
					}
				} catch {
					onStatus( line.productId, 'retry' );
				}
			}
			let after: Cart;
			try {
				after = await cart();
			} catch {
				held.forEach( ( id ) => onStatus( id, 'added' ) );
				sent.forEach( ( id ) => onStatus( id, 'unverified' ) );
				return false;
			}
			let complete = sent.size + held.size === lines.length;
			for ( const line of lines ) {
				if ( held.has( line.productId ) ) {
					onStatus( line.productId, 'added' );
					continue;
				}
				if ( ! sent.has( line.productId ) ) {
					continue;
				}
				const shown = after.quantities.get( line.productId ) ?? 0;
				if ( shown >= line.quantity ) {
					onStatus( line.productId, 'added' );
				} else {
					onStatus( line.productId, 'unverified' );
					complete = false;
				}
			}
			return complete;
		},
	};
}
