/** The real protected transport prepares proof before dispatching a turn. */
import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { sendTurn, TURN_TIMEOUT_MS } from './turn';

beforeEach( () => {
	vi.stubGlobal( 'crypto', webcrypto );
	document.body.innerHTML = '<main><form><textarea></textarea></form></main>';
	window.linkerPublicProtectionConfig = {
		api: 'https://site.test/wp-json/linker/v1/protection',
		nonce: 'synthetic',
		mode: 'enforce',
		language: 'en',
	};
} );

afterEach( () => {
	vi.useRealTimers();
	delete window.linkerPublicProtectionConfig;
	delete window.linkerPublicProtection;
	vi.unstubAllGlobals();
} );

const request = {
	turnUrl: 'https://site.test/wp-json/linker-ai/v1/genie/turn',
	nonce: 'synthetic',
	locale: 'en' as const,
	page: { type: 'category' as const },
};

test( 'verification preparation does not consume the native turn response window', async () => {
	vi.useFakeTimers();
	const proof = vi.fn( async () => {
		await new Promise( ( resolve ) => setTimeout( resolve, 38_000 ) );
		return 'synthetic-proof';
	} );
	window.linkerPublicProtection = { proof, reset: vi.fn() };
	const onOperation = vi.fn();
	const fetcher = vi.fn< typeof fetch >( async ( _url, init ) => {
		expect( new Headers( init?.headers ).get( 'X-Linker-Proof' ) ).toBe(
			'synthetic-proof'
		);
		await new Promise( ( resolve ) => setTimeout( resolve, 60_001 ) );
		return new Response(
			JSON.stringify( {
				stream:
					'event: block\ndata: {"type":"text","text":"25000 W","refs":[]}\n\n' +
					'event: done\ndata: {"ok":true}\n\n',
			} )
		);
	} );
	const outcome = sendTurn( {
		...request,
		messages: [
			{ role: 'user', content: 'slow verification power check' },
		],
		fetcher,
		onOperation,
	} ).then(
		( turn ) => turn,
		( error: unknown ) => error
	);
	await vi.waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	await vi.advanceTimersByTimeAsync( 38_000 );
	expect( fetcher ).toHaveBeenCalledOnce();
	await vi.advanceTimersByTimeAsync( 60_001 );
	await expect( outcome ).resolves.toMatchObject( {
		blocks: [ { type: 'text', text: '25000 W' } ],
	} );
	expect( onOperation ).toHaveBeenCalledOnce();
	expect( fetcher ).toHaveBeenCalledOnce();
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'a hanging verification is bounded and a late proof cannot dispatch the timed-out turn', async () => {
	vi.useFakeTimers();
	let release: ( value: string ) => void = () => undefined;
	const proof = vi.fn(
		() => new Promise< string >( ( resolve ) => ( release = resolve ) )
	);
	window.linkerPublicProtection = { proof, reset: vi.fn() };
	const fetcher = vi.fn< typeof fetch >();
	const outcome = sendTurn( {
		...request,
		messages: [ { role: 'user', content: 'hanging verification check' } ],
		fetcher,
	} ).then(
		() => {
			throw new Error( 'the hanging verification resolved' );
		},
		( error: unknown ) => error
	);
	await vi.waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	await vi.advanceTimersByTimeAsync( TURN_TIMEOUT_MS );
	await expect( outcome ).resolves.toMatchObject( { name: 'AbortError' } );
	expect( fetcher ).not.toHaveBeenCalled();
	release( 'late-proof' );
	await vi.advanceTimersByTimeAsync( 0 );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( vi.getTimerCount() ).toBe( 0 );
} );
