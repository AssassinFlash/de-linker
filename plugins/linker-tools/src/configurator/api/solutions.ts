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
}

export async function saveSolution(
	restUrl: string,
	nonce: string,
	body: SolutionBody,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< SavedSolution > {
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
		} ),
	} );
	if ( ! response.ok ) {
		throw new Error( `save ${ response.status }` );
	}
	return response.json();
}
