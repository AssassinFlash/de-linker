import { __ } from '@wordpress/i18n';
import { ProtectionClient } from './client';
import { connectForms } from './forms';
import { connectDraftLinks } from './draft';
import { verificationFailedText, verificationPendingText } from './messages';
import type { ProtectionState } from './types';

const config = window.linkerPublicProtectionConfig;
if ( config ) {
	window.linkerPublicProtection = new ProtectionClient( config );
}

connectForms();
connectDraftLinks();

// Woo replaces the native cart form after quantity/removal AJAX. Reconnect the
// new semantic fields; connectForms itself avoids duplicate listeners.
window
	.jQuery?.( document.body )
	.on( 'updated_wc_div updated_cart_totals', () => {
		connectForms();
	} );

// This native staff diagnostic invokes verification only on an explicit click.
document
	.querySelectorAll< HTMLElement >( '[data-linker-protection-check]' )
	.forEach( ( root ) => {
		const button = root.querySelector< HTMLButtonElement >(
			'[data-linker-protection-start]'
		);
		const status = root.querySelector< HTMLElement >(
			'[data-linker-protection-status]'
		);
		const widget = root.querySelector< HTMLElement >(
			'[data-linker-protection-widget]'
		);
		if ( ! button || ! status || ! widget ) {
			return;
		}
		const messages: Record< ProtectionState, string > = {
			checking: verificationPendingText( 'checking' ),
			interactive: verificationPendingText( 'interactive' ),
			retrying: verificationPendingText( 'retrying' ),
			ready: __(
				'Verification passed. No business request was submitted.',
				'linker-commerce'
			),
			failed: verificationFailedText(),
			expired: __(
				'Verification expired. Please try again.',
				'linker-commerce'
			),
		};
		root.addEventListener( 'linker:protection', ( event ) => {
			const state = ( event as CustomEvent< { state: ProtectionState } > )
				.detail.state;
			status.textContent = messages[ state ];
		} );
		button.addEventListener( 'click', async () => {
			button.disabled = true;
			try {
				window.linkerPublicProtection?.reset( 'inquiry' );
				await window.linkerPublicProtection?.proof( 'inquiry', widget );
			} catch {
				status.textContent = messages.failed;
			} finally {
				button.disabled = false;
			}
		} );
	} );
