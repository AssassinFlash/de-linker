/**
 * The inquiry confirmation card (#250): a guest gives the request page's own
 * details, a signed-in customer's come from the account, the card sends exactly
 * the lines it showed, and the sent card states the record's number and status.
 */

/**
 * External dependencies
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { InquiryState, SentInquiry } from '../api/inquiry';
import { InquiryCard } from './InquiryCard';

const URL = '/wp-json/linker-ai/v1/genie/inquiry';

interface Call {
	method: string;
	body: Record< string, unknown > | null;
}

function state( overrides: Partial< InquiryState > = {} ): InquiryState {
	return {
		conversation: 7,
		started: '100',
		startedNonce: 'sig',
		account: null,
		lines: [
			{
				product_id: 4107,
				name: 'SAJ H2-10K-T3',
				sku: 'H2-10K-T3',
				quantity: 2,
				price_html: '<span>1.234,00&nbsp;€</span>',
				url: 'https://de-linker.test/product/saj-h2-10k-t3/',
			},
		],
		linesDigest: 'digest-1',
		message: 'We need two units this quarter.',
		summary: 'Two inverters for a three-phase rooftop.',
		sent: null,
		pageUrl: 'https://de-linker.test/inquiry/',
		...overrides,
	};
}

const SENT: SentInquiry = {
	order: 123,
	number: '123',
	status: 'inquiry-received',
	receipt: true,
	email: 'maria@example.test',
	url: 'https://de-linker.test/checkout/order-received/123/?key=abc',
};

/**
 * The route's wire shape (InquiryRequest::state()): snake_case keys.
 *
 * @param value The card's state.
 */
function wire( value: InquiryState ) {
	return {
		conversation: value.conversation,
		started: value.started,
		started_nonce: value.startedNonce,
		account: value.account,
		lines: value.lines,
		lines_digest: value.linesDigest,
		message: value.message,
		summary: value.summary,
		sent: value.sent,
		page_url: value.pageUrl,
	};
}

/**
 * A route double: GET answers the states in order (the last one repeats), POST
 * answers `reply` with `status`.
 *
 * @param states The GET answers, in order.
 * @param reply  The POST answer.
 * @param status The POST status.
 */
function route(
	states: InquiryState[],
	reply: Record< string, unknown > = {
		sent: true,
		inquiry: SENT,
	},
	status = 200
) {
	const calls: Call[] = [];
	let reads = 0;
	const fetcher = async ( _url: RequestInfo | URL, init?: RequestInit ) => {
		const method = init?.method ?? 'GET';
		calls.push( {
			method,
			body: init?.body ? JSON.parse( String( init.body ) ) : null,
		} );
		if ( 'GET' === method ) {
			const answer = states[ Math.min( reads, states.length - 1 ) ];
			reads += 1;
			return new Response( JSON.stringify( wire( answer ) ), {
				status: 200,
			} );
		}
		return new Response( JSON.stringify( reply ), {
			status,
			headers: { 'Content-Type': 'application/json' },
		} );
	};
	return { calls, fetcher: fetcher as typeof fetch };
}

function card( fetcher: typeof fetch, onSent = vi.fn() ) {
	return {
		onSent,
		...render(
			<InquiryCard
				inquiryUrl={ URL }
				nonce="n"
				locale="en"
				onSent={ onSent }
				fetcher={ fetcher }
			/>
		),
	};
}

async function guestDetails() {
	fireEvent.change( await screen.findByLabelText( 'Name' ), {
		target: { value: ' Maria Weber ' },
	} );
	fireEvent.change( screen.getByLabelText( 'Reply email' ), {
		target: { value: 'maria@example.test' },
	} );
	fireEvent.click(
		screen.getByLabelText(
			'I agree that my details may be used to respond to this message.'
		)
	);
}

test( 'the card shows every line it will send and the one-business-day promise', async () => {
	const { fetcher } = route( [ state() ] );
	card( fetcher );
	expect( await screen.findByText( 'SAJ H2-10K-T3' ) ).toBeTruthy();
	expect( screen.getByText( '× 2' ) ).toBeTruthy();
	expect( screen.getByText( 'H2-10K-T3' ) ).toBeTruthy();
	expect( screen.getByText( '1.234,00 €' ) ).toBeTruthy();
	expect(
		screen.getByText( 'We reply within one business day.' )
	).toBeTruthy();
	expect(
		screen.getByLabelText( 'Attach the conversation summary' )
	).toBeTruthy();
} );

test( 'a guest fills name, address and consent, and the send carries the card', async () => {
	const { calls, fetcher } = route( [ state() ] );
	const { onSent } = card( fetcher );
	await guestDetails();
	fireEvent.click( screen.getByRole( 'button', { name: 'Send inquiry' } ) );
	expect(
		await screen.findByText( 'Inquiry #123 · Inquiry received' )
	).toBeTruthy();
	expect( screen.getByText( 'View your inquiry' ) ).toBeTruthy();
	expect(
		screen.getByText( 'The team replies within one business day.' )
	).toBeTruthy();
	expect( onSent ).toHaveBeenCalledWith( SENT );
	const post = calls.find( ( call ) => 'POST' === call.method );
	expect( post?.body ).toEqual( {
		name: 'Maria Weber',
		email: 'maria@example.test',
		company: '',
		message: 'We need two units this quarter.',
		attach_summary: '1',
		lines: 'digest-1',
		website: '',
		started: '100',
		started_nonce: 'sig',
		consent: '1',
		locale: 'en',
	} );
} );

