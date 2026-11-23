/* The account chain's own manners (ticket #184). Progressive enhancement: every
   form here posts without this file — it only shows the state a submission is
   in, and keeps a form on the page when its two password fields differ. The
   look lives in the WindPress styles (content/windpress/auth.css,
   account.css); this file writes no markup and picks no words. */
( () => {
	'use strict';

	// The account chain's forms: the guest cards, the workspace and the gates.
	const FORMS = '.linker-auth form, .linker-account form, .linker-gate form, .linker-inquiry-form';
	const submittingButtons = new WeakMap();

	// The inquiry consumes Woo's server-side cart. Resume only when Woo returns
	// the requested quantities, including the absence of rows removed with zero.
	const inquiry = document.querySelector( '.linker-inquiry' );
	const draftSurface = document.querySelector( '.linker-inquiry, #tv-storefront-cart' );
	const draftForm = () => draftSurface?.querySelector( '.woocommerce-cart-form' );
	const quantities = ( form ) => Array.from( form?.querySelectorAll( 'input.qty' ) || [] );
	const send = inquiry?.querySelector( '.linker-inquiry-form button[type="submit"]' );
	const notice = draftSurface?.querySelector( '[data-inquiry-draft-pending]' );
	let continuation;
	function syncDraftState() {
		const form = draftForm();
		const busy = Boolean( form?.classList.contains( 'processing' ) );
		if ( send ) {
			send.disabled = busy;
		}
		draftSurface?.querySelectorAll( '.wc-proceed-to-checkout a' ).forEach( ( link ) => {
			link.setAttribute( 'aria-disabled', String( busy ) );
		} );
		if ( ! continuation ) {
			return;
		}
		const attempt = continuation;
		if ( form === attempt.form ) {
			if ( busy ) {
				attempt.processing = true;
			} else if ( attempt.processing ) {
				// Woo unblocked the original form after a failed request.
				continuation = null;
				if ( notice ) notice.hidden = false;
			}
			return;
		}
		continuation = null;
		const rows = quantities( form );
		const saved = new Map( rows.map( ( input ) => [ input.name, Number( input.defaultValue ) ] ) );
		// The customer can still edit quantities while draft verification runs.
		const values = new Map( quantities( attempt.form ).map( ( input ) => [ input.name, input.value ] ) );
		const matches = Array.from( values ).every( ( [ name, value ] ) =>
			value !== '' && ( Number( value ) === 0 ? ! saved.has( name ) : saved.get( name ) === Number( value ) )
		);
		if ( ( form || draftSurface.querySelector( '.wc-empty-cart-message' ) ) && matches &&
			rows.every( ( input ) => values.has( input.name ) ) ) {
			attempt.resume();
		} else {
			if ( notice ) notice.hidden = false;
			for ( const input of rows ) {
				if ( values.has( input.name ) ) {
					input.value = values.get( input.name );
				}
			}
		}
	}

	function saveBeforeContinuing( event, resume ) {
		const form = draftForm();
		if ( ! form ) {
			return false;
		}
		if ( continuation || form.classList.contains( 'processing' ) ) {
			event.preventDefault();
			return true;
		}
		const rows = quantities( form );
		if ( ! rows.some( ( input ) => input.value !== input.defaultValue ) ) {
			return false;
		}
		event.preventDefault();
		for ( const input of rows ) {
			input.required = true;
			if ( ! input.reportValidity() ) {
				input.focus();
				return true;
			}
		}
		continuation = { form, resume };
		if ( notice ) notice.hidden = true;
		// Woo records the clicked update button before routing a verified submit to AJAX.
		const update = form.querySelector( 'button[name="update_cart"], input[type="submit"][name="update_cart"]' );
		update.disabled = false;
		update.click();
		syncDraftState();
		return true;
	}

	if ( draftSurface ) {
		new MutationObserver( syncDraftState ).observe( draftSurface, {
			childList: true,
			subtree: true,
			attributes: true,
			attributeFilter: [ 'class' ],
		} );
		const cancelVerification = ( event ) => {
			if ( continuation?.form.contains( event.target ) ) {
				continuation = null;
			}
		};
		draftSurface.addEventListener( 'linker:draft-verification-cancelled', cancelVerification, true );
		draftSurface.addEventListener( 'linker:protection', ( event ) => {
			if ( [ 'failed', 'expired' ].includes( event.detail.state ) ) {
				cancelVerification( event );
			}
		} );
		draftSurface.addEventListener( 'click', ( event ) => {
			const step = event.target.closest( 'button[data-quantity-step]' );
			if ( step ) {
				const input = step.closest( '.linker-inquiry-stepper' ).querySelector( 'input.qty' );
				if ( step.dataset.quantityStep === '1' ) input.stepUp();
				else input.stepDown();
				input.dispatchEvent( new Event( 'input', { bubbles: true } ) );
				input.dispatchEvent( new Event( 'change', { bubbles: true } ) );
				return;
			}
			const link = event.target.closest( '.wc-proceed-to-checkout a' );
			if ( link && event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey ) {
				carryRetry( link, new URLSearchParams( window.location.search ).get( retryField ) );
				saveBeforeContinuing( event, () => window.location.assign( link.href ) );
			}
		} );
		syncDraftState();
	}
	const inquiryStorageKey = 'linker-inquiry-edit';
	const retryField = 'linker_inquiry_retry';
	const carryRetry = ( link, retry ) => {
		if ( ! retry || ! /^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test( retry ) ) {
			return;
		}
		const target = new URL( link.href );
		if ( target.origin === window.location.origin ) {
			target.searchParams.set( retryField, retry );
			link.href = target.href;
		}
	};
	if ( inquiry ) {
		const form = inquiry.querySelector( '.linker-inquiry-form' );
		const retentionError = inquiry.querySelector( '[data-inquiry-retention-error]' );
		const names = [ 'name', 'email', 'company', 'message' ];
		const context = form?.dataset.inquiryContext || '';
		const field = ( name ) => form?.elements.namedItem( name );
		const retry = field( retryField )?.value || '';
		const retryPending = field( retryField )?.dataset.linkerRetryPending === 'true';

		// A one-use bridge for the explicit edit/return navigation. It stays in
		// this tab, uses the native authentication context, and never writes an inquiry or
		// sends personal details to another endpoint. Server error values win.
		try {
			const raw = window.sessionStorage.getItem( inquiryStorageKey );
			window.sessionStorage.removeItem( inquiryStorageKey );
			const kept = raw ? JSON.parse( raw ) : null;
			if ( context && kept?.context === context && ( kept.retry || '' ) === retry && names.every( ( name ) => typeof kept.fields?.[ name ] === 'string' ) && ( field( 'linker_inquiry_retained' )?.value !== '1' || ( retry && ! retryPending ) ) ) {
				let detailsChanged = false;
				for ( const name of names ) {
					const control = field( name );
					if ( control && typeof kept.fields?.[ name ] === 'string' ) {
						detailsChanged ||= name !== 'message' && control.value !== kept.fields[ name ];
						control.value = kept.fields[ name ];
					}
				}
				if ( field( 'consent' ) ) {
					field( 'consent' ).checked = kept.consent === true;
				}
				if ( field( 'linker_include_project_notes' ) && typeof kept.includeProjectNotes === 'boolean' ) {
					field( 'linker_include_project_notes' ).checked = kept.includeProjectNotes;
				}
				if ( field( 'linker_inquiry_retained' ) ) {
					// The existing handoff contract also preserves intentionally empty text.
					field( 'linker_inquiry_retained' ).value = '1';
				}
				const details = form.querySelector( '.linker-inquiry-details' );
				if ( details && detailsChanged ) {
					details.open = true;
				}
				const summary = details?.querySelector( 'summary small' );
				if ( summary ) {
					summary.textContent = `${ field( 'name' )?.value || '' } · ${ field( 'email' )?.value || '' }`;
				}
			}
		} catch {
			// An unavailable or invalid bridge never replaces the current form.
		}


		document.addEventListener( 'click', ( event ) => {
			const link = event.target.closest( '[data-inquiry-edit], a[lang], a[hreflang]' );
			if ( ! link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey ) {
				return;
			}
			if ( saveBeforeContinuing( event, () => ( link.isConnected ? link : inquiry.querySelector( '[data-inquiry-edit]' ) ).click() ) ) {
				return;
			}
			carryRetry( link, retry );
			// A pending check uses the message and form identity already held by Woo.
			if ( retryPending ) {
				return;
			}
			const fields = Object.fromEntries( names.map( ( name ) => [ name, field( name )?.value || '' ] ) );
			const consent = field( 'consent' )?.checked === true;
			const notesToggle = field( 'linker_include_project_notes' );
			const includeProjectNotes = notesToggle ? notesToggle.checked === true : null;
			if ( ! consent && includeProjectNotes !== false && names.every( ( name ) => fields[ name ] === '' ) ) {
				return;
			}
			try {
				if ( ! context ) {
					throw new Error( 'Missing native inquiry context' );
				}
				window.sessionStorage.setItem( inquiryStorageKey, JSON.stringify( { context, fields, consent, ...( retry ? { retry } : {} ), ...( null !== includeProjectNotes ? { includeProjectNotes } : {} ) } ) );
			} catch {
				event.preventDefault();
				if ( retentionError ) {
					retentionError.hidden = false;
					retentionError.focus();
				}
			}
		} );
	} else if ( draftSurface ) {
		const retry = new URLSearchParams( window.location.search ).get( retryField );
		if ( retry ) {
			document.addEventListener( 'click', ( event ) => {
				const link = event.target.closest( '.wc-proceed-to-checkout a, a[lang], a[hreflang]' );
				if ( link && ! event.defaultPrevented ) {
					carryRetry( link, retry );
				}
			} );
		}
	} else {
		// Account and confirmation pages retire the bridge; editing the draft keeps it.
		try {
			window.sessionStorage.removeItem( inquiryStorageKey );
		} catch {
			// A storage restriction does not affect native account forms.
		}
	}

	const retirePreliminaryInquiry = () => {
		if ( ! document.querySelector( '.linker-account, .linker-inquiry-success' ) ) {
			return;
		}
		const received = document.querySelector( '.linker-inquiry-success[data-linker-received-request]' )?.dataset.linkerReceivedRequest;
		try {
			window.sessionStorage.removeItem( 'linker-preliminary-inquiry' );
			if ( ! received ) {
				return;
			}
			for ( let index = window.sessionStorage.length - 1; index >= 0; index-- ) {
				const key = window.sessionStorage.key( index );
				if ( key?.startsWith( 'linker-preliminary-inquiry-pending:' ) ) {
					const pending = JSON.parse( window.sessionStorage.getItem( key ) || 'null' );
					if ( pending?.requestId === received ) {
						window.sessionStorage.removeItem( key );
					}
				}
			}
		} catch {
			// Native receipt and account pages remain available without storage.
		}
	};
	retirePreliminaryInquiry();
	window.addEventListener( 'pageshow', retirePreliminaryInquiry );

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
	// Woo's login form uses novalidate. Report native constraints here so a
	// missing field stays on this page, before verification or loading state.
	// The button is never disabled: WooCommerce reads the pressed button's own
	// name and value (`login`, `register`, `save_account_details`), and a
	document.addEventListener(
		'submit',
		( event ) => {
			const form = event.target;
			if ( ! ( form instanceof HTMLFormElement ) || ! form.matches( FORMS ) ) {
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
			if ( typeof form.reportValidity === 'function' && ! form.reportValidity() ) {
				event.preventDefault();
				return;
			}
			if ( form.matches( '.linker-inquiry-form' ) && saveBeforeContinuing( event, () => form.requestSubmit( send ) ) ) {
				return;
			}
			if ( event.defaultPrevented ) {
				return;
			}
			if ( form.querySelector( '[data-linker-turnstile]' ) && ! form.querySelector( '[name="cf-turnstile-response"]' )?.value ) {
				return;
			}
			if ( 'submitting' === form.dataset.accountState ) {
				event.preventDefault();
				return;
			}
			form.dataset.accountState = 'submitting';
			if ( form.matches( '.linker-inquiry-form' ) ) {
				try {
					window.sessionStorage.removeItem( inquiryStorageKey );
				} catch {
					// Storage is optional; the native inquiry transport still works.
				}
			}
			const button = form.querySelector( 'button[type="submit"], input[type="submit"]' );
			if ( ! button ) {
				return;
			}
			submittingButtons.set( form, { button, disabled: button.disabled } );
			button.classList.add( 'is-loading' );
			button.setAttribute( 'aria-busy', 'true' );
		},
		true
	);

	// Back/forward-cache restoration resumes this document without its old
	// request. Keep entered values and unrelated disabled controls intact.
	window.addEventListener( 'pageshow', ( event ) => {
		if ( ! event.persisted ) {
			return;
		}
		for ( const form of document.querySelectorAll( FORMS ) ) {
			if ( form.dataset.accountState !== 'submitting' ) {
				continue;
			}
			delete form.dataset.accountState;
			const submitted = submittingButtons.get( form );
			const button = submitted?.button || form.querySelector( 'button[type="submit"], input[type="submit"]' );
			button?.classList.remove( 'is-loading' );
			button?.removeAttribute( 'aria-busy' );
			// Woo's lost-password handler disables this previously usable button
			// when it posts. Other forms keep their native disabled decisions.
			if ( submitted && form.matches( '.lost_reset_password' ) ) {
				submitted.button.disabled = submitted.disabled;
			}
			submittingButtons.delete( form );
		}
		syncDraftState();
	} );

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

		// A public company address: one or more host labels, a dot in the host
		// and at least two characters after its last label (the server's
		// Registration\Website::valid() agrees), tightened so another scheme
		// cannot pass as a bare host. The server repeats the check; this only
		// saves a round trip.
		const websiteOk = ( value ) => {
			const rest = value.replace( /^https?:\/\//i, '' );
			return ! /^[a-z][a-z0-9+.-]*:/i.test( rest ) && /^[^\s/?#.]+(?:\.[^\s/?#.]+)*\.[^\s/?#.]{2,}(?:[/?#]\S*)?$/i.test( rest );
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

		// Keep credentials in the current form if its native POST is refused.
		const challenge = register.querySelector( '[data-linker-turnstile="registration"]' );
		const registrationError = register.querySelector( '[data-registration-error]' );
		if ( challenge && registrationError && typeof window.fetch === 'function' ) {
			register.addEventListener( 'submit', async ( event ) => {
				if ( event.defaultPrevented || step !== 2 ) {
					return;
				}
				event.preventDefault();
				const submitter = event.submitter || register.querySelector( '[name="register"]' );
				const body = new FormData( register );
				body.set( submitter.name, submitter.value );
				registrationError.hidden = true;
				let message = registrationError.dataset.failure;
				try {
					const response = await window.fetch( register.action, { method: 'POST', body, credentials: 'same-origin' } );
					if ( response.ok ) {
						const page = new DOMParser().parseFromString( await response.text(), 'text/html' );
						const notices = page.querySelector( '[data-registration-notices] .woocommerce-error, [data-registration-notices] .wc-block-components-notice-banner.is-error' );
						if ( notices?.textContent.trim() ) {
							message = notices.textContent.trim();
						} else if ( response.redirected && new URL( response.url ).origin === window.location.origin ) {
							window.location.assign( response.url );
							return;
						}
					}
				} catch {
					// A disconnected response can leave the creation result unknown.
				}
				registrationError.textContent = message;
				registrationError.hidden = false;
				delete register.dataset.accountState;
				submitter.classList.remove( 'is-loading' );
				submitter.removeAttribute( 'aria-busy' );
				submittingButtons.delete( register );
				window.linkerTurnstile?.refresh( challenge );
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
