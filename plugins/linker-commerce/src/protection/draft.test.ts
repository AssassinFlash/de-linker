import { afterEach, beforeAll, expect, test, vi } from 'vitest';
import { ProtectionClient } from './client';
import { connectDraftLinks } from './draft';
import { connectForms } from './forms';
import type { TurnstileOptions } from './types';

beforeAll( connectDraftLinks );

afterEach( () => {
	window.linkerPublicProtection?.reset( 'draft_write' );
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	delete window.turnstile;
	vi.unstubAllGlobals();
	document.body.onsubmit = null;
	document.body.replaceChildren();
} );

function cartFixture( language: 'en' | 'de' ) {
	const path = language === 'de' ? '/de/loesungsentwurf/' : '/cart/';
	document.body.innerHTML = `<form class="woocommerce-cart-form" method="post" action="${ path }">
		<a class="remove" href="${ path }?remove_item=line&amp;_wpnonce=cart-nonce"><span>×</span></a>
		<input class="qty" type="number" min="0" name="cart[line][qty]" value="1">
		<button type="submit" name="update_cart" value="1">Update solution draft</button>
		<input type="hidden" name="woocommerce-cart-nonce" value="cart-nonce">
		<input type="hidden" name="linker_request_id" value="cart-id" data-linker-protected-action="draft_write">
		<input type="hidden" name="linker_proof">
		<div data-linker-protection-widget hidden></div>
		<p role="status" aria-live="polite" data-linker-protection-status hidden></p>
	</form>`;
	const config = {
		api: 'https://example.test/wp-json/linker/v1/protection',
		nonce: 'synthetic',
		mode: 'enforce',
		language,
	};
	window.linkerPublicProtectionConfig = config;
	window.linkerPublicProtection = new ProtectionClient( config );
	const verification = vi.fn( async ( url: string ) => ( {
		ok: true,
		json: async () =>
			url.includes( '/prepare' )
				? { site_key: 'synthetic-public', prepare: 'synthetic-stamp' }
				: { proof: 'signed-proof', ttl: 300 },
	} ) );
	vi.stubGlobal( 'fetch', verification );
	const render = vi.fn<
		( container: HTMLElement, options: TurnstileOptions ) => string
	>( () => 'cart-widget' );
	window.turnstile = { render, reset: vi.fn(), remove: vi.fn() };
	const post = vi.fn< ( form: HTMLFormElement ) => void >();
	vi.spyOn( HTMLFormElement.prototype, 'submit' ).mockImplementation(
		function ( this: HTMLFormElement ) {
			post( this );
		}
	);
	connectForms();
	const form = document.querySelector( 'form' )!;
	const link = form.querySelector( 'a' )!;
	const removeIcon = link.querySelector( 'span' )!;
	const focusRemove = () => {
		removeIcon.dispatchEvent(
			new MouseEvent( 'pointerdown', { bubbles: true } )
		);
		link.focus();
	};
	const update = form.querySelector( 'button' )!;
	const quantity = form.querySelector< HTMLInputElement >( '.qty' )!;
	const status = form.querySelector( '[data-linker-protection-status]' )!;
	const nativeUpdate = vi.fn< ( data: FormData ) => void >();
	// Record what Woo's delegated submit handler would serialize.
	document.body.onsubmit = ( event ) => {
		event.preventDefault();
		nativeUpdate(
			new FormData( form, ( event as SubmitEvent ).submitter )
		);
	};
	return {
		form,
		path,
		focusRemove,
		removeIcon,
		verification,
		render,
		post,
		update,
		quantity,
		status,
		nativeUpdate,
	};
}

test.each( [ 'en', 'de' ] as const )(
	'a cold %s Remove gesture starts only its own verification and POSTs only after proof',
	async ( language ) => {
		const cart = cartFixture( language );
		cart.focusRemove();
		// A customer can pause between pressing and releasing the pointer.
		await new Promise( ( resolve ) => setTimeout( resolve, 0 ) );
		expect( cart.verification ).not.toHaveBeenCalled();
		cart.removeIcon.click();
		await vi.waitFor( () => expect( cart.render ).toHaveBeenCalledOnce() );
		expect( cart.verification ).toHaveBeenCalledOnce();
		expect( cart.post ).not.toHaveBeenCalled();
		const [ , challenge ] = cart.render.mock.calls[ 0 ];
		expect( challenge.language ).toBe( language );
		challenge[ 'before-interactive-callback' ]();
		expect(
			cart.form.querySelector( '[data-linker-protection-status]' )
		).not.toBeVisible();
		challenge.callback( 'remove-token' );
		await vi.waitFor( () => expect( cart.post ).toHaveBeenCalledOnce() );
		const [ posted ] = cart.post.mock.calls[ 0 ];
		expect( posted.method ).toBe( 'post' );
		expect( posted.action ).toBe( location.origin + cart.path );
		const data = new FormData( posted );
		expect( data.get( 'remove_item' ) ).toBe( 'line' );
		expect( data.get( '_wpnonce' ) ).toBe( 'cart-nonce' );
		expect( data.get( 'linker_proof' ) ).toBe( 'signed-proof' );
		expect( data.get( 'linker_request_id' ) ).toMatch( /^[0-9a-f-]{36}$/ );
		expect( cart.verification ).toHaveBeenCalledTimes( 2 );
	}
);

