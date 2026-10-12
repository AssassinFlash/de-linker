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
