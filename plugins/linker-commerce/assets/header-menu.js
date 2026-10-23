/* LC owns the header markup. This file only drives its disclosure states. */
( () => {
	'use strict';
	const header = document.getElementById( 'tv-header-v2' );
	if ( ! header ) return;
	const items = [ ...header.querySelectorAll( '.tv-nav-item' ) ];
	const account = header.querySelector( '.tv-b2b-acct' );
	const toggle = header.querySelector( '#tv-mobile-toggle' );
	const panel = header.querySelector( '#tv-mobile-panel' );
	const mobile = toggle?.closest( '.tv-mobile-navigation' );
	const frame = header.querySelector( '.tv-nav-frame' );
	const nav = header.querySelector( '.tv-desktop-nav' );
	const german = document.documentElement.lang.startsWith( 'de' );
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
} )();
