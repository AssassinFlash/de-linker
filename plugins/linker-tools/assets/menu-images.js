/**
 * The header's menu images load when their menu opens: the partials carry
 * them as data-src/data-srcset, and this script hydrates the images of a
 * menu the visitor opens (hover, touch, keyboard or focus) — before any
 * open, the network panel shows no menu image request (#12, old ticket
 * 193). The image tags keep their size and density attributes, so the
 * rendered ratio and sharpness are the partials' own.
 */
( function () {
	'use strict';

	function hydrate( section ) {
		if ( ! section ) {
			return;
		}
		const images = section.querySelectorAll( 'img[data-src]' );
		for ( let i = 0; i < images.length; i++ ) {
			const img = images[ i ];
			if ( ! img.getAttribute( 'src' ) ) {
				img.setAttribute( 'src', img.getAttribute( 'data-src' ) );
			}
			const srcset = img.getAttribute( 'data-srcset' );
			if ( srcset && ! img.getAttribute( 'srcset' ) ) {
				img.setAttribute( 'srcset', srcset );
			}
			img.removeAttribute( 'data-src' );
			img.removeAttribute( 'data-srcset' );
		}
	}

	// A menu opens by hover, click, touch or keyboard focus on its item;
	// the item's section holds that menu's images. The mobile rail's images
	// sit inside their details.tv-mobile-section but outside its summary, so
	// a summary hit also hydrates the section it summarizes.
	[ 'mouseover', 'focusin', 'click' ].forEach( function ( type ) {
		document.addEventListener(
			type,
			function ( event ) {
				const opener =
					event.target.closest &&
					event.target.closest(
						'.tv-nav-item, .tv-mobile-toggle, .tv-mobile-summary, details[data-tv-mobile-primary], details.tv-mobile-section'
					);
				hydrate( opener );
				if (
					opener &&
					opener.matches(
						'summary, .tv-mobile-summary, .tv-mobile-toggle'
					)
				) {
					hydrate( opener.closest( 'details' ) );
				}
			},
			true
		);
	} );
} )();
