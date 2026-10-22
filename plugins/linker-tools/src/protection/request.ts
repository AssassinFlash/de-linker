/** Shared proof/UUID transport; no customer input is persisted outside app memory. */
import { __ } from '@wordpress/i18n';

interface PublicClient {
	proof: ( action: string, container: HTMLElement ) => Promise< string >;
	reset: ( action: string ) => void;
}

declare global {
	interface Window {
		linkerPublicProtectionConfig?: {
			api: string;
			nonce: string;
			mode: string;
			language: 'en' | 'de';
		};
		linkerPublicProtection?: PublicClient;
	}
}

const operations = new Map< string, string >();
const containers = new Map< string, HTMLElement >();
const statuses = new WeakMap< HTMLElement, HTMLElement >();

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
	if ( ! [ 'POST', 'DELETE' ].includes( method.toUpperCase() ) ) {
		return '';
	}
	const parsed = new URL( url, window.location.href );
	const path = (
		parsed.searchParams.get( 'rest_route' ) ??
		parsed.pathname.replace( /^.*\/wp-json/i, '' )
	).toLowerCase();
	if ( path.endsWith( '/genie/turn' ) ) {
		return 'genie';
	}
	if ( path.endsWith( '/genie/contact' ) ) {
		return 'genie_contact';
	}
	if ( path.endsWith( '/genie/inquiry' ) ) {
		return 'genie_inquiry';
	}
	if ( /\/genie\/conversations\/\d+\/email$/.test( path ) ) {
		return 'conversation_mail';
	}
	if ( /\/genie\/turn\/\d+\/vote$/.test( path ) ) {
		return 'vote';
	}
	if ( path.endsWith( '/genie/conversations' ) ) {
		try {
			return JSON.parse( String( body ?? '{}' ) ).id
				? 'conversation_write'
				: 'conversation_create';
		} catch {
			return 'conversation_create';
		}
	}
	if ( /\/genie\/conversations\/\d+$/.test( path ) ) {
		return 'conversation_write';
	}
	if ( /\/engine\/design\/(residential|commercial)$/.test( path ) ) {
		return 'design';
	}
	if ( /\/engine\/roof\/(outline|pack)$/.test( path ) ) {
		return 'roof';
	}
	if ( path.endsWith( '/engine/report/pdf' ) ) {
		return 'report_pdf';
	}
	if ( path.endsWith( '/linker/v1/solutions' ) ) {
		return 'solution_save';
	}
	return '';
}

// Capture the interaction before React disables/moves focus during submission.
let lastForm: HTMLFormElement | null = null;
if ( typeof document !== 'undefined' ) {
	document.addEventListener( 'focusin', ( event ) => {
		if ( event.target instanceof Element ) {
			lastForm = event.target.closest( 'form' );
		}
	} );
}

function containerFor( action: string ): HTMLElement {
	const visible = ( element: Element ) => element.getClientRects().length > 0;
	const forms = Array.from(
		document.querySelectorAll< HTMLFormElement >(
			'form.linker-genie-app__composer, form'
		)
	);
	const form =
		lastForm?.isConnected && visible( lastForm )
			? lastForm
			: forms.find(
					( candidate ) =>
						visible( candidate ) &&
						candidate.querySelector( 'textarea' )
				);
	const old = containers.get( action );
	if (
		old?.isConnected &&
		( ! form || old.parentElement === form.parentElement )
	) {
		return old;
	}
	if ( old ) {
		statuses.get( old )?.remove();
	}
	old?.remove();
	const container = document.createElement( 'div' );
	container.dataset.linkerResourceVerification = action;
	const status = document.createElement( 'p' );
	status.setAttribute( 'role', 'status' );
	status.setAttribute( 'aria-live', 'polite' );
	container.addEventListener( 'linker:protection', ( event ) => {
		const state = ( event as CustomEvent< { state: string } > ).detail
			.state;
		if ( state === 'checking' ) {
			status.textContent = __( 'Checking verification…', 'linker-tools' );
		} else if ( state === 'ready' ) {
			status.textContent = '';
		} else {
			status.textContent = __(
				'Verification could not be completed. Your input is still here. Please try again.',
				'linker-tools'
			);
		}
	} );
	if ( form?.parentElement ) {
		form.before( status, container );
	} else {
		( document.querySelector( 'main' ) ?? document.body ).append(
			status,
			container
		);
	}
	statuses.set( container, status );
	containers.set( action, container );
	return container;
}

