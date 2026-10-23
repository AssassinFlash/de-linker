/**
 * Saving a solution to the customer's account: POST linker/v1/solutions.
 *
 * The route belongs to linker-commerce (the account's "Solution drafts /
 * Lösungsentwürfe", docs/specs/11-commerce.md); it accepts a logged-in user
 * or the claim cookie of a guest. The body is the engine input, which
 * reproduces the design, plus the lines the customer saw.
 *
 * The answer's `url` is the account page of the request's language (#473):
 * linker-commerce builds it with `wc_get_account_endpoint_url()`, and
 * linker-i18n answers that in German only while the request is German
 * (RestLang's `?lang=`, Storefront's German page id, GermanRoutes'
 * endpoint). The save names the page's language the way store.ts's product
 * reads do, so a German page opens
 * `/de/mein-konto/gespeicherte-loesungen/` and an English one
 * `/my-account/saved-solutions/`.
 */

/**
 * Internal dependencies
 */
import type { Locale, ResidentialInput } from '../types';
import type { DraftLine } from './store';

import { resourceFetch } from '../../protection/request';

type Fetch = typeof fetch;

export interface SavedSolution {
	id: number;
	url: string;
}

export class SolutionWriteError extends Error {
	constructor( public readonly changed: boolean ) {
		super( changed ? 'solution_changed' : 'solution_write_failed' );
		this.name = 'SolutionWriteError';
	}
}

export interface SolutionBody {
	kind: 'residential';
	title: string;
	selectionFingerprint?: string;
	input: ResidentialInput;
	lines: DraftLine[];
	/**
	 * Design report PDF for this input, from the engine's existing
	 * `report/pdf` path. Omitted when the save has no design report
	 * (a product card, not a configurator result).
	 */
	reportPdf?: Blob | null;
}

/**
 * Base64 of PDF bytes, the shape SolutionsRoute already accepts as `report_pdf`.
 *
 * @param blob Design report PDF.
 */
function pdfBase64( blob: Blob ): Promise< string > {
	return new Promise( ( resolve, reject ) => {
		const reader = new FileReader();
		reader.onload = () => {
			const data = String( reader.result );
			const comma = data.indexOf( ',' );
			resolve( comma >= 0 ? data.slice( comma + 1 ) : data );
		};
		reader.onerror = () => reject( reader.error ?? new Error( 'report' ) );
		reader.readAsDataURL( blob );
	} );
}

/**
 * Saves the solution and answers where the account shows it.
 *
 * @param restUrl The WordPress REST root.
 * @param nonce   A wp_rest nonce.
 * @param body    The design input and the lines the customer saw.
 * @param locale  The page's language; the answer's URL follows it.
 * @param fetcher Fetch, for tests.
 */
export async function saveSolution(
	restUrl: string,
	nonce: string,
	body: SolutionBody,
	locale: Locale,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< SavedSolution > {
	const reportPdf = body.reportPdf ? await pdfBase64( body.reportPdf ) : '';
	const endpoint = `${ restUrl }linker/v1/solutions?lang=${ locale }`;
	const response = await resourceFetch( fetcher, endpoint, {
		method: 'POST',
		credentials: 'same-origin',
		headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
		body: JSON.stringify( {
			kind: body.kind,
			title: body.title,
			input: body.input,
			selection_fingerprint: body.selectionFingerprint ?? '',
			lines: body.lines.map( ( line ) => ( {
				product_id: line.productId,
				quantity: line.quantity,
			} ) ),
			...( reportPdf ? { report_pdf: reportPdf } : {} ),
		} ),
	} );
	if ( ! response.ok ) {
		const error = await response.json().catch( () => null );
		throw new SolutionWriteError(
			response.status === 409 && error?.code === 'linker_solution_changed'
		);
	}
	return response.json();
}
