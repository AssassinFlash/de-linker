import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { rememberInquiry, restoreInquiry } from './inquiryHandoff';

const scope = 'a'.repeat( 64 );
const key = `linker-genie-inquiry-handoff:v2:${ scope }`;
const config = { restUrl: '/wp-json/', restNonce: 'native-current' };

beforeEach( () => {
	window.sessionStorage.clear();
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieNativeScope;
	window.history.replaceState( null, '', '/proforma-request/' );
	document.body.innerHTML =
		'<textarea id="inquiry-message">Prior completed question</textarea>';
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( {
			ok: true,
			json: async () => ( { scope } ),
		} ) )
	);
} );

afterEach( () => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	window.sessionStorage.clear();
	document.body.innerHTML = '';
} );

test( 'explicit same-owner navigation carries plain text once, without URL or files', async () => {
	const text = '<img src=x onerror=alert(1)> Current unsent question';
	expect( rememberInquiry( window.location.href, text, scope ) ).toBe( true );
	await restoreInquiry( config );
	const field = document.querySelector( 'textarea' )!;
	expect( field.value ).toBe( text );
	expect( document.querySelector( 'img' ) ).toBeNull();
	expect( window.location.search ).toBe( '' );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	field.value = 'Later edit';
	await restoreInquiry( config );
	expect( field.value ).toBe( 'Later edit' );
} );

test( 'an explicit same-origin empty question clears only its earlier same-owner handoff', async () => {
	expect(
		rememberInquiry(
			window.location.href,
			'Earlier question opened in another tab',
			scope
		)
	).toBe( true );
	expect( rememberInquiry( window.location.href, '', scope ) ).toBe( true );
	await restoreInquiry( config );
	expect( document.querySelector( 'textarea' )!.value ).toBe(
		'Prior completed question'
	);
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
} );

test( 'expiry, different destination and customer edits cannot overwrite the native field', async () => {
	const field = document.querySelector( 'textarea' )!;
	rememberInquiry( window.location.href, 'Unsent question', scope );
	const unedited = window.sessionStorage.getItem( key );
	field.value = 'Customer has edited this field';
	await restoreInquiry( config );
	expect( field.value ).toBe( 'Customer has edited this field' );
	expect( window.sessionStorage.getItem( key ) ).toBe( unedited );
	field.value = field.defaultValue;
	rememberInquiry( '/another-request-page/', 'Wrong destination', scope );
	await restoreInquiry( config );
	expect( field.value ).toBe( field.defaultValue );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	const clock = vi.spyOn( Date, 'now' ).mockReturnValue( 1_000_000 );
	rememberInquiry( window.location.href, 'Expired question', scope );
	clock.mockReturnValue( 1_300_001 );
	await restoreInquiry( config );
	expect( field.value ).toBe( field.defaultValue );
	expect( window.sessionStorage.getItem( key ) ).toBeNull();
	clock.mockRestore();
} );
