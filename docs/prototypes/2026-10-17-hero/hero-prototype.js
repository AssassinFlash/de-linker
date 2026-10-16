/* PROTOTYPE · map #220 · ticket #231 — throwaway.
 * Scripted Genie answers (not the real service); product cards come from the
 * site's own Store API, read-only. Variants: /?variant=A|B|C. */
( function () {
	'use strict';
	const hero = document.querySelector( '.hero-cinematic' );
	if ( ! hero ) {
		return;
	}

	const VARIANTS = [
		{ key: 'A', name: '交给右下角 Genie · Dock handoff' },
		{ key: 'B', name: '就地展开 · Unfold in the hero' },
		{ key: 'C', name: '专注模式 · Focus view' },
	];
	const params = new URLSearchParams( location.search );
	let variant = ( params.get( 'variant' ) || 'A' ).toUpperCase();
	if ( ! VARIANTS.some( ( v ) => v.key === variant ) ) {
		variant = 'A';
	}

	const dialog = hero.querySelector( '.hero-dialog' );
	const prompt = hero.querySelector( '.hero-prompt' );
	const send = hero.querySelector( '.hero-send' );
	const capsules = [ ...hero.querySelectorAll( '.hero-capsule' ) ];
	const btnPhoto = hero.querySelector( '[data-linker-assistant-open="nameplate"]' );
	const btnAttach = hero.querySelector( '[data-linker-assistant-open="attach"]' );
	const btnVoice = hero.querySelector( '[data-linker-assistant-open="voice"]' );
	const heroPlaceholder = prompt.placeholder;

	const esc = ( s ) => String( s ?? '' ).replace( /[&<>"']/g, ( c ) => ( { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } )[ c ] );
	const sleep = ( ms ) => new Promise( ( r ) => setTimeout( r, ms ) );
	const decode = ( s ) => {
		const t = document.createElement( 'textarea' );
		t.innerHTML = s;
		return t.value;
	};
	const svg = ( d ) => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ d }</svg>`;
	const ICON = {
		plus: svg( '<path d="M12 5v14M5 12h14"/>' ),
		x: svg( '<path d="M18 6 6 18M6 6l12 12"/>' ),
		expand: svg( '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>' ),
		clip: svg( '<path d="m21.4 11.1-9.2 9.2a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5"/>' ),
		mic: svg( '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3"/>' ),
		up: svg( '<path d="M12 19V5M5 12l7-7 7 7"/>' ),
		spark: svg( '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>' ),
	};

	// ---------- the scripted Genie ----------
	async function products( q, n ) {
		try {
			const r = await fetch( '/wp-json/wc/store/v1/products?per_page=' + n + '&search=' + encodeURIComponent( q ) );
			if ( ! r.ok ) {
				return [];
			}
			return ( await r.json() ).map( ( p ) => ( {
				name: decode( p.name ),
				img: ( p.images && p.images[ 0 ] && ( p.images[ 0 ].thumbnail || p.images[ 0 ].src ) ) || '',
				url: p.permalink,
			} ) );
		} catch ( e ) {
			return [];
		}
	}

	async function answer( text, meta ) {
		const t = text.toLowerCase();
		if ( meta.photo ) {
			return { text: 'From your photo I read <b>SAJ H2-10K-T3</b>, a 10 kW three-phase hybrid inverter. Please confirm it before I use it.', cards: await products( 'H2-10K-T3', 1 ), chips: [ 'Yes, that is my device', 'Which batteries pair with it?', 'No, I will type the model' ] };
		}
		if ( meta.file ) {
			return { text: 'I read <b>' + esc( meta.file ) + '</b>: a datasheet for a three-phase hybrid inverter. Ask me what you need from it, for example which batteries are documented with it.', chips: [ 'Which batteries are documented with it?', 'Show me similar models we carry' ] };
		}
		if ( /\bsaj\b/.test( t ) && /goodwe/.test( t ) ) {
			const [ a, b ] = await Promise.all( [ products( 'ETR-G10', 2 ), products( 'SAJ CB2', 2 ) ] );
			return { text: 'Commercial systems from both brands, side by side. The cards carry the figures; the full comparison opens with one click.', cards: [ ...a, ...b ], chips: [ 'Open the comparison', 'Only three-phase', 'Which needs fewer accessories?' ] };
		}
		if ( /\bsaj\b/.test( t ) ) {
			return { text: 'SAJ: we carry their hybrid inverters, commercial battery systems and accessories. Here are four models; tell me the application and I will narrow it down.', cards: await products( 'SAJ', 4 ), chips: [ 'For a home', 'For a business', 'Show all SAJ products' ] };
		}
		if ( /10 ?kw/.test( t ) ) {
			return { text: 'For a 10 kW storage system the first deciding question is the grid connection. These models fit the size: single- or three-phase?', cards: await products( '10K', 4 ), chips: [ 'Single-phase', 'Three-phase', 'I also need backup power' ] };
		}
		if ( /compatib|pair|kompatib|batter/.test( t ) ) {
			return { text: 'The GoodWe ESA units have documented battery pairings. Every pair below is released by the manufacturer; the conditions are in the compatibility document.', cards: await products( 'GoodWe ESA', 3 ), chips: [ 'Open the compatibility document', 'Which one for about 15 kWh?' ] };
		}
		const cards = await products( text, 4 );
		if ( cards.length ) {
			return { text: 'Here is what I found for “' + esc( text ) + '”.', cards, chips: [ 'Narrow by application', 'Compare two of these' ] };
		}
		return { text: 'I could not match “' + esc( text ) + '” to a product. What are you planning: home or commercial, and roughly what size?', chips: [ 'Home storage', 'Commercial storage', 'Talk to the Linker team' ] };
	}

	// ---------- one conversation, shown on whichever surface is open ----------
	const thread = [];
	let origin = '';

	async function ask( text, meta, from ) {
		text = ( text || '' ).trim();
		if ( ! text && ! meta.photo && ! meta.file ) {
			return;
		}
		if ( ! thread.length && from === 'hero' ) {
			origin = 'Asked from the homepage';
		}
		thread.push( { role: 'user', text, meta } );
		const reply = { role: 'genie', pending: true };
		thread.push( reply );
		openFor( from );
		refresh();
		const a = await answer( text, meta );
		await sleep( 650 );
		reply.pending = false;
		reply.a = a;
		refresh();
	}

	const card = ( p ) => `<a class="hp-card" href="${ esc( p.url ) }">${ p.img ? `<img src="${ esc( p.img ) }" alt="">` : '<span class="hp-card__noimg"></span>' }<span class="hp-card__name">${ esc( p.name ) }</span><span class="hp-card__act">+ Solution draft</span></a>`;

	function messages() {
		return '<p class="hp-intro">Genie is Linker\'s AI assistant. Answers come from our product data and documents.</p>' + thread.map( ( m ) => {
			if ( m.role === 'user' ) {
				let extra = '';
				if ( m.meta.photoUrl ) {
					extra = `<img class="hp-thumb" src="${ m.meta.photoUrl }" alt="">`;
				} else if ( m.meta.file ) {
					extra = `<span class="hp-attach">Attached: ${ esc( m.meta.file ) }</span>`;
				}
				return `<div class="hp-msg hp-msg--user">${ extra }${ m.text ? `<span>${ esc( m.text ) }</span>` : '' }</div>`;
			}
			if ( m.pending ) {
				return '<div class="hp-msg hp-msg--genie"><span class="hp-typing"><i></i><i></i><i></i></span></div>';
			}
			const a = m.a;
			return `<div class="hp-msg hp-msg--genie"><p>${ a.text }</p>
				${ a.cards && a.cards.length ? `<div class="hp-cards">${ a.cards.map( card ).join( '' ) }</div>` : '' }
				${ a.chips && a.chips.length ? `<div class="hp-chips">${ a.chips.map( ( c ) => `<button type="button" class="hp-chip" data-hp-ask="${ esc( c ) }">${ esc( c ) }</button>` ).join( '' ) }</div>` : '' }
			</div>`;
		} ).join( '' );
	}

	const composer = ( where, placeholder ) => `<form class="hp-composer" data-hp-form="${ where }">
		<button type="button" class="hp-icon" data-hp-attach aria-label="Attach a file">${ ICON.clip }</button>
		<textarea rows="1" placeholder="${ placeholder }"></textarea>
		<button type="button" class="hp-icon" data-hp-voice aria-label="Voice input">${ ICON.mic }</button>
		<button type="submit" class="hp-send" aria-label="Send">${ ICON.up }</button>
	</form>`;

	function scrollDown( el ) {
		const t = el.querySelector( '.hp-thread' );
		if ( t ) {
			t.scrollTop = t.scrollHeight;
		}
	}

	// Surface 1 — the dock (every variant continues here).
	const dock = document.createElement( 'section' );
	dock.className = 'hp-dock';
	dock.hidden = true;
	document.body.appendChild( dock );
	function renderDock() {
		dock.innerHTML = `<header class="hp-bar"><p>Genie - Linker's AI assistant</p><div>
				<button type="button" class="hp-icon" data-hp-new aria-label="New conversation">${ ICON.plus }</button>
				<a class="hp-icon" href="/genie/" aria-label="Open full screen">${ ICON.expand }</a>
				<button type="button" class="hp-icon" data-hp-close-dock aria-label="Close">${ ICON.x }</button></div></header>
			${ origin ? `<p class="hp-origin">${ origin }</p>` : '' }
			<div class="hp-thread">${ messages() }</div>${ composer( 'dock', 'Ask Genie' ) }`;
		scrollDown( dock );
	}

	// Surface 2 — the conversation unfolds inside the hero (variant B).
	const heroThread = document.createElement( 'div' );
	heroThread.className = 'hp-hero-thread';
	function renderHero() {
		heroThread.innerHTML = `<div class="hp-bar hp-bar--hero"><p>Genie - Linker's AI assistant</p><div>
				<button type="button" class="hp-link" data-hp-to-dock>Continue in the side panel</button>
				<button type="button" class="hp-icon" data-hp-fold aria-label="Close">${ ICON.x }</button></div></div>
			<div class="hp-thread">${ messages() }</div>`;
		scrollDown( heroThread );
	}

	// Surface 3 — a focus view over the page (variant C).
	const focus = document.createElement( 'div' );
	focus.className = 'hp-focus';
	focus.hidden = true;
	document.body.appendChild( focus );
	function renderFocus() {
		const steps = [ [ 'Compare these models', 'Open the comparison' ], [ 'Check a battery pairing', 'Which batteries pair with it?' ], [ 'Add to my solution draft', 'Add these to my solution draft' ], [ 'Plan a whole system', 'Open the Solution Configurator' ] ];
		focus.innerHTML = `<div class="hp-focus__panel" role="dialog" aria-label="Genie">
			<header class="hp-bar"><p>Genie - Linker's AI assistant</p><button type="button" class="hp-link" data-hp-close-focus>Back to the page <kbd>Esc</kbd></button></header>
			<div class="hp-focus__body"><div class="hp-thread">${ messages() }</div>
				<aside class="hp-next"><h3>Next steps</h3>${ steps.map( ( [ l, q ] ) => `<button type="button" class="hp-step" data-hp-ask="${ esc( q ) }">${ esc( l ) }</button>` ).join( '' ) }
				<p class="hp-next__note">The conversation stays in the side panel when you go back to the page.</p></aside></div>
			${ composer( 'focus', 'Ask a follow-up…' ) }</div>`;
		scrollDown( focus );
	}

	// A way back once the conversation is out of sight.
	const pill = document.createElement( 'button' );
	pill.type = 'button';
	pill.className = 'hp-pill';
	pill.hidden = true;
	document.body.appendChild( pill );
	function showPill() {
		const n = thread.filter( ( m ) => m.role === 'user' ).length;
		if ( n ) {
			pill.innerHTML = `${ ICON.spark } Your Genie conversation (${ n }) · continue`;
			pill.hidden = false;
		}
	}
	pill.addEventListener( 'click', () => {
		pill.hidden = true;
		openDock();
	} );

	const hint = document.createElement( 'p' );
	hint.className = 'hp-hint';
	hint.textContent = 'Genie is answering in the panel on the right →';

	function refresh() {
		if ( ! dock.hidden ) {
			renderDock();
		}
		if ( heroThread.isConnected ) {
			renderHero();
		}
		if ( ! focus.hidden ) {
			renderFocus();
		}
	}

	function openDock() {
		closeFocus( false );
		if ( heroThread.isConnected ) {
			fold( false );
		}
		dock.hidden = false;
		pill.hidden = true;
		renderDock();
	}
	function closeDock() {
		dock.hidden = true;
	}
	function unfold() {
		if ( ! heroThread.isConnected ) {
			dialog.insertBefore( heroThread, dialog.firstChild );
		}
		hero.classList.add( 'hp-unfolded' );
		prompt.placeholder = 'Ask a follow-up…';
		renderHero();
	}
	function fold( withPill ) {
		hero.classList.remove( 'hp-unfolded' );
		heroThread.remove();
		prompt.placeholder = heroPlaceholder;
		if ( withPill ) {
			showPill();
		}
	}
	function openFocus() {
		closeDock();
		focus.hidden = false;
		document.documentElement.classList.add( 'hp-locked' );
		renderFocus();
		const box = focus.querySelector( 'textarea' );
		if ( box ) {
			box.focus();
		}
	}
	function closeFocus( withPill ) {
		if ( focus.hidden ) {
			return;
		}
		focus.hidden = true;
		document.documentElement.classList.remove( 'hp-locked' );
		if ( withPill ) {
			showPill();
		}
	}

	function openFor( from ) {
		if ( from === 'dock' ) {
			return;
		}
		if ( from === 'focus' || ( from === 'hero' && variant === 'C' ) ) {
			prompt.value = '';
			openFocus();
			return;
		}
		if ( from === 'hero' && variant === 'B' ) {
			prompt.value = '';
			if ( dock.hidden ) {
				unfold();
				return;
			}
		}
		prompt.value = '';
		openDock();
		if ( from === 'hero' ) {
			dialog.after( hint );
			hint.classList.add( 'is-on' );
			setTimeout( () => hint.classList.remove( 'is-on' ), 4000 );
		}
	}

	// In variant B, leaving the hero leaves a way back.
	new IntersectionObserver( ( [ entry ] ) => {
		if ( heroThread.isConnected && ! entry.isIntersecting ) {
			showPill();
		} else if ( entry.isIntersecting && heroThread.isConnected ) {
			pill.hidden = true;
		}
	}, { threshold: 0.15 } ).observe( dialog );

	// ---------- the hero's own controls ----------
	prompt.addEventListener( 'keydown', ( e ) => {
		if ( e.key === 'Enter' && ! e.shiftKey ) {
			e.preventDefault();
			ask( prompt.value, {}, 'hero' );
		}
	} );
	send.addEventListener( 'click', ( e ) => {
		e.preventDefault();
		ask( prompt.value, {}, 'hero' );
	} );
	capsules.forEach( ( c ) => c.addEventListener( 'click', ( e ) => {
		e.preventDefault();
		ask( c.textContent, {}, 'hero' );
	} ) );

	function picker( accept, onFile ) {
		const input = document.createElement( 'input' );
		input.type = 'file';
		input.accept = accept;
		input.hidden = true;
		input.addEventListener( 'change', () => {
			if ( input.files[ 0 ] ) {
				onFile( input.files[ 0 ] );
			}
			input.value = '';
		} );
		document.body.appendChild( input );
		return input;
	}
	let pickFrom = 'hero';
	const photoInput = picker( 'image/*', ( f ) => ask( pickFrom === 'hero' ? prompt.value : '', { photo: true, photoUrl: URL.createObjectURL( f ) }, pickFrom ) );
	const fileInput = picker( '.pdf,image/*', ( f ) => ask( pickFrom === 'hero' ? prompt.value : '', { file: f.name }, pickFrom ) );
	btnPhoto.addEventListener( 'click', ( e ) => {
		e.preventDefault();
		pickFrom = 'hero';
		photoInput.click();
	} );
	btnAttach.addEventListener( 'click', ( e ) => {
		e.preventDefault();
		pickFrom = 'hero';
		fileInput.click();
	} );

	function listen( field, button ) {
		// The real build uses the browser's own dictation; the prototype simulates it.
		const before = field.placeholder;
		field.placeholder = 'Listening… (simulated dictation)';
		button.classList.add( 'hp-listening' );
		setTimeout( () => {
			field.value = 'Which battery works with the SAJ H2-10K-T3?';
			field.placeholder = before;
			button.classList.remove( 'hp-listening' );
			field.focus();
		}, 1600 );
	}
	btnVoice.addEventListener( 'click', ( e ) => {
		e.preventDefault();
		listen( prompt, btnVoice );
	} );

	// ---------- the surfaces' controls ----------
	document.addEventListener( 'submit', ( e ) => {
		const form = e.target.closest( '[data-hp-form]' );
		if ( ! form ) {
			return;
		}
		e.preventDefault();
		const box = form.querySelector( 'textarea' );
		ask( box.value, {}, form.dataset.hpForm );
	} );
	document.addEventListener( 'keydown', ( e ) => {
		const box = e.target.closest( '[data-hp-form] textarea' );
		if ( box && e.key === 'Enter' && ! e.shiftKey ) {
			e.preventDefault();
			ask( box.value, {}, box.closest( '[data-hp-form]' ).dataset.hpForm );
		}
	} );
	document.addEventListener( 'click', ( e ) => {
		const el = e.target.closest( '[data-hp-ask],[data-hp-new],[data-hp-close-dock],[data-hp-to-dock],[data-hp-fold],[data-hp-close-focus],[data-hp-attach],[data-hp-voice]' );
		if ( ! el ) {
			return;
		}
		e.preventDefault();
		const where = el.closest( '.hp-focus' ) ? 'focus' : el.closest( '.hp-hero-thread' ) ? 'hero' : 'dock';
		const d = el.dataset;
		if ( d.hpAsk ) {
			ask( d.hpAsk, {}, where === 'hero' ? 'hero' : where );
		} else if ( 'hpNew' in d ) {
			thread.length = 0;
			origin = '';
			renderDock();
		} else if ( 'hpCloseDock' in d ) {
			closeDock();
		} else if ( 'hpToDock' in d ) {
			openDock();
		} else if ( 'hpFold' in d ) {
			fold( true );
		} else if ( 'hpCloseFocus' in d ) {
			closeFocus( true );
		} else if ( 'hpAttach' in d ) {
			pickFrom = where;
			fileInput.click();
		} else if ( 'hpVoice' in d ) {
			listen( el.closest( 'form' ).querySelector( 'textarea' ), el );
		}
	} );

	// The site's own launcher opens the prototype dock while the prototype runs.
	window.addEventListener( 'click', ( e ) => {
		if ( ! e.target.closest( '.linker-genie-open' ) ) {
			return;
		}
		e.preventDefault();
		e.stopImmediatePropagation();
		if ( dock.hidden ) {
			openDock();
		} else {
			closeDock();
		}
	}, true );

	// ---------- prototype chrome ----------
	const bar = document.createElement( 'div' );
	bar.className = 'hp-switcher';
	const current = VARIANTS.find( ( v ) => v.key === variant );
	bar.innerHTML = `<button type="button" data-cycle="-1" aria-label="Previous variant">←</button><span><b>${ current.key }</b> · ${ esc( current.name ) }</span><button type="button" data-cycle="1" aria-label="Next variant">→</button>`;
	document.body.appendChild( bar );
	const badge = document.createElement( 'p' );
	badge.className = 'hp-badge';
	badge.textContent = 'PROTOTYPE #231 · 脚本回答，不是真实 Genie · 产品卡来自本站产品数据';
	document.body.appendChild( badge );

	function cycle( step ) {
		const i = VARIANTS.findIndex( ( v ) => v.key === variant );
		params.set( 'variant', VARIANTS[ ( i + step + VARIANTS.length ) % VARIANTS.length ].key );
		location.search = params.toString();
	}
	bar.addEventListener( 'click', ( e ) => {
		const b = e.target.closest( '[data-cycle]' );
		if ( b ) {
			cycle( Number( b.dataset.cycle ) );
		}
	} );
	document.addEventListener( 'keydown', ( e ) => {
		if ( e.key === 'Escape' ) {
			if ( ! focus.hidden ) {
				closeFocus( true );
			} else if ( ! dock.hidden ) {
				closeDock();
			}
			return;
		}
		if ( e.target.closest( 'input, textarea, select, [contenteditable]' ) || e.metaKey || e.ctrlKey || e.altKey ) {
			return;
		}
		if ( e.key === 'ArrowLeft' || e.key === 'ArrowRight' ) {
			cycle( e.key === 'ArrowLeft' ? -1 : 1 );
		}
	} );
}() );
