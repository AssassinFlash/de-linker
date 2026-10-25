/**
 * The model name of one product, from the get-product ability — the one
 * reader of the pa_model term (linker-commerce's ProductText). The Store API
 * response carries no model, so the card fetches it here instead of showing
 * `#<id>` (AGENTS.md §3: reuse Woo's data, name products by their model).
 *
 * Read-only abilities answer anonymous GETs; the input rides as nested query
 * parameters, exactly what the service's AbilityClient sends.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../../configurator/types';

type Fetch = typeof fetch;

/**
 * Reads one product's model term, empty when the product has none.
 *
 * @param restUrl   The WordPress REST root.
 * @param productId Product ID.
 * @param locale    Page language.
 * @param fetcher   Fetch for tests.
 */
export async function productModel(
	restUrl: string,
	productId: number,
	locale: Locale,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< string > {
	try {
		const base = restUrl.replace( /\/?$/, '/' );
		const url =
			`${ base }wp-abilities/v1/abilities/linker/get-product/run` +
			`?input[product_id]=${ productId }&input[lang]=${ locale }`;
		const response = await fetcher( url, { credentials: 'same-origin' } );
		if ( ! response.ok ) {
			return '';
		}
		const body = ( await response.json() ) as {
			result?: { model?: string | null };
			model?: string | null;
		};
		const model = body.result?.model ?? body.model ?? null;
		return typeof model === 'string' ? model : '';
	} catch {
		return '';
	}
}

/** Current customer and document data, from the same read-only product ability. */
export interface ProductPresentation {
	product_id: number;
	model?: string | null;
	documents?: Array< {
		url?: string;
		title?: string;
		type?: string;
		lang?: string;
	} >;
	commerce?: {
		price_visible?: boolean;
		price_line?: string;
		price_reason?: string | null;
	};
}

/**
 * Use the same 20-second native-read budget as Genie's AbilityClient and
 * PublicationClient. Current customer acceptance measured valid native reads
 * at 8–10 seconds; the former five-second presentation timer discarded their
 * current permissions and document links. Failure still removes stale data,
 * and hung reads remain bounded (docs/specs/13-genie.md, 2026-10-24).
 */
export const ARTIFACT_TIMEOUT_MS = 20_000;

/**
 * Historical prices are snapshots, so restore them from current authority.
 * REST cookie authentication requires the page's nonce; no-store also prevents
 * an approved response being reused after the customer or locale changes.
 *
 * @param restUrl   WordPress REST root.
 * @param productId Product ID.
 * @param locale    Current page language.
 * @param nonce     Current page's wp_rest nonce.
 * @param fetcher   Fetch for tests.
 */
export async function productPresentation(
	restUrl: string,
	productId: number,
	locale: Locale,
	nonce: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< ProductPresentation | null > {
	const controller = new AbortController();
	let timer: ReturnType< typeof setTimeout > | undefined;
	const timeout = new Promise< null >( ( resolve ) => {
		timer = setTimeout( () => {
			controller.abort();
			resolve( null );
		}, ARTIFACT_TIMEOUT_MS );
	} );
	const attempt = async (): Promise< ProductPresentation | null > => {
		try {
			const url =
				`${ restUrl.replace( /\/?$/, '/' ) }wp-abilities/v1/abilities/linker/get-product/run` +
				`?input[product_id]=${ productId }&input[lang]=${ locale }`;
			const response = await fetcher( url, {
				credentials: 'same-origin',
				cache: 'no-store',
				headers: { 'X-WP-Nonce': nonce },
				signal: controller.signal,
			} );
			if ( ! response.ok ) {
				return null;
			}
			const body = await response.json();
			const product = body?.result ?? body;
			if ( product?.product_id !== productId ) {
				return null;
			}
			return {
				...product,
				model: typeof product.model === 'string' ? product.model : null,
				documents: Array.isArray( product.documents )
					? product.documents.filter( ( item: unknown ) => {
							if ( ! item || typeof item !== 'object' ) {
								return false;
							}
							const document = item as Record< string, unknown >;
							return [ 'url', 'title', 'type', 'lang' ].every(
								( key ) =>
									document[ key ] === undefined ||
									typeof document[ key ] === 'string'
							);
						} )
					: [],
			};
		} catch {
			return null;
		}
	};
	try {
		// Race the body too, and settle even when a transport ignores abort.
		return await Promise.race( [ attempt(), timeout ] );
	} finally {
		if ( timer !== undefined ) {
			clearTimeout( timer );
		}
	}
}
