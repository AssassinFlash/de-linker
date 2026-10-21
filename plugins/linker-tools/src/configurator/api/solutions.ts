/**
 * Saving a solution to the customer's account: POST linker/v1/solutions.
 *
 * The route belongs to linker-commerce (the account's "Solution drafts /
 * Lösungsentwürfe", docs/specs/11-commerce.md); it accepts a logged-in user
 * or the claim cookie of a guest. The body is the engine input, which
 * reproduces the design, plus the lines the customer saw.
 */

/**
 * Internal dependencies
 */
import type { ResidentialInput } from '../types';
import type { DraftLine } from './store';

type Fetch = typeof fetch;

export interface SavedSolution {
	id: number;
	url: string;
}

export interface SolutionBody {
	kind: 'residential';
	title: string;
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

export async function saveSolution(
	restUrl: string,
	nonce: string,
	body: SolutionBody,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< SavedSolution > {
	const reportPdf = body.reportPdf ? await pdfBase64( body.reportPdf ) : '';
	const response = await fetcher( `${ restUrl }linker/v1/solutions`, {
		method: 'POST',
		credentials: 'same-origin',
		headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
		body: JSON.stringify( {
			kind: body.kind,
			title: body.title,
			input: body.input,
			lines: body.lines.map( ( line ) => ( {
				product_id: line.productId,
				quantity: line.quantity,
			} ) ),
			...( reportPdf ? { report_pdf: reportPdf } : {} ),
		} ),
	} );
	if ( ! response.ok ) {
		throw new Error( `save ${ response.status }` );
	}
	return response.json();
}