test.each( [ 'challenge', 'verify' ] )(
	'Remove replaces a pending quantity %s without leaving the form pending or submitting the quantity',
	async ( stage ) => {
		const cart = cartFixture( 'en' );
		let verificationStarted!: () => void;
		let finishVerification!: () => void;
		const started = new Promise< void >( ( resolve ) => {
			verificationStarted = resolve;
		} );
		if ( stage === 'verify' ) {
			const prepare = cart.verification.getMockImplementation()!;
			cart.verification.mockImplementationOnce( prepare );
			cart.verification.mockImplementationOnce( async () => {
				await new Promise< void >( ( resolve ) => {
					finishVerification = resolve;
					verificationStarted();
				} );
				return {
					ok: true,
					json: async () => ( { proof: 'stale-proof', ttl: 300 } ),
				};
			} );
		}
		cart.quantity.focus();
		await vi.waitFor( () => expect( cart.render ).toHaveBeenCalledOnce() );
		const [ , quantityCheck ] = cart.render.mock.calls[ 0 ];
		quantityCheck[ 'before-interactive-callback' ]();
		cart.update.click();
		expect( cart.status ).toBeVisible();
		expect( cart.nativeUpdate ).not.toHaveBeenCalled();
		if ( stage === 'verify' ) {
			quantityCheck.callback( 'quantity-token' );
			await started;
		}

		cart.focusRemove();
		cart.removeIcon.click();
		await vi.waitFor( () =>
			expect( cart.render ).toHaveBeenCalledTimes( 2 )
		);
		expect( cart.status ).not.toBeVisible();
		const [ , removeCheck ] = cart.render.mock.calls[ 1 ];
		removeCheck[ 'before-interactive-callback' ]();
		expect(
			cart.removeIcon
				.closest( 'a' )!
				.parentElement!.querySelector(
					'[role="status"]:not([data-linker-protection-status])'
				)
		).toBeVisible();
		if ( stage === 'verify' ) {
			finishVerification();
			await new Promise( ( resolve ) => setTimeout( resolve, 0 ) );
		} else {
			quantityCheck.callback( 'cancelled-token' );
		}
		expect( cart.status ).not.toBeVisible();
		expect( cart.post ).not.toHaveBeenCalled();
		removeCheck.callback( 'remove-token' );
		await vi.waitFor( () => expect( cart.post ).toHaveBeenCalledOnce() );
		expect(
			new FormData( cart.post.mock.calls[ 0 ][ 0 ] ).get( 'linker_proof' )
		).toBe( 'signed-proof' );
		expect( cart.nativeUpdate ).not.toHaveBeenCalled();
	}
);

test.each( [ 'Enter', 'Update button' ] )(
	'after failed Remove, changing quantity to zero warms a check and %s reuses it',
	async ( gesture ) => {
		const cart = cartFixture( 'en' );
		cart.focusRemove();
		cart.removeIcon.click();
		await vi.waitFor( () => expect( cart.render ).toHaveBeenCalledOnce() );
		const [ removeWidget, removeCheck ] = cart.render.mock.calls[ 0 ];
		// Moving focus into the Remove challenge must not warm the cart form.
		const challengeFrame = document.createElement( 'iframe' );
		removeWidget.append( challengeFrame );
		challengeFrame.focus();
		expect( cart.verification ).toHaveBeenCalledOnce();
		removeCheck[ 'error-callback' ]( '110100' );
		await vi.waitFor( () =>
			expect( removeWidget.nextElementSibling ).toHaveTextContent(
				'Verification could not be completed.'
			)
		);
		expect( cart.post ).not.toHaveBeenCalled();
		expect( cart.quantity ).toHaveValue( 1 );

		cart.quantity.dispatchEvent(
			new MouseEvent( 'pointerdown', { bubbles: true } )
		);
		cart.quantity.focus();
		cart.quantity.value = '0';
		cart.quantity.dispatchEvent( new Event( 'input', { bubbles: true } ) );
		await vi.waitFor( () =>
			expect( cart.render ).toHaveBeenCalledTimes( 2 )
		);
		const [ , quantityCheck ] = cart.render.mock.calls[ 1 ];
		if ( gesture === 'Enter' ) {
			cart.quantity.dispatchEvent(
				new KeyboardEvent( 'keypress', {
					key: 'Enter',
					bubbles: true,
					cancelable: true,
				} )
			);
		} else {
			cart.update.click();
		}
		expect( cart.nativeUpdate ).not.toHaveBeenCalled();
		expect( cart.verification ).toHaveBeenCalledTimes( 2 );
		quantityCheck.callback( 'quantity-token' );
		await vi.waitFor( () =>
			expect( cart.nativeUpdate ).toHaveBeenCalledOnce()
		);
		const [ data ] = cart.nativeUpdate.mock.calls[ 0 ];
		expect( data.get( 'cart[line][qty]' ) ).toBe( '0' );
		expect( data.get( 'update_cart' ) ).toBe( '1' );
		expect( data.get( 'woocommerce-cart-nonce' ) ).toBe( 'cart-nonce' );
		expect( data.get( 'linker_request_id' ) ).toBe( 'cart-id' );
		expect( data.get( 'linker_proof' ) ).toBe( 'signed-proof' );
		expect( cart.verification ).toHaveBeenCalledTimes( 3 );
		expect( cart.post ).not.toHaveBeenCalled();
	}
);

