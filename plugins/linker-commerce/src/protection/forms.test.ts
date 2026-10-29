import { afterEach, expect, test, vi } from 'vitest';
import { connectForms } from './forms';
import { ProtectionClient } from './client';
import type { TurnstileOptions } from './types';

afterEach( () => {
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	delete window.turnstile;
	vi.unstubAllGlobals();
	document.body.replaceChildren();
} );

test.each( [ 'registration', 'contact', 'inquiry' ] )(
	'native %s keeps its warmed retrying check visible and resumes its original submit once',
	async ( action ) => {
		const f = fixture( 'enforce', action );
		window.linkerPublicProtection = new ProtectionClient(
			window.linkerPublicProtectionConfig!
		);
		const validation = vi.fn( async ( url: string ) => ( {
			ok: true,
			json: async () =>
				url.includes( 'prepare' )
					? {
							site_key: 'synthetic-public',
							prepare: 'synthetic-stamp',
						}
					: { proof: 'signed-proof', ttl: 300 },
		} ) );
		vi.stubGlobal( 'fetch', validation );
		let options: TurnstileOptions;
		const render = vi.fn( ( _container, received: TurnstileOptions ) => {
			options = received;
			queueMicrotask( () => received[ 'error-callback' ]( '300030' ) );
			return 'native-registration';
		} );
		window.turnstile = { render, reset: vi.fn(), remove: vi.fn() };
		f.form.dispatchEvent( new Event( 'focusin' ) );
		await vi.waitFor( () => expect( render ).toHaveBeenCalledOnce() );
		const widget = f.form.querySelector< HTMLElement >(
			'[data-linker-protection-widget]'
		)!;
		const status = f.form.querySelector< HTMLElement >(
			'[data-linker-protection-status]'
		)!;
		expect( widget.hidden ).toBe( false );
		expect( status.hidden ).toBe( false );
		expect( status ).toHaveTextContent(
			'Verification is being retried. No request has been sent in this attempt.'
		);
		expect( validation ).toHaveBeenCalledOnce();
		expect( f.submit ).not.toHaveBeenCalled();
		for ( let click = 0; click < 2; click++ ) {
			const submitEvent = new SubmitEvent( 'submit', {
				cancelable: true,
				submitter: f.button,
			} );
			f.form.dispatchEvent( submitEvent );
			expect( submitEvent.defaultPrevented ).toBe( true );
		}
		expect( status ).toHaveTextContent(
			'Verification is being retried. No request has been sent in this attempt.'
		);
		options![ 'before-interactive-callback' ]();
		expect( status ).toHaveTextContent(
			'No request has been sent in this attempt. Please complete the verification.'
		);
		options!.callback( 'native-token' );
		await vi.waitFor( () => expect( f.submit ).toHaveBeenCalledOnce() );
		expect( validation ).toHaveBeenCalledTimes( 2 );
		expect( f.form.querySelector( '[name="message"]' ) ).toHaveValue(
			'Customer message'
		);
		expect(
			f.form.querySelector( '[name="linker_request_id"]' )
		).toHaveValue( 'stable-id' );
	}
);

function fixture( mode = 'enforce', action = 'draft_write' ) {
	document.body.innerHTML = `<form><input name="message" value="Customer message"><input name="linker_request_id" value="stable-id" data-linker-protected-action="${ action }"><input name="linker_proof"><div data-linker-protection-widget hidden></div><p role="status" aria-live="polite" data-linker-protection-status hidden></p><button type="submit" name="send" value="1">Send inquiry</button></form>`;
	const form = document.querySelector( 'form' )!;
	const button = form.querySelector( 'button' )!;
	const proof = vi.fn< () => Promise< string > >();
	window.linkerPublicProtectionConfig = {
		mode,
		api: 'https://example.test',
		nonce: '',
		language: 'en',
	};
	window.linkerPublicProtection = {
		warm: vi.fn( () => Promise.resolve( 'proof' ) ),
		proof,
		reset: vi.fn(),
	};
	const submit = vi
		.spyOn( form, 'requestSubmit' )
		.mockImplementation( () => undefined );
	connectForms();
	return { form, button, proof, submit };
}

test( 'browsing is passive; the verified native submit preserves the submitter and UUID', async () => {
	const f = fixture();
	expect( f.proof ).not.toHaveBeenCalled();
	expect( window.linkerPublicProtection?.warm ).not.toHaveBeenCalled();
	f.proof.mockResolvedValue( 'signed-proof' );
	f.form.dispatchEvent(
		new SubmitEvent( 'submit', { cancelable: true, submitter: f.button } )
	);
	await vi.waitFor( () =>
		expect( f.submit ).toHaveBeenCalledWith( f.button )
	);
	expect(
		( f.form.elements.namedItem( 'linker_request_id' ) as HTMLInputElement )
			.value
	).toBe( 'stable-id' );
	expect(
		( f.form.elements.namedItem( 'linker_proof' ) as HTMLInputElement )
			.value
	).toBe( 'signed-proof' );
} );

