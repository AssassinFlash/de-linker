// @vitest-environment jsdom

/**
 * One turn through the app: the disclosure once, the ask chips, and the card
 * states of add-to-draft (docs/specs/13-genie.md).
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
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { GenieConfig } from './config';
import { App, resetTurnLane, type Dictation } from './App';

vi.mock( './api/turn', async ( importOriginal ) => {
	const actual = await importOriginal< typeof import( './api/turn' ) >();
	return {
		// The real message rule, so a restored thread is spelled the same way
		// a live one is; the calls around it are doubles.
		assistantMessage: actual.assistantMessage,
		emailOutcome: actual.emailOutcome,
		readThread: vi.fn( async () => ( { messages: [], turn: null } ) ),
		listConversations: vi.fn( async () => ( {
			currentId: 0,
			conversations: [],
			ok: true,
		} ) ),
		selectConversation: vi.fn(),
		deleteConversation: vi.fn(),
		emailConversation: vi.fn(),
		sendTurn: vi.fn(),
		sendVote: vi.fn( async () => true ),
	};
} );
vi.mock( './api/contact', () => ( {
	readContact: vi.fn( async () => ( {
		started: '100.sig',
		email: null,
		sent: null,
		mailbox: 'sales@de-linker.com',
	} ) ),
	sendContact: vi.fn(),
} ) );
vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'GW10K-ETA' ),
} ) );
import {
	deleteConversation,
	emailConversation,
	listConversations,
	readThread,
	selectConversation,
	sendTurn,
	sendVote,
} from './api/turn';

const GERMAN_STREAM =
	'event: meta\n' +
	'data: {"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"de"}\n\n' +
	'event: block\n' +
	'data: {"type":"text","text":"Hallo, ich bin Genie, der KI-Assistent von Linker.","refs":["p3556"]}\n\n' +
	'event: block\n' +
	'data: {"type":"ask","field":"backup","options":["ohne","benötigt"]}\n\n' +
	'event: done\n' +
	'data: {"ok":true}\n\n';

function config( locale: 'en' | 'de' = 'en' ): GenieConfig {
	return {
		surface: 'helper',
		locale,
		pageType: 'category',
		productId: 0,
		page: { type: 'category' },
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
		conversationsUrl: '/wp-json/linker-ai/v1/genie/conversations',
		voteUrl: '/wp-json/linker-ai/v1/genie/turn',
		restUrl: '/wp-json/',
		restNonce: 'n',
		disclosure:
			"Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system.",
		accountUrl: '/my-account/',
		workspaceUrl: '/genie/',
		signedIn: false,
		retentionDays: 90,
		mailStarted: '1800000000',
		mailStartedNonce: 'stamp-nonce',
		contactUrl: '/wp-json/linker-ai/v1/genie/contact',
		prompts: [
			'Ask Genie',
			'I need a three-phase hybrid inverter for a home.',
		],
	};
}

test( 'the disclosure is spoken once and a prompt sends the first turn', async () => {
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 1,
			failures: [],
			language: 'en',
		},
		blocks: [
			{
				type: 'ask',
				field: 'phase',
				options: [ 'Single-phase', 'Three-phase' ],
			},
		],
	} );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );

	expect(
		screen.getAllByText(
			"Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system."
		)
	).toHaveLength( 1 );

	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'I need a three-phase hybrid inverter for a home.',
			} )
		);
	} );

	expect( sendTurn ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/turn',
		'n',
		'en',
		[
			{
				role: 'user',
				content: 'I need a three-phase hybrid inverter for a home.',
			},
		],
		{ type: 'category' }
	);
	expect( await screen.findByText( 'Three-phase' ) ).toBeInTheDocument();
	// The disclosure is still there exactly once after the turn.
	expect(
		screen.getAllByText(
			"Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system."
		)
	).toHaveLength( 1 );
} );

test( 'a German turn keeps the thread and renders the chips in German', async () => {
	const { parseStream } =
		await vi.importActual< typeof import( './api/turn' ) >( './api/turn' );
	vi.mocked( sendTurn ).mockImplementation( async () =>
		Promise.resolve( parseStream( GERMAN_STREAM ) )
	);
	render( <App config={ config( 'de' ) } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Ask Genie' } ) );
	} );
	await waitFor( () =>
		expect( screen.getByText( 'benötigt' ) ).toBeInTheDocument()
	);
	expect(
		screen.getAllByText(
			'Hallo, ich bin Genie, der KI-Assistent von Linker.'
		).length
	).toBeGreaterThan( 0 );
} );

test( 'a failed proxy call shows the retry sentence, not a fake answer', async () => {
	vi.mocked( sendTurn ).mockRejectedValue( new Error( 'turn 502' ) );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Ask Genie' } ) );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
} );

test( 'the assistant message carries the vote buttons and posts the vote', async () => {
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: {
			turn_id: 41,
			grounded: true,
			fallback: false,
			attempts: 1,
			failures: [],
			language: 'en',
		},
		blocks: [
			{
				type: 'text',
				text: 'Here is a match.',
				refs: [ 'p3556' ],
			},
		],
	} );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'I need a three-phase hybrid inverter for a home.',
			} )
		);
	} );
	const helpful = await screen.findByRole( 'button', {
		name: 'Helpful',
	} );
	const notHelpful = screen.getByRole( 'button', {
		name: 'Not helpful',
	} );
	expect( helpful ).toHaveAttribute( 'aria-pressed', 'false' );
	await act( async () => {
		fireEvent.click( helpful );
	} );
	expect( sendVote ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/turn',
		'n',
		41,
		1
	);
	expect( helpful ).toHaveAttribute( 'aria-pressed', 'true' );
	expect( notHelpful ).toBeDisabled();
	// Both buttons stay in the document: the message height never jumps.
	expect(
		screen.getAllByRole( 'button', { name: 'Not helpful' } )
	).toHaveLength( 1 );
} );

test( 'a reload opens with the thread and the last answer restored', async () => {
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{
				role: 'user',
				content: 'Which inverters fit a three-phase home?',
			},
			{ role: 'assistant', content: 'These three fit.' },
		],
		turn: {
			meta: {
				turn_id: 9,
				grounded: true,
				fallback: false,
				attempts: 1,
				failures: [],
				language: 'en',
			},
			// Text only: a cards block would fetch the product from the
			// Store API, which the card's own tests cover.
			blocks: [
				{ type: 'text', text: 'These three fit.', refs: [ '3556' ] },
			],
		},
	} );

	render( <App config={ config() } /> );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: /open|ask genie/i } )
		);
	} );

	await waitFor( () =>
		expect(
			screen.getByText( 'Which inverters fit a three-phase home?' )
		).toBeDefined()
	);
	// The answer shows twice on purpose — once in the thread, once as the
	// restored turn's own text block, exactly as after a live turn.
	expect( screen.getAllByText( 'These three fit.' ).length ).toBeGreaterThan(
		0
	);
} );

test( 'a first visit with no stored conversation opens empty', async () => {
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	render( <App config={ config() } /> );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: /open|ask genie/i } )
		);
	} );
	expect( screen.queryByText( 'These three fit.' ) ).toBeNull();
} );

// The empty column's own line, the prototype's `.gp-welcome h1` (variant A).
// It belongs to the empty state and leaves with the first turn.
test( 'the empty column carries the welcome title until a turn lands', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	render( <App config={ { ...config(), surface: 'workspace' } } /> );
	expect(
		await screen.findByRole( 'heading', {
			name: 'Where should we begin?',
		} )
	).toBeVisible();
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'I need a three-phase hybrid inverter for a home.',
			} )
		);
	} );
	expect(
		screen.queryByRole( 'heading', { name: 'Where should we begin?' } )
	).toBeNull();
} );

// The prototype's `.gp-answer-brand`: an answer is labelled with the assistant,
// a question is not.
test( 'an answer carries the answer label and a question does not', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	render( <App config={ { ...config(), surface: 'workspace' } } /> );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'I need a three-phase hybrid inverter for a home.',
			} )
		);
	} );
	const brands = document.querySelectorAll(
		'.linker-genie-app__answer-brand'
	);
	expect( brands.length ).toBe( 1 );
	expect( brands[ 0 ].textContent ).toContain( 'Genie' );
	expect(
		document
			.querySelector( '.linker-genie-app__message--user' )
			?.querySelector( '.linker-genie-app__answer-brand' )
	).toBeNull();
} );

test( 'the ready handshake opens once and Close/reopen reports the same state', async () => {
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn ).mockClear();
	const states: boolean[] = [];
	let ready = 0;
	const onState = ( event: Event ) => {
		states.push(
			( event as CustomEvent< { open: boolean } > ).detail.open
		);
	};
	const onReady = () => {
		ready += 1;
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) );
	};
	window.addEventListener( 'linker-genie-state', onState );
	window.addEventListener( 'linker-genie-ready', onReady );
	try {
		render( <App config={ config() } /> );
		expect( ready ).toBe( 1 );
		expect( screen.getByRole( 'button', { name: 'Close' } ) ).toBeVisible();
		fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
		expect( states.at( -1 ) ).toBe( false );
		act( () => {
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) );
		} );
		expect( screen.getByLabelText( 'Ask Genie' ) ).toBeVisible();
		expect( states.at( -1 ) ).toBe( true );
		expect( sendTurn ).not.toHaveBeenCalled();
	} finally {
		window.removeEventListener( 'linker-genie-state', onState );
		window.removeEventListener( 'linker-genie-ready', onReady );
	}
} );

test( 'one entry ask survives a late thread restore without being sent twice', async () => {
	let restore!: ( value: Awaited< ReturnType< typeof readThread > > ) => void;
	vi.mocked( readThread ).mockImplementationOnce(
		() =>
			new Promise( ( resolve ) => {
				restore = resolve;
			} )
	);
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	render( <App config={ config() } /> );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { message: 'What pairs with this model?' },
			} )
		);
	} );
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () => {
		restore( {
			messages: [ { role: 'user', content: 'Old question' } ],
			turn: null,
		} );
	} );
	expect( screen.getByText( 'What pairs with this model?' ) ).toBeVisible();
	expect( screen.getByText( 'Old question' ) ).toBeVisible();
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ][ 3 ] ).toEqual( [
		{ role: 'user', content: 'Old question' },
		{ role: 'user', content: 'What pairs with this model?' },
	] );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'a history that is still loading is not an empty history', async () => {
	resetTurnLane();
	const reads: Array<
		( value: Awaited< ReturnType< typeof readThread > > ) => void
	> = [];
	const lists: Array<
		( value: Awaited< ReturnType< typeof listConversations > > ) => void
	> = [];
	vi.mocked( readThread ).mockImplementation(
		() =>
			new Promise( ( resolve ) => {
				reads.push( resolve );
			} )
	);
	vi.mocked( listConversations ).mockImplementation(
		() =>
			new Promise( ( resolve ) => {
				lists.push( resolve );
			} )
	);
	render( <App config={ { ...config(), surface: 'workspace' } } /> );
	expect( screen.getByRole( 'status' ) ).toHaveTextContent(
		'Loading conversations…'
	);
	expect( screen.queryByText( 'No earlier conversation.' ) ).toBeNull();
	await waitFor( () => expect( reads.length ).toBeGreaterThan( 0 ) );
	reads[ 0 ]!( { messages: [], turn: null } );
	await waitFor( () => expect( lists.length ).toBeGreaterThan( 0 ) );
	lists[ 0 ]!( { currentId: 0, conversations: [], ok: true } );
	expect(
		await screen.findByText( 'No earlier conversation.' )
	).toBeVisible();
	expect( screen.queryByRole( 'status' ) ).toBeNull();
	vi.mocked( readThread ).mockImplementation( async () => ( {
		messages: [],
		turn: null,
	} ) );
	vi.mocked( listConversations ).mockImplementation( async () => ( {
		currentId: 0,
		conversations: [],
		ok: true,
	} ) );
} );

test( 'a failed history load is not an empty history', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 0,
		conversations: [],
		ok: false,
	} );
	render( <App config={ { ...config(), surface: 'workspace' } } /> );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Conversations could not be loaded.'
	);
	expect( screen.queryByText( 'No earlier conversation.' ) ).toBeNull();
} );

test( 'a failed switch says so instead of keeping a silent rail', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 7,
		ok: true,
		conversations: [
			{ id: 7, title: 'Battery pairing', updated: '2026-10-12' },
		],
	} );
	vi.mocked( selectConversation ).mockRejectedValue(
		new Error( 'conversation 500' )
	);
	render( <App config={ { ...config(), surface: 'workspace' } } /> );
	fireEvent.click(
		await screen.findByRole( 'button', { name: 'Battery pairing' } )
	);
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Conversations could not be loaded.'
	);
} );

test( 'the workspace lists real conversations and loads the selected one', async () => {
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 7,
		ok: true,
		conversations: [
			{ id: 7, title: 'Battery pairing', updated: '2026-10-12' },
			{ id: 8, title: 'Document question', updated: '2026-10-11' },
		],
	} );
	vi.mocked( selectConversation ).mockResolvedValue( {
		currentId: 8,
		ok: true,
		conversations: [
			{ id: 7, title: 'Battery pairing', updated: '2026-10-12' },
			{ id: 8, title: 'Document question', updated: '2026-10-11' },
		],
	} );
	vi.mocked( readThread )
		.mockResolvedValueOnce( { messages: [], turn: null } )
		.mockResolvedValueOnce( {
			messages: [ { role: 'user', content: 'Where is the datasheet?' } ],
			turn: null,
		} );

	render( <App config={ { ...config(), surface: 'workspace' } } /> );

	expect(
		await screen.findByRole( 'button', { name: 'Battery pairing' } )
	).toHaveAttribute( 'aria-current', 'true' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Document question' } )
		);
	} );
	expect( selectConversation ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/conversations',
		'n',
		8
	);
	expect(
		await screen.findByText( 'Where is the datasheet?' )
	).toBeVisible();
} );

// The dock head is the Advisor's `.lia-head-btns`: new conversation, the
// full page, the history, closing — as named icon buttons.
test( 'the open dock head carries the icon group', () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect(
		screen.getByRole( 'button', { name: 'New conversation' } )
	).toBeVisible();
	expect(
		screen.getByRole( 'button', { name: 'Conversations' } )
	).toBeVisible();
	expect(
		screen.getByRole( 'link', { name: 'Open full page' } )
	).toHaveAttribute( 'href', '/genie/' );
	expect( screen.getByRole( 'button', { name: 'Close' } ) ).toBeVisible();
} );

// The dock's opening state is the Advisor's `.lia-welcome`: the greeting,
// one subline and the page's own example chips, all of it gone with the
// first turn.
test( 'the dock opens on the welcome and loses it with the first turn', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect(
		screen.getByText( 'Get help with your solar project' )
	).toBeVisible();
	expect(
		screen.getByText( 'Products, documents and your next step.' )
	).toBeVisible();
	expect(
		screen.getByRole( 'button', {
			name: 'I need a three-phase hybrid inverter for a home.',
		} )
	).toBeVisible();
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Ask Genie' } ) );
	} );
	expect(
		screen.queryByText( 'Get help with your solar project' )
	).toBeNull();
} );

// The Advisor's `.lia-privacy` row, on this site's own pages: the questions
// page, the contact page, the privacy policy — German twins on German pages.
test( 'the dock footer carries the site links, locale-aware', () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	const { unmount } = render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect(
		screen.getByRole( 'link', { name: 'FAQ & Downloads' } )
	).toHaveAttribute( 'href', '/faq-download/' );
	expect(
		screen.getByRole( 'link', { name: 'Contact Linker' } )
	).toHaveAttribute( 'href', '/contact/' );
	expect(
		screen.getByRole( 'link', { name: 'Privacy Policy' } )
	).toHaveAttribute( 'href', '/privacy-policy/' );
	unmount();
	render( <App config={ config( 'de' ) } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect(
		screen.getByRole( 'link', { name: 'FAQ & Downloads' } )
	).toHaveAttribute( 'href', '/de/faq-download/' );
	expect(
		screen.getByRole( 'link', { name: 'Contact Linker' } )
	).toHaveAttribute( 'href', '/de/kontakt/' );
	expect(
		screen.getByRole( 'link', { name: 'Privacy Policy' } )
	).toHaveAttribute( 'href', '/de/datenschutz/' );
} );

// The header's clock swaps the conversation for the history view and the
// chevron swaps back; a row continues its conversation.
test( 'the dock history view lists conversations and continues one', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 7,
		ok: true,
		conversations: [
			{ id: 7, title: 'Battery pairing', updated: '2026-10-12' },
			{ id: 8, title: 'Document question', updated: '2026-10-11' },
		],
	} );
	vi.mocked( selectConversation ).mockResolvedValue( {
		currentId: 8,
		ok: true,
		conversations: [
			{ id: 7, title: 'Battery pairing', updated: '2026-10-12' },
			{ id: 8, title: 'Document question', updated: '2026-10-11' },
		],
	} );
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	// The list stays behind the header's clock until asked for.
	expect(
		screen.queryByRole( 'button', { name: 'Battery pairing' } )
	).toBeNull();
	fireEvent.click( screen.getByRole( 'button', { name: 'Conversations' } ) );
	expect(
		await screen.findByRole( 'button', { name: 'Battery pairing' } )
	).toBeVisible();
	// The composer leaves with the conversation.
	expect( screen.queryByLabelText( 'Ask Genie' ) ).toBeNull();
	// The chevron leads back.
	fireEvent.click( screen.getByRole( 'button', { name: 'Back' } ) );
	expect( screen.getByLabelText( 'Ask Genie' ) ).toBeVisible();
	// A row continues its conversation.
	fireEvent.click( screen.getByRole( 'button', { name: 'Conversations' } ) );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Document question' } )
		);
	} );
	expect( selectConversation ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/conversations',
		'n',
		8
	);
	expect( screen.getByLabelText( 'Ask Genie' ) ).toBeVisible();
	// The plus opens a new one.
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'New conversation' } )
		);
	} );
	expect( selectConversation ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/conversations',
		'n',
		undefined
	);
} );

// The turn route carries text only: a picked file's name rides in the
// question, and the chip takes it back out before sending.
test( 'an attached file rides in the question by name', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const fileInput = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	const datasheet = new File( [ 'x' ], 'gw10k-et-datenblatt.pdf', {
		type: 'application/pdf',
	} );
	fireEvent.change( fileInput, { target: { files: [ datasheet ] } } );
	expect( screen.getByText( 'gw10k-et-datenblatt.pdf' ) ).toBeVisible();
	// The send key arms on an attachment alone, and the chip removes it.
	const send = screen.getByRole( 'button', { name: 'Send' } );
	expect( send ).toBeEnabled();
	fireEvent.click(
		screen.getByRole( 'button', {
			name: 'Remove attachment gw10k-et-datenblatt.pdf',
		} )
	);
	expect( screen.queryByText( 'gw10k-et-datenblatt.pdf' ) ).toBeNull();
	expect( send ).toBeDisabled();
	fireEvent.change( fileInput, { target: { files: [ datasheet ] } } );
	await act( async () => {
		fireEvent.click( send );
	} );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ][ 3 ] ).toEqual( [
		{ role: 'user', content: 'Attached: gw10k-et-datenblatt.pdf' },
	] );
	// The sent attachment leaves the composer.
	expect( screen.queryByText( 'gw10k-et-datenblatt.pdf' ) ).toBeNull();
} );

// The dictation button is the browser's own speech recognition: it writes
// what it hears into the field and stops cleanly.
test( 'the dictation button writes what the browser hears', () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	const sessions: Dictation[] = [];
	class FakeDictation implements Dictation {
		lang = '';
		onresult: Dictation[ 'onresult' ] = null;
		onend: Dictation[ 'onend' ] = null;
		onerror: Dictation[ 'onerror' ] = null;
		constructor() {
			sessions.push( this );
		}
		start() {}
		stop() {
			this.onend?.();
		}
	}
	const previous = window.SpeechRecognition;
	window.SpeechRecognition = FakeDictation;
	try {
		render( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		const mic = screen.getByRole( 'button', { name: 'Dictate' } );
		fireEvent.click( mic );
		expect( mic ).toHaveAttribute( 'aria-pressed', 'true' );
		expect( sessions ).toHaveLength( 1 );
		expect( sessions[ 0 ].lang ).toBe( 'en-US' );
		act( () => {
			sessions[ 0 ].onresult?.( {
				results: [ [ { transcript: 'hybrid inverter' } ] ],
			} );
		} );
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'hybrid inverter'
		);
		// A second tap stops the session.
		fireEvent.click( mic );
		expect( mic ).toHaveAttribute( 'aria-pressed', 'false' );
	} finally {
		if ( previous ) {
			window.SpeechRecognition = previous;
		} else {
			delete window.SpeechRecognition;
		}
	}
} );

// A browser without speech recognition carries no dead button.
test( 'no speech recognition, no dictation button', () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect( screen.queryByRole( 'button', { name: 'Dictate' } ) ).toBeNull();
} );

// The mobile sheet's backdrop: a tap off the card folds the dock away.
test( 'the dock mask folds the sheet', () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	const states: boolean[] = [];
	const onState = ( event: Event ) => {
		states.push(
			( event as CustomEvent< { open: boolean } > ).detail.open
		);
	};
	window.addEventListener( 'linker-genie-state', onState );
	try {
		render( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		fireEvent.click( screen.getByRole( 'button', { name: 'Hide' } ) );
		expect( states.at( -1 ) ).toBe( false );
	} finally {
		window.removeEventListener( 'linker-genie-state', onState );
	}
} );

const THREE = [
	{ id: 9, title: 'Third question', updated: '2026-10-18 10:02:00' },
	{ id: 8, title: 'Second question', updated: '2026-10-18 10:01:00' },
	{ id: 7, title: 'First question', updated: '2026-10-18 10:00:00' },
];

// Ticket #235: a new conversation, or a switch, leaves the docked rail where
// it is; the rail only folds where it is an overlay over the conversation.
test( 'a new conversation and a switch keep the wide workspace rail open', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: THREE,
	} );
	vi.mocked( selectConversation ).mockResolvedValue( {
		currentId: 10,
		ok: true,
		conversations: [
			{ id: 10, title: 'Genie', updated: '2026-10-18 10:03:00' },
			...THREE,
		],
	} );
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	render( <App config={ { ...config(), surface: 'workspace' } } /> );
	const rail = screen.getByRole( 'complementary', {
		name: 'Conversations',
	} );
	expect( rail ).toHaveClass( 'is-open' );

	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'New conversation' } )
		);
	} );
	expect( selectConversation ).toHaveBeenLastCalledWith(
		'/wp-json/linker-ai/v1/genie/conversations',
		'n',
		undefined
	);
	expect( rail ).toHaveClass( 'is-open' );
	for ( const item of THREE ) {
		expect(
			screen.getByRole( 'button', { name: item.title } )
		).toBeVisible();
	}

	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'First question' } )
		);
	} );
	expect( rail ).toHaveClass( 'is-open' );
} );

test( 'on a phone the rail overlay folds once a conversation is picked', async () => {
	resetTurnLane();
	const width = window.innerWidth;
	window.innerWidth = 390;
	try {
		vi.mocked( listConversations ).mockResolvedValue( {
			currentId: 9,
			ok: true,
			conversations: THREE,
		} );
		vi.mocked( selectConversation ).mockResolvedValue( {
			currentId: 7,
			ok: true,
			conversations: THREE,
		} );
		vi.mocked( readThread ).mockResolvedValue( {
			messages: [],
			turn: null,
		} );
		render( <App config={ { ...config(), surface: 'workspace' } } /> );
		const rail = screen.getByRole( 'complementary', {
			name: 'Conversations',
		} );
		expect( rail ).not.toHaveClass( 'is-open' );
		fireEvent.click(
			screen.getAllByRole( 'button', { name: 'Conversations' } )[ 0 ]
		);
		expect( rail ).toHaveClass( 'is-open' );
		const first = await screen.findByRole( 'button', {
			name: 'First question',
		} );
		await act( async () => {
			fireEvent.click( first );
		} );
		expect( rail ).not.toHaveClass( 'is-open' );
	} finally {
		window.innerWidth = width;
	}
} );

test( 'a conversation is deleted from the list once the visitor confirms', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: THREE,
	} );
	vi.mocked( deleteConversation ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: [ THREE[ 0 ], THREE[ 2 ] ],
	} );
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.click( screen.getByRole( 'button', { name: 'Conversations' } ) );

	fireEvent.click(
		await screen.findByRole( 'button', {
			name: 'Delete conversation: Second question',
		} )
	);
	// Nothing is deleted before the visitor confirms.
	expect( deleteConversation ).not.toHaveBeenCalled();
	expect(
		screen.getByText( 'Delete this conversation permanently?' )
	).toBeVisible();
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Delete' } ) );
	} );
	expect( deleteConversation ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/conversations',
		'n',
		8
	);
	expect(
		screen.queryByRole( 'button', { name: 'Second question' } )
	).toBeNull();
	expect(
		screen.getByRole( 'button', { name: 'Third question' } )
	).toBeVisible();
} );

test( 'deleting the conversation on screen empties the panel', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: THREE,
	} );
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{ role: 'user', content: 'Third question' },
			{ role: 'assistant', content: 'An answer.' },
		],
		turn: null,
	} );
	vi.mocked( deleteConversation ).mockResolvedValue( {
		currentId: 0,
		ok: true,
		conversations: [ THREE[ 1 ], THREE[ 2 ] ],
	} );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect( await screen.findByText( 'An answer.' ) ).toBeVisible();
	fireEvent.click( screen.getByRole( 'button', { name: 'Conversations' } ) );
	fireEvent.click(
		await screen.findByRole( 'button', {
			name: 'Delete conversation: Third question',
		} )
	);
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Delete' } ) );
	} );
	fireEvent.click( screen.getByRole( 'button', { name: 'Back' } ) );
	expect( screen.queryByText( 'An answer.' ) ).toBeNull();
	expect(
		screen.getByText( 'Get help with your solar project' )
	).toBeVisible();
} );

test( 'a guest gets a confirmation link at the address they type', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: THREE,
	} );
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{ role: 'user', content: 'Third question' },
			{ role: 'assistant', content: 'An answer.' },
		],
		turn: null,
	} );
	vi.mocked( emailConversation ).mockResolvedValue( {
		outcome: 'confirm',
		to: 'tester@example.test',
		limit: 0,
	} );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.click(
		await screen.findByRole( 'button', {
			name: 'Email me this conversation',
		} )
	);
	fireEvent.change( screen.getByLabelText( 'Your email address' ), {
		target: { value: 'tester@example.test' },
	} );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Send email' } ) );
	} );
	// The page's signed start time and the empty honeypot ride along
	// (ConversationMail::passes()).
	expect( emailConversation ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/conversations',
		'n',
		9,
		'en',
		'tester@example.test',
		{
			started: '1800000000',
			started_nonce: 'stamp-nonce',
			website: '',
		}
	);
	expect(
		await screen.findByText(
			'A confirmation link is on its way to tester@example.test. The conversation follows once the link is opened.'
		)
	).toBeVisible();
} );

test( 'a signed-in customer gets the email at the account address, no form', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: THREE,
	} );
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{ role: 'user', content: 'Third question' },
			{ role: 'assistant', content: 'An answer.' },
		],
		turn: null,
	} );
	vi.mocked( emailConversation ).mockResolvedValue( {
		outcome: 'sent',
		to: 'buyer@example.test',
		limit: 0,
	} );
	render( <App config={ { ...config(), signedIn: true } } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const start = await screen.findByRole( 'button', {
		name: 'Email me this conversation',
	} );
	await act( async () => {
		fireEvent.click( start );
	} );
	expect( screen.queryByLabelText( 'Your email address' ) ).toBeNull();
	expect( emailConversation ).toHaveBeenLastCalledWith(
		'/wp-json/linker-ai/v1/genie/conversations',
		'n',
		9,
		'en',
		undefined,
		undefined
	);
	expect(
		await screen.findByText(
			'Your email to buyer@example.test is on its way.'
		)
	).toBeVisible();
} );

test( 'the limit is named with the number the server counts to', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: THREE,
	} );
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{ role: 'user', content: 'Third question' },
			{ role: 'assistant', content: 'An answer.' },
		],
		turn: null,
	} );
	vi.mocked( emailConversation ).mockResolvedValue( {
		outcome: 'throttled',
		to: '',
		limit: 3,
	} );
	render( <App config={ { ...config(), signedIn: true } } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const start = await screen.findByRole( 'button', {
		name: 'Email me this conversation',
	} );
	await act( async () => {
		fireEvent.click( start );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'This connection has reached the limit of 3 emails per hour. Please try again later.'
	);
} );

test( 'at the daily cap the panel says when emailing works again', async () => {
	resetTurnLane();
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: THREE,
	} );
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{ role: 'user', content: 'Third question' },
			{ role: 'assistant', content: 'An answer.' },
		],
		turn: null,
	} );
	vi.mocked( emailConversation ).mockResolvedValue( {
		outcome: 'capped',
		to: '',
		limit: 3,
	} );
	render( <App config={ { ...config(), signedIn: true } } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const start = await screen.findByRole( 'button', {
		name: 'Email me this conversation',
	} );
	await act( async () => {
		fireEvent.click( start );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		"Today's email limit has been reached. Please try again tomorrow."
	);
} );

test( 'the page a confirmation link opens says how it went, once', async () => {
	resetTurnLane();
	window.history.replaceState( null, '', '/genie/?genie_email=sent' );
	try {
		render( <App config={ { ...config(), surface: 'workspace' } } /> );
		expect(
			screen.getByText(
				'Email address confirmed. The conversation is on its way.'
			)
		).toBeVisible();
		expect( window.location.search ).toBe( '' );
	} finally {
		window.history.replaceState( null, '', '/' );
	}
} );
test( 'a request for a person shows the contact card, and Genie keeps answering', async () => {
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 0,
			failures: [],
			language: 'en',
		},
		blocks: [
			{
				type: 'text',
				text: 'Someone from the Linker team can get in touch with you by email.',
				refs: [],
			},
			{ type: 'contact', reason: 'asked' },
		],
	} );
	render( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const input = screen.getByLabelText( 'Ask Genie' );
	await act( async () => {
		fireEvent.change( input, {
			target: { value: 'Can I talk to a person?' },
		} );
		fireEvent.submit( input.closest( 'form' ) as HTMLFormElement );
	} );
	expect(
		await screen.findByText( 'Let the Linker team contact you' )
	).toBeInTheDocument();
	expect(
		await screen.findByLabelText( 'Your email address' )
	).toBeInTheDocument();
	// The offer does not mute Genie: the next question is a turn as usual.
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 1,
			failures: [],
			language: 'en',
		},
		blocks: [ { type: 'text', text: 'The SAJ B2 fits it.', refs: [] } ],
	} );
	await act( async () => {
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Which battery fits the SAJ H2?' },
		} );
		fireEvent.submit(
			screen
				.getByLabelText( 'Ask Genie' )
				.closest( 'form' ) as HTMLFormElement
		);
	} );
	expect(
		await screen.findByText( 'The SAJ B2 fits it.' )
	).toBeInTheDocument();
	expect( sendTurn ).toHaveBeenLastCalledWith(
		'/wp-json/linker-ai/v1/genie/turn',
		'n',
		'en',
		[
			{ role: 'user', content: 'Can I talk to a person?' },
			{
				role: 'assistant',
				content:
					'Someone from the Linker team can get in touch with you by email.',
				turnId: undefined,
			},
			{ role: 'user', content: 'Which battery fits the SAJ H2?' },
		],
		{ type: 'category' }
	);
} );
