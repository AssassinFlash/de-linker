/**
 * Current product display and one server-verified, atomic solution-draft write.
 * The browser cannot turn a stale complete design into a subset of its lines.
 */

/**
 * Internal dependencies
 */
import type {
	Locale,
	StoreProduct,
	ResidentialInput,
	CommercialInput,
} from '../types';
import { resourceFetch } from '../../protection/request';

type Fetch = typeof fetch;

export type AddStatus = 'pending' | 'added' | 'unverified' | 'retry' | 'stale';

export type SelectionProof =
	| {
			kind: 'residential';
			input: ResidentialInput;
			selection_fingerprint: string;
	  }
	| {
			kind: 'commercial';
			input: CommercialInput;
			selection_fingerprint: string;
			system_index: number;
	  };

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
		onStatus: ( productId: number, status: AddStatus ) => void,
		proof?: SelectionProof
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

		async addAll( lines, onStatus, proof ) {
			lines.forEach( ( line ) => onStatus( line.productId, 'pending' ) );
			let submitted = false;
			try {
				if ( ! proof || lines.length === 0 ) {
					lines.forEach( ( line ) =>
						onStatus( line.productId, 'stale' )
					);
					return false;
				}
				const before = await cart();
				submitted = true;
				const response = await resourceFetch(
					fetcher,
					`${ restUrl }linker/v1/solutions/draft`,
					{
						method: 'POST',
						credentials: 'same-origin',
						headers: {
							'Content-Type': 'application/json',
							Nonce: before.nonce,
							...( restNonce ? { 'X-WP-Nonce': restNonce } : {} ),
						},
						body: JSON.stringify( proof ),
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