test( 'a signed-in customer is not asked for details', async () => {
	const { calls, fetcher } = route( [
		state( {
			account: {
				email: 'partner@example.test',
				name: 'Maria Weber',
				company: 'Weber Solar',
			},
		} ),
	] );
	card( fetcher );
	expect( await screen.findByText( 'SAJ H2-10K-T3' ) ).toBeTruthy();
	expect( screen.queryByLabelText( 'Name' ) ).toBeNull();
	expect( screen.queryByLabelText( 'Reply email' ) ).toBeNull();
	fireEvent.click( screen.getByRole( 'button', { name: 'Send inquiry' } ) );
	await screen.findByText( 'Inquiry #123 · Inquiry received' );
	const post = calls.find( ( call ) => 'POST' === call.method );
	expect( post?.body ).toMatchObject( {
		name: '',
		email: '',
		message: 'We need two units this quarter.',
		attach_summary: '1',
		lines: 'digest-1',
		consent: '',
	} );
} );

test( 'the summary switch off sends without the summary', async () => {
	const { calls, fetcher } = route( [ state() ] );
	card( fetcher );
	await guestDetails();
	fireEvent.click(
		screen.getByLabelText( 'Attach the conversation summary' )
	);
	fireEvent.click( screen.getByRole( 'button', { name: 'Send inquiry' } ) );
	await screen.findByText( 'Inquiry #123 · Inquiry received' );
	const post = calls.find( ( call ) => 'POST' === call.method );
	expect( post?.body?.attach_summary ).toBe( '' );
} );

test( 'an empty draft sends nothing and names the inquiry page', async () => {
	const { calls, fetcher } = route( [ state( { lines: [], message: '' } ) ] );
	card( fetcher );
	expect(
		await screen.findByText( 'No products in your solution draft.' )
	).toBeTruthy();
	expect(
		screen.getByText(
			'Add a product to your solution draft or write a message.'
		)
	).toBeTruthy();
	expect(
		screen
			.getByRole( 'button', { name: 'Send inquiry' } )
			.hasAttribute( 'disabled' )
	).toBe( true );
	expect(
		screen.getByRole( 'link', { name: 'Open the inquiry page' } )
	).toBeTruthy();
	expect( calls.some( ( call ) => 'POST' === call.method ) ).toBe( false );
} );

test( 'the card refuses a send without a name, an address or consent', async () => {
	const { calls, fetcher } = route( [ state() ] );
	card( fetcher );
	await screen.findByText( 'SAJ H2-10K-T3' );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send inquiry' } ) );
	expect( await screen.findByText( 'Please add your name.' ) ).toBeTruthy();
	fireEvent.change( screen.getByLabelText( 'Name' ), {
		target: { value: 'Maria Weber' },
	} );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send inquiry' } ) );
	expect(
		await screen.findByText(
			'Please add an email address we can reply to.'
		)
	).toBeTruthy();
	fireEvent.change( screen.getByLabelText( 'Reply email' ), {
		target: { value: 'maria@example.test' },
	} );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send inquiry' } ) );
	expect(
		await screen.findByText(
			'Please agree to the use of your details for the reply.'
		)
	).toBeTruthy();
	expect( calls.some( ( call ) => 'POST' === call.method ) ).toBe( false );
} );

test( 'a draft that changed is shown again and the send is refused once', async () => {
	const changed = state( {
		lines: [
			{
				product_id: 4108,
				name: 'SAJ H2-8K-T3',
				sku: 'H2-8K-T3',
				quantity: 1,
				price_html: '<span>999,00&nbsp;€</span>',
				url: 'https://de-linker.test/product/saj-h2-8k-t3/',
			},
		],
		linesDigest: 'digest-2',
	} );
	const { calls, fetcher } = route(
		[ state(), changed ],
		{ sent: false, code: 'linker_genie_inquiry_changed' },
		409
	);
	card( fetcher );
	await guestDetails();
	fireEvent.click( screen.getByRole( 'button', { name: 'Send inquiry' } ) );
	expect(
		await screen.findByText(
			'Your solution draft changed. Check the lines and send the inquiry again.'
		)
	).toBeTruthy();
	expect( screen.getByText( 'SAJ H2-8K-T3' ) ).toBeTruthy();
	expect( calls.filter( ( call ) => 'GET' === call.method ).length ).toBe(
		2
	);
} );

test( 'an inquiry this conversation already sent shows the record', async () => {
	const { fetcher } = route( [ state( { sent: SENT } ) ] );
	const onSent = vi.fn();
	card( fetcher, onSent );
	expect(
		await screen.findByText( 'Your inquiry is with the Linker team' )
	).toBeTruthy();
	expect(
		screen.getByText( 'Inquiry #123 · Inquiry received' )
	).toBeTruthy();
	await waitFor( () => expect( onSent ).toHaveBeenCalledWith( SENT ) );
} );
