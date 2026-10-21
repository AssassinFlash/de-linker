import { beforeEach, expect, test, vi } from 'vitest';
import { rememberInquiry, restoreInquiry } from './inquiryHandoff';

beforeEach( () => {
	window.sessionStorage.clear();
	document.body.innerHTML =
		'<textarea id="inquiry-message">Prior completed question</textarea>';
	vi.restoreAllMocks();
} );

test( 'explicit navigation carries plain text once, without URL or files', () => {
	const text = '<img src=x onerror=alert(1)> Current unsent question';
	rememberInquiry( window.location.href, text );
	restoreInquiry();
	const field = document.querySelector( 'textarea' )!;
	expect( field.value ).toBe( text );
	expect( document.querySelector( 'img' ) ).toBeNull();
	expect( window.sessionStorage.length ).toBe( 0 );
	field.value = 'Later edit';
	restoreInquiry();
	expect( field.value ).toBe( 'Later edit' );
} );

test( 'an explicit same-origin empty question clears an earlier handoff', () => {
	rememberInquiry( window.location.href, 'Earlier question opened in another tab' );
	rememberInquiry( window.location.href, '' );
	restoreInquiry();
	expect( document.querySelector( 'textarea' )!.value ).toBe(
		'Prior completed question'
	);
	expect( window.sessionStorage.length ).toBe( 0 );
} );

test( 'expiry, different destination and customer edits cannot overwrite the native field', () => {
	const field = document.querySelector( 'textarea' )!;
	rememberInquiry( window.location.href, 'Unsent question' );
	field.value = 'Customer has edited this field';
	restoreInquiry();
	expect( field.value ).toBe( 'Customer has edited this field' );
	field.value = field.defaultValue;
	rememberInquiry( '/another-request-page/', 'Wrong destination' );
	restoreInquiry();
	expect( field.value ).toBe( field.defaultValue );
	const clock = vi.spyOn( Date, 'now' ).mockReturnValue( 1_000_000 );
	rememberInquiry( window.location.href, 'Expired question' );
	clock.mockReturnValue( 1_300_001 );
	restoreInquiry();
	expect( field.value ).toBe( field.defaultValue );
	clock.mockRestore();
} );
