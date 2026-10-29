import { __ } from '@wordpress/i18n';
import {
	pendingState,
	verificationFailedText,
	verificationPendingText,
} from './messages';

/**
 * Native validation, submit buttons and redirects keep their existing owners.
 *
 * @param root Current document or native refreshed fragment.
 */
export function connectForms( root: ParentNode = document ): void {
	root.querySelectorAll< HTMLInputElement >(
		'[data-linker-protected-action]'
	).forEach( ( marker ) => {
		const form = marker.closest( 'form' );
		const action = marker.dataset.linkerProtectedAction;
		const widget = form?.querySelector< HTMLElement >(
			'[data-linker-protection-widget]'
		);
		const status = form?.querySelector< HTMLElement >(
			'[data-linker-protection-status]'
		);
		const proof = form?.querySelector< HTMLInputElement >(
			'[name="linker_proof"]'
		);
		if (
			! form ||
			! action ||
			! widget ||
			! status ||
			! proof ||
			marker.dataset.connected
		) {
			return;
		}
		marker.dataset.connected = 'true';
		const submit = form.querySelector(
			'button[type="submit"], input[type="submit"]'
		);
		if ( submit ) {
			submit.before( widget, status );
		}
		let submitting = false;
		let verified = false;
		const requiresVerification = () =>
			window.linkerPublicProtectionConfig?.mode === 'enforce' &&
			! (
				window.linkerPublicProtectionConfig.businessVerification ===
					'optional' && [ 'contact', 'inquiry' ].includes( action )
			);
		const failed = () => {
			status.hidden = false;
			status.textContent = verificationFailedText();
		};
		widget.addEventListener( 'linker:protection', ( event ) => {
			const state = ( event as CustomEvent< { state: string } > ).detail
				.state;
			if ( state === 'interactive' || state === 'retrying' ) {
				widget.hidden = false;
				status.hidden = false;
				status.textContent = verificationPendingText( state );
			} else if ( state === 'failed' || state === 'expired' ) {
				failed();
			} else if ( state === 'ready' ) {
				status.hidden = true;
			}
		} );
		const warm = () => {
			if (
				requiresVerification() &&
				marker.dataset.linkerProtectionRecovery !== 'true'
			) {
				widget.hidden = false;
				window.linkerPublicProtection?.warm( action, widget ).then(
					() => {
						widget.hidden = true;
					},
					() => {
						widget.hidden = true;
					}
				);
			}
		};
		form.addEventListener( 'focusin', warm, { once: true } );
		form.addEventListener( 'pointerdown', warm, { once: true } );
		// Woo's quantity Enter handler calls AJAX directly, bypassing submit.
		form.addEventListener(
			'keypress',
			( event: KeyboardEvent ) => {
				if (
					action !== 'draft_write' ||
					window.linkerPublicProtectionConfig?.mode !== 'enforce' ||
					event.key !== 'Enter' ||
					! ( event.target instanceof HTMLInputElement ) ||
					! event.target.matches( 'input.qty' ) ||
					! form.classList.contains( 'woocommerce-cart-form' )
				) {
					return;
				}
				const update = form.querySelector<
					HTMLButtonElement | HTMLInputElement
				>(
					'button[name="update_cart"],input[type="submit"][name="update_cart"]'
				);
				if ( ! update ) {
					return;
				}
				event.preventDefault();
				event.stopImmediatePropagation();
				form.requestSubmit( update );
			},
			{ capture: true }
		);
		form.addEventListener(
			'submit',
			async ( event: SubmitEvent ) => {
				if (
					event.defaultPrevented ||
					verified ||
					! requiresVerification()
				) {
					return;
				}
				if (
					[ 'contact', 'inquiry' ].includes( action ) &&
					marker.dataset.linkerProtectionRecovery === 'true'
				) {
					// Only the server's native recovery page carries this hint.
					// Business validates UUID/input/identity and recovers completed
					// results first. A missing result still requires a valid proof;
					// a definite refusal removes this hint on the next native page.
					proof.value =
						window.linkerPublicProtection?.ready?.(
							action,
							widget
						) || '';
					widget.hidden = true;
					status.hidden = false;
					status.textContent = __(
						'Checking the status of your earlier request…',
						'linker-commerce'
					);
					return;
				}
				event.preventDefault();
				// Woo's delegated submit handler does not inspect defaultPrevented.
				// Let it serialize/block the form only on the verified native resubmit.
				event.stopImmediatePropagation();
				if ( submitting ) {
					return;
				}
				submitting = true;
				status.hidden = false;
				widget.hidden = false;
				status.textContent = verificationPendingText(
					pendingState( widget.dataset.linkerVerificationState )
				);
				const button = event.submitter;
				try {
					const token = await window.linkerPublicProtection?.proof(
						action,
						widget
					);
					if ( ! token ) {
						throw new Error( 'verification_unavailable' );
					}
					// A warmed proof may resolve during native submit dispatch.
					// The browser ignores requestSubmit while that dispatch is active.
					await new Promise< void >( ( resolve ) =>
						setTimeout( resolve, 0 )
					);
					widget.hidden = true;
					proof.value = token;
					if (
						action === 'draft_write' &&
						button instanceof HTMLButtonElement &&
						button.name === 'apply_coupon'
					) {
						// Woo's coupon AJAX deliberately omits form fields. The
						// native POST retains its cart nonce and our scoped proof.
						const command = document.createElement( 'input' );
						command.type = 'hidden';
						command.name = button.name;
						command.value = button.value || '1';
						form.append( command );
						form.submit();
						return;
					}
					verified = true;
					form.dataset.linkerProtectionVerified = 'true';
					form.requestSubmit( button );
				} catch {
					failed();
				} finally {
					verified = false;
					delete form.dataset.linkerProtectionVerified;
					submitting = false;
				}
			},
			{ capture: true }
		);
	} );
}
