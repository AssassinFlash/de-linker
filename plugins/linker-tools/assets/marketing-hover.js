/**
 * The marketing pages' content modules switch on desktop hover too: a
 * hover clicks the module's own trigger, so what switches is the page's
 * own click behaviour — nothing about click, keyboard or touch changes,
 * and no hover fires on pointers that cannot hover (#12, old ticket 192).
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

	document.addEventListener( 'mouseover', function ( event ) {
		const el = event.target.closest && event.target.closest( triggers );
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
} )();