test( 'starting a quantity update replaces a pending Remove without a stale message or POST', async () => {
	const cart = cartFixture( 'en' );
	cart.focusRemove();
	cart.removeIcon.click();
	await vi.waitFor( () => expect( cart.render ).toHaveBeenCalledOnce() );
	const [ removeWidget, removeCheck ] = cart.render.mock.calls[ 0 ];
	const removeStatus = removeWidget.nextElementSibling;
	removeCheck[ 'before-interactive-callback' ]();
	expect( removeStatus ).toBeVisible();

	cart.quantity.focus();
	cart.update.click();
	await vi.waitFor( () => expect( cart.render ).toHaveBeenCalledTimes( 2 ) );
	expect( removeStatus ).not.toBeInTheDocument();
	removeCheck.callback( 'cancelled-remove-token' );
	expect( cart.nativeUpdate ).not.toHaveBeenCalled();
	cart.render.mock.calls[ 1 ][ 1 ].callback( 'quantity-token' );
	await vi.waitFor( () =>
		expect( cart.nativeUpdate ).toHaveBeenCalledOnce()
	);
	expect( cart.post ).not.toHaveBeenCalled();
} );

test( 'native draft links keep retry and interaction visible before one proof-bound POST', async () => {
	document.body.innerHTML =
		'<main><a href="/?add-to-cart=12">Add to solution draft</a></main>';
	const config = {
		api: 'https://example.test/wp-json/linker/v1/protection',
		nonce: 'synthetic',
		mode: 'enforce',
		language: 'en' as const,
	};
	window.linkerPublicProtectionConfig = config;
	window.linkerPublicProtection = new ProtectionClient( config );
	const validation = vi.fn( async ( url: string ) => ( {
		ok: true,
		json: async () =>
			url.includes( 'prepare' )
				? { site_key: 'synthetic-public', prepare: 'synthetic-stamp' }
				: { proof: 'signed-proof', ttl: 300 },
	} ) );
	vi.stubGlobal( 'fetch', validation );
	let options: TurnstileOptions;
	const render = vi.fn( ( _container, received: TurnstileOptions ) => {
		options = received;
		queueMicrotask( () =>
			received[ 'error-callback' ](
				render.mock.calls.length === 1 ? '110100' : '300030'
			)
		);
		return 'native-draft';
	} );
	window.turnstile = { render, reset: vi.fn(), remove: vi.fn() };
	const submit = vi
		.spyOn( HTMLFormElement.prototype, 'submit' )
		.mockImplementation( () => undefined );
	connectDraftLinks();
	const link = document.querySelector( 'a' )!;
	link.click();
	await vi.waitFor( () =>
		expect( document.querySelector( '[role="status"]' ) ).toHaveTextContent(
			'Verification could not be completed.'
		)
	);
	expect( submit ).not.toHaveBeenCalled();
	link.click();
	link.click();
	await vi.waitFor( () => expect( render ).toHaveBeenCalledTimes( 2 ) );
	expect( document.querySelectorAll( '[role="status"]' ) ).toHaveLength( 1 );
	expect( document.querySelector( '[role="status"]' ) ).toHaveTextContent(
		'Verification is being retried. No request has been sent in this attempt.'
	);
	expect( validation ).toHaveBeenCalledTimes( 2 );
	expect( submit ).not.toHaveBeenCalled();
	options![ 'before-interactive-callback' ]();
	expect( document.querySelector( '[role="status"]' ) ).toHaveTextContent(
		'No request has been sent in this attempt. Please complete the verification.'
	);
	options!.callback( 'native-token' );
	await vi.waitFor( () => expect( submit ).toHaveBeenCalledOnce() );
	expect( validation ).toHaveBeenCalledTimes( 3 );
	const posted = new FormData( document.querySelector( 'form' )! );
	expect( posted.get( 'add-to-cart' ) ).toBe( '12' );
	expect( posted.get( 'linker_proof' ) ).toBe( 'signed-proof' );
	expect( posted.get( 'linker_request_id' ) ).toMatch(
		/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
	);
} );
