/** Saving a current signed Genie product list without engineering input. */
import type { Locale } from '../../configurator/types';
import {
	SolutionWriteError,
	type SavedSolution,
} from '../../configurator/api/solutions';
import { resourceFetch } from '../../protection/request';

export class GenieSaveUnconfirmedError extends Error {
	constructor() {
		super( 'save_unconfirmed' );
		this.name = 'GenieSaveUnconfirmedError';
	}
}

export async function saveGenieSolution(
	restUrl: string,
	restNonce: string,
	proof: string,
	locale: Locale,
	fetcher: typeof fetch = ( ...args ) => fetch( ...args )
): Promise< SavedSolution > {
	if ( ! proof ) {
		throw new SolutionWriteError( true );
	}
	const cart = await fetcher( `${ restUrl }wc/store/v1/cart`, {
		credentials: 'same-origin',
	} );
	const nonce = cart.headers.get( 'Nonce' );
	if ( ! cart.ok || ! nonce ) {
		throw new SolutionWriteError( false );
	}
	let response: Response;
	try {
		response = await resourceFetch(
			fetcher,
			`${ restUrl }linker-ai/v1/genie/solution?lang=${ locale }`,
			{
				method: 'POST',
				credentials: 'same-origin',
				headers: {
					'Content-Type': 'application/json',
					Nonce: nonce,
					'X-WP-Nonce': restNonce,
				},
				body: JSON.stringify( { proof } ),
			}
		);
	} catch {
		throw new GenieSaveUnconfirmedError();
	}
	if ( response.status >= 500 ) {
		throw new GenieSaveUnconfirmedError();
	}
	if ( ! response.ok ) {
		const error = await response.json().catch( () => null );
		throw new SolutionWriteError(
			response.status === 409 && error?.code === 'linker_solution_changed'
		);
	}
	try {
		const saved = await response.json();
		if (
			! Number.isInteger( saved?.id ) ||
			typeof saved?.url !== 'string'
		) {
			throw new GenieSaveUnconfirmedError();
		}
		return saved;
	} catch {
		throw new GenieSaveUnconfirmedError();
	}
}
