/** Renew the WordPress session nonce only after core rejected authentication. */
let renewed: { initial: string; current: string } | undefined;

export const genieFetch: typeof fetch = async ( input, init ) => {
	const headers = new Headers( init?.headers );
	const initial = headers.get( 'X-WP-Nonce' );
	if ( ! initial ) {
		return fetch( input, init );
	}
	if ( renewed?.initial === initial ) {
		headers.set( 'X-WP-Nonce', renewed.current );
		init = { ...init, headers };
	}
	const response = await fetch( input, init );
	if (
		response.status !== 403 ||
		! response.headers.get( 'Content-Type' )?.includes( 'application/json' )
	) {
		return response;
	}
	const error = await response.clone().json();
	const mount = document.querySelector< HTMLElement >(
		'[data-genie-nonce-url]'
	);
	const url = mount?.dataset.genieNonceUrl;
	if ( error?.code !== 'rest_cookie_invalid_nonce' || ! url ) {
		return response;
	}
	const refreshed = await fetch( url, {
		credentials: 'same-origin',
		cache: 'no-store',
		signal: init?.signal,
	} );
	const nonce = ( await refreshed.text() ).trim();
	if (
		refreshed.status === 400 &&
		nonce === '0' &&
		mount?.dataset.signedIn === '0'
	) {
		// Core's rest-nonce action has no logged-out handler.
		headers.delete( 'X-WP-Nonce' );
		return fetch( input, { ...init, headers } );
	}
	if ( ! refreshed.ok || ! /^[a-z0-9]{10}$/i.test( nonce ) ) {
		return response;
	}
	renewed = { initial, current: nonce };
	headers.set( 'X-WP-Nonce', nonce );
	return fetch( input, { ...init, headers } );
};
