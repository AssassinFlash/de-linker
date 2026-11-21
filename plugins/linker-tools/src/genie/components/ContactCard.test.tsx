/**
 * "Let Linker contact me" (#243): a guest leaves an address, a signed-in
 * customer is never asked for one, and the card promises a reply within one
 * business day.
 */

/**
 * External dependencies
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { readContact } from '../api/contact';
import type { ContactReason } from '../api/turn';
import { ContactCard } from './ContactCard';

const URL = '/wp-json/linker-ai/v1/genie/contact';
const PAGE = { type: 'product', url: 'https://de-linker.test/product/x/' };

interface Call {
	method: string;
	body: Record< string, unknown > | null;
}

/**
 * A route double: GET answers `state`, POST answers `reply` with `status`.
 *
 * @param state  The GET answer.
 * @param reply  The POST answer.
 * @param status The POST status.
 */
function route(
	state: Record< string, unknown >,
	reply: Record< string, unknown > = {},
	status = 200
) {
	const calls: Call[] = [];
	const fetcher = async ( _url: RequestInfo | URL, init?: RequestInit ) => {
		const method = init?.method ?? 'GET';
		calls.push( {
			method,
			body: init?.body ? JSON.parse( String( init.body ) ) : null,
		} );
		const answer = 'GET' === method ? { source: '7:2', ...state } : reply;
		return new Response( JSON.stringify( answer ), {
			status: 'GET' === method ? 200 : status,
		} );
	};
	return { calls, fetcher: fetcher as typeof fetch };
}

function card( fetcher: typeof fetch, reason: ContactReason = 'asked' ) {
	return render(
		<ContactCard
			block={ { type: 'contact', reason } }
			contactUrl={ URL }
			nonce="n"
			locale="en"
			page={ PAGE }
			fetcher={ fetcher }
		/>
	);
}

afterEach( () => {
	delete window.linkerTurnstile;
} );

test( 'one guest click waits for verification and an edit cancels that intent', async () => {
	const { calls, fetcher } = route( {
		email: null,
		sent: null,
		mailbox: 'sales@de-linker.com',
	} );
	let answer: ( value: string ) => void;
	window.linkerTurnstile = {
		mount: ( _node, _action, ready ) => {
			answer = ready;
			return () => {};
		},
		refresh: vi.fn(),
	};
	card( fetcher );
	const email = await screen.findByRole( 'textbox', { name: /email/i } );
	fireEvent.change( email, { target: { value: 'maria@example.test' } } );
	fireEvent.click( screen.getByRole( 'checkbox' ) );
	const send = screen.getByRole( 'button', { name: 'Contact me' } );
	fireEvent.click( send );
	expect( calls.filter( ( row ) => row.method === 'POST' ) ).toHaveLength(
		0
	);
	fireEvent.change( email, { target: { value: 'ellen@example.test' } } );
	answer!( 'verified-after-edit' );
	expect( calls.filter( ( row ) => row.method === 'POST' ) ).toHaveLength(
		0
	);
	answer!( '' );
	fireEvent.click( send );
	fireEvent.click( send );
	answer!( 'fresh' );
	await waitFor( () =>
		expect( calls.filter( ( row ) => row.method === 'POST' ) ).toHaveLength(
			1
		)
	);
	expect( calls.at( -1 )?.body?.email ).toBe( 'ellen@example.test' );
} );

test( 'an anonymous contact submits its widget answer with the native request', async () => {
	const { calls, fetcher } = route( { email: null }, { sent: true } );
	const mount = vi.fn( ( _node, _action, ready ) => {
		ready( 'widget-answer' );
		return () => {};
	} );
	window.linkerTurnstile = { mount, refresh: vi.fn() };
	card( fetcher );
	await waitFor( () => expect( mount ).toHaveBeenCalledOnce() );
	fireEvent.click( screen.getByRole( 'button', { name: 'Contact me' } ) );
	await waitFor( () =>
		expect( calls.at( -1 )?.body?.[ 'cf-turnstile-response' ] ).toBe(
			'widget-answer'
		)
	);
} );

