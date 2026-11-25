import { genieFetch } from './restFetch';
/**
 * Current product display and one server-verified, atomic solution-draft write.
 * The browser cannot turn a stale complete design into a subset of its lines.
 */

/**
 * Internal dependencies
 */
import type { Locale, StoreProduct } from '../types';
import { resourceFetch } from '../../protection/request';

type Fetch = typeof fetch;

export type AddStatus = 'pending' | 'added' | 'unverified' | 'retry' | 'stale';

interface DraftLine {
	productId: number;
	quantity: number;
}

interface StoreClient {
	products: ( ids: number[], locale: Locale ) => Promise< StoreProduct[] >;
	addAll: (
		lines: DraftLine[],
		onStatus: ( productId: number, status: AddStatus ) => void,
		proof?: string
	) => Promise< boolean >;
}

function containsSelection(
	items: { id: number; quantity: number }[],
	lines: DraftLine[]
): boolean {
	const out = new Map< number, number >();
	for ( const item of items ) {
		out.set( item.id, ( out.get( item.id ) ?? 0 ) + item.quantity );
	}
	return lines.every(
		( line ) => ( out.get( line.productId ) ?? 0 ) >= line.quantity
	);
}

export function storeClient(
	restUrl: string,
	fetcher: Fetch = genieFetch,
	restNonce = ''
): StoreClient {
	const base = `${ restUrl }wc/store/v1`;

	async function cartNonce(): Promise< string > {
		const response = await fetcher( `${ base }/cart`, {
			credentials: 'same-origin',
		} );
		if ( ! response.ok ) {
			throw new Error( `cart ${ response.status }` );
		}
		return response.headers.get( 'Nonce' ) ?? '';
	}

	async function addSelection(
		lines: DraftLine[],
		proof: string,
		nonce: string
	): Promise< AddStatus > {
		try {
			const response = await resourceFetch(
				fetcher,
				`${ restUrl }linker-ai/v1/genie/draft`,
				{
					method: 'POST',
					credentials: 'same-origin',
					headers: {
						'Content-Type': 'application/json',
						Nonce: nonce,
						...( restNonce ? { 'X-WP-Nonce': restNonce } : {} ),
					},
					body: JSON.stringify( { proof } ),
				}
			);
			if ( ! response.ok ) {
				if ( response.status === 409 ) {
					const error = await response.json().catch( () => null );
					if ( error?.code === 'linker_solution_changed' ) {
						return 'stale';
					}
				}
				return 'unverified';
			}
			const receipt = await response.json();
			if ( containsSelection( receipt.items ?? [], lines ) ) {
				return 'added';
			}
		} catch {
			// Woo can commit the draft before the browser receives a complete receipt.
		}
		try {
			const cart = await fetcher( `${ base }/cart?_fields=items`, {
				credentials: 'same-origin',
				cache: 'no-store',
			} );
			if (
				cart.ok &&
				containsSelection( ( await cart.json() ).items, lines )
			) {
				return 'added';
			}
		} catch {
			// The native cart is also unavailable. Keep the addition unconfirmed.
		}
		return 'unverified';
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
			if ( ! response.ok ) {
				// A refused read rejects: returning [] here once made a failed
				// Store API round look identical to "no such product", so the
				// card could not tell a pending read from a failed one (#901).
				throw new Error( `products ${ response.status }` );
			}
			const products: StoreProduct[] = await response.json();
			const text = document.createElement( 'textarea' );
			return products.map( ( product ) => {
				text.innerHTML = product.name.replace( /</g, '&lt;' );
				return { ...product, name: text.value };
			} );
		},

		async addAll( lines, onStatus, proof ) {
			const report = ( state: AddStatus ) =>
				lines.forEach( ( line ) => onStatus( line.productId, state ) );
			report( 'pending' );
			let state: AddStatus = 'stale';
			if ( proof !== undefined && lines.length > 0 ) {
				try {
					const nonce = await cartNonce();
					state = await addSelection( lines, proof, nonce );
				} catch {
					// Reading the native cart nonce failed before any write.
					state = 'retry';
				}
			}
			if ( state === 'added' ) {
				document.body.dispatchEvent(
					new CustomEvent( 'wc-blocks_added_to_cart', {
						bubbles: true,
					} )
				);
			}
			report( state );
			return state === 'added';
		},
	};
}
