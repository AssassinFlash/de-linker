/* PROTOTYPE · map #220 · ticket #249 — throwaway. */
( function () {
	'use strict';
	const ctx = window.lppCtx;
	if ( ! ctx ) {
		return;
	}
	const params = new URLSearchParams( location.search );
	const VARIANTS = [
		{ key: 'A', name: '提示卡 · Peek card' },
		{ key: 'B', name: '气泡 · One-line bubble' },
		{ key: 'C', name: '情境卡 · Context card' },
	];
	let variant = ( params.get( 'pc' ) || 'A' ).toUpperCase();
	if ( ! VARIANTS.some( ( v ) => v.key === variant ) ) {
		variant = 'A';
	}
	const DWELL = Math.max( 0, Number( params.get( 'dwell' ) || 8 ) ) * 1000;
	const DAY = 864e5;
	const KEY_DISMISSED = 'lpp-dismissed-until';
	const KEY_SHOWN = 'lpp-shown-this-visit';
	const store = {
		get( s, k ) {
			try {
				return s.getItem( k );
			} catch ( e ) {
				return null;
			}
		},
		set( s, k, v ) {
			try {
				s.setItem( k, v );
			} catch ( e ) {}
		},
		del( s, k ) {
			try {
				s.removeItem( k );
			} catch ( e ) {}
		},
	};
	const esc = ( s ) => String( s ?? '' ).replace( /[&<>"']/g, ( c ) => ( { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } )[ c ] );

	// What the card says, per page type.
	const COPY = {
		home: {
			title: 'Ask Genie about any product we carry',
			lead: 'Genie knows our whole range — models, pairings and documents.',
			chips: [ 'Find the SAJ H2-10K-T3', 'Identify a device from a nameplate photo', 'Turn my parts list into a solution draft', 'Compare GoodWe and SAJ storage systems' ],
			tiles: [ [ 'Type a model', 'Find the SAJ H2-10K-T3' ], [ 'Photo of a nameplate', 'Identify a device from a nameplate photo' ], [ 'Upload a parts list', 'Turn my parts list into a solution draft' ], [ 'Compare brands', 'Compare GoodWe and SAJ storage systems' ] ],
		},
		product: {
			title: `Looking at the ${ ctx.name }?`,
			lead: 'Genie can answer about this model straight away.',
			chips: [ `Which batteries pair with the ${ ctx.name }?`, `Show the documents for the ${ ctx.name }`, `Compare the ${ ctx.name } with similar models` ],
		},
		category: {
			title: `Browsing ${ ctx.name }?`,
			lead: 'Tell Genie your project and it narrows the list down.',
			chips: [ `Help me choose between these ${ ctx.name.toLowerCase() }`, 'Single- or three-phase — which do I need?', 'Compare the three most popular models' ],
		},
		solution: {
			title: `Planning ${ ctx.name.toLowerCase() }?`,
			lead: 'Genie can size it and pick the products with you.',
			chips: [ 'Size a system for my project', 'Which products fit this solution?', 'Open the Solution Configurator' ],
		},
	}[ ctx.type ];

	const launcher = () => document.querySelector( '.linker-genie-open' );
	const mobile = () => window.innerWidth < 600;
	let shown = false;
	let timer = null;
	let armedAt = 0;
	let anchorPassed = false;
	let conversationOpen = false;

	window.addEventListener( 'linker-genie-state', ( e ) => {
		conversationOpen = !! ( e.detail && e.detail.open );
		if ( conversationOpen ) {
			hide();
		}
		status();
	} );

	function dismissedUntil() {
		return Number( store.get( localStorage, KEY_DISMISSED ) || 0 );
	}
	function eligible() {
		const typing = document.activeElement && document.activeElement.closest( 'input, textarea, select, [contenteditable]' );
		return ! shown && ! conversationOpen && ! typing && ! store.get( sessionStorage, KEY_SHOWN ) && dismissedUntil() < Date.now();
	}

	function anchorY() {
		if ( ctx.type === 'home' ) {
			const hero = document.querySelector( '.hero-cinematic' );
			if ( hero ) {
				return hero.getBoundingClientRect().bottom + window.scrollY - window.innerHeight * 0.4;
			}
		}
		return window.innerHeight * 0.75; // past the first screen of content
	}

	function onScroll() {
		if ( ! anchorPassed && window.scrollY >= anchorY() ) {
			anchorPassed = true;
			armedAt = Date.now();
			timer = setTimeout( () => {
				if ( eligible() ) {
					show();
				}
				status();
			}, DWELL );
		}
		status();
	}

	// ---------- the card ----------
	const el = document.createElement( 'div' );
	el.className = 'lpp lpp--' + variant;
	el.hidden = true;
	el.setAttribute( 'role', 'complementary' );
	el.setAttribute( 'aria-label', 'Genie suggestions' );
	document.body.appendChild( el );

	const mark = '<span class="lpp-mark" aria-hidden="true">✦</span>';
	const close = '<button type="button" class="lpp-close" data-lpp-close aria-label="Close — do not show again for 30 days">×</button>';
	const disclosure = '<p class="lpp-ai">AI assistant · answers can contain mistakes</p>';

	function render() {
		const chips = ( list ) => list.map( ( q ) => `<button type="button" class="lpp-chip" data-lpp-ask="${ esc( q ) }">${ esc( q ) }</button>` ).join( '' );
		if ( variant === 'A' ) {
			el.innerHTML = `<div class="lpp-head">${ mark }<span>Genie</span>${ close }</div>
				<p class="lpp-title">${ esc( COPY.title ) }</p><p class="lpp-lead">${ esc( COPY.lead ) }</p>
				<div class="lpp-chips">${ chips( COPY.chips.slice( 0, ctx.type === 'home' ? 4 : 3 ) ) }</div>${ disclosure }`;
		} else if ( variant === 'B' ) {
			el.innerHTML = `<div class="lpp-bubble"><button type="button" class="lpp-bubble__text" data-lpp-expand>${ mark } ${ esc( COPY.title ) } <span class="lpp-bubble__cta">Ask Genie</span></button>${ close }</div>
				<div class="lpp-more" hidden>${ chips( COPY.chips.slice( 0, 3 ) ) }${ disclosure }</div>`;
		} else {
			const img = ( document.querySelector( 'meta[property="og:image"]' ) || {} ).content;
			const body = ctx.type === 'home'
				? `<div class="lpp-tiles">${ COPY.tiles.map( ( [ l, q ] ) => `<button type="button" class="lpp-tile" data-lpp-ask="${ esc( q ) }">${ esc( l ) }</button>` ).join( '' ) }</div>`
				: `${ ctx.type === 'product' && img ? `<img class="lpp-img" src="${ esc( img ) }" alt="">` : '' }<div class="lpp-rows">${ COPY.chips.map( ( q ) => `<button type="button" class="lpp-row" data-lpp-ask="${ esc( q ) }">${ esc( q ) }<span>→</span></button>` ).join( '' ) }</div>`;
			el.innerHTML = `<div class="lpp-head">${ mark }<span>Genie · ${ esc( COPY.title ) }</span>${ close }</div>${ body }${ disclosure }`;
		}
	}

	function show() {
		shown = true;
		store.set( sessionStorage, KEY_SHOWN, '1' );
		if ( mobile() ) {
			const l = launcher();
			if ( l ) {
				l.classList.add( 'lpp-badged' );
			}
			return;
		}
		render();
		el.hidden = false;
		requestAnimationFrame( () => el.classList.add( 'is-in' ) );
	}
	function hide() {
		el.classList.remove( 'is-in' );
		el.hidden = true;
		const l = launcher();
		if ( l ) {
			l.classList.remove( 'lpp-badged' );
		}
	}

	el.addEventListener( 'click', ( e ) => {
		const t = e.target.closest( '[data-lpp-close],[data-lpp-ask],[data-lpp-expand]' );
		if ( ! t ) {
			return;
		}
		if ( 'lppClose' in t.dataset ) {
			store.set( localStorage, KEY_DISMISSED, String( Date.now() + 30 * DAY ) );
			hide();
		} else if ( 'lppExpand' in t.dataset ) {
			el.querySelector( '.lpp-more' ).hidden = false;
			el.classList.add( 'is-open' );
		} else {
			hide();
			// The dock loader's own contract (Entries.php), as pdp-ui.js uses it.
			window.dispatchEvent( new CustomEvent( 'linker-genie-ask', { detail: { message: t.dataset.lppAsk, trigger: t } } ) );
		}
		status();
	} );
	document.addEventListener( 'click', ( e ) => {
		if ( e.target.closest( '.linker-genie-open' ) ) {
			hide();
		}
	} );

	// ---------- prototype chrome: variant switcher + trigger status ----------
	const bar = document.createElement( 'div' );
	bar.className = 'lpp-switcher';
	document.body.appendChild( bar );
	function status() {
		const v = VARIANTS.find( ( x ) => x.key === variant );
		const left = anchorPassed && ! shown ? Math.max( 0, Math.ceil( ( armedAt + DWELL - Date.now() ) / 1000 ) ) : null;
		const parts = [
			anchorPassed ? '已滚过主内容 ✓' : '尚未滚过主内容',
			left !== null ? `停留倒计时 ${ left }s` : '',
			shown ? '本次访问已出现' : '',
			dismissedUntil() > Date.now() ? '已关闭（30 天内不再出现）' : '',
			conversationOpen ? '对话进行中' : '',
		].filter( Boolean ).join( ' · ' );
		bar.innerHTML = `<button type="button" data-cyc="-1" aria-label="Previous">←</button><span><b>${ v.key }</b> · ${ esc( v.name ) }</span><button type="button" data-cyc="1" aria-label="Next">→</button>
			<span class="lpp-status">${ esc( parts ) }</span><button type="button" class="lpp-btn" data-now>现在显示</button><button type="button" class="lpp-btn" data-reset>重置</button>`;
	}
	bar.addEventListener( 'click', ( e ) => {
		const b = e.target.closest( 'button' );
		if ( ! b ) {
			return;
		}
		if ( b.dataset.cyc ) {
			const i = VARIANTS.findIndex( ( x ) => x.key === variant );
			params.set( 'pc', VARIANTS[ ( i + Number( b.dataset.cyc ) + 3 ) % 3 ].key );
			params.set( 'trigger', 'now' );
			location.search = params.toString();
		} else if ( 'now' in b.dataset ) {
			hide();
			shown = false;
			show();
		} else if ( 'reset' in b.dataset ) {
			store.del( localStorage, KEY_DISMISSED );
			store.del( sessionStorage, KEY_SHOWN );
			location.reload();
		}
		status();
	} );
	setInterval( status, 1000 );

	window.addEventListener( 'scroll', onScroll, { passive: true } );
	status();
	if ( params.get( 'trigger' ) === 'now' ) {
		setTimeout( show, 300 );
	} else {
		onScroll();
	}
}() );
