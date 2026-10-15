/* The account chain's own manners (ticket #184). Progressive enhancement: every
   form here posts without this file — it only shows the state a submission is
   in, and keeps a form on the page when its two password fields differ. The
   look lives in the WindPress styles (content/windpress/auth.css,
   account.css); this file writes no markup and picks no words. */
( () => {
	'use strict';

	// The account chain's forms: the guest cards, the workspace and the gates.
	const FORMS = '.linker-auth form, .linker-account form, .linker-gate form';

	// The second field of a two-field password check, and the line under it.
	function passwordPair( form ) {
		const first = form.querySelector( '[name="password_1"]' );
		const second = form.querySelector( '[name="password_2"]' );
		return first && second ? { first, second } : null;
	}

	function showMismatch( error, second, on ) {
		error.hidden = ! on;
		if ( ! on ) {
			second.removeAttribute( 'aria-invalid' );
			second.removeAttribute( 'aria-describedby' );
			return;
		}
		second.setAttribute( 'aria-invalid', 'true' );
		if ( error.id ) {
			second.setAttribute( 'aria-describedby', error.id );
		}
	}

	// One submission at a time: the pressed button reports that it is working.
	// The browser's own field validation still runs first, so an empty required
	// field keeps its native message instead of a button that never lands.
	// The button is never disabled: WooCommerce reads the pressed button's own
	// name and value (`login`, `register`, `save_account_details`), and a
	// disabled control is left out of the submission.
	document.addEventListener(
		'submit',
		( event ) => {
			const form = event.target;
			if ( ! ( form instanceof HTMLFormElement ) || ! form.matches( FORMS ) ) {
				return;
			}
			const error = form.querySelector( '[data-password-mismatch]' );
			const pair = passwordPair( form );
			if ( error && pair && '' !== pair.second.value && pair.first.value !== pair.second.value ) {
				event.preventDefault();
				showMismatch( error, pair.second, true );
				pair.second.focus();
				return;
			}
			if ( error && pair ) {
				showMismatch( error, pair.second, false );
			}
			if ( typeof form.checkValidity === 'function' && ! form.checkValidity() ) {
				return;
			}
			if ( 'submitting' === form.dataset.accountState ) {
				event.preventDefault();
				return;
			}
			form.dataset.accountState = 'submitting';
			const button = form.querySelector( 'button[type="submit"], input[type="submit"]' );
			if ( ! button ) {
				return;
			}
			button.classList.add( 'is-loading' );
			button.setAttribute( 'aria-busy', 'true' );
		},
		true
	);

	// While the two fields are typed, the line follows them: it appears when
	// they differ and clears itself once they agree again.
	for ( const error of document.querySelectorAll( '[data-password-mismatch]' ) ) {
		const form = error.closest( 'form' );
		const pair = form ? passwordPair( form ) : null;
		if ( ! form || ! pair ) {
			continue;
		}
		const paint = () => showMismatch( error, pair.second, '' !== pair.second.value && pair.first.value !== pair.second.value );
		pair.first.addEventListener( 'input', paint );
		pair.second.addEventListener( 'input', paint );
	}
} )();
