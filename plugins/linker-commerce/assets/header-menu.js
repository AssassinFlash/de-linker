/* LC owns the header markup. This file only drives its disclosure states. */
( () => {
	'use strict';
	const header = document.getElementById( 'tv-header-v2' );
	if ( ! header ) return;
	const cartLinks = Array.from( header.querySelectorAll( '[data-cart-count-url]' ) );
	if ( cartLinks.length ) {
		let read;
		const draftMarker = 'linker-draft-active';
		function draftActive() {
			try { return window.sessionStorage.getItem( draftMarker ) === '1'; }
			catch { return false; } // Browser storage can be disabled for this visit.
		}
		function rememberDraft( active ) {
			try {
				if ( active ) window.sessionStorage.setItem( draftMarker, '1' );
				else window.sessionStorage.removeItem( draftMarker );
			} catch { /* Woo still owns the count on this page. */ }
		}
		function showCount( count ) {
			cartLinks.forEach( link => {
				let badge = link.querySelector( '.tv-b2b-acct-count' );
				const label = link.querySelector( '.tv-header-utility-label' )?.textContent;
				if ( label ) link.setAttribute( 'aria-label', count ? label + ' (' + count + ')' : label );
				if ( count === 0 ) {
					badge?.remove();
					return;
				}
				if ( ! badge ) {
					badge = document.createElement( 'span' );
					badge.className = 'tv-b2b-acct-count';
					link.append( badge );
				}
				badge.textContent = String( count );
			} );
		}
		async function syncCart( changed = false ) {
			read?.abort();
			const hasWooCookie = /(?:^|;\s*)woocommerce_(?:items_in_cart|cart_hash)=/.test( document.cookie );
			if ( ! changed && ! hasWooCookie && ! draftActive() && ! cartLinks.some( link => link.querySelector( '.tv-b2b-acct-count' ) ) ) {
				return;
			}
			const controller = new AbortController();
			read = controller;
			const url = new URL( cartLinks[ 0 ].dataset.cartCountUrl, document.baseURI );
			url.searchParams.set( '_fields', 'items_count' );
			try {
				const response = await fetch( url, { credentials: 'same-origin', cache: 'no-store', signal: controller.signal } );
				if ( ! response.ok ) throw new Error( String( response.status ) );
				const { items_count: count } = await response.json();
				if ( ! controller.signal.aborted && Number.isInteger( count ) ) {
					showCount( count );
					rememberDraft( count > 0 );
				}
			} catch ( error ) {
				if ( ! controller.signal.aborted ) console.warn( 'Solution draft count unavailable', error );
			}
		}
		syncCart();
		window.addEventListener( 'pageshow', event => { if ( event.persisted ) syncCart(); } );
		document.addEventListener( 'visibilitychange', () => { if ( ! document.hidden ) syncCart(); } );
		const changed = () => {
			rememberDraft( true );
			syncCart( true );
		};
		document.addEventListener( 'wc-blocks_added_to_cart', changed );
		document.addEventListener( 'wc-blocks_removed_from_cart', changed );
		window.jQuery?.( document.body ).on( 'added_to_cart removed_from_cart updated_cart_totals', changed );
	}

	const items = [ ...header.querySelectorAll( '.tv-nav-item' ) ];
	const account = header.querySelector( '.tv-b2b-acct' );
	const toggle = header.querySelector( '#tv-mobile-toggle' );
	const panel = header.querySelector( '#tv-mobile-panel' );
	const mobile = toggle?.closest( '.tv-mobile-navigation' );
	const frame = header.querySelector( '.tv-nav-frame' );
	const nav = header.querySelector( '.tv-desktop-nav' );
	const german = document.documentElement.lang.startsWith( 'de' );
	const searchLink = header.querySelector( '[data-tv-header-search]' );
	const dialog = header.querySelector( '#tv-site-search' );
	if ( searchLink && typeof dialog?.showModal === 'function' ) {
		const form = dialog.querySelector( 'form' );
		const input = form.elements.s;
		const matches = dialog.querySelector( '.tv-search-matches' );
		const status = dialog.querySelector( '[role="status"]' );
		let request;
		let timer;
		function resetMatches() {
			clearTimeout( timer );
			request?.abort();
			matches.replaceChildren();
			matches.hidden = true;
			status.textContent = '';
		}
		searchLink.setAttribute( 'aria-label', dialog.querySelector( 'h2' ).textContent );
		searchLink.setAttribute( 'aria-haspopup', 'dialog' );
		searchLink.setAttribute( 'aria-controls', dialog.id );
		searchLink.addEventListener( 'click', event => {
			if ( event.metaKey || event.ctrlKey || event.shiftKey || event.altKey ) return;
			event.preventDefault();
			dialog.showModal();
			input.focus();
		} );
		dialog.querySelector( '[data-tv-search-close]' ).addEventListener( 'click', () => dialog.close() );
		dialog.addEventListener( 'keydown', event => {
			if ( event.key === 'Escape' ) {
				event.preventDefault();
				event.stopPropagation();
				dialog.close();
			}
		} );
		dialog.addEventListener( 'close', () => { resetMatches(); form.reset(); searchLink.focus(); } );
		input.addEventListener( 'input', () => {
			resetMatches();
			const term = input.value.trim();
			if ( term.length < Number( searchLink.dataset.searchMin ) ) return;
			timer = setTimeout( async () => {
				const controller = new AbortController();
				request = controller;
				const url = new URL( searchLink.dataset.searchUrl, document.baseURI );
				url.searchParams.set( 'q', term );
				url.searchParams.set( 'lang', german ? 'de' : 'en' );
				try {
					const response = await fetch( url, { signal: controller.signal } );
					if ( ! response.ok ) throw new Error( String( response.status ) );
					const { items } = await response.json();
					if ( controller.signal.aborted ) return;
					for ( const item of items ) {
						const li = document.createElement( 'li' );
						const link = document.createElement( 'a' );
						const sku = document.createElement( 'small' );
						link.href = item.url;
						link.textContent = item.title;
						sku.textContent = item.sku;
						link.append( sku );
						li.append( link );
						matches.append( li );
					}
					matches.hidden = ! items.length;
					status.textContent = items.length
						? ( german ? 'Passende Modelle: ' : 'Matching models: ' ) + items.length
						: ( german ? 'Kein passendes Modell. Suchen Sie auf der gesamten Website.' : 'No matching model. Search the whole site for more results.' );
				} catch ( error ) {
					if ( ! controller.signal.aborted ) status.textContent = german
						? 'Modellvorschläge sind gerade nicht verfügbar. Sie können die Website durchsuchen.'
						: 'Model suggestions are unavailable. You can still search the site.';
				}
			}, 180 );
		} );
	}

	const disclosures = items.concat( account ? [ account ] : [] );
	function buttonFor( item ) {
		return item.querySelector( '.tv-nav-link, .tv-b2b-acct-btn' );
	}
	function setOpen( item, open ) {
		buttonFor( item ).setAttribute( 'aria-expanded', String( open ) );
		const menu = item.querySelector( '.tv-b2b-acct-menu' );
		if ( menu ) menu.hidden = ! open;
	}
	function closeOthers( current ) {
		disclosures.forEach( item => { if ( item !== current ) setOpen( item, false ); } );
	}
	disclosures.forEach( item => {
		const button = buttonFor( item );
		const isOpen = () => button.getAttribute( 'aria-expanded' ) === 'true';
		const menu = item.querySelector( '.tv-mega-menu, .tv-b2b-acct-menu' );
		// `.tv-b2b-acct` carries no data-tv-nav-primary; the account menu is
		// the one other disclosure.
		if ( ! menu.id ) menu.id = 'linker-menu-' + ( item.dataset.tvNavPrimary || 'account' );
		button.setAttribute( 'aria-controls', menu.id );
		// Account visibility follows `hidden`; mega-menu display follows
		// aria-expanded through WindPress. Keep the initial account state
		// consistent even when its markup arrives without `hidden`.
		if ( menu.classList.contains( 'tv-b2b-acct-menu' ) ) setOpen( item, false );
		let hovered = false;
		item.addEventListener( 'pointerenter', event => {
			if ( event.pointerType === 'touch' ) return;
			hovered = true;
			closeOthers( item );
			setOpen( item, true );
		} );
		item.addEventListener( 'pointerleave', () => {
			hovered = false;
			if ( ! item.contains( document.activeElement ) ) setOpen( item, false );
		} );
		button.addEventListener( 'click', event => {
			const open = hovered && event.detail > 0 || ! isOpen();
			hovered = false;
			closeOthers( item );
			setOpen( item, open );
		} );
		item.addEventListener( 'focusout', event => {
			if ( ! item.contains( event.relatedTarget ) ) setOpen( item, false );
		} );
			item.addEventListener( 'keydown', event => {
				const links = [ ...menu.querySelectorAll( 'a[href]' ) ];
				if ( ! links.length || ! [ 'ArrowDown', 'ArrowUp', 'Home', 'End' ].includes( event.key ) ) return;
				event.preventDefault();
				closeOthers( item );
				setOpen( item, true );
				const at = links.indexOf( document.activeElement );
				const next = event.key === 'Home' ? 0 : event.key === 'End' ? links.length - 1 : event.key === 'ArrowDown' ? ( at + 1 ) % links.length : ( at <= 0 ? links.length : at ) - 1;
				// Opening now makes the native menu visible immediately. Focus
				// must follow this key, without a delayed callback that can
				// override a later selection or a closed disclosure.
				links[ next ].focus();
			} );
	} );
	function setPanel( open ) {
		if ( mobile ) mobile.open = open;
		panel.dataset.open = String( open );
		// A native summary exposes the details element's actual expanded state.
		// Retain the button contract while an existing LC partial is replaced.
		if ( ! mobile ) toggle.setAttribute( 'aria-expanded', String( open ) );
		toggle.setAttribute( 'aria-label', german ? ( open ? 'Menü schließen' : 'Menü öffnen' ) : ( open ? 'Close menu' : 'Open menu' ) );
	}
	if ( toggle && panel ) {
		toggle.setAttribute( 'aria-controls', panel.id );
		if ( mobile ) {
			// Adopt an opening made before this enhancement arrived. The browser
			// already owns summary activation and the panel's first disclosure.
			setPanel( mobile.open );
			mobile.addEventListener( 'toggle', () => setPanel( mobile.open ) );
		}
		toggle.addEventListener( 'click', () => {
			closeOthers( null );
			if ( ! mobile ) setPanel( panel.dataset.open !== 'true' );
		} );
	}
	document.addEventListener( 'click', event => {
		disclosures.forEach( item => { if ( ! item.contains( event.target ) ) setOpen( item, false ); } );
		if ( panel && panel.dataset.open === 'true' && ! panel.contains( event.target ) && ! toggle.contains( event.target ) ) {
			setPanel( false );
		}
	} );
	document.addEventListener( 'focusout', event => {
		if ( ! panel || panel.dataset.open !== 'true' ) return;
		const next = event.relatedTarget;
		if ( next && ( panel.contains( next ) || toggle.contains( next ) ) ) return;
		setPanel( false );
	} );
	document.addEventListener( 'keydown', event => {
		if ( event.key !== 'Escape' ) return;
		const open = disclosures.find( item => buttonFor( item ).getAttribute( 'aria-expanded' ) === 'true' );
		if ( open ) {
			setOpen( open, false );
			buttonFor( open ).focus();
		} else if ( panel && panel.dataset.open === 'true' && ! document.querySelector( 'dialog[open]' ) ) {
			setPanel( false );
			toggle.focus();
		}
	} );
	if ( frame && nav ) {
		// The initial CSS offers the native panel before this enhancement can
		// measure the row. Do not dismiss a desktop opening made in that gap.
		let keepEarlyDesktopPanel = Boolean( mobile?.open ) && matchMedia( '(min-width:1280px)' ).matches;
		function fits() {
			const style = getComputedStyle( frame );
			const children = [ ...frame.children ].filter( child => getComputedStyle( child ).display !== 'none' );
			const required = children.reduce( ( sum, child ) => sum + child.getBoundingClientRect().width + ( parseFloat( getComputedStyle( child ).marginRight ) || 0 ), 0 ) + ( children.length - 1 ) * ( parseFloat( style.columnGap ) || 0 );
			return Math.ceil( required ) <= Math.floor( frame.clientWidth - parseFloat( style.paddingLeft ) - parseFloat( style.paddingRight ) );
		}
		let pending = false;
		function fit() {
			pending = false;
			const restorePrimaryFocus = keepEarlyDesktopPanel && ! mobile.open && document.activeElement === toggle;
			if ( ! mobile?.open ) keepEarlyDesktopPanel = false;
			header.removeAttribute( 'data-tv-nav-folded' );
			header.dataset.tvActionsCompact = 'false';
			if ( keepEarlyDesktopPanel && matchMedia( '(min-width:1280px)' ).matches ) {
				header.dataset.tvActionsCompact = 'true';
				header.dataset.tvNavFolded = 'true';
			} else if ( matchMedia( '(min-width:1280px)' ).matches && ! fits() ) {
				header.dataset.tvActionsCompact = 'true';
				if ( ! fits() ) header.dataset.tvNavFolded = 'true';
			}
			if ( getComputedStyle( nav ).display === 'none' ) closeOthers( account );
			else if ( panel ) setPanel( false );
			if ( restorePrimaryFocus && getComputedStyle( mobile ).display === 'none' ) {
				const primary = items[ 0 ] && buttonFor( items[ 0 ] );
				primary?.focus();
			}
		}
		function schedule() { if ( ! pending ) { pending = true; requestAnimationFrame( fit ); } }
		const observer = new ResizeObserver( schedule );
		observer.observe( frame );
		const actions = frame.querySelector( '.tv-desktop-actions' );
		if ( actions ) observer.observe( actions );
		if ( mobile ) mobile.addEventListener( 'toggle', schedule );
		window.addEventListener( 'resize', schedule, { passive: true } );
		document.fonts.ready.then( schedule );
		fit();
	}

	// Keep page actions reachable wherever the closed assistant shares their corner.
	function positionGenieLauncher() {
		const launcher = document.querySelector( '.linker-genie-open' );
		if ( ! launcher ) return;
		const hero = document.querySelector( '#home-a .hero-cinematic' );
		if ( hero ) {
			new IntersectionObserver( ( [ entry ] ) => {
				document.body.toggleAttribute( 'data-genie-hero-away', ! entry.isIntersecting );
			} ).observe( hero );
		}
		const areas = document.querySelectorAll( '#linker-faq-page .linker-library-main, #linker-compare, #tv-storefront-pdp .pdp-spec-deck, #tv-storefront-pdp .pdp-spec-list, #tv-blog-single-v1 .reader-all, #service-redesign section' );
		if ( ! areas.length ) return;
		let observer;
		function observeLauncherArea() {
			const bounds = launcher.getBoundingClientRect();
			if ( ! bounds.width || ! bounds.height ) return;
			observer?.disconnect();
			const intersecting = new Set();
			const margins = [ -bounds.top, bounds.right - document.documentElement.clientWidth, bounds.bottom - document.documentElement.clientHeight, -bounds.left ];
			observer = new IntersectionObserver( entries => {
				for ( const entry of entries ) {
					if ( entry.isIntersecting ) intersecting.add( entry.target );
					else intersecting.delete( entry.target );
				}
				document.body.toggleAttribute( 'data-genie-over-content', intersecting.size > 0 );
			}, { rootMargin: margins.map( value => value + 'px' ).join( ' ' ) } );
			areas.forEach( area => observer.observe( area ) );
		}
		new ResizeObserver( observeLauncherArea ).observe( launcher );
		window.addEventListener( 'resize', observeLauncherArea, { passive: true } );
	}
	if ( document.readyState === 'loading' ) document.addEventListener( 'DOMContentLoaded', positionGenieLauncher, { once: true } );
	else positionGenieLauncher();
} )();
