import type {
	ProtectionConfig,
	ProtectionState,
	PublicProtection,
	TurnstileApi,
} from './types';

// Initial interaction/network bounds are documented in spec 519.
const NETWORK_MS = 15000;
const CHALLENGE_MS = 120000;
// Cloudflare's documented default retry interval; the original challenge
// deadline stays absolute across retries (widget-configurations, 2026-10-28).
const RETRY_MS = 8000;
const API_SCRIPT =
	'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

interface Attempt {
	token?: string;
	promise: Promise< string >;
	container: HTMLElement;
	expires: number;
	widget?: string;
	reject?: ( reason: Error ) => void;
	/** The provider's own expiry already told the listener; it outranks `failed`. */
	expired?: boolean;
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
		container.dataset.linkerVerificationState = state;
		if ( state === 'checking' || state === 'ready' ) {
			delete container.dataset.linkerVerificationError;
		}
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
		} catch ( error: unknown ) {
			if (
				error instanceof Error &&
				error.message.startsWith( 'verification_' )
			) {
				throw error;
			}
			// These requests precede the protected operation. Preserve that
			// boundary even when fetch/abort/JSON throws an unrelated error type.
			let reason = 'verification_network';
			if ( controller.signal.aborted ) {
				reason = 'verification_network_timeout';
			} else if ( error instanceof SyntaxError ) {
				reason = 'verification_response';
			}
			throw new Error( reason, { cause: error } );
		} finally {
			clearTimeout( timer );
		}
		return result;
	}

	ready( action: string, container: HTMLElement ): string {
		const attempt = this.attempts.get( action );
		return attempt?.container === container && attempt.expires > Date.now()
			? attempt.token || ''
			: '';
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
			// Preparation, script load and validation each retain their network
			// bound. They must not expire an otherwise pending human challenge.
			expires: Date.now() + CHALLENGE_MS + 3 * NETWORK_MS,
			promise: Promise.resolve( '' ),
		};
		this.attempts.set( action, attempt );
		this.state( container, action, 'checking' );
		attempt.promise = this.run( action, attempt ).catch(
			( error: unknown ) => {
				if ( this.attempts.get( action ) === attempt ) {
					this.attempts.delete( action );
					this.remove( attempt );
					// The provider's expiry already published the accurate state;
					// `failed` here would overwrite it in the same tick.
					if ( ! attempt.expired ) {
						this.state( container, action, 'failed' );
					}
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
			let settled = false;
			let resetTimer: ReturnType< typeof setTimeout > | undefined;
			const clearTimers = () => {
				clearTimeout( timer );
				clearTimeout( resetTimer );
			};
			const fail = ( reason: string ) => {
				if ( settled ) {
					return;
				}
				settled = true;
				clearTimers();
				reject( new Error( reason ) );
			};
			const timer = setTimeout(
				() => fail( 'verification_timeout' ),
				CHALLENGE_MS
			);
			attempt.reject = ( reason: Error ) => {
				settled = true;
				clearTimers();
				reject( reason );
			};
			const retry = ( reset = false ) => {
				if ( settled ) {
					return;
				}
				this.state( attempt.container, action, 'retrying' );
				// Official 110600/110620 timeout recovery requires reset(),
				// unlike native auto-retry for iframe/generic challenge errors.
				// Neither branch can move the original challenge deadline.
				if ( reset && resetTimer === undefined ) {
					resetTimer = setTimeout( () => {
						resetTimer = undefined;
						if ( ! settled && attempt.widget !== undefined ) {
							try {
								api.reset( attempt.widget );
							} catch {
								fail( 'verification_widget' );
							}
						}
					}, RETRY_MS );
				}
			};
			try {
				attempt.widget = api.render( attempt.container, {
					sitekey: prepared.site_key,
					action,
					language: this.config.language,
					// Loaded only after interaction. Keep the provider's check,
					// failure feedback and recovery visible in that interaction.
					appearance: 'always',
					size: 'flexible',
					retry: 'auto',
					'retry-interval': RETRY_MS,
					'refresh-timeout': 'manual',
					callback: ( value ) => {
						if ( settled ) {
							return;
						}
						settled = true;
						clearTimers();
						resolve( value );
					},
					'error-callback': ( code ) => {
						if ( settled ) {
							return;
						}
						// Keep only the provider's fixed numeric diagnostic, never
						// a token or arbitrary provider response, for local inspection.
						const diagnostic = /^\d{6}$/.test( code ?? '' )
							? code!
							: '';
						if ( diagnostic ) {
							attempt.container.dataset.linkerVerificationError =
								diagnostic;
						}
						// The official error table marks these failures retryable.
						// Removing the widget here cancels the provider's native
						// retry and makes a genuine customer start over forever.
						if (
							/^(300|600)\d{3}$/.test( diagnostic ) ||
							[ '110600', '110620', '200500' ].includes(
								diagnostic
							)
						) {
							retry(
								[ '110600', '110620' ].includes( diagnostic )
							);
							return;
						}
						fail(
							`verification_widget${ diagnostic ? `_${ diagnostic }` : '' }`
						);
					},
					'before-interactive-callback': () => {
						if ( ! settled ) {
							attempt.container.hidden = false;
							this.state(
								attempt.container,
								action,
								'interactive'
							);
						}
					},
					'unsupported-callback': () =>
						fail( 'verification_unsupported' ),
					'expired-callback': () => {
						if ( this.attempts.get( action ) !== attempt ) {
							return;
						}
						// The listener's own `expired` state must survive the
						// rejection below; `failed` would overwrite it in the same
						// tick and make the state unreachable.
						attempt.expired = true;
						attempt.expires = 0;
						this.state( attempt.container, action, 'expired' );
						fail( 'verification_expired' );
					},
					'timeout-callback': () => retry( true ),
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
		attempt.token = result.proof;
		this.state( attempt.container, action, 'ready' );
		return result.proof;
	}

	private remove( attempt: Attempt ): void {
		attempt.reject?.( new Error( 'verification_cancelled' ) );
		if ( attempt.widget !== undefined ) {
			window.turnstile?.remove( attempt.widget );
		}
	}

	/**
	 * Retire only the proof used by the request that actually succeeded.
	 *
	 * @param action Completed resource scope.
	 * @param proof  Actual proof sent with the successful request.
	 */
	complete( action: string, proof: string ): boolean {
		const attempt = this.attempts.get( action );
		if ( ! proof || ! attempt || attempt.token !== proof ) {
			return false;
		}
		this.reset( action );
		return true;
	}

	reset( action: string ): void {
		const attempt = this.attempts.get( action );
		this.attempts.delete( action );
		if ( attempt ) {
			this.remove( attempt );
		}
	}
	/**
	 * Cancel only the widget owned by the closing surface.
	 * @param action    Current resource scope.
	 * @param container Actual widget of the closing surface.
	 */
	cancel( action: string, container: HTMLElement ): boolean {
		if ( this.attempts.get( action )?.container !== container ) {
			return false;
		}
		this.reset( action );
		return true;
	}
}
