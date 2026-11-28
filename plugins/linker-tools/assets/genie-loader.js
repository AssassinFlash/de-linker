/* global HTMLElement, requestAnimationFrame, cancelAnimationFrame */
( function () {
	const config = document.querySelector( '[data-linker-genie-loader]' );
	if ( ! config ) {
		return;
	}
	const payload = JSON.parse(
		config.textContent ||
			config.getAttribute( 'data-linker-genie-boot-payload' )
	);
	let loaded = false;
	let ready = false;
	let pendingOpen = false;
	let pendingAsk = '';
	let pendingEntries = Object.create( null );
	let pendingOpener = null;
	// Opened to send a nameplate photo (#236): the app offers the picker.
	let pendingAttach = false;
	// Opened for a parts list (#251): the picker expects the list's file.
	let pendingList = false;
	// The saved solution the design report's "Ask Genie" opened with (#496).
	let pendingSolution = 0;
	// Opening from the home hero (#232): re-read the thread the hero
	// wrote, and mark it as asked from the homepage.
	let pendingRefresh = false;
	let pendingFromHome = false;
	let failure = null;
	let dismissed = false;
	let failureBoundary = null;
	function available( node ) {
		return (
			node instanceof HTMLElement &&
			node.isConnected &&
			! node.matches( ':disabled,[hidden],[tabindex="-1"]' ) &&
			! node.closest( '[hidden],[inert]' ) &&
			node.getClientRects().length > 0
		);
	}
	// The existing helper mount, including its LC account row, owns focus while the app is unavailable.
	function bindFailureBoundary( panel, initial ) {
		const mobile = window.innerWidth <= 860; // The current helper sheet breakpoint.
		const saved = [ 'role', 'aria-modal', 'aria-label' ].map(
			function ( name ) {
				return [ name, panel.getAttribute( name ) ];
			}
		);
		const overflow = document.body.style.overflow;
		const background = [];
		panel.setAttribute( 'role', 'dialog' );
		panel.setAttribute( 'aria-label', payload.title );
		if ( mobile ) {
			panel.setAttribute( 'aria-modal', 'true' );
			document.body.style.overflow = 'hidden';
			let branch = panel;
			while ( branch.parentElement ) {
				Array.from( branch.parentElement.children ).forEach(
					function ( sibling ) {
						if (
							sibling !== branch &&
							sibling instanceof HTMLElement
						) {
							background.push( [
								sibling,
								Boolean( sibling.inert ),
							] );
							sibling.inert = true;
						}
					}
				);
				branch = branch.parentElement;
			}
		} else {
			panel.removeAttribute( 'aria-modal' );
		}
		const frame = requestAnimationFrame( function () {
			if ( available( initial ) ) {
				initial.focus( { preventScroll: true } );
			}
		} );
		function key( event ) {
			if ( event.defaultPrevented ) {
				return;
			}
			if ( event.key === 'Escape' ) {
				event.preventDefault();
				event.stopPropagation();
				closeFailure();
				return;
			}
			if ( ! mobile || event.key !== 'Tab' ) {
				return;
			}
			const controls = Array.from(
				panel.querySelectorAll(
					'button,a[href],input,textarea,summary,[tabindex]'
				)
			).filter( available );
			const first = controls[ 0 ],
				last = controls[ controls.length - 1 ],
				active = panel.ownerDocument.activeElement;
			if ( ! first ) {
				event.preventDefault();
				return;
			}
			if (
				event.shiftKey &&
				( active === first || ! panel.contains( active ) )
			) {
				event.preventDefault();
				last.focus();
			} else if (
				! event.shiftKey &&
				( active === last || ! panel.contains( active ) )
			) {
				event.preventDefault();
				first.focus();
			}
		}
		function resize() {
			if ( failureBoundary ) {
				failureBoundary( false );
			}
			if ( failure && ! panel.hidden ) {
				failureBoundary = bindFailureBoundary( panel, initial );
			}
		}
		document.addEventListener( 'keydown', key );
		window.addEventListener( 'resize', resize );
		return function ( returnFocus ) {
			cancelAnimationFrame( frame );
			document.removeEventListener( 'keydown', key );
			window.removeEventListener( 'resize', resize );
			background.forEach( function ( item ) {
				if ( item[ 0 ].inert ) {
					item[ 0 ].inert = item[ 1 ];
				}
			} );
			if ( mobile && document.body.style.overflow === 'hidden' ) {
				document.body.style.overflow = overflow;
			}
			saved.forEach( function ( item ) {
				if ( item[ 1 ] === null ) {
					panel.removeAttribute( item[ 0 ] );
				} else {
					panel.setAttribute( item[ 0 ], item[ 1 ] );
				}
			} );
			const active = panel.ownerDocument.activeElement;
			if (
				returnFocus &&
				( ! active ||
					active === document.body ||
					panel.contains( active ) ) &&
				available( pendingOpener )
			) {
				pendingOpener.focus( { preventScroll: true } );
			}
		};
	}
	function closeFailure() {
		dismissed = true;
		pendingOpen = false;
		// Cancel this delivery intent. The source and its persisted entry remain recoverable without auto-send.
		pendingAsk = '';
		pendingAttach = false;
		pendingList = false;
		pendingRefresh = false;
		pendingFromHome = false;
		pendingSolution = 0;
		pendingEntries = Object.create( null );
		shell( false );
		clearFailure( true );
	}
	function clearFailure( returnFocus ) {
		if ( failureBoundary ) {
			failureBoundary( !! returnFocus );
			failureBoundary = null;
		}
		if ( failure ) {
			failure.remove();
			failure = null;
		}
	}
	function showFailure() {
		removePreview();
		if ( dismissed && ! payload.open ) {
			return;
		}
		clearFailure();
		const panel = document.querySelector( '[data-linker-genie-mount]' );
		if ( ! panel ) {
			return;
		}
		failure = document.createElement( 'section' );
		failure.className = 'linker-genie-app';
		failure.setAttribute( 'data-linker-genie-load-error', '' );
		const header = document.createElement( 'header' );
		header.className = 'linker-genie-load-error__header';
		const title = document.createElement( 'h2' );
		title.textContent = payload.title;
		header.appendChild( title );
		if ( ! payload.open ) {
			const close = document.createElement( 'button' );
			close.type = 'button';
			close.className = 'linker-genie-app__prompt';
			close.textContent = payload.close;
			close.addEventListener( 'click', closeFailure );
			header.appendChild( close );
		}
		failure.appendChild( header );
		const message = document.createElement( 'p' );
		message.className = 'linker-genie-app__error';
		message.setAttribute( 'role', 'alert' );
		message.textContent = payload.error;
		const retry = document.createElement( 'button' );
		retry.type = 'button';
		retry.className = 'linker-genie-app__prompt';
		retry.setAttribute( 'data-linker-genie-open', '' );
		retry.textContent = payload.retry;
		failure.appendChild( message );
		const actions = document.createElement( 'div' );
		actions.className = 'linker-genie-load-error__actions';
		actions.appendChild( retry );
		failure.appendChild( actions );
		panel.appendChild( failure );
		shell( true );
		if ( ! payload.open ) {
			failureBoundary = bindFailureBoundary( panel, retry );
		} else {
			retry.focus();
		}
	}
	function shell( expanded ) {
		const panel = document.querySelector( '[data-linker-genie-mount]' );
		if ( panel ) {
			panel.hidden = ! expanded;
		}
		document
			.querySelectorAll( '[data-linker-genie-open]' )
			.forEach( function ( button ) {
				button.setAttribute( 'aria-expanded', String( expanded ) );
			} );
	}
	function deliver() {
		if (
			! ready ||
			dismissed ||
			( ! pendingOpen && Object.keys( pendingEntries ).length === 0 )
		) {
			return;
		}
		shell( true );
		Object.keys( pendingEntries ).forEach( function ( id ) {
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-open', {
					detail: {
						entry: pendingEntries[ id ],
						opener: pendingOpener,
					},
				} )
			);
		} );
		const message = pendingAsk;
		const attach = pendingAttach;
		const list = pendingList;
		const refresh = pendingRefresh;
		const fromHome = pendingFromHome;
		const solution = pendingSolution;
		pendingOpen = false;
		pendingAsk = '';
		pendingAttach = false;
		pendingList = false;
		pendingRefresh = false;
		pendingFromHome = false;
		pendingSolution = 0;
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: {
					message,
					attach,
					list,
					refresh,
					fromHome,
					solution,
					opener: pendingOpener,
				},
			} )
		);
	}
	let preview = null;
	function showPendingQuestion( message ) {
		if ( ! message || ready || preview ) {
			return;
		}
		const panel = document.querySelector( '[data-linker-genie-mount]' );
		if ( ! panel ) {
			return;
		}
		preview = document.createElement( 'div' );
		preview.className = 'linker-genie-loading-preview';
		const title = document.createElement( 'strong' );
		title.textContent = payload.title;
		const bubble = document.createElement( 'p' );
		bubble.className =
			'linker-genie-app__message linker-genie-app__message--user';
		bubble.textContent = message;
		const status = document.createElement( 'p' );
		status.setAttribute( 'role', 'status' );
		status.textContent = payload.waiting;
		preview.append( title, bubble, status );
		panel.appendChild( preview );
		shell( true );
	}
	function removePreview() {
		if ( preview ) {
			preview.remove();
			preview = null;
		}
	}
	let warmed = false;
	function warmBundle() {
		if ( warmed || ready || loaded ) {
			return;
		}
		warmed = true;
		const link = document.createElement( 'link' );
		link.rel = 'preload';
		link.as = 'script';
		link.href = payload.src;
		document.head.appendChild( link );
	}
	document.addEventListener(
		'pointerover',
		function ( event ) {
			if (
				event.target.closest &&
				event.target.closest( '[data-linker-genie-open]' )
			) {
				warmBundle();
			}
		},
		{ passive: true }
	);
	if ( window.requestIdleCallback ) {
		window.requestIdleCallback( warmBundle );
	} else {
		window.addEventListener( 'load', warmBundle, { once: true } );
	}
	function open( message, refresh, fromHome, solution ) {
		dismissed = false;
		pendingOpen = true;
		// A plain reopen during loading must not erase the first question.
		if ( message && ! pendingAsk ) {
			pendingAsk = message;
		}
		if ( refresh ) {
			pendingRefresh = true;
		}
		if ( fromHome ) {
			pendingFromHome = true;
		}
		// A saved solution reference (#496): the report's "Ask Genie" saves the
		// solution first and hands its id to the app, which sends it with the
		// page context of every later turn.
		if ( typeof solution === 'number' && solution > 0 ) {
			pendingSolution = solution;
		}
		boot();
		showPendingQuestion( pendingAsk );
		deliver();
	}
	window.addEventListener( 'linker-genie-ready', function () {
		ready = true;
		removePreview();
		clearFailure();
		if ( payload.open ) {
			pendingOpen = true;
		}
		deliver();
	} );
	window.addEventListener( 'linker-genie-state', function ( event ) {
		shell( event.detail.open );
	} );
	window.addEventListener( 'linker-genie-entry-state', function ( event ) {
		if ( event.detail && event.detail.phase === 'accepted' ) {
			delete pendingEntries[ event.detail.id ];
		}
	} );
	window.addEventListener( 'linker-genie-hero-view', function () {
		if ( document.querySelector( '[data-genie-hero-history]' ) ) {
			boot();
		}
	} );
	window.addEventListener( 'linker-genie-ask', function ( event ) {
		const detail = event.detail;
		pendingOpener =
			detail && detail.opener instanceof HTMLElement
				? detail.opener
				: config.ownerDocument.activeElement;
		if ( detail && detail.entry && typeof detail.entry.id === 'string' ) {
			pendingEntries[ detail.entry.id ] = detail.entry;
			open( '' );
			return;
		}
		const refresh = !! detail && true === detail.refresh;
		const fromHome = !! detail && true === detail.fromHome;
		// The saved solution the design report's "Ask Genie" saved (#496).
		const solution =
			detail && typeof detail.solution === 'number' ? detail.solution : 0;
		if (
			detail &&
			typeof detail.message === 'string' &&
			detail.message.trim()
		) {
			open( detail.message, refresh, fromHome, solution );
		} else if ( detail && true === detail.attach ) {
			pendingAttach = true;
			pendingList = true === detail.list;
			open( '', refresh, fromHome, solution );
		} else if ( refresh ) {
			// The home hero hands its conversation to the dock without a
			// new question (#232).
			open( '', true, fromHome, solution );
		}
	} );
	const scripts = new Map();
	function script( url ) {
		if ( ! scripts.has( url ) ) {
			const tag = document.createElement( 'script' );
			tag.src = url;
			tag.async = false;
			scripts.set(
				url,
				new Promise( ( resolve, reject ) => {
					tag.onload = () => {
						scripts.delete( url );
						resolve();
					};
					tag.onerror = () => {
						scripts.delete( url );
						tag.remove();
						reject( new Error( url ) );
					};
					document.body.appendChild( tag );
				} )
			);
		}
		return scripts.get( url );
	}
	function missingDependency( url, entry ) {
		const path = entry.nativeDependencies?.[ url ];
		return (
			! path || ! path.reduce( ( value, key ) => value?.[ key ], window )
		);
	}
	// Both entries share the native runtimes, even when opened in the same turn.
	window.linkerLoadGenieEntry = async function ( entry ) {
		const styles = ( entry.styles || [] )
			.filter(
				( url ) =>
					url &&
					! Array.from( document.styleSheets ).some(
						( sheet ) =>
							sheet.href === new URL( url, document.baseURI ).href
					)
			)
			.map(
				( url ) =>
					new Promise( ( resolve, reject ) => {
						const link = document.createElement( 'link' );
						link.rel = 'stylesheet';
						link.href = url;
						link.onload = resolve;
						link.onerror = () => {
							link.remove();
							reject( new Error( url ) );
						};
						document.head.appendChild( link );
					} )
			);
		const deps = entry.deps
			.filter( ( url ) => missingDependency( url, entry ) )
			.map( script );
		const translations = ( entry.translationUrls || [] ).map(
			async ( url ) => {
				const response = await fetch( url, { credentials: 'omit' } );
				if ( ! response.ok ) {
					throw new Error( url );
				}
				const catalog = await response.json();
				const messages =
					catalog.locale_data?.[ 'linker-tools' ] ||
					catalog.locale_data?.messages;
				if ( ! messages ) {
					throw new Error( url );
				}
				return messages;
			}
		);
		const [ , catalogs ] = await Promise.all( [
			Promise.all( [ ...styles, ...deps ] ),
			Promise.all( translations ),
		] );
		for ( const messages of catalogs ) {
			window.wp.i18n.setLocaleData( messages, 'linker-tools' );
		}
		await script( entry.src );
	};
	function boot() {
		// Native enqueued dependencies finish before DOMContentLoaded.
		// Re-executing them would reset the planner's translations.
		if (
			document.readyState === 'loading' &&
			( ! payload.open ||
				payload.deps.some( ( url ) =>
					missingDependency( url, payload )
				) )
		) {
			document.addEventListener( 'DOMContentLoaded', boot, {
				once: true,
			} );
			return;
		}
		if ( loaded || ready ) {
			return;
		}
		loaded = true;
		clearFailure();
		// The workspace has no bubble to reopen a hidden page. Keep it
		// visible while the app loads; ready then delivers open.
		// A helper stays closed until the visitor's click is delivered.
		shell( !! payload.open || !! preview );
		window.linkerLoadGenieEntry( payload ).catch( () => {
			loaded = false;
			showFailure();
			Object.keys( pendingEntries ).forEach( function ( id ) {
				window.dispatchEvent(
					new CustomEvent( 'linker-genie-entry-state', {
						detail: { id, phase: 'failed' },
					} )
				);
			} );
		} );
	}
	// A workspace page has no bubble. Setting pendingOpen and waiting
	// for a click leaves the mount empty: nothing ever calls boot().
	// Boot before any script is inserted; ready then delivers open.
	if ( payload.open ) {
		pendingOpen = true;
		boot();
	}
	document.addEventListener(
		'click',
		function ( event ) {
			const trigger = event.target.closest?.(
				'[data-linker-genie-open]'
			);
			if ( ! trigger ) {
				return;
			}
			// An anchor opener (the empty Proforma request's Genie
			// pill) keeps its href as the no-JavaScript fallback.
			// With the dock present the click opens the panel here,
			// so the navigation must not fire on top of it.
			if ( trigger.tagName === 'A' ) {
				event.preventDefault();
			}
			// A page chip carries its label as the first question. A plain
			// opener (the bubble, a retry) has no payload and must not ask.
			if ( ! failure || ! failure.contains( trigger ) ) {
				pendingOpener = trigger;
			}
			open( trigger.getAttribute( 'data-ask-message' ) || '' );
		},
		true
	);
} )();
