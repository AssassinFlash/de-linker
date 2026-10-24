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

test( 'new destination edits, focus, empty values and bfcache pages are respected', () => {
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
	expect( field( 'message' ) ).toHaveValue( '' );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
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
