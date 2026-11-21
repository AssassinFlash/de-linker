/** Retain the native write identity across an uncertain response. */
const operations = new Map< string, string >();

/**
 * Only writes that the native resource adapter owns; reads stay ordinary reads.
 * @param url
 * @param method
 * @param body
 */
export function resourceAction(
	url: string,
	method = 'GET',
	body?: BodyInit | null
): string {
	if ( method.toUpperCase() !== 'POST' ) {
		return '';
	}
	const parsed = new URL( url, window.location.href );
	const route = (
		parsed.searchParams.get( 'rest_route' ) ??
		parsed.pathname.replace( /^.*\/wp-json/i, '' )
	).toLowerCase();
	if ( route === '/linker-ai/v1/genie/turn' ) {
		return 'genie';
	}
	if ( route === '/linker-ai/v1/genie/solution' ) {
		return 'solution_save';
	}
	if (
		route === '/linker-ai/v1/genie/conversations' &&
		! JSON.parse( String( body ?? '{}' ) ).id
	) {
		return 'conversation_create';
	}
	return '';
}

/**
 * Send the business request once. An explicit retry of an uncertain write uses its original operation.
 *
 * @param fetcher     Native transport.
 * @param input       Route.
 * @param init        Request data and native WordPress nonce.
 * @param onOperation Notifies the composer which persisted turn to recover.
 */
export async function resourceFetch(
	fetcher: typeof fetch,
	input: RequestInfo | URL,
	init?: RequestInit,
	onOperation?: ( id: string ) => void
): Promise< Response > {
	if ( typeof window === 'undefined' ) {
		return fetcher( input, init );
	}
	const url =
		typeof input === 'string' || input instanceof URL
			? String( input )
			: input.url;
	const action = resourceAction( url, init?.method, init?.body );
	if ( ! action ) {
		return fetcher( input, init );
	}
	init?.signal?.throwIfAborted();
	// Keep just the digest of potentially large uploaded files in browser memory.
	const digest = await crypto.subtle.digest(
		'SHA-256',
		new TextEncoder().encode(
			`${ init?.method }|${ url }|${ String( init?.body ?? '' ) }`
		)
	);
	const key = Array.from( new Uint8Array( digest ), ( n ) =>
		n.toString( 16 ).padStart( 2, '0' )
	).join( '' );
	const id = operations.get( key ) ?? crypto.randomUUID();
	if ( ! operations.has( key ) ) {
		if ( operations.size >= 8 ) {
			operations.delete( operations.keys().next().value as string );
		}
		operations.set( key, id );
	}
	const headers = new Headers( init?.headers );
	headers.set( 'X-Linker-Operation', id );
	init?.signal?.throwIfAborted();
	onOperation?.( id );
	const response = await fetcher( input, {
		...init,
		headers,
		credentials: 'same-origin',
	} );
	if (
		response.ok ||
		response.headers.get( 'X-Linker-Resource-Outcome' ) === 'failed'
	) {
		if ( operations.get( key ) === id ) {
			operations.delete( key );
		}
	}
	return response;
}
