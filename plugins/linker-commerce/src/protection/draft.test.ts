import { afterEach, expect, test, vi } from 'vitest';
import { ProtectionClient } from './client';
import { connectDraftLinks } from './draft';
import type { TurnstileOptions } from './types';

afterEach( () => {
	window.linkerPublicProtection?.reset( 'draft_write' );
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
	delete window.turnstile;
	vi.unstubAllGlobals();
	document.body.replaceChildren();
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
