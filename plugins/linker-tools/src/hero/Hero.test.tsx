// @vitest-environment jsdom

/**
 * The conversation the hero unfolds (ticket #232): the header and its two
 * exits, the stored thread, a real turn through the session, the #236
 * attachment card and its manual-model exit, and files riding with a turn.
 */

/**
 * External dependencies
 */
import {
	act,
	fireEvent,
	render,
	screen,
	waitFor,
} from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { GenieConfig } from '../genie/config';
import {
	TurnError,
	UnfinishedStreamError,
	type Turn,
	type TurnMessage,
} from '../genie/api/turn';
import type { Upload } from '../genie/attachments/prepare';
import { HeroConversation, type HeroBridge } from './Hero';
import { HeroSession, type HeroSessionConfig } from './session';

vi.mock( '../genie/api/contact', () => ( {
	readContact: vi.fn( async () => ( {
		started: '100.sig',
		email: null,
		sent: null,
		mailbox: 'sales@de-linker.com',
	} ) ),
	sendContact: vi.fn(),
} ) );
vi.mock( '../genie/api/inquiry', () => ( {
	readInquiry: vi.fn( async () => ( {
		conversation: 5,
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
	} ) ),
	sendInquiry: vi.fn(),
} ) );
vi.mock( '../genie/api/product', () => ( {
	productModel: vi.fn( async () => 'GW10K-ETA' ),
} ) );

const CONFIG: GenieConfig = {
	surface: 'helper',
	locale: 'en',
	pageType: 'home',
	productId: 0,
	turnUrl: '/wp-json/linker-ai/v1/genie/turn',
	threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
	conversationsUrl: '/wp-json/linker-ai/v1/genie/conversations',
	voteUrl: '/wp-json/linker-ai/v1/genie/turn',
	restUrl: '/wp-json/',
	restNonce: 'n',
	disclosure: 'You are chatting with an AI system.',
	accountUrl: '/my-account/',
	workspaceUrl: '/genie/',
	prompts: [],
	page: { type: 'home', url: '/', title: 'Home page' },
	signedIn: false,
	retentionDays: 90,
	mailStarted: '100.sig',
	mailStartedNonce: 'sig',
	contactUrl: '/wp-json/linker-ai/v1/genie/contact',
	inquiryUrl: '/wp-json/linker-ai/v1/genie/inquiry',
};

const DOCK_THREAD: TurnMessage[] = [
	{ role: 'user', content: 'Which inverters fit a three-phase home?' },
	{ role: 'assistant', content: 'These three fit.' },
];

function reply( text: string ): Turn {
	return {
		meta: {
			turn_id: 7,
			grounded: true,
			fallback: false,
			attempts: 1,
			failures: [],
			language: 'en',
		},
		blocks: [ { type: 'text', text, refs: [] } ],
	};
}

const SESSION_CONFIG: HeroSessionConfig = {
	restUrl: CONFIG.restUrl,
	turnUrl: CONFIG.turnUrl,
	threadUrl: CONFIG.threadUrl,
	nonce: CONFIG.restNonce,
	locale: CONFIG.locale,
	page: CONFIG.page,
};

function session( stored: TurnMessage[] = [], turn: Turn | null = null ) {
	const read = vi.fn( async () => ( { messages: [ ...stored ], turn } ) );
	const send = vi.fn(
		async ( request: { messages: TurnMessage[]; uploads?: Upload[] } ) =>
			reply( `Answer ${ request.messages.length }` )
	);
	return {
		session: new HeroSession( SESSION_CONFIG, read, send ),
		read,
		send,
	};
}

beforeEach( () => {
	sessionStorage.clear();
} );

afterEach( () => {
	sessionStorage.clear();
} );

function renderHero(
	heroSession: HeroSession,
	overrides: Partial< {
		onContinue: () => void;
		onClose: () => void;
		onConversation: ( has: boolean ) => void;
		setPrompt: ( text: string ) => void;
		focusPrompt: () => void;
		requestPicker: () => void;
	} > = {}
) {
	const calls = {
		onContinue: overrides.onContinue ?? vi.fn(),
		onClose: overrides.onClose ?? vi.fn(),
		onConversation: overrides.onConversation ?? vi.fn(),
		setPrompt: overrides.setPrompt ?? vi.fn(),
		focusPrompt: overrides.focusPrompt ?? vi.fn(),
		requestPicker: overrides.requestPicker ?? vi.fn(),
	};
	let bridge: HeroBridge | null = null;
	render(
		<HeroConversation
			config={ CONFIG }
			session={ heroSession }
			onReady={ ( next ) => {
				bridge = next;
			} }
			{ ...calls }
		/>
	);
	return { ...calls, bridge: () => bridge as unknown as HeroBridge };
}

