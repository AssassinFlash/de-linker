import { afterEach, expect, test, vi } from 'vitest';
import { connectForms } from './forms';

afterEach( () => {
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	document.body.replaceChildren();
} );

function fixture( mode = 'enforce' ) {
	document.body.innerHTML =
		'<form><input name="message" value="Customer message"><input name="linker_request_id" value="stable-id" data-linker-protected-action="inquiry"><input name="linker_proof"><div data-linker-protection-widget hidden></div><p data-linker-protection-status hidden></p><button type="submit" name="send" value="1">Send inquiry</button></form>';
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
		).toContain( 'Your entries are still here' )
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
