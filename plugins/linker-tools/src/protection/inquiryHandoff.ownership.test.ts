import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { rememberInquiry, restoreInquiry } from './inquiryHandoff';

const A = 'a'.repeat( 64 );
const B = 'b'.repeat( 64 );
const prefix = 'linker-genie-inquiry-handoff:v2:';
const config = { restUrl: '/wp-json/', restNonce: 'native-current' };

function destination(): HTMLTextAreaElement {
	window.history.replaceState( null, '', '/proforma-request/' );
	document.body.innerHTML = '<textarea id="inquiry-message"></textarea>';
	return document.querySelector( 'textarea' )!;
}

function pendingIdentity() {
	let finish!: ( scope?: string ) => void;
	vi.stubGlobal(
		'fetch',
		vi.fn(
			() =>
				new Promise( ( resolve ) => {
					finish = ( scope = A ) =>
						resolve( {
							ok: true,
							json: async () => ( { scope } ),
						} );
				} )
		)
	);
	return ( scope = A ) => finish( scope );
}

function currentIdentity( scope = A ) {
	const request = vi.fn( async () => ( {
		ok: true,
		json: async () => ( { scope } ),
	} ) );
	vi.stubGlobal( 'fetch', request );
	return request;
}

beforeEach( () => {
	window.sessionStorage.clear();
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieNativeScope;
	window.history.replaceState( null, '', '/genie/' );
	document.body.innerHTML = '';
} );

afterEach( () => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	window.sessionStorage.clear();
	document.body.innerHTML = '';
} );

for ( const [ identity, scope ] of [
	[ 'another customer', 'b'.repeat( 64 ) ],
	[ 'signed-out guest', 'c'.repeat( 64 ) ],
] as const ) {
	test( `ordinary fallback never puts A's accepted question into ${ identity }'s native inquiry`, async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn( async () => ( {
				ok: true,
				json: async () => ( { scope } ),
			} ) )
		);
		rememberInquiry( '/proforma-request/', 'Private A project costs', A );
		const before = Object.fromEntries(
			Object.keys( window.sessionStorage ).map( ( key ) => [
				key,
				window.sessionStorage.getItem( key ),
			] )
		);
		window.history.replaceState( null, '', '/proforma-request/' );
		document.body.innerHTML =
			'<textarea id="inquiry-message">Current native inquiry default</textarea>';
		await restoreInquiry( config );
		expect( document.querySelector( 'textarea' )!.value ).toBe(
			'Current native inquiry default'
		);
		for ( const [ key, raw ] of Object.entries( before ) ) {
			expect( window.sessionStorage.getItem( key ) ).toBe( raw );
		}
	} );
}

test( 'late native identity cannot fill or consume a newer same-owner navigation', async () => {
	rememberInquiry( '/proforma-request/', 'First accepted A question', A );
	const field = destination();
	const finish = pendingIdentity();
	const firstRestore = restoreInquiry( config );
	expect( fetch ).toHaveBeenCalledTimes( 1 );
	expect(
		rememberInquiry( '/proforma-request/', 'Newer accepted A question', A )
	).toBe( true );
	const newer = window.sessionStorage.getItem( prefix + A );
	finish();
	await firstRestore;
	expect( field.value ).toBe( field.defaultValue );
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe( newer );
	const explicitRestore = restoreInquiry( config );
	expect( fetch ).toHaveBeenCalledTimes( 2 );
	finish();
	await explicitRestore;
	expect( field.value ).toBe( 'Newer accepted A question' );
	expect( window.sessionStorage.getItem( prefix + A ) ).toBeNull();
} );

test( 'a slot created during the identity await needs a later explicit restore', async () => {
	rememberInquiry( '/proforma-request/', 'Foreign B question', B );
	const foreign = window.sessionStorage.getItem( prefix + B );
	const field = destination();
	const finish = pendingIdentity();
	const pending = restoreInquiry( config );
	rememberInquiry( '/proforma-request/', 'Newly accepted A question', A );
	const created = window.sessionStorage.getItem( prefix + A );
	finish();
	await pending;
	expect( field.value ).toBe( field.defaultValue );
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe( created );
	currentIdentity();
	await restoreInquiry( config );
	expect( field.value ).toBe( 'Newly accepted A question' );
	expect( window.sessionStorage.getItem( prefix + B ) ).toBe( foreign );
} );

