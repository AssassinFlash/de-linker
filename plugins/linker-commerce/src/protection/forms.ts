import { __ } from '@wordpress/i18n';

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
		const failed = () => {
			status.hidden = false;
			status.textContent = __(
				'Verification could not be completed. Your entries are still here. Please try again or email sales@de-linker.com.',
				'linker-commerce'
			);
		};
		const warm = () => {
			if ( window.linkerPublicProtectionConfig?.mode === 'enforce' ) {
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
		form.addEventListener( 'submit', async ( event: SubmitEvent ) => {
			if (
				verified ||
				window.linkerPublicProtectionConfig?.mode !== 'enforce'
			) {
				return;
			}
			event.preventDefault();
			if ( submitting ) {
				return;
			}
			submitting = true;
			status.hidden = false;
			widget.hidden = false;
			status.textContent = __(
				'Checking verification…',
				'linker-commerce'
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
				widget.hidden = true;
				proof.value = token;
				verified = true;
				form.requestSubmit( button );
			} catch {
				failed();
			} finally {
				verified = false;
				submitting = false;
			}
		} );
	} );
}
