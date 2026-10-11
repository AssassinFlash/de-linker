/**
 * The catalogue search box: the Ask Genie chip and the model/item-number
 * resolution (docs/specs/13-genie.md, §C "the search box of the product
 * pages recognizes a question and shows the Ask Genie chip"; ticket #68).
 *
 * Two behaviours, both only when the page carries the search box:
 *
 * - What reads as a question (a question mark, a question word or a request
 *   like "I need …" / "Ich brauche …", in English or German) shows the chip
 *   next to the box. Clicking it opens Genie with the typed text as the first
 *   message — the app is booted by the dock's loader, which watches the same
 *   click, and receives the text as the pending ask.
 * - Submitting a model or item number asks the catalogue search endpoint what
 *   it names: exactly one product goes straight to its page, everything else
 *   (several hits, nothing, an error, the endpoint too slow) leaves the plain
 *   form to submit, and the archive filters by `q` as it always has.
 *
 * The script is a plain asset: it binds and prints nothing, so the search box
 * works without it (the form's native GET) and the chip is server-rendered
 * markup that only becomes visible here.
 */
( function () {
	'use strict';

	const config = window.linkerSearchAsk;
	if ( ! config ) {
		return;
	}

	const input = document.querySelector( config.input );
	const chip = config.chip ? document.querySelector( config.chip ) : null;
	if ( ! input ) {
		return;
	}

	// A question in English or German: a question mark anywhere, a question
	// word, or a request the visitor phrases as a need. Model and item
	// numbers match none of these.
	const QUESTION = new RegExp(
		'(\\?|\\b(how|what|which|where|when|why|who|can|could|do|does|is|are|will|would|should|help|find|recommend|compare|need|want|wie|was|welche|welcher|welches|wo|wann|warum|wer|kann|können|ist|sind|soll|sollte|hilfe|hilf|empfehl|vergleich|brauche|möchte|habe)\\b)',
		'i'
	);

	function isQuestion( value ) {
		const text = value.trim();
		return text.length >= config.questionLength && QUESTION.test( text );
	}

	// Hands the text to the Genie app. The app may not have loaded yet (it
	// boots from the same click): the text is left on the app's mount element
	// for the app's first mount to pick up, and announced as an event for an
	// app that is already mounted.
	function askGenie( text ) {
		if ( '' === text ) {
			return;
		}
		const mount = document.querySelector( '[data-linker-app="genie"]' );
		if ( mount ) {
			mount.setAttribute( 'data-pending-ask', text );
		}
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-ask', { detail: { message: text } } )
		);
		const opener = document.querySelector( '.linker-genie-open' );
		if ( opener ) {
			opener.click();
		}
	}

	function updateChip() {
		if ( chip ) {
			chip.hidden = ! isQuestion( input.value );
		}
	}

	input.addEventListener( 'input', updateChip );
	updateChip();

	if ( chip ) {
		chip.addEventListener( 'click', function () {
			askGenie( input.value.trim() );
		} );
	}

	const form = input.form;
	if ( ! form || ! config.endpoint ) {
		return;
	}

	// One product named: its page. More than one, none, an error or a slow
	// answer: the form submits and the archive filters by the query.
	form.addEventListener( 'submit', function ( event ) {
		const value = input.value.trim();
		if ( value.length < config.queryLength ) {
			return;
		}
		if ( isQuestion( value ) ) {
			event.preventDefault();
			askGenie( value );
			return;
		}
		event.preventDefault();
		const controller =
			'undefined' !== typeof AbortController
				? new AbortController()
				: null;
		let timer = 0;
		if ( controller ) {
			timer = window.setTimeout( function () {
				controller.abort();
			}, config.timeout );
		}

		fetch(
			config.endpoint +
				( config.endpoint.indexOf( '?' ) >= 0 ? '&' : '?' ) +
				'q=' +
				encodeURIComponent( value ) +
				'&limit=2&lang=' +
				encodeURIComponent( config.lang ),
			{
				headers: { Accept: 'application/json' },
				credentials: 'same-origin',
				signal: controller ? controller.signal : undefined,
			}
		)
			.then( function ( response ) {
				return response.ok ? response.json() : null;
			} )
			.then( function ( data ) {
				window.clearTimeout( timer );
				const items =
					data && Array.isArray( data.items ) ? data.items : [];
				if ( 1 === items.length && items[ 0 ].url ) {
					window.location.assign( items[ 0 ].url );
					return;
				}
				form.submit();
			} )
			.catch( function () {
				window.clearTimeout( timer );
				form.submit();
			} );
	} );
} )();
