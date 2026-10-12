/* LC owns the header markup. This file only drives its disclosure states. */
( () => {
	'use strict';
	const header = document.getElementById( 'tv-header-v2' );
	if ( ! header ) return;
	const items = [ ...header.querySelectorAll( '.tv-nav-item' ) ];
	const account = header.querySelector( '.tv-b2b-acct' );
	const toggle = header.querySelector( '#tv-mobile-toggle' );
	const panel = header.querySelector( '#tv-mobile-panel' );
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
		const menu = item.querySelector( '.tv-mega-menu, .tv-b2b-acct-menu' );
		if ( ! menu.id ) menu.id = 'linker-menu-' + item.dataset.tvNavPrimary;
		button.setAttribute( 'aria-controls', menu.id );
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
			const open = hovered && event.detail > 0 || button.getAttribute( 'aria-expanded' ) !== 'true';
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
			links[ next ].focus();
		} );
	} );
	function setPanel( open ) {
		panel.dataset.open = String( open );
		toggle.setAttribute( 'aria-expanded', String( open ) );
		toggle.setAttribute( 'aria-label', german ? ( open ? 'Menü schließen' : 'Menü öffnen' ) : ( open ? 'Close menu' : 'Open menu' ) );
	}
	if ( toggle && panel ) {
		toggle.setAttribute( 'aria-controls', panel.id );
		toggle.addEventListener( 'click', () => {
			closeOthers( null );
			setPanel( panel.dataset.open !== 'true' );
		} );
	}
	document.addEventListener( 'click', event => {
		disclosures.forEach( item => { if ( ! item.contains( event.target ) ) setOpen( item, false ); } );
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
		function fits() {
			const style = getComputedStyle( frame );
			const children = [ ...frame.children ].filter( child => getComputedStyle( child ).display !== 'none' );
			const required = children.reduce( ( sum, child ) => sum + child.getBoundingClientRect().width + ( parseFloat( getComputedStyle( child ).marginRight ) || 0 ), 0 ) + ( children.length - 1 ) * ( parseFloat( style.columnGap ) || 0 );
			return Math.ceil( required ) <= Math.floor( frame.clientWidth - parseFloat( style.paddingLeft ) - parseFloat( style.paddingRight ) );
		}
		let pending = false;
		function fit() {
			pending = false;
			header.removeAttribute( 'data-tv-nav-folded' );
			header.removeAttribute( 'data-tv-actions-compact' );
			if ( matchMedia( '(min-width:1280px)' ).matches && ! fits() ) {
				header.dataset.tvActionsCompact = 'true';
				if ( ! fits() ) header.dataset.tvNavFolded = 'true';
			}
			if ( getComputedStyle( nav ).display === 'none' ) closeOthers( account );
			else if ( panel ) setPanel( false );
		}
		function schedule() { if ( ! pending ) { pending = true; requestAnimationFrame( fit ); } }
		const observer = new ResizeObserver( schedule );
		observer.observe( frame );
		const actions = frame.querySelector( '.tv-desktop-actions' );
		if ( actions ) observer.observe( actions );
		window.addEventListener( 'resize', schedule, { passive: true } );
		document.fonts.ready.then( schedule );
		fit();
	}
} )();
