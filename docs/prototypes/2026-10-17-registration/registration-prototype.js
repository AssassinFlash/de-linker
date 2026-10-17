/* PROTOTYPE · map #220 · ticket #225 — throwaway. Nothing is submitted; the debug box shows what would be sent. */
( function () {
	'use strict';
	const DATA = window.LINKER_REG_PROTO || { countries: {}, europe: [], logo: '' };
	const params = new URLSearchParams( location.search );
	const VARIANTS = [
		{ key: 'A', name: '单页 · 两组（研究推荐）' },
		{ key: 'B', name: '两步 · 先公司，后您和登录' },
		{ key: 'C', name: '单页 · 先您和登录，后公司' },
	];
	let v = ( params.get( 'reg' ) || 'A' ).toUpperCase();
	if ( ! VARIANTS.some( ( x ) => x.key === v ) ) {
		v = 'A';
	}
	const MIN_SECONDS = 3; // placeholder; the real threshold comes from logged fill times after launch (#224)
	const opened = Date.now();
	const esc = ( s ) => String( s ?? '' ).replace( /[&<>"']/g, ( c ) => ( { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } )[ c ] );
	const decode = ( s ) => {
		const t = document.createElement( 'textarea' );
		t.innerHTML = s;
		return t.value;
	};

	// Countries: Germany first, then the rest of Europe, then everyone else (Woo's own list and continents).
	const all = Object.entries( DATA.countries ).map( ( [ code, name ] ) => ( { code, name: decode( name ) } ) );
	const eu = new Set( DATA.europe );
	const byName = ( a, b ) => a.name.localeCompare( b.name );
	const groups = [
		{ label: 'Europe', items: all.filter( ( c ) => eu.has( c.code ) ).sort( ( a, b ) => ( b.code === 'DE' ) - ( a.code === 'DE' ) || byName( a, b ) ) },
		{ label: 'Other countries', items: all.filter( ( c ) => ! eu.has( c.code ) ).sort( byName ) },
	];
	const nameOf = ( code ) => ( all.find( ( c ) => c.code === code ) || {} ).name || '';

	const host = document.querySelector( 'main' ) || document.querySelector( '#content' );
	if ( ! host ) {
		return;
	}

	const req = '<span class="req" aria-hidden="true">*</span>';
	const opt = '<span class="opt">(optional)</span>';
	const field = ( id, label, attrs, help ) => `<div class="rgp-f"><label class="rgp-l" for="rgp-${ id }">${ label }</label><input class="rgp-i" id="rgp-${ id }" name="${ id }" ${ attrs }>${ help ? `<p class="rgp-help">${ help }</p>` : '' }<p class="rgp-err" data-err="${ id }" hidden></p></div>`;

	const company = `
		<section class="rgp-group">
			<h2 class="rgp-gh">Your company</h2>
			${ field( 'billing_company', `Company name${ req }`, 'type="text" autocomplete="organization" required' ) }
			<div class="rgp-f" role="radiogroup" aria-labelledby="rgp-type-l">
				<span class="rgp-l" id="rgp-type-l">Business type${ req }</span>
				<div class="rgp-types">
					<label class="rgp-type"><input type="radio" name="linker_customer_role" value="installer">Installer</label>
					<label class="rgp-type"><input type="radio" name="linker_customer_role" value="epc">EPC contractor</label>
					<label class="rgp-type"><input type="radio" name="linker_customer_role" value="distributor">Distributor</label>
				</div>
				<p class="rgp-err" data-err="linker_customer_role" hidden></p>
			</div>
			<div class="rgp-f">
				<label class="rgp-l" for="rgp-country">Country${ req }</label>
				<div class="rgp-cbox">
					<input class="rgp-i" id="rgp-country" role="combobox" aria-expanded="false" aria-controls="rgp-list" autocomplete="off" value="Germany" data-code="DE">
					<div class="rgp-list" id="rgp-list" role="listbox" hidden></div>
				</div>
				<p class="rgp-err" data-err="billing_country" hidden></p>
			</div>
			<div class="rgp-oneof">
				<p class="rgp-gnote">We use one of these to verify your company. Fill in at least one.</p>
				${ field( 'linker_website', 'Company website', 'type="url" inputmode="url" autocomplete="url" placeholder="example.com"' ) }
				${ field( 'billing_vat_id', 'VAT ID', 'type="text" autocomplete="off" placeholder="DE123456789"', 'We check EU VAT IDs in the European Commission’s VIES system.' ) }
				<p class="rgp-err" data-err="oneof" hidden></p>
			</div>
		</section>`;

	const you = `
		<section class="rgp-group">
			<h2 class="rgp-gh">You and your sign-in</h2>
			<div class="rgp-two">
				${ field( 'billing_first_name', `First name${ req }`, 'type="text" autocomplete="given-name" required' ) }
				${ field( 'billing_last_name', `Last name${ req }`, 'type="text" autocomplete="family-name" required' ) }
			</div>
			${ field( 'email', `Email address${ req }`, 'type="email" autocomplete="email" required', 'You sign in with it, and we send the approval here.' ) }
			<div class="rgp-f">
				<label class="rgp-l" for="rgp-password">Password${ req }</label>
				<div class="rgp-pw"><input class="rgp-i" id="rgp-password" name="password" type="password" autocomplete="new-password" required><button type="button" data-eye>Show</button></div>
				<p class="rgp-help">Use at least 8 characters with a mix of letters, numbers and symbols.</p>
				<p class="rgp-err" data-err="password" hidden></p>
			</div>
		</section>`;

	const honeypot = '<div class="rgp-hp" aria-hidden="true"><label>Leave this empty<input type="text" name="linker_hp" tabindex="-1" autocomplete="off"></label></div>';
	const footer = `
		<p class="rgp-terms">By registering you accept our <a href="/terms-of-sale/">Terms of Sale</a>.</p>
		<button type="submit" class="rgp-btn">Register</button>
		<p class="rgp-signin">Already have a partner account? <a href="/my-account/">Sign in</a></p>
		<div class="rgp-debug" data-debug>Bot check: waiting for submit.</div>`;

	let body;
	if ( v === 'A' ) {
		body = company + you + honeypot + footer;
	} else if ( v === 'C' ) {
		body = you + company + honeypot + footer;
	} else {
		body = `<div class="rgp-steps"><span class="on"></span><span data-step2></span></div><p class="rgp-stepnote" data-stepnote>Step 1 of 2 · Your company</p>
			<div data-pane="1">${ company }<button type="button" class="rgp-btn" data-next>Continue</button><p class="rgp-signin">Already have a partner account? <a href="/my-account/">Sign in</a></p></div>
			<div data-pane="2" hidden>${ you }${ honeypot }${ footer }<button type="button" class="rgp-btn rgp-btn--ghost" data-back>Back</button></div>`;
	}

	host.innerHTML = `<div class="rgp"><div class="rgp-card">
		<aside class="rgp-side">
			${ DATA.logo ? `<img src="${ esc( DATA.logo ) }" alt="Linker">` : '' }
			<h2>Create your partner account</h2>
			<p>For installers, EPCs and distributors: net prices, documents and inquiries in one workspace.</p>
			<ul><li>You see net prices on every product after approval</li><li>We answer inquiries within one working day</li><li>We run the VAT ID check in VIES for you</li></ul>
		</aside>
		<div class="rgp-main">
			<h1 class="rgp-h1">Create your business account</h1>
			<p class="rgp-lead">We review every new account before activation.</p>
			<form novalidate data-form>${ body }</form>
		</div>
	</div></div>`;

	const form = host.querySelector( '[data-form]' );
	const $ = ( sel ) => form.querySelector( sel );

	// Country combobox: type to filter, Europe first, keyboard support.
	const cin = $( '#rgp-country' );
	const list = $( '#rgp-list' );
	let active = -1;
	function renderList( q ) {
		const needle = q.trim().toLowerCase();
		const html = [];
		let n = 0;
		for ( const g of groups ) {
			const items = g.items.filter( ( c ) => ! needle || c.name.toLowerCase().includes( needle ) || c.code.toLowerCase() === needle );
			if ( ! items.length ) {
				continue;
			}
			html.push( `<div class="grp">${ g.label }</div>` );
			for ( const c of items ) {
				html.push( `<div class="opt" role="option" data-code="${ c.code }" data-i="${ n++ }" aria-selected="false">${ esc( c.name ) }</div>` );
			}
		}
		list.innerHTML = html.length ? html.join( '' ) : '<div class="none">No country matches.</div>';
		active = -1;
	}
	function openList() {
		renderList( cin.dataset.code ? '' : cin.value );
		list.hidden = false;
		cin.setAttribute( 'aria-expanded', 'true' );
	}
	function closeList() {
		list.hidden = true;
		cin.setAttribute( 'aria-expanded', 'false' );
		if ( ! cin.dataset.code ) {
			cin.value = '';
		}
	}
	function pick( code ) {
		cin.value = nameOf( code );
		cin.dataset.code = code;
		closeList();
	}
	cin.addEventListener( 'focus', () => {
		cin.select();
		openList();
	} );
	cin.addEventListener( 'input', () => {
		delete cin.dataset.code;
		renderList( cin.value );
		list.hidden = false;
	} );
	cin.addEventListener( 'keydown', ( e ) => {
		const opts = [ ...list.querySelectorAll( '.opt' ) ];
		if ( e.key === 'ArrowDown' || e.key === 'ArrowUp' ) {
			e.preventDefault();
			active = Math.max( 0, Math.min( opts.length - 1, active + ( e.key === 'ArrowDown' ? 1 : -1 ) ) );
			opts.forEach( ( o, i ) => o.setAttribute( 'aria-selected', String( i === active ) ) );
			opts[ active ]?.scrollIntoView( { block: 'nearest' } );
		} else if ( e.key === 'Enter' ) {
			e.preventDefault();
			const o = opts[ Math.max( 0, active ) ];
			if ( o ) {
				pick( o.dataset.code );
			}
		} else if ( e.key === 'Escape' ) {
			closeList();
		}
	} );
	list.addEventListener( 'mousedown', ( e ) => {
		const o = e.target.closest( '.opt' );
		if ( o ) {
			e.preventDefault();
			pick( o.dataset.code );
		}
	} );
	cin.addEventListener( 'blur', () => setTimeout( closeList, 120 ) );

	form.addEventListener( 'click', ( e ) => {
		if ( e.target.closest( '[data-eye]' ) ) {
			const pw = $( '#rgp-password' );
			pw.type = pw.type === 'password' ? 'text' : 'password';
			e.target.textContent = pw.type === 'password' ? 'Show' : 'Hide';
		}
		if ( e.target.closest( '[data-next]' ) ) {
			if ( validate( 1 ) ) {
				$( '[data-pane="1"]' ).hidden = true;
				$( '[data-pane="2"]' ).hidden = false;
				$( '[data-step2]' ).classList.add( 'on' );
				$( '[data-stepnote]' ).textContent = 'Step 2 of 2 · You and your sign-in';
				$( '#rgp-billing_first_name' ).focus();
			}
		}
		if ( e.target.closest( '[data-back]' ) ) {
			$( '[data-pane="1"]' ).hidden = false;
			$( '[data-pane="2"]' ).hidden = true;
			$( '[data-step2]' ).classList.remove( 'on' );
			$( '[data-stepnote]' ).textContent = 'Step 1 of 2 · Your company';
		}
	} );

	function setErr( key, msg, input ) {
		const p = form.querySelector( `[data-err="${ key }"]` );
		if ( p ) {
			p.textContent = msg || '';
			p.hidden = ! msg;
		}
		if ( input ) {
			input.classList.toggle( 'is-bad', !! msg );
		}
		return ! msg;
	}
	const val = ( name ) => ( form.querySelector( `[name="${ name }"]` )?.value || '' ).trim();

	// An error clears as soon as the customer edits that field.
	const clearOn = ( e ) => {
		const name = e.target.name || ( e.target === cin ? 'billing_country' : '' );
		const key = name === 'linker_website' || name === 'billing_vat_id' ? 'oneof' : name;
		setErr( key, '', e.target.classList.contains( 'rgp-i' ) ? e.target : null );
		if ( key === 'oneof' ) {
			setErr( 'linker_website', '', $( '#rgp-linker_website' ) );
			$( '#rgp-billing_vat_id' ).classList.remove( 'is-bad' );
		}
	};
	form.addEventListener( 'input', clearOn );
	form.addEventListener( 'change', clearOn );

	function validate( part ) {
		let ok = true;
		if ( part !== 2 ) {
			ok = setErr( 'billing_company', val( 'billing_company' ) ? '' : 'Enter your company name.', $( '#rgp-billing_company' ) ) && ok;
			ok = setErr( 'linker_customer_role', form.querySelector( '[name="linker_customer_role"]:checked' ) ? '' : 'Choose your business type.' ) && ok;
			ok = setErr( 'billing_country', cin.dataset.code ? '' : 'Choose your country.', cin ) && ok;
			const site = val( 'linker_website' );
			const vat = val( 'billing_vat_id' );
			const oneOk = site || vat;
			ok = setErr( 'oneof', oneOk ? '' : 'Enter your company website or VAT ID, so we can verify your company.' ) && ok;
			$( '#rgp-linker_website' ).classList.toggle( 'is-bad', ! oneOk );
			$( '#rgp-billing_vat_id' ).classList.toggle( 'is-bad', ! oneOk );
			if ( site && ! /^(https?:\/\/)?[^\s.]+\.[^\s]{2,}$/i.test( site ) ) {
				ok = setErr( 'linker_website', 'Enter a web address such as example.com.', $( '#rgp-linker_website' ) ) && ok;
			} else {
				setErr( 'linker_website', '', site ? $( '#rgp-linker_website' ) : null );
			}
		}
		if ( part !== 1 ) {
			ok = setErr( 'billing_first_name', val( 'billing_first_name' ) ? '' : 'Enter your first name.', $( '#rgp-billing_first_name' ) ) && ok;
			ok = setErr( 'billing_last_name', val( 'billing_last_name' ) ? '' : 'Enter your last name.', $( '#rgp-billing_last_name' ) ) && ok;
			ok = setErr( 'email', /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test( val( 'email' ) ) ? '' : 'Enter a valid email address.', $( '#rgp-email' ) ) && ok;
			ok = setErr( 'password', val( 'password' ).length >= 8 ? '' : 'Use at least 8 characters.', $( '#rgp-password' ) ) && ok;
		}
		if ( ! ok ) {
			form.querySelector( '.is-bad, .rgp-err:not([hidden])' )?.scrollIntoView( { block: 'center', behavior: 'smooth' } );
		}
		return ok;
	}

	form.addEventListener( 'submit', ( e ) => {
		e.preventDefault();
		const secs = ( Date.now() - opened ) / 1000;
		const hp = val( 'linker_hp' );
		const bot = hp !== '' || secs < MIN_SECONDS;
		const debug = form.querySelector( '[data-debug]' );
		if ( ! validate( 0 ) ) {
			debug.textContent = 'Validation failed; nothing would be sent.';
			return;
		}
		const sent = {
			billing_company: val( 'billing_company' ),
			linker_customer_role: form.querySelector( '[name="linker_customer_role"]:checked' ).value,
			billing_country: cin.dataset.code,
			linker_website: val( 'linker_website' ),
			billing_vat_id: val( 'billing_vat_id' ),
			billing_first_name: val( 'billing_first_name' ),
			billing_last_name: val( 'billing_last_name' ),
			email: val( 'email' ),
		};
		if ( bot ) {
			debug.innerHTML = `Bot check: <b>blocked</b> (honeypot ${ hp ? 'filled' : 'empty' }, ${ secs.toFixed( 1 ) } s, minimum ${ MIN_SECONDS } s). No account, no email; the block is counted.`;
			return;
		}
		form.closest( '.rgp-main' ).innerHTML = `<div class="rgp-done"><div class="tick">✓</div>
			<h1 class="rgp-h1">Thank you, we are checking your company</h1>
			<p>We review every new account by hand. As soon as yours is approved, we email <b>${ esc( sent.email ) }</b> and you can sign in.</p>
			<p>Until then you can browse products and send inquiries as a guest.</p>
			<a class="rgp-btn rgp-btn--ghost" style="display:block;max-width:320px;margin:24px auto 0;line-height:49px;text-decoration:none" href="/products/">Browse products</a>
			<div class="rgp-debug" style="text-align:left">Bot check: passed (honeypot empty, ${ secs.toFixed( 1 ) } s).<br>Would be saved: ${ esc( JSON.stringify( sent ) ) } + password.<br>Street, postcode, city and phone are not asked here; the Proforma request page collects them.</div></div>`;
	} );

	// Variant switcher, as in the other #220 prototypes.
	const bar = document.createElement( 'div' );
	bar.className = 'rgp-switcher';
	const cur = VARIANTS.find( ( x ) => x.key === v );
	bar.innerHTML = `<button type="button" data-c="-1">←</button><span><b>${ cur.key }</b> · ${ esc( cur.name ) }</span><button type="button" data-c="1">→</button><button type="button" data-bot title="Fill the honeypot like a bot would">Bot</button>`;
	document.body.appendChild( bar );
	bar.addEventListener( 'click', ( e ) => {
		const b = e.target.closest( '[data-c]' );
		if ( b ) {
			const i = VARIANTS.findIndex( ( x ) => x.key === v );
			params.set( 'reg', VARIANTS[ ( i + Number( b.dataset.c ) + 3 ) % 3 ].key );
			location.search = params.toString();
		}
		if ( e.target.closest( '[data-bot]' ) ) {
			const hp = form.querySelector( '[name="linker_hp"]' );
			if ( hp ) {
				hp.value = 'http://spam.example';
				e.target.textContent = 'Bot ✓';
			}
		}
	} );
	document.addEventListener( 'keydown', ( e ) => {
		if ( ! e.target.closest( 'input, textarea' ) && ( e.key === 'ArrowLeft' || e.key === 'ArrowRight' ) ) {
			bar.querySelector( `[data-c="${ e.key === 'ArrowLeft' ? -1 : 1 }"]` ).click();
		}
	} );
}() );
