import { __ } from '@wordpress/i18n';
import type { FormAction, TurnstileApi, WidgetConfig, Widgets } from './types';

const scriptUrl =
	'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

function failureMessage(): string {
	return __(
		'Verification could not be completed. No request has been sent in this attempt. Please try again or email sales@de-linker.com.',
		'linker-commerce'
	);
}

/**
 * The first visible business form loads the provider for the document.
 *
 * @param config Public widget key and current form language.
 */
export function createWidgets( config: WidgetConfig ): Widgets {
	let loading: Promise< TurnstileApi > | undefined;
	const retries = new WeakMap< HTMLElement, () => void >();

	function load(): Promise< TurnstileApi > {
		if ( window.turnstile ) {
			return Promise.resolve( window.turnstile );
		}
		if ( ! loading ) {
			loading = new Promise< TurnstileApi >( ( resolve, reject ) => {
				const script = document.createElement( 'script' );
				const failure = () => {
					loading = undefined;
					script.remove();
					reject( new Error( 'turnstile_unavailable' ) );
				};
				script.src = scriptUrl;
				script.async = true;
				script.onload = () =>
					window.turnstile ? resolve( window.turnstile ) : failure();
				script.onerror = failure;
				document.head.append( script );
			} );
		}
		return loading;
	}

	function mount(
		container: HTMLElement,
		action: FormAction,
		onToken?: ( token: string ) => void
	): () => void {
		let id: string | undefined;
		let disposed = false;
		const slot = document.createElement( 'div' );
		const status = document.createElement( 'p' );
		status.setAttribute( 'role', 'status' );
		status.hidden = true;
		const retry = document.createElement( 'button' );
		retry.type = 'button';
		retry.className = 'btn-secondary';
		retry.textContent = __( 'Try again', 'linker-commerce' );
		retry.hidden = true;
		container.append( slot, status, retry );

		function feedback( message: string ) {
			status.textContent = message;
			status.hidden = ! message;
		}
		function failed() {
			onToken?.( '' );
			feedback( failureMessage() );
			retry.hidden = false;
			return true;
		}
		function reset() {
			onToken?.( '' );
			feedback( '' );
			retry.hidden = true;
			if ( id !== undefined ) {
				window.turnstile?.reset( id );
			} else {
				void render();
			}
		}
		async function render() {
			try {
				const api = await load();
				if ( disposed ) {
					return;
				}
				id = api.render( slot, {
					sitekey: config.siteKey,
					action,
					language: config.language,
					// Flexible widgets require 300 CSS pixels; narrow mobile forms use compact.
					size: container.clientWidth >= 300 ? 'flexible' : 'compact',
					'refresh-expired': 'manual',
					callback: ( token ) => {
						feedback( '' );
						retry.hidden = true;
						onToken?.( token );
					},
					'expired-callback': reset,
					'error-callback': failed,
				} );
			} catch {
				if ( ! disposed ) {
					failed();
				}
			}
		}
		retry.onclick = reset;
		retries.set( container, reset );
		void render();
		return () => {
			disposed = true;
			retries.delete( container );
			if ( id !== undefined ) {
				window.turnstile?.remove( id );
			}
			slot.remove();
			status.remove();
			retry.remove();
		};
	}

	return { mount, refresh: ( container ) => retries.get( container )?.() };
}

const actions = [ 'inquiry', 'contact', 'registration' ] as const;
const mounted = new WeakSet< HTMLElement >();

/**
 * Native fields are serialized by the browser together with the provider's response.
 *
 * @param root    The current document or a newly mounted inquiry form.
 * @param widgets The widgets shared by native forms and Genie.
 */
export function connectForms( root: ParentNode, widgets: Widgets ): void {
	const markers = root.querySelectorAll< HTMLElement >(
		'[data-linker-turnstile]'
	);
	for ( const marker of markers ) {
		const action = actions.find(
			( name ) => name === marker.dataset.linkerTurnstile
		);
		const form = marker.closest( 'form' );
		if ( ! action || ! form || mounted.has( marker ) ) {
			continue;
		}
		mounted.add( marker );
		let ready = false;
		let pending: HTMLElement | null | undefined;
		const clearPending = ( event: Event ) => {
			if (
				event.target instanceof HTMLElement &&
				! marker.contains( event.target )
			) {
				pending = undefined;
			}
		};
		form.addEventListener( 'input', clearPending );
		form.addEventListener( 'change', clearPending );
		const start = () =>
			widgets.mount( marker, action, ( token ) => {
				ready = Boolean( token );
				if ( ready && pending !== undefined ) {
					const submitter = pending;
					pending = undefined;
					queueMicrotask( () => {
						if (
							form.isConnected &&
							form.contains( marker ) &&
							! form.matches(
								'[data-linker-register].is-split[data-active-step="1"]'
							)
						) {
							form.requestSubmit( submitter ?? undefined );
						}
					} );
				}
			} );
		if (
			marker.getClientRects().length === 0 &&
			'IntersectionObserver' in window
		) {
			// The registration widget lives in the final pane of the native form.
			const observer = new IntersectionObserver( ( entries ) => {
				if ( entries.some( ( entry ) => entry.isIntersecting ) ) {
					observer.disconnect();
					start();
				}
			} );
			observer.observe( marker );
		} else {
			start();
		}
		form.addEventListener(
			'submit',
			( event ) => {
				if (
					ready ||
					! form.contains( marker ) ||
					( action === 'registration' &&
						form.matches(
							'[data-linker-register].is-split[data-active-step="1"]'
						) )
				) {
					return;
				}
				pending = event.submitter ?? null;
				event.preventDefault();
				event.stopImmediatePropagation();
				const status =
					marker.querySelector< HTMLElement >( '[role="status"]' );
				if ( status && status.hidden ) {
					status.hidden = false;
					status.textContent = __(
						'No request has been sent in this attempt. Please complete the verification.',
						'linker-commerce'
					);
				}
				marker.scrollIntoView?.( { block: 'nearest' } );
			},
			{ capture: true }
		);
	}
}
