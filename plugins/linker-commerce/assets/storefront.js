/**
 * The product page's image viewer: the gallery's buttons open the dialog
 * with their image (#12; the look of the viewer the site serves today — a
 * centered dialog over a dimmed page — with the plain dialog element).
 */
( function () {
	'use strict';

	var pdp = document.getElementById( 'tv-storefront-pdp' );
	if ( ! pdp || ! window.HTMLDialogElement ) {
		return;
	}

	var viewer = document.getElementById( 'pdp-image-viewer' );
	var viewerImg = viewer ? viewer.querySelector( '.pdp-viewer-img' ) : null;
	if ( ! viewer || ! viewerImg ) {
		return;
	}

	pdp.addEventListener( 'click', function ( event ) {
		var opener = event.target.closest( '[data-pdp-viewer-open]' );
		if ( ! opener ) {
			return;
		}
		var img = opener.querySelector( 'img' );
		if ( ! img ) {
			return;
		}
		viewerImg.src = img.currentSrc || img.src;
		viewerImg.alt = img.alt || '';
		viewer.showModal();
	} );

	viewer.addEventListener( 'click', function ( event ) {
		if ( event.target === viewer || event.target.closest( '[data-pdp-viewer-close]' ) ) {
			viewer.close();
		}
	} );
} )();

/**
 * The archive's filter drawer: on narrow viewports the rail is a drawer
 * the visitor opens and closes (the catalogue the site serves today opens
 * it from a floating button; the buttons inside close it again).
 */
( function () {
	'use strict';

	var catalog = document.getElementById( 'tv-woo-b2b-catalog' );
	if ( ! catalog ) {
		return;
	}
	var rail = catalog.querySelector( '#sidebar-filters' );
	var close = catalog.querySelector( '#catalog-filter-close' );
	var apply = catalog.querySelector( '#catalog-filter-apply' );
	if ( ! rail ) {
		return;
	}

	function open() {
		rail.classList.add( 'is-open' );
		document.body.classList.add( 'catalog-filter-open' );
	}
	function shut() {
		rail.classList.remove( 'is-open' );
		document.body.classList.remove( 'catalog-filter-open' );
	}

	var opener = document.createElement( 'button' );
	opener.type = 'button';
	opener.className = 'catalog-filter-open-btn';
	opener.textContent = rail.getAttribute( 'aria-label' ) || 'Filters';
	opener.addEventListener( 'click', open );
	rail.parentNode.insertBefore( opener, rail );

	if ( close ) {
		close.addEventListener( 'click', shut );
	}
	if ( apply ) {
		apply.addEventListener( 'click', shut );
	}
} )();
