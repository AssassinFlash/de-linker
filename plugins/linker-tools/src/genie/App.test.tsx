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
import { App, resetTurnLane } from './App';

vi.mock( './api/turn', async ( importOriginal ) => {
	const actual = await importOriginal< typeof import( './api/turn' ) >();
	return {
		// The real message rule, so a restored thread is spelled the same way
		// a live one is; the calls around it are doubles.
		assistantMessage: actual.assistantMessage,
		readThread: vi.fn( async () => ( { messages: [], turn: null } ) ),
		listConversations: vi.fn( async () => ( {
			currentId: 0,
			conversations: [],
			ok: true,
		} ) ),
		selectConversation: vi.fn(),
		sendTurn: vi.fn(),
		sendVote: vi.fn( async () => true ),
	};
} );
vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'GW10K-ETA' ),
} ) );
import {
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
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
		conversationsUrl: '/wp-json/linker-ai/v1/genie/conversations',
		voteUrl: '/wp-json/linker-ai/v1/genie/turn',
		restUrl: '/wp-json/',
		restNonce: 'n',
		disclosure:
			"Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system.",
		accountUrl: '/my-account/',
		workspaceUrl: '/linker-advisor/',
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

test( 'the ready handshake opens once and Hide/reopen reports the same state', async () => {
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
		expect( screen.getByRole( 'button', { name: 'Hide' } ) ).toBeVisible();
		fireEvent.click( screen.getByRole( 'button', { name: 'Hide' } ) );
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