for ( const mutation of [
	'edited then reverted',
	'default changed',
	'retained submission appeared',
	'field replaced',
	'path changed',
	'identity lifecycle changed',
] as const ) {
	test( `late restore preserves its raw handoff when ${ mutation }`, async () => {
		rememberInquiry( '/proforma-request/', 'Accepted A question', A );
		const raw = window.sessionStorage.getItem( prefix + A );
		const field = destination();
		const finish = pendingIdentity();
		const pending = restoreInquiry( config );
		if ( mutation === 'edited then reverted' ) {
			field.value = 'Customer edits during lookup';
			field.dispatchEvent( new Event( 'input', { bubbles: true } ) );
			field.value = field.defaultValue;
		} else if ( mutation === 'default changed' ) {
			field.defaultValue = 'Updated native server default';
		} else if ( mutation === 'retained submission appeared' ) {
			const form = document.createElement( 'form' );
			field.before( form );
			form.append( field );
			form.insertAdjacentHTML(
				'beforeend',
				'<input type="hidden" name="linker_inquiry_retained" value="1">'
			);
		} else if ( mutation === 'field replaced' ) {
			field.outerHTML =
				'<textarea id="inquiry-message">Replacement native field</textarea>';
		} else if ( mutation === 'path changed' ) {
			window.history.replaceState( null, '', '/another-request-page/' );
		} else {
			window.dispatchEvent( new Event( 'linker-genie-identity-change' ) );
		}
		const current = document.querySelector( 'textarea' )!;
		const before = current.value;
		finish();
		await pending;
		expect( current.value ).toBe( before );
		expect( window.sessionStorage.getItem( prefix + A ) ).toBe( raw );
	} );
}

test( 'current owner restores independently while legacy, unknown and foreign bytes stay intact', async () => {
	const legacy =
		'{"path":"/proforma-request/","message":"Legacy private question","expires":9}';
	window.sessionStorage.setItem( 'linker-genie-inquiry-handoff', legacy );
	window.sessionStorage.setItem( prefix + A, '{foreign malformed bytes' );
	expect(
		rememberInquiry( '/proforma-request/', 'Current B question', B )
	).toBe( true );
	const field = destination();
	currentIdentity( B );
	await restoreInquiry( config );
	expect( field.value ).toBe( 'Current B question' );
	expect( window.sessionStorage.getItem( prefix + B ) ).toBeNull();
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe(
		'{foreign malformed bytes'
	);
	expect(
		window.sessionStorage.getItem( 'linker-genie-inquiry-handoff' )
	).toBe( legacy );
} );

test( 'empty sender clears only its verified own slot and never legacy or foreign data', () => {
	const legacy = 'unknown ownerless bytes';
	window.sessionStorage.setItem( 'linker-genie-inquiry-handoff', legacy );
	rememberInquiry( '/proforma-request/', 'A question', A );
	const foreign = window.sessionStorage.getItem( prefix + A );
	rememberInquiry( '/proforma-request/', 'B question', B );
	expect( rememberInquiry( '/proforma-request/', '', B ) ).toBe( true );
	expect( window.sessionStorage.getItem( prefix + B ) ).toBeNull();
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe( foreign );
	expect(
		window.sessionStorage.getItem( 'linker-genie-inquiry-handoff' )
	).toBe( legacy );
} );

test( 'unknown own-slot bytes cannot be replaced, cleared or restored', async () => {
	const unknown = '{"v":3,"message":"Unknown future format"}';
	window.sessionStorage.setItem( prefix + A, unknown );
	expect( rememberInquiry( '/proforma-request/', 'New question', A ) ).toBe(
		false
	);
	expect( rememberInquiry( '/proforma-request/', '', A ) ).toBe( false );
	const field = destination();
	currentIdentity();
	await restoreInquiry( config );
	expect( field.value ).toBe( field.defaultValue );
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe( unknown );
} );

test( 'sender rejects missing original ownership and cross-origin destinations without a native request', () => {
	const request = currentIdentity();
	expect( rememberInquiry( '/proforma-request/', 'Private text', '' ) ).toBe(
		false
	);
	expect(
		rememberInquiry( 'https://foreign.example/inquiry/', 'Private text', A )
	).toBe( false );
	expect( window.sessionStorage.length ).toBe( 0 );
	expect( request ).not.toHaveBeenCalled();
} );

