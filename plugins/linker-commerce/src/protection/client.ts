import type {
	ProtectionConfig,
	ProtectionState,
	PublicProtection,
	TurnstileApi,
} from './types';

// Initial interaction/network bounds are documented in spec 519.
const NETWORK_MS = 15000;
const CHALLENGE_MS = 120000;
const API_SCRIPT =
	'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

interface Attempt {
	promise: Promise< string >;
	container: HTMLElement;
	expires: number;
	widget?: string;
	reject?: ( reason: Error ) => void;
}

export class ProtectionClient implements PublicProtection {
	private script?: Promise< TurnstileApi >;
	private attempts = new Map< string, Attempt >();

	constructor( private config: ProtectionConfig ) {}

	private state(
		container: HTMLElement,
		action: string,
		state: ProtectionState
	) {
		container.dispatchEvent(
			new CustomEvent( 'linker:protection', {
				bubbles: true,
				detail: { action, state },
			} )
		);
	}

	private load(): Promise< TurnstileApi > {
		if ( window.turnstile ) {
			return Promise.resolve( window.turnstile );
		}
		if ( ! this.script ) {
			this.script = new Promise( ( resolve, reject ) => {
				const script = document.createElement( 'script' );
				const fail = () => {
					clearTimeout( timer );
					script.remove();
					reject( new Error( 'verification_script' ) );
				};
				const timer = setTimeout( fail, NETWORK_MS );
				script.src = API_SCRIPT;
				script.async = true;
				script.onerror = fail;
				script.onload = () => {
					if ( ! window.turnstile ) {
						fail();
						return;
					}
					clearTimeout( timer );
					resolve( window.turnstile );
				};
				document.head.append( script );
			} );
			this.script.catch( () => {
				this.script = undefined;
			} );
		}
		return this.script;
	}

	private async request< T >(
		operation: string,
		input: object
	): Promise< T > {
		const url = new URL( this.config.api );
		if ( url.searchParams.has( 'rest_route' ) ) {
			url.searchParams.set(
				'rest_route',
				`${ url.searchParams.get( 'rest_route' ) }/${ operation }`
			);
		} else {
			url.pathname = `${ url.pathname.replace( /\/$/, '' ) }/${ operation }`;
		}
		url.searchParams.set( '_locale', 'user' );
		const controller = new AbortController();
		const timer = setTimeout( () => controller.abort(), NETWORK_MS );
		let result: T;
		try {
			const response = await fetch( url.href, {
				method: 'POST',
				credentials: 'same-origin',
				cache: 'no-store',
				headers: {
					'Content-Type': 'application/json',
					'X-WP-Nonce': this.config.nonce,
				},
				body: JSON.stringify( input ),
				signal: controller.signal,
			} );
			if ( ! response.ok ) {
				throw new Error( `verification_http_${ response.status }` );
			}
			result = ( await response.json() ) as T;
		} finally {
			clearTimeout( timer );
		}
		return result;
	}

	warm( action: string, container: HTMLElement ): Promise< string > {
		return this.proof( action, container );
	}

	proof( action: string, container: HTMLElement ): Promise< string > {
		const prior = this.attempts.get( action );
		if (
			prior &&
			prior.container === container &&
			prior.expires > Date.now()
		) {
			return prior.promise;
		}
		this.reset( action );
		const attempt: Attempt = {
			container,
			expires: Date.now() + CHALLENGE_MS,
			promise: Promise.resolve( '' ),
		};
		this.attempts.set( action, attempt );
		this.state( container, action, 'checking' );
		attempt.promise = this.run( action, attempt ).catch(
			( error: unknown ) => {
				if ( this.attempts.get( action ) === attempt ) {
					this.attempts.delete( action );
					this.remove( attempt );
					this.state( container, action, 'failed' );
				}
				throw error;
			}
		);
		return attempt.promise;
	}

	private async run( action: string, attempt: Attempt ): Promise< string > {
		if ( ! [ 'observe', 'enforce' ].includes( this.config.mode ) ) {
			throw new Error( 'verification_disabled' );
		}
		const prepared = await this.request< {
			site_key: string;
			prepare: string;
		} >( 'prepare', { action } );
		const api = await this.load();
		if (
			this.attempts.get( action ) !== attempt ||
			! attempt.container.isConnected
		) {
			throw new Error( 'verification_cancelled' );
		}
		const token = await new Promise< string >( ( resolve, reject ) => {
			const fail = ( reason: string ) => {
				clearTimeout( timer );
				reject( new Error( reason ) );
			};
			const timer = setTimeout(
				() => fail( 'verification_timeout' ),
				CHALLENGE_MS
			);
			attempt.reject = ( reason: Error ) => {
				clearTimeout( timer );
				reject( reason );
			};
			try {
				attempt.widget = api.render( attempt.container, {
					sitekey: prepared.site_key,
					action,
					language: this.config.language,
					appearance: 'interaction-only',
					callback: ( value ) => {
						clearTimeout( timer );
						resolve( value );
					},
					'error-callback': () => fail( 'verification_widget' ),
					'expired-callback': () => {
						attempt.expires = 0;
						this.state( attempt.container, action, 'expired' );
						fail( 'verification_expired' );
					},
					'timeout-callback': () => fail( 'verification_timeout' ),
				} );
			} catch {
				fail( 'verification_widget' );
			}
		} );
		if ( this.attempts.get( action ) !== attempt ) {
			throw new Error( 'verification_cancelled' );
		}
		const result = await this.request< {
			proof: string;
			expires: number;
			ttl: number;
		} >( 'verify', { action, prepare: prepared.prepare, token } );
		if (
			this.attempts.get( action ) !== attempt ||
			! result.proof ||
			! Number.isFinite( result.ttl ) ||
			result.ttl <= 0
		) {
			throw new Error( 'verification_expired' );
		}
		// Local clock skew cannot invalidate a genuine customer challenge.
		// The server still enforces the original signed absolute expiry.
		attempt.expires = Date.now() + Math.min( result.ttl, 300 ) * 1000;
		this.state( attempt.container, action, 'ready' );
		return result.proof;
	}

	private remove( attempt: Attempt ): void {
		attempt.reject?.( new Error( 'verification_cancelled' ) );
		if ( attempt.widget !== undefined ) {
			window.turnstile?.remove( attempt.widget );
		}
	}

	reset( action: string ): void {
		const attempt = this.attempts.get( action );
		this.attempts.delete( action );
		if ( attempt ) {
			this.remove( attempt );
		}
	}
}
