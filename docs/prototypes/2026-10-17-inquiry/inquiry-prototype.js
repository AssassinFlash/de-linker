/* PROTOTYPE · map #220 · inquiry open to everyone — throwaway. Sending does nothing. */
( async function () {
	'use strict';
	const params = new URLSearchParams( location.search );
	const VARIANTS = [
		{ key: 'A', name: '访客 · 单卡（联系表单的样子）' },
		{ key: 'B', name: '访客 · 左表单右草稿' },
		{ key: 'C', name: '已登录 · 资料已知，一键发送' },
	];
	let v = ( params.get( 'iq' ) || 'A' ).toUpperCase();
	if ( ! VARIANTS.some( ( x ) => x.key === v ) ) {
		v = 'A';
	}
	const esc = ( s ) => String( s ?? '' ).replace( /[&<>"']/g, ( c ) => ( { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } )[ c ] );
	const decode = ( s ) => {
		const t = document.createElement( 'textarea' );
		t.innerHTML = s;
		return t.value;
	};

	let items = [];
	try {
		const cart = await ( await fetch( '/wp-json/wc/store/v1/cart', { credentials: 'include' } ) ).json();
		items = ( cart.items || [] ).map( ( i ) => ( { name: decode( i.name ), qty: i.quantity, img: i.images && i.images[ 0 ] ? i.images[ 0 ].thumbnail : '' } ) );
	} catch ( e ) {}

	const host = document.querySelector( 'main .woocommerce' ) || document.querySelector( 'main' );
	if ( ! host ) {
		return;
	}

	const draft = items.length
		? `<ul class="iqp-items">${ items.map( ( i ) => `<li>${ i.img ? `<img src="${ esc( i.img ) }" alt="">` : '<span class="iqp-noimg"></span>' }<span class="iqp-name">${ esc( i.name ) }</span><span class="iqp-qty">× ${ i.qty }</span></li>` ).join( '' ) }</ul>
			<p class="iqp-price">Prices: quoted in your Proforma${ v === 'C' ? '' : ' — partners see net prices after sign-in' }.</p>`
		: '<p class="iqp-empty">Your solution draft is empty — that is fine. Tell us what you need in the message.</p>';

	const guestFields = `
		<label class="iqp-label">Your message <span>optional</span><textarea rows="4" placeholder="Project, quantities, delivery, any question — anything you want us to know."></textarea></label>
		<div class="iqp-two">
			<label class="iqp-label">Name<input type="text" autocomplete="name"></label>
			<label class="iqp-label">Reply email<input type="email" autocomplete="email"></label>
		</div>
		<label class="iqp-label">Company <span>optional</span><input type="text" autocomplete="organization"></label>
		<label class="iqp-check"><input type="checkbox"> I agree that my details may be used to respond to this inquiry.</label>`;

	const send = `<button type="button" class="iqp-send" data-send>Send inquiry ↗</button>
		<p class="iqp-note">No account needed. We reply within one working day.</p>`;

	let html;
	if ( v === 'A' ) {
		html = `<section class="iqp-card iqp-card--narrow">
			<p class="iqp-eyebrow">PROFORMA REQUEST</p>
			<h1 class="iqp-h1">Send us your inquiry</h1>
			<p class="iqp-lead">We prepare your Proforma and reply to the email below.</p>
			<h2 class="iqp-h2">Your solution draft</h2>${ draft }
			<h2 class="iqp-h2">Where can we reply?</h2>${ guestFields }${ send }
			<p class="iqp-signin">Already a partner? <a href="/my-account/">Sign in</a> to see net prices and have this filled in.</p>
		</section>`;
	} else if ( v === 'B' ) {
		html = `<div class="iqp-grid">
			<section class="iqp-card">
				<p class="iqp-eyebrow">PROFORMA REQUEST</p>
				<h1 class="iqp-h1">Send us your inquiry</h1>
				<p class="iqp-lead">We prepare your Proforma and reply to the email below.</p>
				${ guestFields }${ send }
				<p class="iqp-signin">Already a partner? <a href="/my-account/">Sign in</a> to see net prices and have this filled in.</p>
			</section>
			<aside class="iqp-card iqp-card--side"><h2 class="iqp-h2">Your solution draft</h2>${ draft }<a class="iqp-edit" href="/cart/">Edit the draft</a></aside>
		</div>`;
	} else {
		html = `<section class="iqp-card iqp-card--narrow">
			<p class="iqp-eyebrow">PROFORMA REQUEST</p>
			<h1 class="iqp-h1">Send your inquiry</h1>
			<h2 class="iqp-h2">Your solution draft</h2>${ draft }
			<div class="iqp-known"><div><strong>Example Company 18</strong><br>Customer 18 · customer-18@example.test<br>Musterstraße 1, 12345 Musterstadt, Germany</div><button type="button" class="iqp-link" data-edit>Change</button></div>
			<div class="iqp-more" hidden>The billing fields WooCommerce already has (name, company, VAT ID, address, phone) open here, filled in.</div>
			<label class="iqp-label">Your message <span>optional</span><textarea rows="3" placeholder="Project name, delivery wishes, questions."></textarea></label>
			<button type="button" class="iqp-send" data-send>Send inquiry ↗</button>
			<p class="iqp-note">We reply within one working day. You can follow this inquiry in your account.</p>
		</section>`;
	}
	host.innerHTML = `<div class="iqp">${ html }</div>`;

	host.addEventListener( 'click', ( e ) => {
		if ( e.target.closest( '[data-send]' ) ) {
			host.querySelector( '.iqp' ).innerHTML = `<section class="iqp-card iqp-card--narrow iqp-done"><p class="iqp-eyebrow">INQUIRY #1618 RECEIVED</p><h1 class="iqp-h1">Thank you — we have your inquiry.</h1>
				<p class="iqp-lead">A copy is on its way to your email. We reply within one working day.</p>
				${ v === 'C' ? '<p class="iqp-lead">Follow it under <a href="/my-account/">My account → Inquiries</a>.</p>' : '<div class="iqp-offer"><strong>Create an account with this email</strong><p>See net prices once we approve it, and follow this inquiry. One step — we use what you already typed.</p><button type="button" class="iqp-send iqp-send--ghost">Create my account</button></div>' }</section>`;
		}
		if ( e.target.closest( '[data-edit]' ) ) {
			host.querySelector( '.iqp-more' ).hidden = false;
		}
	} );

	const bar = document.createElement( 'div' );
	bar.className = 'iqp-switcher';
	const cur = VARIANTS.find( ( x ) => x.key === v );
	bar.innerHTML = `<button type="button" data-c="-1">←</button><span><b>${ cur.key }</b> · ${ esc( cur.name ) }</span><button type="button" data-c="1">→</button>`;
	document.body.appendChild( bar );
	bar.addEventListener( 'click', ( e ) => {
		const b = e.target.closest( '[data-c]' );
		if ( b ) {
			const i = VARIANTS.findIndex( ( x ) => x.key === v );
			params.set( 'iq', VARIANTS[ ( i + Number( b.dataset.c ) + 3 ) % 3 ].key );
			location.search = params.toString();
		}
	} );
	document.addEventListener( 'keydown', ( e ) => {
		if ( ! e.target.closest( 'input, textarea' ) && ( e.key === 'ArrowLeft' || e.key === 'ArrowRight' ) ) {
			bar.querySelector( `[data-c="${ e.key === 'ArrowLeft' ? -1 : 1 }"]` ).click();
		}
	} );
}() );