test.each( [ 'contact', 'inquiry' ] )(
	'optional business verification leaves %s native submission and fast filling unobstructed',
	( action ) => {
		const f = fixture( 'enforce', action );
		window.linkerPublicProtectionConfig!.businessVerification = 'optional';
		f.form.dispatchEvent( new Event( 'focusin' ) );
		f.form.dispatchEvent( new Event( 'pointerdown' ) );
		const event = new SubmitEvent( 'submit', {
			cancelable: true,
			submitter: f.button,
		} );
		f.form.dispatchEvent( event );
		expect( event.defaultPrevented ).toBe( false );
		expect( f.proof ).not.toHaveBeenCalled();
		expect( window.linkerPublicProtection?.warm ).not.toHaveBeenCalled();
		expect( f.submit ).not.toHaveBeenCalled();
		expect( f.form.querySelector( '[name="message"]' ) ).toHaveValue(
			'Customer message'
		);
	}
);

test( 'optional business verification cannot relax a draft mutation', async () => {
	const f = fixture( 'enforce', 'draft_write' );
	window.linkerPublicProtectionConfig!.businessVerification = 'optional';
	f.proof.mockResolvedValue( 'draft-proof' );
	const event = new SubmitEvent( 'submit', {
		cancelable: true,
		submitter: f.button,
	} );
	f.form.dispatchEvent( event );
	expect( event.defaultPrevented ).toBe( true );
	await vi.waitFor( () => expect( f.submit ).toHaveBeenCalledTimes( 1 ) );
	expect( f.proof ).toHaveBeenCalledTimes( 1 );
} );

test( 'verification outage retains all input and permits an explicit retry', async () => {
	const f = fixture();
	f.proof
		.mockRejectedValueOnce( new Error( 'verification_http_503' ) )
		.mockResolvedValueOnce( 'recovered-proof' );
	f.form.dispatchEvent(
		new SubmitEvent( 'submit', { cancelable: true, submitter: f.button } )
	);
	await vi.waitFor( () =>
		expect(
			f.form.querySelector( '[data-linker-protection-status]' )
				?.textContent
		).toContain( 'No request has been sent in this attempt' )
	);
	expect( f.submit ).not.toHaveBeenCalled();
	expect(
		( f.form.elements.namedItem( 'message' ) as HTMLInputElement ).value
	).toBe( 'Customer message' );
	f.form.dispatchEvent(
		new SubmitEvent( 'submit', { cancelable: true, submitter: f.button } )
	);
	await vi.waitFor( () => expect( f.submit ).toHaveBeenCalledTimes( 1 ) );
} );

test( 'a warmed proof resumes after the original native submit dispatch', async () => {
	vi.useFakeTimers();
	try {
		const f = fixture();
		f.proof.mockResolvedValue( 'already-warmed-proof' );
		f.form.dispatchEvent(
			new SubmitEvent( 'submit', {
				cancelable: true,
				submitter: f.button,
			} )
		);
		await Promise.resolve();
		await Promise.resolve();
		// Native requestSubmit is ignored while its original dispatch is active.
		expect( f.submit ).not.toHaveBeenCalled();
		await vi.runOnlyPendingTimersAsync();
		expect( f.submit ).toHaveBeenCalledExactlyOnceWith( f.button );
	} finally {
		vi.useRealTimers();
	}
} );

test( 'repeated clicks during verification cannot submit twice and observe never blocks', async () => {
	const f = fixture();
	let resolve!: ( value: string ) => void;
	f.proof.mockReturnValue(
		new Promise( ( ready ) => {
			resolve = ready;
		} )
	);
	f.form.dispatchEvent(
		new SubmitEvent( 'submit', { cancelable: true, submitter: f.button } )
	);
	f.form.dispatchEvent(
		new SubmitEvent( 'submit', { cancelable: true, submitter: f.button } )
	);
	expect( f.proof ).toHaveBeenCalledTimes( 1 );
	resolve( 'proof' );
	await vi.waitFor( () => expect( f.submit ).toHaveBeenCalledTimes( 1 ) );
	const observe = fixture( 'observe' );
	const event = new SubmitEvent( 'submit', {
		cancelable: true,
		submitter: observe.button,
	} );
	observe.form.dispatchEvent( event );
	expect( event.defaultPrevented ).toBe( false );
	expect( observe.proof ).not.toHaveBeenCalled();
} );