test( 'the unfolded conversation names Genie and offers both exits', async () => {
	const { onContinue, onClose } = renderHero( session().session );

	expect(
		screen.getByText( "Genie - Linker's AI assistant" )
	).toBeInTheDocument();
	expect(
		screen.getByText( "Genie is Linker's AI assistant." )
	).toBeInTheDocument();
	// Focus moves into the unfolded surface (review round 1, item 3).
	expect( screen.getByRole( 'button', { name: 'Close' } ) ).toHaveFocus();

	fireEvent.click(
		screen.getByRole( 'button', { name: 'Continue in the side panel' } )
	);
	expect( onContinue ).toHaveBeenCalledTimes( 1 );

	fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
	expect( onClose ).toHaveBeenCalledTimes( 1 );
} );

test( 'the hero shows the conversation the dock stored', async () => {
	const { onConversation } = renderHero( session( DOCK_THREAD ).session );

	expect(
		await screen.findByText( 'Which inverters fit a three-phase home?' )
	).toBeInTheDocument();
	expect( screen.getAllByText( 'These three fit.' ).length ).toBeGreaterThan(
		0
	);
	expect( onConversation ).toHaveBeenCalledWith( true );
} );

test( 'a question asked through the hero gets a real answer and counts as a conversation', async () => {
	const answers = session();
	const { bridge, onConversation } = renderHero( answers.session );

	await act( async () => {
		bridge().ask( 'Which inverters fit a three-phase home?' );
	} );

	await waitFor( () =>
		expect(
			screen.getByText( 'Which inverters fit a three-phase home?' )
		).toBeInTheDocument()
	);
	// The answer is in the thread and in the live region for screen readers.
	await waitFor( () =>
		expect( screen.getAllByText( 'Answer 1' ).length ).toBeGreaterThan( 0 )
	);
	expect( answers.send ).toHaveBeenCalledTimes( 1 );
	expect( onConversation ).toHaveBeenCalledWith( true );
	// The live region carries the new answer (review round 1, item 3).
	expect( screen.getByRole( 'status' ) ).toHaveTextContent( 'Answer 1' );
} );

test( 'a failed first turn puts the question back and shows the retry sentence', async () => {
	const read = vi.fn( async () => ( { messages: [], turn: null } ) );
	const send = vi.fn( async () => {
		throw new Error( 'turn 502' );
	} );
	const setPrompt = vi.fn();
	const { bridge } = renderHero(
		new HeroSession( SESSION_CONFIG, read, send ),
		{ setPrompt }
	);

	await act( async () => {
		bridge().ask( 'saj' );
	} );

	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( setPrompt ).toHaveBeenLastCalledWith( 'saj' );
	expect( screen.queryByText( 'saj' ) ).toBeNull();
	expect(
		screen.getByRole( 'button', { name: 'Try again' } )
	).toBeInTheDocument();
} );

test( 'retrying a failed hero turn sends it once', async () => {
	const read = vi.fn( async () => ( { messages: [], turn: null } ) );
	const send = vi
		.fn()
		.mockRejectedValueOnce( new Error( 'turn 502' ) )
		.mockResolvedValueOnce( reply( 'Recovered' ) );
	const { bridge } = renderHero(
		new HeroSession( SESSION_CONFIG, read, send )
	);

	await act( async () => {
		bridge().ask( 'saj' );
	} );
	const retry = await screen.findByRole( 'button', { name: 'Try again' } );
	fireEvent.click( retry );
	fireEvent.click( retry );

	await waitFor( () => expect( send ).toHaveBeenCalledTimes( 2 ) );
	expect( send.mock.calls[ 1 ][ 0 ].messages ).toEqual( [
		{ role: 'user', content: 'saj' },
	] );
	expect(
		( await screen.findAllByText( 'Recovered' ) ).length
	).toBeGreaterThan( 0 );
	expect(
		screen.queryByText( 'Genie did not answer. Please try again.' )
	).toBeNull();
} );