test( 'a guest leaves an address and reads the one-business-day promise', async () => {
	const { calls, fetcher } = route(
		{
			started: '100',
			started_nonce: 'sig',
			email: null,
			sent: null,
			mailbox: 'sales@de-linker.com',
		},
		{ sent: true, email: 'maria@example.test', receipt: true }
	);
	card( fetcher );
	expect(
		screen.getByText(
			'Leave your email address and the team replies within one business day.'
		)
	).toBeTruthy();
	const field = await screen.findByLabelText( 'Your email address' );
	fireEvent.change( field, { target: { value: ' maria@example.test ' } } );
	fireEvent.click(
		screen.getByLabelText(
			'I agree that my details may be used to respond to this message.'
		)
	);
	await waitFor( () =>
		expect(
			screen
				.getByRole( 'button', { name: 'Contact me' } )
				.hasAttribute( 'disabled' )
		).toBe( false )
	);
	fireEvent.click( screen.getByRole( 'button', { name: 'Contact me' } ) );
	await screen.findByText( 'Your request is with the Linker team' );
	expect(
		screen.getByText(
			'The team replies to maria@example.test within one business day.'
		)
	).toBeTruthy();
	const post = calls.find( ( call ) => 'POST' === call.method );
	expect( post?.body ).toEqual( {
		source: '7:2',
		'cf-turnstile-response': 'native-test-response',
		email: 'maria@example.test',
		website: '',
		consent: '1',
		reason: 'asked',
		locale: 'en',
		page: PAGE,
	} );
} );

test( 'a signed-in customer is not asked for an address', async () => {
	const { calls, fetcher } = route(
		{
			started: '100',
			started_nonce: 'sig',
			email: 'maria@firma.test',
			sent: null,
			mailbox: 'sales@de-linker.com',
		},
		{ sent: true, email: 'maria@firma.test', receipt: true }
	);
	card( fetcher, 'dissatisfied' );
	await screen.findByText(
		'The team replies to maria@firma.test within one business day.'
	);
	expect(
		screen.getByText( 'Should someone from the Linker team get in touch?' )
	).toBeTruthy();
	expect( screen.queryByLabelText( 'Your email address' ) ).toBeNull();
	fireEvent.click( screen.getByRole( 'button', { name: 'Contact me' } ) );
	await screen.findByText( 'Your request is with the Linker team' );
	const post = calls.find( ( call ) => 'POST' === call.method );
	expect( post?.body && 'email' in post.body ).toBe( false );
} );

test( 'a received contact has no mail omission while delivery is pending', async () => {
	const { fetcher } = route( {
		sent: { email: 'maria@example.test', receipt: null },
	} );
	const result = await readContact( '/contact', 'nonce', fetcher );
	expect( result?.sent?.receipt ).toBeNull();
	card( fetcher );
	await screen.findByText( 'Your request is with the Linker team' );
	expect(
		screen.queryByText( 'We have not sent a confirmation email.' )
	).toBeNull();
} );

test( 'a request already with the team shows as sent', async () => {
	const { fetcher } = route( {
		email: null,
		sent: { email: 'maria@example.test', receipt: false },
	} );
	card( fetcher );
	await screen.findByText( 'Your request is with the Linker team' );
	expect( screen.queryByRole( 'button' ) ).toBeNull();
	// The receipt cap held the receipt back: the card says so.
	expect(
		screen.getByText( 'We have not sent a confirmation email.' )
	).toBeTruthy();
} );

test.each( [
	[
		'linker_genie_contact_email',
		400,
		'Please enter a valid email address.',
	],
	[
		'linker_genie_contact_consent',
		400,
		'Please agree to the use of your details for the reply.',
	],
	[
		'linker_genie_contact_limited',
		429,
		'Genie cannot pass on your request right now. Please try again later or write to sales@de-linker.com.',
	],
	[
		'linker_genie_contact_unavailable',
		503,
		'Genie cannot pass on your request right now. Please try again later or write to sales@de-linker.com.',
	],
] )(
	'a refusal (%s) says why and keeps the form',
	async ( code, status, text ) => {
		const { fetcher } = route(
			{
				started: '100',
				started_nonce: 'sig',
				email: null,
				sent: null,
				mailbox: 'sales@de-linker.com',
			},
			{ code },
			status
		);
		card( fetcher );
		fireEvent.change(
			await screen.findByLabelText( 'Your email address' ),
			{
				target: { value: 'not-an-address' },
			}
		);
		await waitFor( () =>
			expect(
				screen
					.getByRole( 'button', { name: 'Contact me' } )
					.hasAttribute( 'disabled' )
			).toBe( false )
		);
		fireEvent.click( screen.getByRole( 'button', { name: 'Contact me' } ) );
		expect( ( await screen.findByRole( 'alert' ) ).textContent ).toBe(
			text
		);
		expect(
			screen.getByRole( 'button', { name: 'Contact me' } )
		).toBeTruthy();
	}
);