/**
 * One logical operation keeps its UUID across an ambiguous network retry. A
 * successful response releases that UUID; a new explicit action gets a new one.
 * The server chooses dimensions, identity, version and engine deduplication.
 * @param fetcher
 * @param input
 * @param init
 * @param onOperation Receives the actual enforced operation just before sending.
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
	const config = window.linkerPublicProtectionConfig;
	let url: string;
	if ( typeof input === 'string' ) {
		url = input;
	} else if ( input instanceof URL ) {
		url = input.href;
	} else {
		url = input.url;
	}
	const action = resourceAction( url, init?.method, init?.body );
	if ( ! config || config.mode === 'off' || ! action ) {
		return fetcher( input, init );
	}
	const observe = config.mode === 'observe';
	const client = window.linkerPublicProtection;
	if ( ! observe && ! client ) {
		throw new Error( 'verification_unavailable' );
	}
	const headers = new Headers( init?.headers );
	if ( ! headers.has( 'X-WP-Nonce' ) ) {
		headers.set( 'X-WP-Nonce', config.nonce );
	}
	let key = '';
	let id = '';
	try {
		// Hash keys avoid retaining an extra copy of an uploaded file in the map.
		const hash = await crypto.subtle.digest(
			'SHA-256',
			new TextEncoder().encode(
				`${ init?.method }|${ url }|${ String( init?.body ?? '' ) }`
			)
		);
		key = Array.from( new Uint8Array( hash ), ( value ) =>
			value.toString( 16 ).padStart( 2, '0' )
		).join( '' );
		id = operations.get( key ) ?? crypto.randomUUID();
		if ( ! operations.has( key ) ) {
			if ( operations.size >= 8 ) {
				operations.delete( operations.keys().next().value as string );
			}
			operations.set( key, id );
		}
	} catch ( error ) {
		if ( ! observe ) {
			throw error;
		}
		// Shadow diagnostics cannot prevent the original authenticated request.
	}
	if ( id ) {
		headers.set( 'X-Linker-Operation', id );
	}
	if ( ! observe ) {
		const proof = await client!.proof( action, containerFor( action ) );
		headers.set( 'X-Linker-Proof', proof );
	}
	init?.signal?.throwIfAborted();
	if ( id && ! observe ) {
		onOperation?.( id );
	}
	const response = await fetcher( input, {
		...init,
		headers,
		credentials: 'same-origin',
	} );
	if ( response.ok ) {
		operations.delete( key );
		if (
			[ 'genie_contact', 'genie_inquiry', 'conversation_mail' ].includes(
				action
			)
		) {
			if ( ! observe ) {
				client?.reset( action );
			}
		}
	} else if ( [ 429, 502, 503 ].includes( response.status ) ) {
		// A gateway status alone says nothing about a completed business write.
		// Only the native adapter's known pure-work failure permits a fresh UUID.
		const pure = [ 'design', 'roof', 'report_pdf' ].includes( action );
		let code = '';
		try {
			const data: unknown = await response.clone().json();
			if ( data && typeof data === 'object' && 'code' in data ) {
				code = String( data.code );
			}
		} catch {
			// An absent/untrusted body preserves the original operation identity.
		}
		if (
			( pure &&
				response.headers.get( 'X-Linker-Resource-Outcome' ) ===
					'failed' ) ||
			code === 'linker_admission_quota' ||
			( action === 'genie' && code === 'linker_genie_quota' )
		) {
			operations.delete( key );
		}
	} else if ( [ 400, 409 ].includes( response.status ) ) {
		// Proof expiry needs a new proof, not another side effect. The UUID
		// remains stable so the journal can recover an already completed write.
		if ( ! observe ) {
			client?.reset( action );
		}
	}
	return response;
}