test( 'a cut stream on the hero keeps the question and not the partial answer', async () => {
	const read = vi.fn( async () => ( { messages: [], turn: null } ) );
	const send = vi.fn( async () => {
		throw new UnfinishedStreamError();
	} );
	const setPrompt = vi.fn();
	const view = renderHero( new HeroSession( SESSION_CONFIG, read, send ), {
		setPrompt,
	} );

	await act( async () => {
		view.bridge().ask( 'backup for 10 kW' );
	} );

	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( screen.getByText( 'backup for 10 kW' ) ).toBeInTheDocument();
	expect( screen.queryByText( '10 kW from a cut stream' ) ).toBeNull();
	expect( setPrompt ).toHaveBeenLastCalledWith( '' );
} );

test( 'a cut stream on the hero keeps the file, and removing it takes it off the retry', async () => {
	const read = vi.fn( async () => ( { messages: [], turn: null } ) );
	const send = vi
		.fn()
		.mockRejectedValueOnce( new UnfinishedStreamError() )
		.mockResolvedValueOnce( reply( 'Recovered' ) );
	const setPrompt = vi.fn();
	const view = renderHero( new HeroSession( SESSION_CONFIG, read, send ), {
		setPrompt,
	} );
	const file = new File( [ '%PDF-1.4' ], 'datasheet.pdf', {
		type: 'application/pdf',
	} );

	await act( async () => {
		view.bridge().ask( 'backup for 10 kW', [ file ] );
	} );

	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( setPrompt ).toHaveBeenLastCalledWith( '' );
	expect( screen.getByText( 'datasheet.pdf' ) ).toBeInTheDocument();
	fireEvent.click(
		screen.getByRole( 'button', {
			name: 'Remove attachment datasheet.pdf',
		} )
	);
	expect( screen.queryByText( 'datasheet.pdf' ) ).toBeNull();
	fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) );
	await waitFor( () => expect( send ).toHaveBeenCalledTimes( 2 ) );
	expect( send.mock.calls[ 1 ][ 0 ].uploads ).toEqual( [] );
} );

test( 'a conflicting turn puts the question back and re-reads the thread', async () => {
	const read = vi
		.fn()
		.mockResolvedValueOnce( { messages: [], turn: null } )
		.mockResolvedValueOnce( { messages: [], turn: null } )
		.mockResolvedValueOnce( {
			messages: [
				{ role: 'user', content: 'Which inverter?' },
				{
					role: 'assistant',
					content: 'The hybrid inverter is three-phase.',
				},
			],
			turn: null,
		} );
	const send = vi.fn( async () => {
		throw new TurnError( 409, 'linker_genie_turn_conflict' );
	} );
	const setPrompt = vi.fn();
	const { bridge } = renderHero(
		new HeroSession( SESSION_CONFIG, read, send ),
		{ setPrompt }
	);

	await act( async () => {
		bridge().ask( 'EV chargers' );
	} );

	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'The conversation changed while Genie was answering. Send your question again.'
	);
	expect(
		screen.queryByText( 'Genie did not answer. Please try again.' )
	).toBeNull();
	expect( screen.queryByText( 'EV chargers' ) ).toBeNull();
	expect( screen.getByText( 'Which inverter?' ) ).toBeInTheDocument();
	expect( setPrompt ).toHaveBeenCalledWith( 'EV chargers' );
	expect( read ).toHaveBeenCalledTimes( 3 );
} );

test( 'the nameplate card confirms into an ordinary question', async () => {
	const turn: Turn = {
		meta: null,
		blocks: [],
		attachments: [
			{
				id: 'att1',
				name: 'nameplate.jpg',
				kind: 'nameplate',
				match: 'exact',
				brand: 'SAJ',
				model: 'H2-10K-T3',
				products: [ { product_id: 4107, label: 'H2-10K-T3' } ],
			},
		],
	};
	const answers = session(
		[
			{ role: 'user', content: 'Attached: nameplate.jpg' },
			{ role: 'assistant', content: 'I read your nameplate.' },
		],
		turn
	);
	renderHero( answers.session );

	const confirm = await screen.findByRole( 'button', {
		name: 'Yes, show its documents',
	} );
	fireEvent.click( confirm );

	await waitFor( () => expect( answers.send ).toHaveBeenCalledTimes( 1 ) );
	expect( answers.send.mock.calls[ 0 ][ 0 ].messages[ 2 ] ).toEqual( {
		role: 'user',
		content: "Yes, it's the SAJ H2-10K-T3. Show me its documents.",
	} );
} );

