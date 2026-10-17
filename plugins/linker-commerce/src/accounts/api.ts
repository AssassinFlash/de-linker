/**
 * WordPress dependencies
 */
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { Collection, Decision, SavedDecision } from './types';

export class AccountsApi {
	constructor(
		private readonly url: string,
		private readonly nonce: string
	) {}

	private async request< T >(
		url: string,
		options: RequestInit = {}
	): Promise< T > {
		// Native WordPress REST locale selector: card data uses the employee's
		// backend language, independently of the site's default language.
		const endpoint = new URL( url );
		endpoint.searchParams.set( '_locale', 'user' );
		const response = await fetch( endpoint.href, {
			...options,
			credentials: 'same-origin',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': this.nonce,
			},
		} );
		const result = await response.json();
		if ( ! response.ok ) {
			throw new Error(
				typeof result.message === 'string'
					? result.message
					: __(
							'The request failed. Please try again.',
							'linker-commerce'
						)
			);
		}
		return result as T;
	}

	list(
		focus = 0,
		status: 'pending' | 'restricted' = 'pending'
	): Promise< Collection > {
		const url = new URL( this.url );
		if ( focus ) {
			url.searchParams.set( 'focus', String( focus ) );
		}
		if ( status === 'restricted' ) {
			url.searchParams.set( 'status', status );
		}
		return this.request< Collection >( url.href );
	}

	decide(
		id: number,
		status: Decision,
		reason: string
	): Promise< SavedDecision > {
		const url = new URL( this.url );
		// WordPress may use ?rest_route= instead of pretty REST permalinks.
		if ( url.searchParams.has( 'rest_route' ) ) {
			url.searchParams.set(
				'rest_route',
				`${ url.searchParams.get( 'rest_route' ) }/${ id }/approval`
			);
		} else {
			url.pathname = `${ url.pathname.replace( /\/$/, '' ) }/${ id }/approval`;
		}
		return this.request< SavedDecision >( url.href, {
			method: 'POST',
			body: JSON.stringify( { status, reason } ),
		} );
	}
}