test( 'native delegated AJAX sees only the verified resubmit and replaced forms reconnect', async () => {
	const f = fixture();
	let finish!: ( proof: string ) => void;
	f.proof.mockReturnValue(
		new Promise( ( resolve ) => {
			finish = resolve;
		} )
	);
	const native = vi.fn();
	document.body.addEventListener( 'submit', native );
	f.submit.mockImplementation( ( button ) => {
		f.form.dispatchEvent(
			new SubmitEvent( 'submit', {
				bubbles: true,
				cancelable: true,
				submitter: button,
			} )
		);
	} );
	f.form.dispatchEvent(
		new SubmitEvent( 'submit', {
			bubbles: true,
			cancelable: true,
			submitter: f.button,
		} )
	);
	expect( native ).not.toHaveBeenCalled();
	finish( 'verified-proof' );
	await vi.waitFor( () => expect( native ).toHaveBeenCalledTimes( 1 ) );
	document.body.removeEventListener( 'submit', native );
	const replacement = fixture();
	connectForms();
	replacement.proof.mockResolvedValue( 'replacement-proof' );
	replacement.form.dispatchEvent(
		new SubmitEvent( 'submit', {
			bubbles: true,
			cancelable: true,
			submitter: replacement.button,
		} )
	);
	await vi.waitFor( () =>
		expect( replacement.submit ).toHaveBeenCalledTimes( 1 )
	);
} );

test( 'quantity Enter reaches native AJAX through the same verified submit', async () => {
	const f = fixture( 'enforce', 'draft_write' );
	f.form.className = 'woocommerce-cart-form';
	f.button.name = 'update_cart';
	const qty = document.createElement( 'input' );
	qty.className = 'qty';
	qty.name = 'cart[fixture][qty]';
	qty.value = '2';
	f.form.append( qty );
	f.proof.mockResolvedValue( 'quantity-proof' );
	const nativeKey = vi.fn();
	const nativeSubmit = vi.fn();
	document.body.addEventListener( 'keypress', nativeKey );
	document.body.addEventListener( 'submit', nativeSubmit );
	f.submit.mockImplementation( ( button ) => {
		f.form.dispatchEvent(
			new SubmitEvent( 'submit', {
				bubbles: true,
				cancelable: true,
				submitter: button,
			} )
		);
	} );
	qty.dispatchEvent(
		new KeyboardEvent( 'keypress', {
			bubbles: true,
			cancelable: true,
			key: 'Enter',
		} )
	);
	expect( nativeKey ).not.toHaveBeenCalled();
	await vi.waitFor( () => expect( nativeSubmit ).toHaveBeenCalledTimes( 1 ) );
	expect( f.proof ).toHaveBeenCalledTimes( 1 );
	expect( f.submit ).toHaveBeenCalledWith( f.button );
	document.body.removeEventListener( 'keypress', nativeKey );
	document.body.removeEventListener( 'submit', nativeSubmit );
} );

test( 'coupon uses native POST with its command and scoped proof instead of stripped AJAX data', async () => {
	const f = fixture( 'enforce', 'draft_write' );
	f.button.name = 'apply_coupon';
	f.proof.mockResolvedValue( 'coupon-proof' );
	const post = vi
		.spyOn( f.form, 'submit' )
		.mockImplementation( () => undefined );
	f.form.dispatchEvent(
		new SubmitEvent( 'submit', {
			bubbles: true,
			cancelable: true,
			submitter: f.button,
		} )
	);
	await vi.waitFor( () => expect( post ).toHaveBeenCalledTimes( 1 ) );
	expect(
		f.form.querySelector< HTMLInputElement >( '[name="linker_proof"]' )
			?.value
	).toBe( 'coupon-proof' );
	expect(
		f.form.querySelector< HTMLInputElement >( 'input[name="apply_coupon"]' )
			?.value
	).toBe( '1' );
	expect( f.submit ).not.toHaveBeenCalled();
} );

test( 'product quantity Enter keeps its native product form behavior', () => {
	const f = fixture( 'enforce', 'draft_write' );
	const qty = document.createElement( 'input' );
	qty.className = 'qty';
	f.form.append( qty );
	const event = new KeyboardEvent( 'keypress', {
		bubbles: true,
		cancelable: true,
		key: 'Enter',
	} );
	qty.dispatchEvent( event );
	expect( event.defaultPrevented ).toBe( false );
	expect( f.submit ).not.toHaveBeenCalled();
	expect( f.proof ).not.toHaveBeenCalled();
} );

