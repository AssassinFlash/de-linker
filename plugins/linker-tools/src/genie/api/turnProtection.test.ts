/** The real protected transport prepares proof before dispatching a turn. */
import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
	sendTurn,
	TURN_TIMEOUT_MS,
	TURN_VERIFICATION_TIMEOUT_MS,
} from './turn';

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

/** A mounted Genie surface: the widget lives in this node, not a guessed form. */
function verificationSlot() {
	const slot = document.createElement( 'div' );
	slot.dataset.linkerResourceVerificationSlot = '';
	document.body.append( slot );
	return slot;
}

test( 'verification preparation does not consume the native turn response window', async () => {
	vi.useFakeTimers();
	const slot = verificationSlot();
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
		verification: {
			slot: () => slot,
			signal: new AbortController().signal,
			challenge: true,
			onDispatch: vi.fn(),
		},
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

test( 'a dispatched turn keeps the 90-second response window, not the challenge one', async () => {
	// Preparation may wait for the customer, the answer may not: once a
	// validated proof dispatches, the connection has its original 90 seconds.
	// Preparation here takes 38 seconds — inside the shared challenge
	// lifetime — so a turn that kept the long bound would still be waiting.
	vi.useFakeTimers();
	const slot = verificationSlot();
	const proof = vi.fn( async () => {
		await new Promise( ( resolve ) => setTimeout( resolve, 38_000 ) );
		return 'synthetic-proof';
	} );
	window.linkerPublicProtection = { proof, reset: vi.fn() };
	// The proxy accepted the request and never answered it.
	const fetcher = vi.fn< typeof fetch >(
		() => new Promise< Response >( () => undefined )
	);
	let dispatchedAt = 0;
	const outcome = sendTurn( {
		...request,
		messages: [ { role: 'user', content: 'stalled answer' } ],
		fetcher,
		verification: {
			slot: () => slot,
			signal: new AbortController().signal,
			challenge: true,
			onDispatch: () => {
				dispatchedAt = Date.now();
			},
		},
	} ).then(
		() => {
			throw new Error( 'the stalled answer resolved' );
		},
		( error: unknown ) => error
	);
	let settled = false;
	void outcome.then( () => {
		settled = true;
	} );
	await vi.waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	await vi.advanceTimersByTimeAsync( 38_000 );
	expect( fetcher ).toHaveBeenCalledOnce();
	expect( dispatchedAt ).toBeGreaterThan( 0 );
	// Stop one millisecond short of the response deadline counted from the
	// actual dispatch, whatever the fake clock's absolute origin is.
	const remaining = dispatchedAt + TURN_TIMEOUT_MS - Date.now() - 1;
	expect( remaining ).toBeGreaterThan( 0 );
	await vi.advanceTimersByTimeAsync( remaining );
	expect( settled ).toBe( false );
	await vi.advanceTimersByTimeAsync( 1 );
	await expect( outcome ).resolves.toMatchObject( { name: 'AbortError' } );
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
	await vi.advanceTimersByTimeAsync( TURN_VERIFICATION_TIMEOUT_MS );
	await expect( outcome ).resolves.toMatchObject( { name: 'AbortError' } );
	expect( fetcher ).not.toHaveBeenCalled();
	release( 'late-proof' );
	await vi.advanceTimersByTimeAsync( 0 );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'a turn without a verification context never takes the challenge window', async () => {
	// A surface that sends no verification asks for no challenge, so its whole
	// request keeps the existing 90-second limit. Stretching that to the shared
	// client's 165-second lifetime would also stretch an ordinary model turn.
	vi.useFakeTimers();
	const proof = vi.fn( () => new Promise< string >( () => undefined ) );
	window.linkerPublicProtection = { proof, reset: vi.fn() };
	const fetcher = vi.fn< typeof fetch >();
	const outcome = sendTurn( {
		...request,
		messages: [ { role: 'user', content: 'ordinary unverified turn' } ],
		fetcher,
	} ).then(
		() => {
			throw new Error( 'the unverified turn resolved' );
		},
		( error: unknown ) => error
	);
	await vi.waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	await vi.advanceTimersByTimeAsync( TURN_TIMEOUT_MS );
	await expect( outcome ).resolves.toMatchObject( { name: 'AbortError' } );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'a deployment that only observes keeps the response window before dispatch too', async () => {
	// Observe records the operation and sends no proof, so no challenge is
	// running — but the turn still waits for the draft owner before it may
	// send. Without a real challenge that wait keeps the ordinary 90 seconds
	// rather than borrowing the shared client's 165-second window.
	vi.useFakeTimers();
	window.linkerPublicProtectionConfig = {
		...window.linkerPublicProtectionConfig!,
		mode: 'observe',
	};
	const proof = vi.fn( async () => 'unused-proof' );
	window.linkerPublicProtection = { proof, reset: vi.fn() };
	const slot = document.createElement( 'div' );
	slot.dataset.linkerResourceVerificationSlot = '';
	document.body.append( slot );
	const fetcher = vi.fn< typeof fetch >();
	const onDispatch = vi.fn();
	const outcome = sendTurn( {
		...request,
		messages: [ { role: 'user', content: 'observed turn' } ],
		fetcher,
		verification: {
			slot: () => slot,
			signal: new AbortController().signal,
			challenge: false,
			// The owner check never completes: this is the pre-dispatch wait.
			beforeDispatch: () => new Promise< void >( () => undefined ),
			onDispatch,
		},
	} ).then(
		() => {
			throw new Error( 'the observed turn resolved' );
		},
		( error: unknown ) => error
	);
	await vi.advanceTimersByTimeAsync( TURN_TIMEOUT_MS - 1 );
	expect( proof ).not.toHaveBeenCalled();
	expect( fetcher ).not.toHaveBeenCalled();
	expect( onDispatch ).not.toHaveBeenCalled();
	await vi.advanceTimersByTimeAsync( 1 );
	await expect( outcome ).resolves.toMatchObject( { name: 'AbortError' } );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( onDispatch ).not.toHaveBeenCalled();
	expect( vi.getTimerCount() ).toBe( 0 );
} );

test( 'an empty proof cannot mark dispatch or call the turn transport', async () => {
	const slot = document.createElement( 'div' );
	slot.dataset.linkerResourceVerificationSlot = '';
	document.body.append( slot );
	window.linkerPublicProtection = {
		proof: vi.fn( async () => '' ),
		reset: vi.fn(),
	};
	const fetcher = vi.fn< typeof fetch >();
	const onDispatch = vi.fn();
	await expect(
		sendTurn( {
			...request,
			messages: [
				{ role: 'user', content: 'Keep an empty-proof question' },
			],
			fetcher,
			verification: {
				slot: () => slot,
				signal: new AbortController().signal,
				challenge: true,
				onDispatch,
			},
		} )
	).rejects.toThrow( 'verification_unavailable' );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( onDispatch ).not.toHaveBeenCalled();
	expect( slot.hidden ).toBe( true );
} );

test( 'synchronous operation cancellation is checked before the actual dispatch callback', async () => {
	const slot = document.createElement( 'div' );
	slot.dataset.linkerResourceVerificationSlot = '';
	document.body.append( slot );
	window.linkerPublicProtection = {
		proof: vi.fn( async () => 'cached-proof' ),
		reset: vi.fn(),
	};
	const controller = new AbortController();
	const fetcher = vi.fn< typeof fetch >();
	const onDispatch = vi.fn();
	await expect(
		sendTurn( {
			...request,
			messages: [ { role: 'user', content: 'Synchronous cancel' } ],
			fetcher,
			onOperation: () =>
				controller.abort( new Error( 'verification_cancelled' ) ),
			verification: {
				slot: () => slot,
				signal: controller.signal,
				challenge: true,
				onDispatch,
			},
		} )
	).rejects.toThrow( 'verification_cancelled' );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( onDispatch ).not.toHaveBeenCalled();
} );
