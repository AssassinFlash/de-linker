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

function quantities( items: { id: number; quantity: number }[] ) {
	const out = new Map< number, number >();
	for ( const item of items ) {
		out.set( item.id, ( out.get( item.id ) ?? 0 ) + item.quantity );
	}
	return out;
}

export function storeClient(
	restUrl: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args ),
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
			lines.forEach( ( line ) => onStatus( line.productId, 'pending' ) );
			let submitted = false;
			try {
				if ( proof === undefined || lines.length === 0 ) {
					lines.forEach( ( line ) =>
						onStatus( line.productId, 'stale' )
					);
					return false;
				}
				const nonce = await cartNonce();
				submitted = true;
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
					const error = await response.json().catch( () => null );
					if (
						response.status === 409 &&
						error?.code === 'linker_solution_changed'
					) {
						lines.forEach( ( line ) =>
							onStatus( line.productId, 'stale' )
						);
						return false;
					}
					throw new Error( `draft ${ response.status }` );
				}
				const body = await response.json();
				const after = quantities( body.items ?? [] );
				document.body.dispatchEvent(
					new CustomEvent( 'wc-blocks_added_to_cart', {
						bubbles: true,
					} )
				);
				const complete = lines.every(
					( line ) =>
						( after.get( line.productId ) ?? 0 ) >= line.quantity
				);
				lines.forEach( ( line ) =>
					onStatus(
						line.productId,
						complete ? 'added' : 'unverified'
					)
				);
				return complete;
			} catch {
				lines.forEach( ( line ) =>
					onStatus(
						line.productId,
						submitted ? 'unverified' : 'retry'
					)
				);
				return false;
			}
		},
	};
}
