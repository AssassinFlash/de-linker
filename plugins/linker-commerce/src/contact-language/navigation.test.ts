import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { connectContactLanguage } from './navigation';

const key = 'linker.contact.language.v1';
let disconnect = () => {};

function fixture(
	owner = 'actor-a',
	context = 'epc-layout',
	recovered = false
) {
	document.body.innerHTML = `
	<a data-linker-language-choice="de" href="/de/kontakt/?intent=document">DE</a>
	<a data-linker-language-choice="en" aria-current="true" href="/contact/?intent=document">EN</a>
	<form data-linker-contact-draft-owner="${ owner }" data-linker-contact-draft-context="${ context }" data-linker-contact-draft-lifetime="300000" data-linker-contact-recovered="${ recovered ? '1' : '0' }">
	<textarea name="message" maxlength="5000"></textarea>
	<input name="name" maxlength="190"><input name="email" maxlength="190"><input name="company" maxlength="190">
	<select name="intent"><option value="document" selected>Documents</option><option value="project">Project</option></select>
	<input name="consent" type="checkbox">
	<input name="linker_contact_selection_include" value="0" type="hidden">
	<input name="linker_contact_selection" type="checkbox" checked value="current-server-json">
	<input name="linker_contact_nonce" value="fresh-nonce"><input name="linker_proof" value="fresh-proof"><input name="linker_request_id" value="fresh-id"><input name="password" value="never-copied">
	<div data-linker-contact-draft-error hidden><a data-linker-contact-draft-new-tab target="_blank" rel="noopener noreferrer">Open translated page</a></div>
	</form>`;
	return document.querySelector( 'form' )!;
}

function field( name: string ): HTMLInputElement {
	return document.querySelector( `[name="${ name }"]` )!;
}

function languageClick(
	init: MouseEventInit = {}
): Pick< MouseEvent, 'defaultPrevented' > {
	const event = new MouseEvent( 'click', {
		bubbles: true,
		cancelable: true,
		...init,
	} );
	// Preserve the product handler's result without asking jsdom to navigate.
	const link = document.querySelector(
		'a[data-linker-language-choice="de"]'
	)!;
	let prevented = false;
	window.addEventListener(
		'click',
		() => {
			prevented = event.defaultPrevented;
			// The product handler already ran. Suppress only jsdom's unsupported navigation.
			event.preventDefault();
		},
		{ once: true }
	);
	link.dispatchEvent( event );
	return { defaultPrevented: prevented };
}

function saveEdit() {
	fixture();
	disconnect = connectContactLanguage();
	field( 'message' ).value = 'A & B "quoted" \\ Rückfrage + 100%';
	field( 'name' ).value = 'Sample Person';
	field( 'intent' ).value = 'project';
	field( 'linker_contact_selection' ).checked = false;
	languageClick();
	const stored = JSON.parse( window.sessionStorage.getItem( key )! );
	disconnect();
	return stored;
}

beforeEach( () => {
	window.sessionStorage.clear();
	window.history.replaceState( null, '', '/contact/?intent=document' );
} );
afterEach( () => {
	disconnect();
	document.body.replaceChildren();
	vi.restoreAllMocks();
} );

