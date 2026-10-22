/* The account chain's own manners (ticket #184). Progressive enhancement: every
   form here posts without this file — it only shows the state a submission is
   in, and keeps a form on the page when its two password fields differ. The
   look lives in the WindPress styles (content/windpress/auth.css,
   account.css); this file writes no markup and picks no words. */
( () => {
	'use strict';

	// The account chain's forms: the guest cards, the workspace and the gates.
	const FORMS = '.linker-auth form, .linker-account form, .linker-gate form, .linker-inquiry-form';

	// Woo blocks only the independent draft form while an edit is pending.
	// Keep the inquiry from overtaking that write and submitting the old lines.
	const inquiry = document.querySelector( '.linker-inquiry' );
	const draftBusy = () => Boolean( inquiry?.querySelector( '.woocommerce-cart-form.processing' ) );
	if ( inquiry ) {
		const send = inquiry.querySelector( '.linker-inquiry-form button[type="submit"]' );
		if ( send ) {
			const syncDraftState = () => {
				send.disabled = draftBusy();
			};
			new MutationObserver( syncDraftState ).observe( inquiry, {
				childList: true,
				subtree: true,
				attributes: true,
				attributeFilter: [ 'class' ],
			} );
			syncDraftState();
		}
	}

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

	// WooCommerce's own frontend/lost-password.js disables the reset form's button
	// on every submit — it assumes the page is leaving. A mismatching attempt stays
	// on the page instead, so the button is cleared once the whole dispatch is over
	// (the timer runs after every handler, WooCommerce's included) and the
	// corrected attempt can post again.
	function keepButtonLive( form ) {
		const button = form.querySelector( 'button[type="submit"], input[type="submit"]' );
		if ( ! button ) {
			return;
		}
		setTimeout( () => button.removeAttribute( 'disabled' ), 0 );
	}

	// One submission at a time: the pressed button reports that it is working.
	// The browser's own field validation still runs first, so an empty required
	// field keeps its native message instead of a button that never lands.
	// The button is never disabled: WooCommerce reads the pressed button's own
	// name and value (`login`, `register`, `save_account_details`), and a
	document.addEventListener(
		'submit',
		( event ) => {
			const form = event.target;
			if ( ! ( form instanceof HTMLFormElement ) || ! form.matches( FORMS ) ) {
				return;
			}
			if ( form.matches( '.linker-inquiry-form' ) && draftBusy() ) {
				event.preventDefault();
				return;
			}
			// The register card's step 1 is not a submission: the step script
			// below opens step 2 instead, before this handler marks the form.
			if ( form.matches( '[data-linker-register].is-split' ) && '1' === form.dataset.activeStep ) {
				return;
			}
			const error = form.querySelector( '[data-password-mismatch]' );
			const pair = passwordPair( form );
			if ( error && pair && '' !== pair.second.value && pair.first.value !== pair.second.value ) {
				event.preventDefault();
				showMismatch( error, pair.second, true );
				pair.second.focus();
				keepButtonLive( form );
				return;
			}
			if ( error && pair ) {
				showMismatch( error, pair.second, false );
			}
			if ( typeof form.checkValidity === 'function' && ! form.checkValidity() ) {
				return;
			}
			// Verification waits on the original submit. Mark busy only when
			// its verified resubmit reaches this native UI handler. The server
			// still validates the proof; this marker grants no permission.
			if ( window.linkerPublicProtectionConfig?.mode === 'enforce' && form.querySelector( '[data-linker-protected-action]' ) && form.dataset.linkerProtectionVerified !== 'true' ) {
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

	// WooCommerce's strength meter listens to keyup. A pasted or
	// password-manager-filled value fires input/change only, so the meter would
	// appear on blur and move the submit button out from under the click. A
	// synthetic keyup on input lets Woo's own meter settle while the visitor is
	// still in the field.
	for ( const password of document.querySelectorAll( '#reg_password, #password_1' ) ) {
		password.addEventListener( 'input', () => password.dispatchEvent( new KeyboardEvent( 'keyup', { bubbles: true } ) ) );
	}

	// ── The register card's two steps (ticket #225) ─────────────────────────
	// One WooCommerce form, two panes. Without this file both panes stay
	// visible and the single Register button posts the whole form; with it the
	// progress bar and the step note report the pane, step 1's own fields are
	// checked before it opens step 2, and the hidden pane's controls are
	// disabled so the browser never validates a field the visitor cannot see.
	const register = document.querySelector( 'form[data-linker-register]' );
	if ( register ) {
		const pane = ( number ) => register.querySelector( `[data-pane="${ number }"]` );
		const panes = { 1: pane( 1 ), 2: pane( 2 ) };
		const note = ( number ) => register.querySelector( `[data-stepnote="${ number }"]` );
		const next = register.querySelector( '[data-next]' );
		const back = register.querySelector( '[data-back]' );
		const progress = register.querySelector( '[data-progress]' );
		const oneof = register.querySelector( '[data-oneof-error]' );
		const clientError = register.querySelector( '[data-client-error]' );
		const website = register.querySelector( '[name="linker_company_website"]' );
		const vat = register.querySelector( '[name="billing_vat_id"]' );
		let step = 2 === Number( register.dataset.activeStep ) ? 2 : 1;

		const controls = ( root ) => [ ...root.querySelectorAll( 'input, select, textarea, button' ) ].filter( ( control ) => ! control.matches( 'input[type="hidden"]' ) );

		// The accepted prototype's own address test (registration-prototype.js:257),
		// tightened so another scheme cannot pass as a bare host. The server
		// repeats the check; this only saves a round trip.
		const websiteOk = ( value ) => {
			const rest = value.replace( /^https?:\/\//i, '' );
			return ! /^[a-z][a-z0-9+.-]*:/i.test( rest ) && /^[^\s/?#.]+\.[^\s/?#.]{2,}(?:[/?#]\S*)?$/i.test( rest );
		};

		const mark = ( row, invalid ) => {
			row.classList.toggle( 'woocommerce-invalid', invalid );
			for ( const control of row.querySelectorAll( 'input, select' ) ) {
				if ( invalid ) {
					control.setAttribute( 'aria-invalid', 'true' );
				} else {
					control.removeAttribute( 'aria-invalid' );
				}
			}
		};

		const validStepOne = () => {
			let first = null;
			let bad = false;
			for ( const row of panes[ 1 ].querySelectorAll( '.validate-required' ) ) {
				const radios = row.querySelectorAll( 'input[type="radio"]' );
				// A required row always names its control: aria-required is the
				// card's own marker, the fallback covers a field whose attributes
				// came from another renderer.
				const control = radios.length
					? radios[ 0 ]
					: row.querySelector( 'input[aria-required="true"], select[aria-required="true"]' ) || row.querySelector( 'input:not([type="hidden"]), select, textarea' );
				if ( ! control ) {
					continue;
				}
				const empty = radios.length ? ! [ ...radios ].some( ( radio ) => radio.checked ) : '' === control.value.trim();
				mark( row, empty );
				if ( empty ) {
					bad = true;
					first = first || ( radios.length ? row.querySelector( 'label' ) : control );
				}
			}
			const site = website ? website.value.trim() : '';
			const number = vat ? vat.value.trim() : '';
			const one = '' !== site || '' !== number;
			if ( oneof ) {
				oneof.hidden = one;
			}
			if ( website && vat ) {
				website.removeAttribute( 'aria-invalid' );
				vat.removeAttribute( 'aria-invalid' );
				if ( ! one ) {
					website.setAttribute( 'aria-invalid', 'true' );
					vat.setAttribute( 'aria-invalid', 'true' );
					bad = true;
					first = first || website;
				} else if ( '' !== site && ! websiteOk( site ) ) {
					website.setAttribute( 'aria-invalid', 'true' );
					bad = true;
					first = first || website;
				}
			}
			if ( clientError ) {
				clientError.hidden = ! bad;
			}
			if ( first && typeof first.focus === 'function' ) {
				first.focus();
			}
			return ! bad;
		};

		const paint = ( focus ) => {
			register.dataset.activeStep = String( step );
			if ( progress ) {
				progress.hidden = false;
				progress.setAttribute( 'aria-valuenow', String( step ) );
			}
			for ( const number of [ 1, 2 ] ) {
				const current = note( number );
				if ( current ) {
					current.hidden = number !== step;
				}
				const segment = register.querySelector( `[data-progress-segment="${ number }"]` );
				if ( segment ) {
					segment.classList.toggle( 'is-on', number <= step );
				}
				for ( const control of controls( panes[ number ] ) ) {
					control.disabled = 2 === number && 1 === step;
				}
			}
			if ( next ) {
				next.hidden = 1 !== step;
			}
			if ( back ) {
				back.hidden = 2 !== step;
			}
			if ( focus ) {
				const target = panes[ step ].querySelector( 'input:not([type="hidden"]), select, textarea' );
				if ( target ) {
					target.focus();
					const heading = register.closest( '.linker-auth' )?.querySelector( '#linker-auth-register-heading' );
					if ( heading && typeof heading.scrollIntoView === 'function' ) {
						const margin = Number.parseFloat( window.getComputedStyle( heading ).scrollMarginTop ) || 0;
						const height = window.visualViewport?.height || window.innerHeight;
						// Preserve native field focus in a short/keyboard viewport;
						// otherwise the existing heading margin also reveals the step.
						if ( target.getBoundingClientRect().bottom - heading.getBoundingClientRect().top + margin <= height ) {
							heading.scrollIntoView( { block: 'start' } );
						}
					}
				}
			}
		};

		register.classList.add( 'is-split' );
		paint( false );

		if ( next ) {
			next.addEventListener( 'click', () => {
				if ( validStepOne() ) {
					step = 2;
					paint( true );
				}
			} );
		}
		if ( back ) {
			back.addEventListener( 'click', () => {
				step = 1;
				paint( true );
			} );
		}

		const clearEditedFeedback = ( event ) => {
			const row = event.target.closest( '.form-row' );
			if ( row ) {
				mark( row, false );
			}
			if ( clientError ) {
				clientError.hidden = true;
			}
			if ( event.target === website || event.target === vat ) {
				const one = ( website && '' !== website.value.trim() ) || ( vat && '' !== vat.value.trim() );
				if ( one ) {
					for ( const alternative of [ website, vat ] ) {
						if ( alternative && '' === alternative.value.trim() ) {
							alternative.removeAttribute( 'aria-invalid' );
						}
					}
				}
				if ( oneof ) {
					oneof.hidden = one;
				}
			}
		};
		register.addEventListener( 'input', clearEditedFeedback );
		register.addEventListener( 'change', clearEditedFeedback );

		document.addEventListener(
			'submit',
			( event ) => {
				if ( event.target !== register || ! register.classList.contains( 'is-split' ) || '1' !== register.dataset.activeStep ) {
					return;
				}
				event.preventDefault();
				if ( validStepOne() ) {
					step = 2;
					paint( true );
				}
			},
			true
		);

		// WooCommerce's searchable select (selectWoo, already enqueued on the
		// account pages) with the site's translations. Without it the select
		// stays a native select and still works.
		const country = register.querySelector( 'select.linker-country-select' );
		const $ = window.jQuery;
		const params = window.wc_country_select_params;
		if ( country && $ && $.fn && $.fn.selectWoo ) {
			const language = params
				? {
						noResults: () => params.i18n_no_matches,
						searching: () => params.i18n_searching,
						errorLoading: () => params.i18n_ajax_error,
						inputTooShort: () => params.i18n_input_too_short_1,
						inputTooLong: () => params.i18n_input_too_long_1,
				  }
				: undefined;
			$( country ).selectWoo( { width: '100%', minimumResultsForSearch: 0, dropdownCssClass: 'linker-country-dropdown', language } );
		}
	}
} )();
