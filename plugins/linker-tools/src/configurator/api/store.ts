/**
 * WooCommerce Store API: product display data and the solution draft (the cart).
 *
 * "Add all" adds each line, then reads the draft back and compares quantities:
 * a line counts as added only when the draft shows it (docs/specs/14 "走 Store
 * API 并读回"). A line the draft already holds at the scheme quantity is not
 * sent again: the live planner records a written line and leaves it out of the
 * next add, and the Store API adds onto an existing line rather than setting
 * it. Product display data is asked for in the page's language (`?lang=`,
 * linker-i18n's RestLang; the default is English). The `permalink` in that
 * response is already that language's product page (linker-i18n Storefront,
 * #413): a German card links to `/de/produkt/…` and an English card to
 * `/product/…`. Callers use the field as the link. They do not build a
 * second URL.
 */

/**
 * Internal dependencies
 */
import type { Locale, StoreProduct } from '../types';

type Fetch = typeof fetch;

export type AddStatus = 'pending' | 'added' | 'unverified' | 'retry';

/**
 * How long a short readback waits before reading the draft once more: a burst of
 * line writes can be a moment behind the cart read (seen once in the #251 e2e,
 * 2026-10-19, 16 lines; the Store API itself answered every line). A quarter
 * second is one paint of the card's "Adding…" and far below the customer's
 * patience; the reads settle `added` or `unverified`.
 */
const SETTLE_MS = 250;
// Reads after a short one, 250 ms apart: three retries cover a cart read that
// lagged a burst of 16 writes in the #251 e2e (seen in a few hundred runs on
// 2026-10-19; the Store API itself answered every line). The waits only happen
// when a line reads short, and each is followed by a real read.
const SETTLE_READS = 3;

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
			const short = () =>
				lines.some(
					( line ) =>
						sent.has( line.productId ) &&
						( after.quantities.get( line.productId ) ?? 0 ) <
							line.quantity
				);
			for (
				let attempt = 0;
				attempt < SETTLE_READS && short();
				attempt++
			) {
				// A line the first read did not show yet gets settled reads.
				await new Promise( ( resolve ) =>
					setTimeout( resolve, SETTLE_MS )
				);
				try {
					after = await cart();
				} catch {
					// Keep the last read: its statuses are the honest ones.
					break;
				}
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