test( 'an actual language click carries only editable values and restores current server context', () => {
	const stored = saveEdit();
	expect( stored.fields.message ).toBe(
		'A & B "quoted" \\ Rückfrage + 100%'
	);
	expect( Object.keys( stored.fields ).sort() ).toEqual( [
		'company',
		'email',
		'intent',
		'message',
		'name',
	] );
	expect( JSON.stringify( stored ) ).not.toMatch(
		/fresh-nonce|fresh-proof|fresh-id|never-copied|current-server-json/
	);
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	fixture();
	field( 'linker_contact_selection' ).value = 'new-German-server-json';
	disconnect = connectContactLanguage();
	expect( field( 'message' ) ).toHaveValue( stored.fields.message );
	expect( field( 'name' ) ).toHaveValue( 'Sample Person' );
	expect( field( 'intent' ) ).toHaveValue( 'project' );
	expect( field( 'linker_contact_selection' ) ).not.toBeChecked();
	expect( field( 'linker_contact_selection' ).value ).toBe(
		'new-German-server-json'
	);
	expect( field( 'consent' ) ).not.toBeChecked();
	expect( field( 'linker_contact_nonce' ) ).toHaveValue( 'fresh-nonce' );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test.each( [
	'expired',
	'future',
	'owner',
	'context',
	'target',
	'version',
	'intent',
	'length',
	'type',
	'extra-field',
] )( '%s state cannot overwrite the destination and is consumed', ( mode ) => {
	const stored = saveEdit();
	if ( mode === 'expired' ) {
		stored.until = Date.now() - 1;
	}
	if ( mode === 'future' ) {
		stored.until = Date.now() + 600000;
	}
	if ( mode === 'owner' ) {
		stored.owner = 'other-actor';
	}
	if ( mode === 'context' ) {
		stored.context = 'other-page';
	}
	if ( mode === 'target' ) {
		stored.target = window.location.origin + '/contact/';
	}
	if ( mode === 'version' ) {
		stored.version = 2;
	}
	if ( mode === 'intent' ) {
		stored.fields.intent = 'unknown';
	}
	if ( mode === 'length' ) {
		stored.fields.message = 'x'.repeat( 5001 );
	}
	if ( mode === 'type' ) {
		stored.fields.message = { html: '<img>' };
	}
	if ( mode === 'extra-field' ) {
		stored.fields.password = 'unexpected';
	}
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	fixture();
	disconnect = connectContactLanguage();
	expect( field( 'message' ) ).toHaveValue( '' );
	expect( field( 'linker_contact_selection' ) ).toBeChecked();
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test( 'server recovery including empty values wins, and receipts clear pending without a form', () => {
	const stored = saveEdit();
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	fixture( 'actor-a', 'epc-layout', true );
	disconnect = connectContactLanguage();
	expect( field( 'message' ) ).toHaveValue( '' );
	expect( field( 'linker_contact_selection' ) ).toBeChecked();
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	disconnect();
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	document.body.innerHTML =
		'<div class="linker-contact-receipt">Received</div>';
	disconnect = connectContactLanguage();
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test.each( [ 'kept', 'cleared' ] )(
	'native recovery with an excluded source carries its %s edit and explicit false',
	( mode ) => {
		const form = fixture( 'actor-a', 'epc-layout', true );
		field( 'message' ).defaultValue = 'Native recovered question';
		field( 'linker_contact_selection' ).remove();
		const excluded = document.createElement( 'fieldset' );
		excluded.className = 'linker-contact-selection--excluded';
		form.prepend( excluded );
		disconnect = connectContactLanguage();
		if ( mode === 'cleared' ) {
			field( 'message' ).value = '';
		}
		languageClick();
		const stored = JSON.parse( window.sessionStorage.getItem( key )! );
		expect( stored.include ).toBe( false );
		disconnect();
		window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
		fixture();
		disconnect = connectContactLanguage();
		expect( field( 'message' ) ).toHaveValue(
			mode === 'cleared' ? '' : 'Native recovered question'
		);
		expect( field( 'linker_contact_selection' ) ).not.toBeChecked();
		expect( field( 'linker_contact_selection' ).value ).toBe(
			'current-server-json'
		);
	}
);

test( 'malformed pending is removed before parsing, rather than surviving each visit', () => {
	fixture();
	window.sessionStorage.setItem( key, '{not json' );
	disconnect = connectContactLanguage();
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	expect( field( 'message' ) ).toHaveValue( '' );
} );

test( 'new destination edits, empty values and bfcache pages are respected', () => {
	const stored = saveEdit();
	stored.fields.name = '';
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	fixture();
	field( 'name' ).defaultValue = 'Server default';
	field( 'message' ).value = 'New destination question';
	disconnect = connectContactLanguage();
	expect( field( 'name' ) ).toHaveValue( '' );
	expect( field( 'message' ) ).toHaveValue( 'New destination question' );
	field( 'message' ).value = 'Later edit';
	window.dispatchEvent(
		new PageTransitionEvent( 'pageshow', { persisted: true } )
	);
	expect( field( 'message' ) ).toHaveValue( 'Later edit' );
	disconnect();
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	fixture();
	field( 'message' ).focus();
	disconnect = connectContactLanguage();
	expect( field( 'message' ) ).toHaveValue( stored.fields.message );
	expect( field( 'message' ).ownerDocument.activeElement ).toBe(
		field( 'message' )
	);
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test( 'a head entry keeps pending until the complete native form arrives', async () => {
	const stored = saveEdit();
	stored.fields.email = 'qa@example.test';
	stored.consent = true;
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	document.body.replaceChildren();
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	expect( window.sessionStorage.getItem( key ) ).not.toBeNull();

	fixture();
	const consent = field( 'consent' );
	consent.remove();
	await Promise.resolve();
	expect( window.sessionStorage.getItem( key ) ).not.toBeNull();
	expect( field( 'message' ) ).toHaveValue( '' );
	document.dispatchEvent( new Event( 'DOMContentLoaded' ) );
	expect( window.sessionStorage.getItem( key ) ).not.toBeNull();
	field( 'email' ).focus();
	document.querySelector( 'form' )!.append( consent );
	await Promise.resolve();

	expect( field( 'message' ) ).toHaveValue( stored.fields.message );
	expect( field( 'name' ) ).toHaveValue( stored.fields.name );
	expect( field( 'email' ) ).toHaveValue( 'qa@example.test' );
	expect( field( 'intent' ) ).toHaveValue( 'project' );
	expect( field( 'consent' ) ).toBeChecked();
	expect( field( 'linker_contact_selection' ) ).not.toBeChecked();
	expect( field( 'email' ).ownerDocument.activeElement ).toBe(
		field( 'email' )
	);
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	field( 'message' ).value = 'Later target edit';
	document.querySelector( 'form' )!.append( document.createElement( 'div' ) );
	await Promise.resolve();
	expect( field( 'message' ) ).toHaveValue( 'Later target edit' );
} );

test( 'a source click before the parser observer saves all fields and survives late readiness', async () => {
	document.body.replaceChildren();
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	fixture();
	field( 'message' ).value = 'Early source question';
	field( 'name' ).value = 'Early source name';
	field( 'email' ).value = 'qa@example.test';
	field( 'company' ).value = 'Early company';
	field( 'intent' ).value = 'project';
	field( 'consent' ).checked = true;
	field( 'linker_contact_selection' ).checked = false;
	// No microtask checkpoint: the native click is the first complete-form check.
	expect( languageClick().defaultPrevented ).toBe( false );
	const serialized = window.sessionStorage.getItem( key );
	expect( JSON.parse( serialized! ) ).toMatchObject( {
		fields: {
			message: 'Early source question',
			name: 'Early source name',
			email: 'qa@example.test',
			company: 'Early company',
			intent: 'project',
		},
		consent: true,
		include: false,
	} );
	document.dispatchEvent( new Event( 'DOMContentLoaded' ) );
	await Promise.resolve();
	expect( window.sessionStorage.getItem( key ) ).toBe( serialized );
} );

test( 'a language click restores incoming state synchronously before saving the next handoff', () => {
	const stored = saveEdit();
	stored.consent = true;
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	document.body.replaceChildren();
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	fixture();
	const link = document.querySelector< HTMLAnchorElement >(
		'[data-linker-language-choice="de"]'
	)!;
	link.href = '/contact/?intent=document';
	expect( languageClick().defaultPrevented ).toBe( false );
	const next = JSON.parse( window.sessionStorage.getItem( key )! );
	expect( next.fields ).toEqual( stored.fields );
	expect( next.consent ).toBe( true );
	expect( next.include ).toBe( false );
	expect( next.target ).toBe(
		window.location.origin + '/contact/?intent=document'
	);
} );

test( 'early real edits including clear and checkbox return-to-default protect only those fields', async () => {
	const stored = saveEdit();
	stored.fields.email = 'qa@example.test';
	stored.fields.company = 'Saved company';
	stored.consent = true;
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	const form = fixture();
	const company = field( 'company' );
	company.remove();
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	field( 'message' ).value = 'Target typing';
	field( 'message' ).dispatchEvent( new Event( 'input', { bubbles: true } ) );
	field( 'message' ).value = '';
	field( 'message' ).dispatchEvent( new Event( 'input', { bubbles: true } ) );
	field( 'name' ).value = 'New target name';
	field( 'name' ).dispatchEvent( new Event( 'change', { bubbles: true } ) );
	field( 'intent' ).value = 'project';
	field( 'intent' ).dispatchEvent( new Event( 'change', { bubbles: true } ) );
	field( 'intent' ).value = 'document';
	field( 'intent' ).dispatchEvent( new Event( 'change', { bubbles: true } ) );
	for ( const name of [ 'consent', 'linker_contact_selection' ] ) {
		field( name ).checked = ! field( name ).defaultChecked;
		field( name ).dispatchEvent( new Event( 'change', { bubbles: true } ) );
		field( name ).checked = field( name ).defaultChecked;
		field( name ).dispatchEvent( new Event( 'change', { bubbles: true } ) );
	}
	field( 'email' ).focus();
	form.append( company );
	await Promise.resolve();
	expect( field( 'message' ) ).toHaveValue( '' );
	expect( field( 'name' ) ).toHaveValue( 'New target name' );
	expect( field( 'intent' ) ).toHaveValue( 'document' );
	expect( field( 'consent' ) ).not.toBeChecked();
	expect( field( 'linker_contact_selection' ) ).toBeChecked();
	expect( field( 'email' ) ).toHaveValue( 'qa@example.test' );
	expect( field( 'company' ) ).toHaveValue( 'Saved company' );
	expect( field( 'linker_contact_selection' ).value ).toBe(
		'current-server-json'
	);
	expect( field( 'linker_contact_nonce' ) ).toHaveValue( 'fresh-nonce' );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test( 'an in-progress composition protects its field before the first input event', async () => {
	const stored = saveEdit();
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	const form = fixture();
	const consent = field( 'consent' );
	consent.remove();
	disconnect = connectContactLanguage();
	field( 'message' ).dispatchEvent(
		new CompositionEvent( 'compositionstart', { bubbles: true } )
	);
	form.append( consent );
	await Promise.resolve();
	expect( field( 'message' ) ).toHaveValue( '' );
	expect( field( 'name' ) ).toHaveValue( stored.fields.name );
} );

test( 'a dirty partial form keeps its current page without writing incomplete fields', async () => {
	const stored = saveEdit();
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	const form = fixture();
	const company = field( 'company' );
	company.remove();
	disconnect = connectContactLanguage();
	field( 'message' ).value = 'Partial target edit';
	field( 'message' ).dispatchEvent( new Event( 'input', { bubbles: true } ) );
	const incoming = window.sessionStorage.getItem( key );
	const set = vi.spyOn( Storage.prototype, 'setItem' );
	expect( languageClick().defaultPrevented ).toBe( true );
	expect( set ).not.toHaveBeenCalled();
	expect( window.sessionStorage.getItem( key ) ).toBe( incoming );
	expect( field( 'message' ) ).toHaveValue( 'Partial target edit' );
	expect(
		document.querySelector( '[data-linker-contact-draft-error]' )
	).toBeVisible();
	form.append( company );
	await Promise.resolve();
	expect( field( 'message' ) ).toHaveValue( 'Partial target edit' );
	expect( field( 'name' ) ).toHaveValue( stored.fields.name );
} );

test( 'a receipt arriving after the head entry consumes pending without a form', async () => {
	const stored = saveEdit();
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	document.body.replaceChildren();
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	expect( window.sessionStorage.getItem( key ) ).not.toBeNull();
	document.body.innerHTML =
		'<div class="linker-contact-receipt">Received</div>';
	await Promise.resolve();
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test( 'readiness clears a page without a form only once', () => {
	document.body.replaceChildren();
	window.sessionStorage.setItem( key, '{old malformed state' );
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	expect( window.sessionStorage.getItem( key ) ).not.toBeNull();
	document.dispatchEvent( new Event( 'DOMContentLoaded' ) );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	window.sessionStorage.setItem( key, 'new handoff' );
	document.dispatchEvent( new Event( 'DOMContentLoaded' ) );
	expect( window.sessionStorage.getItem( key ) ).toBe( 'new handoff' );
} );

test( 'a delegated native submit clears pending only for a Contact form', () => {
	document.body.replaceChildren();
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	const form = fixture();
	field( 'message' ).value = 'Ready to carry';
	languageClick();
	const pending = window.sessionStorage.getItem( key );
	const other = document.createElement( 'form' );
	document.body.append( other );
	other.dispatchEvent( new Event( 'submit', { bubbles: true } ) );
	expect( window.sessionStorage.getItem( key ) ).toBe( pending );
	form.dispatchEvent( new Event( 'submit', { bubbles: true } ) );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test( 'cleanup removes parser observation and all delegated listeners', async () => {
	const stored = saveEdit();
	window.sessionStorage.setItem( key, JSON.stringify( stored ) );
	window.history.replaceState( null, '', '/de/kontakt/?intent=document' );
	document.body.replaceChildren();
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	disconnect = connectContactLanguage();
	disconnect();
	const form = fixture();
	field( 'message' ).value = 'Keep after cleanup';
	field( 'message' ).dispatchEvent( new Event( 'input', { bubbles: true } ) );
	expect( languageClick().defaultPrevented ).toBe( false );
	form.dispatchEvent( new Event( 'submit', { bubbles: true } ) );
	document.dispatchEvent( new Event( 'DOMContentLoaded' ) );
	await Promise.resolve();
	expect( field( 'message' ) ).toHaveValue( 'Keep after cleanup' );
	expect( field( 'name' ) ).toHaveValue( '' );
	expect( window.sessionStorage.getItem( key ) ).toBe(
		JSON.stringify( stored )
	);
} );

test.each( [
	{ ctrlKey: true },
	{ metaKey: true },
	{ shiftKey: true },
	{ altKey: true },
	{ button: 1 },
] )( 'native modified/new-tab click %o stores nothing', ( modifier ) => {
	fixture();
	disconnect = connectContactLanguage();
	field( 'message' ).value = 'Keep original';
	expect( languageClick( modifier ).defaultPrevented ).toBe( false );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test( 'storage failure keeps actual edits and offers a new translated tab; an untouched form still navigates', () => {
	fixture();
	disconnect = connectContactLanguage();
	vi.spyOn( Storage.prototype, 'setItem' ).mockImplementation( () => {
		throw new Error( 'quota' );
	} );
	expect( languageClick().defaultPrevented ).toBe( false );
	field( 'message' ).value = 'Still here';
	const event = languageClick();
	expect( event.defaultPrevented ).toBe( true );
	expect( field( 'message' ) ).toHaveValue( 'Still here' );
	const error = document.querySelector< HTMLElement >(
		'[data-linker-contact-draft-error]'
	)!;
	const link = error.querySelector( 'a' )!;
	expect( error.hidden ).toBe( false );
	expect( link.href ).toBe(
		window.location.origin + '/de/kontakt/?intent=document'
	);
	expect( link.target ).toBe( '_blank' );
	expect( link.ownerDocument.activeElement ).toBe( link );
} );

test( 'active language prevents a destructive reload, while external and blank links remain native', () => {
	fixture();
	disconnect = connectContactLanguage();
	field( 'message' ).value = 'Keep original';
	const current = new MouseEvent( 'click', {
		bubbles: true,
		cancelable: true,
	} );
	document.querySelector( '[aria-current="true"]' )!.dispatchEvent( current );
	expect( current.defaultPrevented ).toBe( true );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	const link = document.querySelector< HTMLAnchorElement >(
		'[data-linker-language-choice="de"]'
	)!;
	link.target = '_blank';
	expect( languageClick().defaultPrevented ).toBe( false );
	link.target = '';
	link.href = 'https://outside.test/de/';
	expect( languageClick().defaultPrevented ).toBe( false );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );
