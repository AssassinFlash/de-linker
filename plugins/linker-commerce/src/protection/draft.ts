import { __ } from '@wordpress/i18n';

interface DraftJQuery {
	( element: HTMLElement ): {
		on: (
			event: string,
			callback: (
				event: unknown,
				button: { get: ( index: number ) => HTMLElement },
				data: Record< string, unknown >
			) => void
		) => void;
	};
}

declare global {
	interface Window {
		jQuery?: DraftJQuery;
	}
}

/** Keep native Woo AJAX buttons; ordinary action links post without proof in URLs. */
export function connectDraftLinks(): void {
	const prepared = new WeakMap<
		HTMLElement,
		{ proof: string; id: string }
	>();
	const busy = new WeakSet< HTMLElement >();
	window
		.jQuery?.( document.body )
		.on( 'adding_to_cart', ( _event, button, data ) => {
			const ready = prepared.get( button.get( 0 ) );
			if ( ready ) {
				data.linker_proof = ready.proof;
				data.linker_request_id = ready.id;
				prepared.delete( button.get( 0 ) );
			}
		} );
	document.addEventListener(
		'click',
		async ( event: MouseEvent ) => {
			if (
				window.linkerPublicProtectionConfig?.mode !== 'enforce' ||
				! ( event.target instanceof Element )
			) {
				return;
			}
			const link = event.target.closest< HTMLAnchorElement >( 'a[href]' );
			if ( ! link || prepared.has( link ) ) {
				return;
			}
			const url = new URL( link.href, location.href );
			const action = [
				'add-to-cart',
				'remove_item',
				'undo_item',
				'remove_coupon',
				'order_again',
			].find( ( key ) => url.searchParams.has( key ) );
			if ( url.origin !== location.origin || ! action ) {
				return;
			}
			event.preventDefault();
			event.stopImmediatePropagation();
			if ( busy.has( link ) ) {
				return;
			}
			busy.add( link );
			const widget = document.createElement( 'div' );
			const status = document.createElement( 'p' );
			status.setAttribute( 'role', 'status' );
			status.textContent = __(
				'Checking verification…',
				'linker-commerce'
			);
			link.insertAdjacentElement( 'afterend', widget );
			widget.insertAdjacentElement( 'afterend', status );
			try {
				const proof = await window.linkerPublicProtection?.proof(
					'draft_write',
					widget
				);
				if ( ! proof ) {
					throw new Error( 'verification_unavailable' );
				}
				const id = crypto.randomUUID();
				if (
					link.classList.contains( 'ajax_add_to_cart' ) &&
					window.jQuery
				) {
					prepared.set( link, { proof, id } );
					link.click();
					window.linkerPublicProtection?.reset( 'draft_write' );
					widget.remove();
					status.remove();
				} else {
					const form = document.createElement( 'form' );
					form.method = 'post';
					form.action = `${ url.origin }${ url.pathname }`;
					const fields = new URLSearchParams( url.search );
					fields.set( 'linker_request_id', id );
					fields.set( 'linker_proof', proof );
					for ( const [ name, value ] of fields ) {
						const input = document.createElement( 'input' );
						input.type = 'hidden';
						input.name = name;
						input.value = value;
						form.append( input );
					}
					document.body.append( form );
					form.submit();
				}
			} catch {
				status.textContent = __(
					'Verification could not be completed. Your solution draft is unchanged. Please try again.',
					'linker-commerce'
				);
			} finally {
				busy.delete( link );
			}
		},
		true
	);
}