test( 'missing native mount leaves the handoff and native field untouched', async () => {
	rememberInquiry( '/proforma-request/', 'Accepted A question', A );
	const raw = window.sessionStorage.getItem( prefix + A );
	const field = destination();
	const request = currentIdentity();
	await restoreInquiry();
	expect( field.value ).toBe( field.defaultValue );
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe( raw );
	expect( request ).not.toHaveBeenCalled();
} );

for ( const failure of [
	'native unavailable',
	'tab storage unavailable',
	'handoff read failed',
] as const ) {
	test( `${ failure } cannot claim the cached text or consume its bytes`, async () => {
		rememberInquiry( '/proforma-request/', 'Accepted A question', A );
		const raw = window.sessionStorage.getItem( prefix + A );
		const field = destination();
		const request = currentIdentity();
		if ( failure === 'native unavailable' ) {
			request.mockRejectedValue(
				new Error( 'Native context unavailable' )
			);
		} else {
			const nativeGet = Storage.prototype.getItem;
			vi.spyOn( Storage.prototype, 'getItem' ).mockImplementation(
				function ( this: Storage, key: string ) {
					if (
						key ===
						( failure === 'tab storage unavailable'
							? 'linker-genie-entry-tab'
							: prefix + A )
					) {
						throw new Error( 'Storage read unavailable' );
					}
					return nativeGet.call( this, key );
				}
			);
		}
		await restoreInquiry( config );
		expect( field.value ).toBe( field.defaultValue );
		vi.restoreAllMocks();
		expect( window.sessionStorage.getItem( prefix + A ) ).toBe( raw );
	} );
}

test( 'failed persistent write reports failure and preserves the prior accepted navigation', () => {
	rememberInquiry( '/proforma-request/', 'First A question', A );
	const raw = window.sessionStorage.getItem( prefix + A );
	vi.spyOn( Storage.prototype, 'setItem' ).mockImplementation( () => {
		throw new Error( 'Storage quota' );
	} );
	expect( rememberInquiry( '/proforma-request/', 'New A question', A ) ).toBe(
		false
	);
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe( raw );
} );

test( 'failed exact removal never fills the native field', async () => {
	rememberInquiry( '/proforma-request/', 'Accepted A question', A );
	const raw = window.sessionStorage.getItem( prefix + A );
	const field = destination();
	currentIdentity();
	vi.spyOn( Storage.prototype, 'removeItem' ).mockImplementation( () => {
		throw new Error( 'Storage removal unavailable' );
	} );
	await restoreInquiry( config );
	expect( field.value ).toBe( field.defaultValue );
	expect( window.sessionStorage.getItem( prefix + A ) ).toBe( raw );
} );

test( 'the real DOM-ready entry reads only existing native route config and restores the same owner once', async () => {
	rememberInquiry( '/proforma-request/', 'Accepted A question', A );
	const field = destination();
	document.body.insertAdjacentHTML(
		'beforeend',
		'<div data-linker-app="genie" data-rest-url="/wp-json" data-rest-nonce="native-mounted"></div>'
	);
	const request = currentIdentity();
	const onInput = vi.fn();
	field.addEventListener( 'input', onInput );
	vi.spyOn( document, 'readyState', 'get' ).mockReturnValue( 'loading' );
	await import( './inquiryEntry' );
	expect( request ).not.toHaveBeenCalled();
	document.dispatchEvent( new Event( 'DOMContentLoaded' ) );
	await vi.waitFor( () =>
		expect( field.value ).toBe( 'Accepted A question' )
	);
	expect( request ).toHaveBeenCalledExactlyOnceWith(
		'/wp-json/linker-ai/v1/genie/entry-context',
		expect.objectContaining( {
			method: 'POST',
			credentials: 'same-origin',
			cache: 'no-store',
			headers: expect.objectContaining( {
				'X-WP-Nonce': 'native-mounted',
			} ),
		} )
	);
	document.dispatchEvent( new Event( 'DOMContentLoaded' ) );
	expect( onInput ).toHaveBeenCalledTimes( 1 );
	expect( request ).toHaveBeenCalledTimes( 1 );
	expect( window.sessionStorage.getItem( prefix + A ) ).toBeNull();
} );
