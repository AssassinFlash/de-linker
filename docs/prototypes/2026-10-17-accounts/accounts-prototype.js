/* PROTOTYPE · map #220 · ticket #226 — throwaway. Sample applicants; nothing is saved. */
( function () {
	'use strict';
	const root = document.getElementById( 'lap-root' );
	if ( ! root ) {
		return;
	}

	const VARIANTS = [
		{ key: 'A', name: '列表 · List table' },
		{ key: 'B', name: '审核台 · Review desk' },
		{ key: 'C', name: '仪表盘 + 顶栏提醒 · Dashboard & top-bar flag' },
	];
	const params = new URLSearchParams( location.search );
	let variant = ( params.get( 'variant' ) || 'A' ).toUpperCase();
	if ( ! VARIANTS.some( ( v ) => v.key === variant ) ) {
		variant = 'A';
	}
	const focusId = Number( params.get( 'focus' ) || 0 );
	let drawerOpen = params.get( 'drawer' ) === '1';

	const MIN = 60e3;
	const H = 60 * MIN;
	const D = 24 * H;
	const now = Date.now();
	const FREEMAIL = [ 'gmail.com', 'gmx.com', 'gmx.de', 'web.de', 'outlook.com', 'hotmail.com', 'yahoo.com', 'qq.com', '163.com', 'icloud.com', 'free-mail.example.test' ]; // Reserved test provider for these fictional examples.

	const accounts = [
		{ id: 41, company: 'Solartechnik Huber GmbH', type: 'Installer', country: 'DE', countryName: 'Germany', contact: 'Markus Huber', email: 'sample41@company41.example.test', vat: 'DE298765431', vies: 'valid', viesName: 'SOLARTECHNIK HUBER GMBH', address: 'Industriestraße 12, 84028 Landshut', registered: now - 2 * H, status: 'pending' },
		{ id: 42, company: 'Instal-Słońce Sp. z o.o.', type: 'Installer', country: 'PL', countryName: 'Poland', contact: 'Piotr Nowak', email: 'sample42@company42.example.test', vat: '', vies: 'none', address: 'ul. Słoneczna 4, 30-001 Kraków', registered: now - 20 * MIN, status: 'pending' },
		{ id: 43, company: 'Zonnepaneel Groothandel B.V.', type: 'Distributor', country: 'NL', countryName: 'Netherlands', contact: 'Jeroen de Vries', email: 'sample43@company43.example.test', vat: 'NL861234567B01', vies: 'unavailable', address: 'Havenweg 88, 3542 AD Utrecht', registered: now - 3 * H, status: 'pending' },
		{ id: 44, company: 'Example What is SEO Services', type: 'EPC contractor', country: 'SE', countryName: 'Sweden', contact: 'Avery Example', email: 'sample44@free-mail.example.test', vat: '', vies: 'none', address: 'Storgatan 1, 111 51 Stockholm', registered: now - 2.4 * D, status: 'pending', example: '虚构可疑申请，仅用于演示' },
		{ id: 37, company: 'Alpen Energie Projekt GmbH', type: 'EPC contractor', country: 'AT', countryName: 'Austria', contact: 'Lisa Gruber', email: 'sample37@company37.example.test', vat: 'ATU71234567', vies: 'valid', viesName: 'ALPEN ENERGIE PROJEKT GMBH', address: 'Bahnhofstraße 5, 6020 Innsbruck', registered: now - 6 * D, status: 'approved', decidedAt: now - 5 * D },
		{ id: 35, company: 'Brightwatt Solar Ltd', type: 'Distributor', country: 'GB', countryName: 'United Kingdom', contact: 'Tom Fletcher', email: 'sample35@company35.example.test', vat: 'GB123456789', vies: 'not-eu', address: '14 Mill Lane, Bristol BS1 4ST', registered: now - 9 * D, status: 'approved', decidedAt: now - 8 * D },
		{ id: 33, company: 'Elektro Schmid e.K.', type: 'Installer', country: 'DE', countryName: 'Germany', contact: 'Anna Schmid', email: 'sample33@company33.example.test', vat: '', vies: 'none', address: 'Marktplatz 3, 72070 Tübingen', registered: now - 12 * D, status: 'restricted', reason: 'Proformas on hold until we receive your trade licence (Gewerbeanmeldung).', decidedAt: now - 11 * D },
		{ id: 31, company: 'Sun Hobby Shop', type: 'Distributor', country: 'DE', countryName: 'Germany', contact: 'Kevin Bauer', email: 'sample31@free-mail.example.test', vat: '', vies: 'none', address: 'Gartenweg 7, 10115 Berlin', registered: now - 15 * D, status: 'rejected', reason: 'We supply trade customers only; your request reads as a private purchase.', decidedAt: now - 14 * D },
	];

	const STATUS = { pending: 'Waiting', approved: 'Approved', restricted: 'Restricted', rejected: 'Rejected' };
	const esc = ( s ) => String( s ?? '' ).replace( /[&<>"']/g, ( c ) => ( { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } )[ c ] );
	const flag = ( cc ) => `<span class="lap-cc">${ cc }</span>`; // a code badge: WordPress swaps flag emoji for images the local instance blocks
	const domainOf = ( a ) => a.email.split( '@' )[ 1 ] || '';
	const isFreemail = ( a ) => FREEMAIL.includes( domainOf( a ) );
	const byId = ( id ) => accounts.find( ( a ) => a.id === id );
	const pendingList = () => accounts.filter( ( a ) => a.status === 'pending' ).sort( ( x, y ) => x.registered - y.registered );

	function ago( t ) {
		const d = Date.now() - t;
		if ( d < H ) {
			return Math.max( 1, Math.round( d / MIN ) ) + ' min ago';
		}
		if ( d < D ) {
			return Math.round( d / H ) + ' h ago';
		}
		return Math.round( d / D ) + ' days ago';
	}

	function signals( a ) {
		const out = [];
		if ( /what is|gsa|seo|https?:|www\./i.test( a.company ) ) {
			out.push( { level: 'bad', text: 'Company name looks like a bot' } );
		}
		out.push( isFreemail( a ) ? { level: 'warn', text: 'Freemail address (' + domainOf( a ) + ')' } : { level: 'ok', text: 'Company domain ' + domainOf( a ) } );
		const vies = {
			valid: [ 'ok', 'VIES valid · ' + ( a.viesName || '' ) ],
			invalid: [ 'bad', 'VIES: number not valid' ],
			unavailable: [ 'warn', 'VIES did not answer — retried hourly' ],
			'not-eu': [ 'info', 'Not an EU VAT ID — check the UK register' ],
			none: [ 'warn', 'No VAT ID given' ],
		}[ a.vies ];
		out.push( { level: vies[ 0 ], text: vies[ 1 ] } );
		return out;
	}

	function lookups( a ) {
		const links = [ { label: 'Google', href: 'https://www.google.com/search?q=' + encodeURIComponent( a.company + ' ' + a.countryName ) } ];
		if ( ! isFreemail( a ) ) {
			links.push( { label: 'Website', href: 'https://' + domainOf( a ) } );
		}
		links.push( { label: 'North Data', href: 'https://www.northdata.com/' + encodeURIComponent( a.company ) } );
		if ( a.vat && a.vies !== 'not-eu' ) {
			links.push( { label: 'VIES', href: 'https://ec.europa.eu/taxation_customs/vies/#/vat-validation' } );
		}
		return links;
	}

	const chip = ( s ) => `<span class="lap-chip lap-chip--${ s.level }">${ esc( s.text ) }</span>`;

	function detailBlock( a ) {
		return `<dl class="lap-dl">
			<dt>Company</dt><dd>${ esc( a.company ) }</dd>
			<dt>Business type</dt><dd>${ esc( a.type ) }</dd>
			<dt>Contact</dt><dd>${ esc( a.contact ) } · <a href="mailto:${ esc( a.email ) }">${ esc( a.email ) }</a></dd>
			<dt>Country</dt><dd>${ flag( a.country ) } ${ esc( a.countryName ) }</dd>
			<dt>Address</dt><dd>${ esc( a.address ) }</dd>
			<dt>VAT ID</dt><dd>${ a.vat ? esc( a.vat ) : '—' }</dd>
			<dt>Registered</dt><dd>${ new Date( a.registered ).toLocaleString( 'de-DE' ) }</dd>
		</dl>`;
	}

	// ----- decisions (in memory only) -----
	let reasonFor = null; // { id, status }
	let toast = null;
	let toastTimer = null;

	function decide( id, status, reason ) {
		const a = byId( id );
		const before = { status: a.status, reason: a.reason, decidedAt: a.decidedAt };
		a.status = status;
		a.reason = reason || '';
		a.decidedAt = Date.now();
		reasonFor = null;
		const verb = { approved: 'Approved', restricted: 'Restricted', rejected: 'Rejected' }[ status ];
		toast = {
			text: `${ verb } · ${ a.company } — email to ${ a.email } is on its way`,
			undo() {
				Object.assign( a, before );
				toast = null;
				render();
			},
		};
		clearTimeout( toastTimer );
		toastTimer = setTimeout( () => {
			toast = null;
			render();
		}, 7000 );
		if ( variant === 'B' ) {
			const next = pendingList()[ 0 ];
			selectedB = next ? next.id : id;
		}
		render();
	}

	function reasonForm( a, status ) {
		const reject = status === 'rejected';
		return `<div class="lap-reason">
			<label>Reason — the customer reads this in the email
				<textarea data-reason rows="3" placeholder="${ reject ? 'e.g. We supply trade customers only.' : 'e.g. Proformas on hold until we receive your trade licence.' }"></textarea>
			</label>
			<button class="button ${ reject ? 'lap-danger-solid' : 'button-primary' }" data-confirm="${ a.id }:${ status }">${ reject ? 'Reject and send email' : 'Restrict and send email' }</button>
			<button class="button-link" data-cancel>Cancel</button>
		</div>`;
	}

	function decidedNote( a ) {
		return `<span class="lap-status lap-status--${ a.status }">${ STATUS[ a.status ] }</span>
			${ a.reason ? `<div class="lap-sub">“${ esc( a.reason ) }”</div>` : '' }
			<div class="lap-sub">${ ago( a.decidedAt ) } · <a href="#" data-reopen="${ a.id }">Change</a></div>`;
	}

	function buttons( a, big ) {
		const cls = big ? ' button-hero' : '';
		return `<div class="lap-actions">
			<button class="button button-primary${ cls }" data-approve="${ a.id }">Approve</button>
			<button class="button${ cls }" data-ask="${ a.id }:restricted">Restrict</button>
			<button class="button${ cls } lap-danger" data-ask="${ a.id }:rejected">Reject</button>
		</div>`;
	}

	// ----- variant A: list table -----
	let filterA = 'pending';
	let searchA = '';
	const openDetails = new Set( focusId ? [ focusId ] : [] );

	function renderA() {
		const pend = pendingList().length;
		const count = ( k ) => ( k === 'all' ? accounts.length : accounts.filter( ( a ) => a.status === k ).length );
		const tabs = [ [ 'pending', 'Waiting' ], [ 'approved', 'Approved' ], [ 'restricted', 'Restricted' ], [ 'rejected', 'Rejected' ], [ 'all', 'All' ] ];
		const rows = accounts.filter( ( a ) => ( filterA === 'all' || a.status === filterA ) && ( ! searchA || ( a.company + ' ' + a.email ).toLowerCase().includes( searchA ) ) );
		return `<h1 class="wp-heading-inline">Accounts</h1>${ pend ? `<span class="lap-pill lap-pill--wait">${ pend } waiting for you</span>` : '<span class="lap-pill lap-pill--done">Nothing waiting</span>' }
			<hr class="wp-header-end">
			<ul class="subsubsub">${ tabs.map( ( [ k, l ], i ) => `<li><a href="#" data-filter="${ k }" class="${ filterA === k ? 'current' : '' }">${ l } <span class="count">(${ count( k ) })</span></a>${ i < tabs.length - 1 ? ' |' : '' }</li>` ).join( '' ) }</ul>
			<p class="search-box"><input type="search" id="lap-search" value="${ esc( searchA ) }" placeholder="Company or email"></p>
			<table class="wp-list-table widefat fixed striped lap-table">
				<thead><tr><th class="lap-col-company">Company</th><th class="lap-col-type">Type</th><th class="lap-col-country">Country</th><th class="lap-col-vat">VAT ID</th><th>Checks</th><th class="lap-col-reg">Registered</th><th class="lap-col-actions">Decision</th></tr></thead>
				<tbody>${ rows.length ? rows.map( rowA ).join( '' ) : '<tr><td colspan="7">Nothing here.</td></tr>' }</tbody>
			</table>`;
	}

	function rowA( a ) {
		const open = openDetails.has( a.id );
		let decision = a.status === 'pending' ? buttons( a, false ) : decidedNote( a );
		if ( reasonFor && reasonFor.id === a.id ) {
			decision = reasonForm( a, reasonFor.status );
		}
		return `<tr class="${ focusId === a.id ? 'lap-focus' : '' }">
				<td><strong>${ esc( a.company ) }</strong>${ a.example ? ` <span class="lap-tag">${ esc( a.example ) }</span>` : '' }
					<div class="lap-sub">${ esc( a.contact ) } · ${ esc( a.email ) }</div>
					<div class="row-actions visible"><a href="#" data-toggle="${ a.id }">${ open ? 'Hide details' : 'Details' }</a> | ${ lookups( a ).map( ( l ) => `<a href="${ l.href }" target="_blank" rel="noopener">${ l.label } ↗</a>` ).join( ' | ' ) }</div></td>
				<td>${ esc( a.type ) }</td>
				<td>${ flag( a.country ) }</td>
				<td>${ a.vat ? `<code>${ esc( a.vat ) }</code>` : '<span class="lap-muted">—</span>' }</td>
				<td>${ signals( a ).map( chip ).join( '' ) }</td>
				<td>${ ago( a.registered ) }</td>
				<td>${ decision }</td>
			</tr>${ open ? `<tr class="lap-detail"><td colspan="7">${ detailBlock( a ) }</td></tr>` : '' }`;
	}

	// ----- variant B: review desk (queue + one applicant at a time) -----
	let selectedB = 0;
	const ticks = {};

	function renderB() {
		const pend = pendingList();
		const done = accounts.filter( ( a ) => a.status !== 'pending' ).sort( ( x, y ) => y.decidedAt - x.decidedAt );
		if ( ! byId( selectedB ) ) {
			selectedB = byId( focusId ) ? focusId : ( pend[ 0 ] || done[ 0 ] ).id;
		}
		return `<h1 class="wp-heading-inline">Accounts</h1><span class="lap-pill ${ pend.length ? 'lap-pill--wait' : 'lap-pill--done' }">${ pend.length ? pend.length + ' to review' : 'All reviewed' }</span>
			<hr class="wp-header-end">
			<div class="lap-desk">
				<aside class="lap-queue">
					<h2>Waiting (${ pend.length })</h2>${ pend.map( qItem ).join( '' ) || '<p class="lap-muted">Nothing waiting.</p>' }
					<h2>Decided recently</h2>${ done.map( qItem ).join( '' ) }
				</aside>
				<section>${ reviewCard( byId( selectedB ) ) }</section>
			</div>`;
	}

	function qItem( a ) {
		const bad = signals( a ).some( ( s ) => s.level === 'bad' );
		const meta = a.status === 'pending' ? 'waiting ' + ago( a.registered ).replace( ' ago', '' ) : STATUS[ a.status ];
		return `<button class="lap-qitem ${ a.id === selectedB ? 'is-current' : '' }" data-select="${ a.id }">
			<span class="lap-qitem__top"><strong>${ esc( a.company ) }</strong>${ bad ? '<span class="lap-dot" title="Bot signal"></span>' : '' }</span>
			<span class="lap-qitem__meta">${ flag( a.country ) } ${ esc( a.type ) } · ${ meta }</span>
		</button>`;
	}

	function reviewCard( a ) {
		const t = ticks[ a.id ] || ( ticks[ a.id ] = { company: false, trade: false, contact: false } );
		const pending = a.status === 'pending';
		let foot = `<p>${ STATUS[ a.status ] } ${ ago( a.decidedAt ) }${ a.reason ? ' — “' + esc( a.reason ) + '”' : '' } · <a href="#" data-reopen="${ a.id }">Change decision</a></p>`;
		if ( pending ) {
			const left = pendingList().length - 1;
			foot = reasonFor && reasonFor.id === a.id
				? reasonForm( a, reasonFor.status )
				: buttons( a, true ) + `<span class="lap-hint">${ left > 0 ? left + ' more after this one' : 'Last one waiting' } · keys: A approve · R reject · J / K next / previous</span>`;
		}
		return `<div class="lap-card">
			<header class="lap-card__head">
				<div><h2>${ esc( a.company ) }${ a.example ? ` <span class="lap-tag">${ esc( a.example ) }</span>` : '' }</h2>
				<p>${ flag( a.country ) } ${ esc( a.countryName ) } · ${ esc( a.type ) } · registered ${ ago( a.registered ) }</p></div>
				<span class="lap-status lap-status--${ a.status }">${ STATUS[ a.status ] }</span>
			</header>
			<div class="lap-card__cols">
				<div><h3>What they told us</h3>${ detailBlock( a ) }</div>
				<div>
					<h3>Automatic checks</h3>
					<ul class="lap-checks">${ signals( a ).map( ( s ) => `<li class="lap-check lap-check--${ s.level }">${ esc( s.text ) }</li>` ).join( '' ) }</ul>
					<h3>Look it up</h3>
					<p class="lap-links">${ lookups( a ).map( ( l ) => `<a class="button button-small" href="${ l.href }" target="_blank" rel="noopener">${ l.label } ↗</a>` ).join( ' ' ) }</p>
					${ pending ? `<h3>Your check</h3>
					<label class="lap-tick"><input type="checkbox" data-tick="${ a.id }:company" ${ t.company ? 'checked' : '' }> The company exists</label>
					<label class="lap-tick"><input type="checkbox" data-tick="${ a.id }:trade" ${ t.trade ? 'checked' : '' }> It is a trade business (installer, EPC, distributor)</label>
					<label class="lap-tick"><input type="checkbox" data-tick="${ a.id }:contact" ${ t.contact ? 'checked' : '' }> The contact person belongs to it</label>` : '' }
				</div>
			</div>
			<footer class="lap-card__foot">${ foot }</footer>
		</div>`;
	}

	// ----- variant C: dashboard widget + top-bar flag + drawer -----
	const openC = new Set();

	function renderC() {
		const pend = pendingList();
		return `<h1>Dashboard</h1>
			<div class="lap-widget">
				<div class="lap-widget__head"><h2>Accounts waiting for you <span class="lap-badge">${ pend.length }</span></h2><a href="#" data-goto="A">All accounts →</a></div>
				${ pend.length ? `<div class="lap-cards">${ pend.map( cardC ).join( '' ) }</div>` : '<p class="lap-muted">Nothing waiting. New registrations show up here and as a red flag in the top bar.</p>' }
			</div>
			<div class="lap-fake-widgets"><div class="lap-fake">At a glance</div><div class="lap-fake">Activity</div></div>
			${ drawerOpen ? `<div class="lap-drawer-mask" data-close-drawer></div><aside class="lap-drawer"><header><h2>${ pend.length } accounts to review</h2><button class="button-link" data-close-drawer>Close</button></header>${ pend.map( cardC ).join( '' ) }</aside>` : '' }`;
	}

	function cardC( a ) {
		const open = openC.has( a.id );
		return `<div class="lap-c ${ focusId === a.id ? 'lap-focus-card' : '' }">
			<h3>${ esc( a.company ) }</h3>
			${ a.example ? `<span class="lap-tag">${ esc( a.example ) }</span>` : '' }
			<div class="lap-sub">${ flag( a.country ) } ${ esc( a.countryName ) } · ${ esc( a.type ) } · ${ ago( a.registered ) }</div>
			<div class="lap-sub">${ esc( a.contact ) } · ${ esc( a.email ) }</div>
			<div>${ signals( a ).map( chip ).join( '' ) }</div>
			<div class="lap-sub"><a href="#" data-togglec="${ a.id }">${ open ? 'Hide details' : 'Details' }</a> · ${ lookups( a ).map( ( l ) => `<a href="${ l.href }" target="_blank" rel="noopener">${ l.label } ↗</a>` ).join( ' · ' ) }</div>
			${ open ? detailBlock( a ) : '' }
			${ reasonFor && reasonFor.id === a.id ? reasonForm( a, reasonFor.status ) : buttons( a, false ) }
		</div>`;
	}

	// ----- shell -----
	function switcherBar() {
		const v = VARIANTS.find( ( x ) => x.key === variant );
		return `<div class="lap-switcher" role="toolbar" aria-label="Prototype variants">
			<button type="button" data-cycle="-1" aria-label="Previous variant">←</button>
			<span><b>${ v.key }</b> · ${ esc( v.name ) }</span>
			<button type="button" data-cycle="1" aria-label="Next variant">→</button>
		</div>`;
	}

	function syncChrome() {
		const pend = pendingList().length;
		const menuBadge = document.querySelector( '#toplevel_page_linker-accounts-prototype .awaiting-mod' );
		if ( menuBadge ) {
			menuBadge.textContent = String( pend );
			menuBadge.style.display = pend ? '' : 'none';
		}
		const flagNode = document.querySelector( '#wp-admin-bar-linker-accounts-flag .lap-flag' );
		if ( flagNode ) {
			flagNode.textContent = pend ? pend + ' accounts to review' : 'Accounts: all reviewed';
		}
		document.body.classList.toggle( 'lap-variant-C', variant === 'C' );
	}

	function render() {
		const active = document.activeElement && document.activeElement.id === 'lap-search';
		const body = { A: renderA, B: renderB, C: renderC }[ variant ]();
		root.innerHTML = `<div class="lap-banner">PROTOTYPE · 账户页 #226 · 示例数据，按钮不写数据库 · 字段沿用现在的注册表单（注册字段研究定稿后同步） · 通知邮件的链接带 <code>&amp;focus=&lt;用户ID&gt;</code> 直达该申请</div>
			${ body }
			${ switcherBar() }
			${ toast ? `<div class="lap-toast">${ esc( toast.text ) } <button type="button" data-undo>Undo</button></div>` : '' }`;
		syncChrome();
		if ( active ) {
			const input = document.getElementById( 'lap-search' );
			input.focus();
			input.setSelectionRange( input.value.length, input.value.length );
		}
	}

	function setVariant( key ) {
		variant = key;
		reasonFor = null;
		params.set( 'variant', key );
		params.delete( 'drawer' );
		drawerOpen = false;
		history.replaceState( null, '', location.pathname + '?' + params.toString() );
		render();
	}

	function cycle( step ) {
		const i = VARIANTS.findIndex( ( v ) => v.key === variant );
		setVariant( VARIANTS[ ( i + step + VARIANTS.length ) % VARIANTS.length ].key );
	}

	root.addEventListener( 'click', ( event ) => {
		const el = event.target.closest( '[data-filter],[data-toggle],[data-togglec],[data-approve],[data-ask],[data-confirm],[data-cancel],[data-reopen],[data-select],[data-goto],[data-close-drawer],[data-cycle],[data-undo]' );
		if ( ! el ) {
			return;
		}
		const d = el.dataset;
		if ( el.tagName === 'A' || el.tagName === 'BUTTON' ) {
			event.preventDefault();
		}
		if ( d.filter ) {
			filterA = d.filter;
		} else if ( d.toggle ) {
			const id = Number( d.toggle );
			openDetails.has( id ) ? openDetails.delete( id ) : openDetails.add( id );
		} else if ( d.togglec ) {
			const id = Number( d.togglec );
			openC.has( id ) ? openC.delete( id ) : openC.add( id );
		} else if ( d.approve ) {
			decide( Number( d.approve ), 'approved' );
			return;
		} else if ( d.ask ) {
			const [ id, status ] = d.ask.split( ':' );
			reasonFor = { id: Number( id ), status };
			render();
			const box = root.querySelector( '[data-reason]' );
			if ( box ) {
				box.focus();
			}
			return;
		} else if ( d.confirm ) {
			const [ id, status ] = d.confirm.split( ':' );
			const box = root.querySelector( '[data-reason]' );
			const reason = box ? box.value.trim() : '';
			if ( ! reason ) {
				box.classList.add( 'lap-required' );
				box.placeholder = 'A reason is required — the customer reads it.';
				box.focus();
				return;
			}
			decide( Number( id ), status, reason );
			return;
		} else if ( 'cancel' in d ) {
			reasonFor = null;
		} else if ( d.reopen ) {
			const a = byId( Number( d.reopen ) );
			a.status = 'pending';
			a.reason = '';
			if ( variant === 'B' ) {
				selectedB = a.id;
			}
			if ( variant === 'A' ) {
				filterA = 'pending';
			}
		} else if ( d.select ) {
			selectedB = Number( d.select );
			reasonFor = null;
		} else if ( d.goto ) {
			setVariant( d.goto );
			return;
		} else if ( 'closeDrawer' in d ) {
			drawerOpen = false;
		} else if ( d.cycle ) {
			cycle( Number( d.cycle ) );
			return;
		} else if ( 'undo' in d && toast ) {
			toast.undo();
			return;
		}
		render();
	} );

	root.addEventListener( 'change', ( event ) => {
		const box = event.target.closest( '[data-tick]' );
		if ( box ) {
			const [ id, key ] = box.dataset.tick.split( ':' );
			ticks[ Number( id ) ][ key ] = box.checked;
		}
	} );

	root.addEventListener( 'input', ( event ) => {
		if ( event.target.id === 'lap-search' ) {
			searchA = event.target.value.trim().toLowerCase();
			filterA = searchA ? 'all' : filterA;
			render();
		}
	} );

	document.addEventListener( 'keydown', ( event ) => {
		const typing = event.target.closest( 'input, textarea, select, [contenteditable]' );
		if ( typing || event.metaKey || event.ctrlKey || event.altKey ) {
			return;
		}
		if ( event.key === 'ArrowLeft' || event.key === 'ArrowRight' ) {
			cycle( event.key === 'ArrowLeft' ? -1 : 1 );
			return;
		}
		if ( variant !== 'B' ) {
			return;
		}
		const list = [ ...pendingList(), ...accounts.filter( ( a ) => a.status !== 'pending' ) ];
		const i = list.findIndex( ( a ) => a.id === selectedB );
		const a = byId( selectedB );
		if ( event.key === 'j' || event.key === 'k' ) {
			selectedB = list[ Math.min( list.length - 1, Math.max( 0, i + ( event.key === 'j' ? 1 : -1 ) ) ) ].id;
			reasonFor = null;
			render();
		} else if ( event.key === 'a' && a && a.status === 'pending' ) {
			decide( a.id, 'approved' );
		} else if ( event.key === 'r' && a && a.status === 'pending' ) {
			reasonFor = { id: a.id, status: 'rejected' };
			render();
			const box = root.querySelector( '[data-reason]' );
			if ( box ) {
				box.focus();
			}
		}
	} );

	// The top-bar flag opens the drawer in place (variant C) instead of reloading.
	const flagLink = document.querySelector( '#wp-admin-bar-linker-accounts-flag > a' );
	if ( flagLink ) {
		flagLink.addEventListener( 'click', ( event ) => {
			event.preventDefault();
			if ( variant !== 'C' ) {
				setVariant( 'C' );
			}
			drawerOpen = true;
			render();
		} );
	}

	render();
}() );