test( 'the manual model exit fills the hero follow-up field', async () => {
	const turn: Turn = {
		meta: null,
		blocks: [],
		attachments: [
			{
				id: 'att1',
				name: 'nameplate.jpg',
				kind: 'nameplate',
				match: 'unreadable',
				brand: null,
				model: null,
				products: [],
			},
		],
	};
	const { setPrompt, focusPrompt } = renderHero(
		session(
			[
				{ role: 'user', content: 'Attached: nameplate.jpg' },
				{ role: 'assistant', content: 'I could not read it.' },
			],
			turn
		).session
	);

	fireEvent.click(
		await screen.findByRole( 'button', { name: 'Type the model' } )
	);

	expect( setPrompt ).toHaveBeenCalledWith( 'My device is the ' );
	expect( focusPrompt ).toHaveBeenCalledTimes( 1 );
} );

test( 'a picked PDF is prepared, sent apart from the messages, and read', async () => {
	const answers = session();
	const { bridge } = renderHero( answers.session );
	const file = new File( [ '%PDF-1.4\n%%EOF' ], 'datasheet.pdf', {
		type: 'application/pdf',
	} );

	await act( async () => {
		bridge().ask( '', [ file ] );
	} );

	await waitFor( () => expect( answers.send ).toHaveBeenCalledTimes( 1 ) );
	const { messages, uploads } = answers.send.mock.calls[ 0 ][ 0 ];
	expect( messages[ messages.length - 1 ] ).toEqual( {
		role: 'user',
		content: 'Attached: datasheet.pdf',
	} );
	expect( uploads ).toHaveLength( 1 );
	expect( uploads?.[ 0 ] ).toMatchObject( {
		name: 'datasheet.pdf',
		type: 'application/pdf',
	} );
} );

test( 'a file type Genie cannot read is refused before any turn', async () => {
	const answers = session();
	const { bridge } = renderHero( answers.session );
	const file = new File( [ 'plain text' ], 'notes.txt', {
		type: 'text/plain',
	} );

	await act( async () => {
		bridge().ask( '', [ file ] );
	} );

	expect(
		await screen.findByText(
			'This file type cannot be sent. Genie reads photos (JPEG, PNG, WebP or HEIC), PDFs and parts lists (CSV or .xlsx).'
		)
	).toBeInTheDocument();
	expect( answers.send ).not.toHaveBeenCalled();
} );

test( 'the #243 contact card renders in the hero', async () => {
	const turn: Turn = {
		meta: null,
		blocks: [ { type: 'contact', reason: 'asked' } ],
	};
	renderHero(
		session(
			[
				{ role: 'user', content: 'Can I talk to a person?' },
				{ role: 'assistant', content: 'The Linker team can help.' },
			],
			turn
		).session
	);

	expect(
		await screen.findByText( 'Let the Linker team contact you' )
	).toBeInTheDocument();
	expect( document.querySelector( '.linker-genie-contact' ) ).not.toBeNull();
} );

test( 'the #250 inquiry confirmation card renders in the hero', async () => {
	const turn: Turn = {
		meta: null,
		blocks: [ { type: 'action', name: 'send_inquiry', args: {} } ],
	};
	renderHero(
		session(
			[
				{ role: 'user', content: 'Please send an inquiry.' },
				{ role: 'assistant', content: 'Check the inquiry below.' },
			],
			turn
		).session
	);

	expect( await screen.findByText( 'Your inquiry' ) ).toBeInTheDocument();
	expect( document.querySelector( '.linker-genie-inquiry' ) ).not.toBeNull();
	expect( screen.getAllByText( 'SAJ H2-10K-T3' ).length ).toBeGreaterThan(
		0
	);
	expect(
		screen.getByText( 'We reply within one business day.' )
	).toBeInTheDocument();
} );