test.each( [ 'contact', 'inquiry' ] )(
	'required %s keeps all fields after a real verification failure, then submits one verified retry',
	async ( action ) => {
		const f = fixture( 'enforce', action );
		window.linkerPublicProtection = new ProtectionClient(
			window.linkerPublicProtectionConfig!
		);
		const validation = vi.fn( async ( url: string ) => ( {
			ok: true,
			json: async () =>
				url.includes( 'prepare' )
					? {
							site_key: 'synthetic-public',
							prepare: 'synthetic-stamp',
						}
					: { proof: 'signed-proof', ttl: 300 },
		} ) );
		validation.mockRejectedValueOnce(
			new TypeError( 'synthetic network failure' )
		);
		vi.stubGlobal( 'fetch', validation );
		window.turnstile = {
			render: vi.fn( ( _container, options ) => {
				queueMicrotask( () => options.callback( 'native-token' ) );
				return 'recovered-widget';
			} ),
			reset: vi.fn(),
			remove: vi.fn(),
		};
		const submit = () =>
			f.form.dispatchEvent(
				new SubmitEvent( 'submit', {
					cancelable: true,
					submitter: f.button,
				} )
			);
		expect( submit() ).toBe( false );
		await vi.waitFor( () =>
			expect(
				f.form.querySelector( '[role="status"]' )
			).toHaveTextContent( 'No request has been sent in this attempt.' )
		);
		await vi.waitFor( () =>
			expect(
				f.form.querySelector( '[role="status"]' )
			).toHaveTextContent( 'Verification could not be completed.' )
		);
		expect( f.submit ).not.toHaveBeenCalled();
		expect( f.form.querySelector( '[name="message"]' ) ).toHaveValue(
			'Customer message'
		);
		expect( f.form.querySelector( '[name="linker_proof"]' ) ).toHaveValue(
			''
		);
		expect( submit() ).toBe( false );
		await vi.waitFor( () => expect( f.submit ).toHaveBeenCalledOnce() );
		expect( f.form.querySelector( '[name="linker_proof"]' ) ).toHaveValue(
			'signed-proof'
		);
		expect(
			f.form.querySelector( '[name="linker_request_id"]' )
		).toHaveValue( 'stable-id' );
	}
);

test.each( [ 'contact', 'inquiry' ] )(
	'a native %s recovery page checks the old UUID, then a definite refusal returns to fresh verification',
	async ( action ) => {
		const fresh = fixture( 'enforce', action );
		fresh.proof.mockResolvedValue( 'original-proof' );
		fresh.form.dispatchEvent(
			new SubmitEvent( 'submit', {
				cancelable: true,
				submitter: fresh.button,
			} )
		);
		await vi.waitFor( () => expect( fresh.submit ).toHaveBeenCalledOnce() );
		// The actual PHP FormFields contract marks only the server-restored
		// original UUID after a possibly pending/unknown native POST result.
		const restored = fixture( 'enforce', action );
		restored.form.querySelector< HTMLElement >(
			'[data-linker-protected-action]'
		)!.dataset.linkerProtectionRecovery = 'true';
		restored.proof.mockRejectedValue( new Error( 'verification_network' ) );
		restored.form.dispatchEvent( new Event( 'focusin' ) );
		restored.form.dispatchEvent( new Event( 'pointerdown' ) );
		expect( window.linkerPublicProtection?.warm ).not.toHaveBeenCalled();
		const check = new SubmitEvent( 'submit', {
			cancelable: true,
			submitter: restored.button,
		} );
		restored.form.dispatchEvent( check );
		expect( check.defaultPrevented ).toBe( false );
		expect( restored.proof ).not.toHaveBeenCalled();
		expect(
			restored.form.querySelector( '[name="linker_proof"]' )
		).toHaveValue( '' );
		expect(
			restored.form.querySelector( '[name="linker_request_id"]' )
		).toHaveValue( 'stable-id' );
		expect(
			restored.form.querySelector( '[role="status"]' )
		).toHaveTextContent( 'Checking the status of your earlier request…' );
		// If Business finds no completed result, required proof refusal is
		// definite; its next native recovery page omits the marker.
		const refused = fixture( 'enforce', action );
		refused.proof.mockResolvedValue( 'fresh-proof' );
		const retry = new SubmitEvent( 'submit', {
			cancelable: true,
			submitter: refused.button,
		} );
		refused.form.dispatchEvent( retry );
		expect( retry.defaultPrevented ).toBe( true );
		await vi.waitFor( () =>
			expect( refused.submit ).toHaveBeenCalledOnce()
		);
		expect(
			refused.form.querySelector( '[name="linker_proof"]' )
		).toHaveValue( 'fresh-proof' );
	}
);
