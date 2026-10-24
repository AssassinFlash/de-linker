/**
 * The marketing pages' content modules switch on desktop hover too: a
 * hover clicks the module's own trigger, so what switches is the page's
 * own click behaviour. Only real pointer movement may activate a module;
 * scrolling or keyboard-driven layout changes must keep their selection.
 * Pointers that cannot hover retain the native click/touch behaviour.
 */
( function () {
	'use strict';

	if (
		! window.matchMedia ||
		! window.matchMedia( '(hover: hover) and (pointer: fine)' ).matches
	) {
		return;
	}

	// The trigger selectors arrive from the server (SiteChrome's single
	// list, passed as an inline variable before this script).
	const triggers = window.linkerHoverTriggers;
	let pointerX;
	let pointerY;
	let pointerTarget;

	document.addEventListener( 'mousemove', function ( event ) {
		// Layout changes can put another trigger under a stationary pointer.
		if ( pointerX === event.clientX && pointerY === event.clientY ) {
			return;
		}
		pointerX = event.clientX;
		pointerY = event.clientY;
		const el = event.target.closest && event.target.closest( triggers );
		// Entering a module switches it once, even when its active marker is
		// local to that module. Moving within nested labels is not re-entry.
		if ( pointerTarget === el ) {
			return;
		}
		pointerTarget = el;
		if ( ! el ) {
			return;
		}
		// The module that is already showing needs no switch.
		if (
			el.matches(
				'[aria-selected="true"], [aria-current="page"], .is-active, .active, .current'
			)
		) {
			return;
		}
		el.click();
	} );

	document.addEventListener( 'mouseout', function ( event ) {
		if ( ! event.relatedTarget ) {
			pointerTarget = undefined;
			pointerX = undefined;
			pointerY = undefined;
		}
	} );
} )();
