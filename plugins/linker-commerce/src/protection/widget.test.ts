import { afterEach, expect, it, vi } from 'vitest';
import { createWidgets, connectForms } from './widget';
import type { TurnstileOptions } from './types';

afterEach( () => {
	document.body.replaceChildren();
	delete window.turnstile;
} );

it( 'leaves an ordinary product or draft page untouched', () => {
	document.body.innerHTML = '<a href="/product/battery/">Battery</a>';
	const api = { render: vi.fn(), remove: vi.fn(), reset: vi.fn() };
	window.turnstile = api;
	const widgets = createWidgets( { siteKey: 'public-key', language: 'en' } );
	connectForms( document, widgets );
	expect( api.render ).not.toHaveBeenCalled();
	expect( document.querySelector( 'script[src*="cloudflare"]' ) ).toBeNull();
} );

it( 'uses a fresh native response after expiry and keeps typed form fields', async () => {
	document.body.innerHTML =
		'<form><input name="message" value="My battery"><div data-linker-turnstile="contact"></div></form>';
	let options: TurnstileOptions;
	const api = {
		render: vi.fn( ( _el: HTMLElement, value: TurnstileOptions ) => {
			options = value;
			return 'widget-1';
		} ),
		reset: vi.fn(),
		remove: vi.fn(),
	};
	window.turnstile = api;
	const widgets = createWidgets( { siteKey: 'public-key', language: 'de' } );
	connectForms( document, widgets );
	await vi.waitFor( () => expect( api.render ).toHaveBeenCalledOnce() );
	expect( options!.action ).toBe( 'contact' );
	expect( options!.sitekey ).toBe( 'public-key' );
	expect( options!.language ).toBe( 'de' );
	options![ 'expired-callback' ]();
	expect( options! ).toMatchObject( {
		'refresh-expired': 'auto',
		retry: 'auto',
		theme: 'light',
	} );
	expect( api.reset ).not.toHaveBeenCalled();
	expect( new FormData( document.forms[ 0 ] ).get( 'message' ) ).toBe(
		'My battery'
	);
} );

it( 'keeps an incomplete protected form on screen and allows native submission once verified', async () => {
	document.body.innerHTML =
		'<form><input name="message" value="My battery"><div data-linker-turnstile="contact"></div></form>';
	let options: TurnstileOptions;
	window.turnstile = {
		render: vi.fn( ( _el: HTMLElement, value: TurnstileOptions ) => {
			options = value;
			return 'one';
		} ),
		reset: vi.fn(),
		remove: vi.fn(),
	};
	connectForms(
		document,
		createWidgets( { siteKey: 'public-key', language: 'de' } )
	);
	const form = document.forms[ 0 ];
	const submit = () =>
		form.dispatchEvent(
			new Event( 'submit', { bubbles: true, cancelable: true } )
		);
	await vi.waitFor( () =>
		expect( window.turnstile!.render ).toHaveBeenCalledOnce()
	);
	const resume = vi
		.spyOn( form, 'requestSubmit' )
		.mockImplementation( () => {} );
	expect( submit() ).toBe( false );
	expect( form.querySelector( '[role="status"]' ) ).toHaveTextContent(
		'Verifying, please wait…'
	);
	expect( new FormData( form ).get( 'message' ) ).toBe( 'My battery' );
	options!.callback( 'response-token' );
	await vi.waitFor( () => expect( resume ).toHaveBeenCalledTimes( 1 ) );
	options!.callback( 'next-token' );
	expect( resume ).toHaveBeenCalledTimes( 1 );
	expect( submit() ).toBe( true );
	options![ 'expired-callback' ]();
	expect( submit() ).toBe( false );
} );

it( 'loads on a Genie transfer, not chat, and can retry a failed script in place', async () => {
	const container = document.createElement( 'div' );
	document.body.append( container );
	const response = vi.fn();
	const widgets = createWidgets( { siteKey: 'public-key', language: 'en' } );
	expect( document.head.querySelector( 'script' ) ).toBeNull();
	const close = widgets.mount( container, 'genie_inquiry', response );
	const retry = container.querySelector< HTMLButtonElement >(
		'button.btn-secondary'
	)!;
	expect( retry ).toHaveAttribute( 'hidden' );
	const script = document.head.querySelector( 'script' )!;
	expect( script.src ).toMatch(
		/^https:\/\/challenges\.cloudflare\.com\/turnstile\/v0\/api\.js\?render=explicit$/
	);
	script.dispatchEvent( new Event( 'error' ) );
	await vi.waitFor( () =>
		expect( container.textContent ).toContain( 'sales@de-linker.com' )
	);
	expect( response ).toHaveBeenLastCalledWith( '' );
	let options: TurnstileOptions;
	const api = {
		render: vi.fn( ( _target: HTMLElement, opt: TurnstileOptions ) => {
			options = opt;
			return 'genie-transfer';
		} ),
		reset: vi.fn(),
		remove: vi.fn(),
	};
	window.turnstile = api;
	expect( retry ).not.toHaveAttribute( 'hidden' );
	retry.click();
	await vi.waitFor( () => expect( api.render ).toHaveBeenCalledOnce() );
	options!.callback( 'native-response' );
	expect( response ).toHaveBeenLastCalledWith( 'native-response' );
	widgets.refresh( container );
	expect( response ).toHaveBeenLastCalledWith( '' );
	expect( api.reset ).toHaveBeenCalledWith( 'genie-transfer' );
	close();
	expect( api.remove ).toHaveBeenCalledWith( 'genie-transfer' );
} );

it( 'mounts the registration widget once the final pane has a width', async () => {
	document.body.innerHTML =
		'<form data-linker-register data-active-step="1"><div data-linker-turnstile="registration"></div></form>';
	const marker = document.querySelector< HTMLElement >(
		'[data-linker-turnstile]'
	)!;
	const form = document.forms[ 0 ];
	let width = 0;
	Object.defineProperty( marker, 'clientWidth', { get: () => width } );
	let resized: () => void;
	class Observer {
		constructor( callback: () => void ) {
			resized = callback;
		}
		observe() {}
		disconnect() {}
	}
	vi.stubGlobal( 'ResizeObserver', Observer );
	try {
		const render = vi.fn().mockReturnValue( 'register' );
		window.turnstile = { render, reset: vi.fn(), remove: vi.fn() };
		connectForms(
			document,
			createWidgets( { siteKey: 'public-key', language: 'de' } )
		);
		width = 360;
		resized!();
		expect( render ).not.toHaveBeenCalled();
		form.dataset.activeStep = '2';
		resized!();
		await vi.waitFor( () => expect( render ).toHaveBeenCalledOnce() );
		const options = render.mock.calls[ 0 ][ 1 ] as TurnstileOptions;
		expect( options.size ).toBe( 'flexible' );
		options[ 'error-callback' ]( '200500' );
		expect( marker.dataset.turnstileError ).toBe( '200500' );
		expect( marker.querySelector( 'button' ) ).toHaveAttribute( 'hidden' );
		options[ 'error-callback' ]( '110200' );
		expect( marker.querySelector( 'button' ) ).not.toHaveAttribute(
			'hidden'
		);
		options.callback( 'response-token' );
		expect( marker.dataset.turnstileError ).toBeUndefined();
	} finally {
		vi.unstubAllGlobals();
	}
} );
