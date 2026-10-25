// @vitest-environment jsdom
import {
	installNativeIdentityFixture,
	renderOwned,
	currentOwnedRaw,
} from '../genie/testing/nativeIdentity';

/**
 * The conversation the hero unfolds (ticket #232): the header and its two
 * exits, the stored thread, a real turn through the session, the #236
 * attachment card and its manual-model exit, and files riding with a turn.
 */

/**
 * External dependencies
 */
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { webcrypto } from 'node:crypto';

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

installNativeIdentityFixture();

beforeEach( () => {
	sessionStorage.clear();
} );

afterEach( () => {
	sessionStorage.clear();
} );

async function renderHero(
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
	await renderOwned(
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
	const { onContinue, onClose } = await renderHero( session().session );

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
	const { onConversation } = await renderHero(
		session( DOCK_THREAD ).session
	);

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
	const { bridge, onConversation } = await renderHero( answers.session );

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
	const { bridge } = await renderHero(
		new HeroSession( SESSION_CONFIG, read, send ),
		{ setPrompt }
	);

	await act( async () => {
		bridge().ask( 'saj' );
	} );

	await waitFor( () =>
		expect( screen.getByRole( 'alert' ) ).toHaveTextContent(
			'Genie did not answer. Please try again.'
		)
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
	const { bridge } = await renderHero(
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

test( 'hero retry restores this request from a complete native Thread response', async () => {
	const { readThread } =
		await vi.importActual< typeof import( '../genie/api/turn' ) >(
			'../genie/api/turn'
		);
	let stored: {
		conversation_id: number;
		operation_id?: string;
		messages: TurnMessage[];
		stream: string;
	} = {
		conversation_id: 563,
		messages: [],
		stream: '',
	};
	const read = () =>
		readThread(
			'/thread',
			'n',
			async () =>
				new Response( JSON.stringify( stored ), { status: 200 } )
		);
	const send = vi.fn(
		async ( request: {
			messages: TurnMessage[];
			onOperation?: ( id: string ) => void;
		} ) => {
			request.onOperation?.( '56300000-0000-4000-8000-000000000001' );
			stored = {
				...stored,
				operation_id: '56300000-0000-4000-8000-000000000001',
				messages: request.messages,
				stream: 'event: block\ndata: {"type":"text","text":"Stored hero answer.","refs":[]}\n\nevent: done\ndata: {"ok":true}\n\n',
			};
			throw new Error( 'Ambiguous response after completion' );
		}
	);
	const view = await renderHero(
		new HeroSession( SESSION_CONFIG, read, send )
	);
	await act( async () => {
		view.bridge().ask( 'saj' );
	} );
	fireEvent.click(
		await screen.findByRole( 'button', { name: 'Try again' } )
	);
	await waitFor( () =>
		expect(
			screen.queryByText( 'Genie did not answer. Please try again.' )
		).toBeNull()
	);
	expect( send ).toHaveBeenCalledTimes( 1 );
	expect(
		( await screen.findAllByText( 'Stored hero answer.' ) ).length
	).toBeGreaterThan( 0 );
} );

test( 'a cut stream on the hero keeps the question and not the partial answer', async () => {
	const read = vi.fn( async () => ( { messages: [], turn: null } ) );
	const send = vi.fn( async () => {
		throw new UnfinishedStreamError();
	} );
	const setPrompt = vi.fn();
	const view = await renderHero(
		new HeroSession( SESSION_CONFIG, read, send ),
		{
			setPrompt,
		}
	);

	await act( async () => {
		view.bridge().ask( 'backup for 10 kW' );
	} );

	await waitFor( () =>
		expect( screen.getByRole( 'alert' ) ).toHaveTextContent(
			'Genie did not answer. Please try again.'
		)
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
	const view = await renderHero(
		new HeroSession( SESSION_CONFIG, read, send ),
		{
			setPrompt,
		}
	);
	const file = new File( [ '%PDF-1.4' ], 'datasheet.pdf', {
		type: 'application/pdf',
	} );

	await act( async () => {
		view.bridge().ask( 'backup for 10 kW', [ file ] );
	} );

	await waitFor( () =>
		expect( screen.getByRole( 'alert' ) ).toHaveTextContent(
			'Genie did not answer. Please try again.'
		)
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
	const { bridge } = await renderHero(
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
	await renderHero( answers.session );

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
	const { setPrompt, focusPrompt } = await renderHero(
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
	const { bridge } = await renderHero( answers.session );
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
	const { bridge } = await renderHero( answers.session );
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
	await renderHero(
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
	await renderHero(
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

test( 'a scoped marketing failure is never painted by Hero for another principal', async () => {
	const original = 'Customer A private failed attachment';
	sessionStorage.setItem(
		'linker-genie-turn-failure',
		JSON.stringify( {
			v: 1,
			kind: 'upstream',
			text: original,
			question: original,
			uploads: [],
			omitted: [],
			entryId: 'marketing-a',
			entryScope: 'a'.repeat( 64 ),
		} )
	);
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( {
			ok: true,
			json: async () => ( { scope: 'b'.repeat( 64 ) } ),
		} ) )
	);
	try {
		const calls = await renderHero( session().session );
		expect(
			JSON.parse( sessionStorage.getItem( 'linker-genie-turn-failure' )! )
				.text
		).toBe( original );
		expect( calls.setPrompt ).not.toHaveBeenCalledWith( original );
		expect( document.body.textContent ).not.toContain( original );
	} finally {
		vi.unstubAllGlobals();
	}
} );
test( 'Hero retry checks the entry owner after the shared-thread refresh', async () => {
	const original = 'Customer A recovered question';
	let scope = 'a'.repeat( 64 );
	sessionStorage.setItem(
		'linker-genie-turn-failure',
		JSON.stringify( {
			v: 1,
			kind: 'upstream',
			text: original,
			question: original,
			uploads: [],
			omitted: [],
			entryId: 'marketing-a',
			entryScope: scope,
		} )
	);
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( { ok: true, json: async () => ( { scope } ) } ) )
	);
	try {
		const model = session();
		const calls = await renderHero( model.session );
		await waitFor( () =>
			expect( calls.setPrompt ).toHaveBeenCalledWith( original )
		);
		scope = 'b'.repeat( 64 );
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			)
		);
		expect( model.send ).not.toHaveBeenCalled();
	} finally {
		vi.unstubAllGlobals();
	}
} );

for ( const action of [ 'send', 'retry' ] as const ) {
	test( `Hero ${ action } preserves scoped text and bytes when the auxiliary identity service is unavailable`, async () => {
		const original = 'Keep scoped Hero schematic';
		const upload = {
			name: 'keep.pdf',
			type: 'application/pdf',
			data: 'YWJj',
		};
		let available = true;
		sessionStorage.setItem(
			'linker-genie-turn-failure',
			JSON.stringify( {
				v: 1,
				kind: 'upstream',
				text: original,
				question: original + '\nAttached: keep.pdf',
				uploads: [ upload ],
				omitted: [],
				entryId: 'hero-marketing',
				entryScope: 'a'.repeat( 64 ),
			} )
		);
		vi.stubGlobal(
			'fetch',
			vi.fn( async () => ( {
				ok: available,
				json: async () => ( { scope: 'a'.repeat( 64 ) } ),
			} ) )
		);
		try {
			const model = session();
			const calls = await renderHero( model.session );
			await waitFor( () =>
				expect( calls.setPrompt ).toHaveBeenCalledWith( original )
			);
			available = false;
			await act( async () =>
				action === 'send'
					? calls.bridge().ask( original )
					: fireEvent.click(
							screen.getByRole( 'button', { name: 'Try again' } )
						)
			);
			expect( model.send ).not.toHaveBeenCalled();
			expect( calls.setPrompt ).toHaveBeenLastCalledWith( original );
			expect( screen.queryByText( 'keep.pdf' ) ).toBeNull();
			const record = JSON.parse( currentOwnedRaw()! );
			expect( record.entryScope ).toBe( 'a'.repeat( 64 ) );
			expect( record.uploads ).toEqual( [ upload ] );
			available = true;
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', { name: 'Try again' } )
				)
			);
			expect( model.send ).not.toHaveBeenCalled();
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', { name: 'Try again' } )
				)
			);
			await waitFor( () =>
				expect( model.send ).toHaveBeenCalledTimes( 1 )
			);
			expect( model.send.mock.calls[ 0 ]?.[ 0 ].uploads ).toEqual( [
				upload,
			] );
		} finally {
			vi.unstubAllGlobals();
		}
	} );
}

test( 'Hero initial scoped failure outage stays hidden and retry restores through fresh verification', async () => {
	let available = false;
	let finishLookup!: () => void;
	const lookup = new Promise< void >( ( resolve ) => {
		finishLookup = resolve;
	} );
	const original = 'Private Hero recovery';
	sessionStorage.setItem(
		'linker-genie-turn-failure',
		JSON.stringify( {
			v: 1,
			kind: null,
			text: original,
			question: original,
			uploads: [],
			omitted: [],
			entryId: 'hero-recovery',
			entryScope: 'a'.repeat( 64 ),
		} )
	);
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => {
			if ( ! available ) {
				await lookup;
			}
			return {
				ok: available,
				json: async () => ( { scope: 'a'.repeat( 64 ) } ),
			};
		} )
	);
	try {
		const model = session();
		const calls = await renderHero( model.session );
		const loading = screen.getByText( 'One moment…' ).closest( '[role]' );
		expect( loading ).toHaveAttribute( 'role', 'status' );
		expect( loading ).toHaveClass( 'linker-genie-app__status' );
		expect( loading ).not.toHaveClass( 'linker-genie-app__error' );
		expect(
			screen.queryByRole( 'button', { name: 'Try again' } )
		).not.toBeInTheDocument();
		expect( calls.setPrompt ).not.toHaveBeenCalledWith( original );
		await act( async () => finishLookup() );
		await screen.findByRole( 'button', { name: 'Try again' } );
		const failure = screen
			.getByText( 'Genie could not load.' )
			.closest( '[role]' );
		expect( failure ).toHaveAttribute( 'role', 'alert' );
		expect( failure ).toHaveClass( 'linker-genie-app__error' );
		expect( calls.setPrompt ).not.toHaveBeenCalledWith( original );
		expect(
			sessionStorage.getItem( 'linker-genie-turn-failure' )
		).not.toBeNull();
		available = true;
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			)
		);
		await waitFor( () =>
			expect( calls.setPrompt ).toHaveBeenCalledWith( original )
		);
		expect( screen.queryByText( 'One moment…' ) ).not.toBeInTheDocument();
		expect( model.send ).not.toHaveBeenCalled();
	} finally {
		vi.unstubAllGlobals();
	}
} );

// Real native transport generates different UUIDs for otherwise identical turns
// whose files or page context differ. A second tab's answer cannot satisfy A.
test.each( [ 'same-operation', 'other-file', 'other-context' ] )(
	'native hero retry identifies %s',
	async ( scenario ) => {
		vi.stubGlobal( 'crypto', webcrypto );
		window.linkerPublicProtectionConfig = {
			api: '/proof',
			nonce: 'n',
			mode: 'enforce',
			language: 'en',
		};
		window.linkerPublicProtection = {
			proof: async () => 'synthetic-proof',
			reset: () => undefined,
		};
		try {
			const actual =
				await vi.importActual< typeof import( '../genie/api/turn' ) >(
					'../genie/api/turn'
				);
			const stream =
				'event: block\ndata: {"type":"text","text":"Completed native answer.","refs":[]}\n\nevent: done\ndata: {"ok":true}\n\n';
			let stored: {
				conversation_id: number;
				operation_id?: string;
				messages: TurnMessage[];
				stream: string;
			} = { conversation_id: 563, messages: [], stream: '' };
			const requests: Array< {
				id: string;
				body: {
					messages: TurnMessage[];
					attachments?: Upload[];
					page: unknown;
				};
			} > = [];
			const transport: typeof fetch = async ( _url, init ) => {
				const body = JSON.parse( String( init?.body ) );
				const id = new Headers( init?.headers ).get(
					'X-Linker-Operation'
				)!;
				requests.push( { id, body } );
				if ( requests.length === 1 && scenario !== 'same-operation' ) {
					return new Response( '{}', { status: 502 } );
				}
				stored = {
					conversation_id: 563,
					operation_id: id,
					messages: body.messages,
					stream,
				};
				return new Response( JSON.stringify( { stream } ), {
					status: requests.length === 1 ? 502 : 200,
				} );
			};
			const read = () =>
				actual.readThread(
					'/thread',
					'n',
					async () => new Response( JSON.stringify( stored ) )
				);
			const send = vi.fn(
				( request: Parameters< typeof actual.sendTurn >[ 0 ] ) =>
					actual.sendTurn( { ...request, fetcher: transport } )
			);
			const sessionA = new HeroSession( SESSION_CONFIG, read, send );
			const file = new File( [ '%PDF-1.7 fileA' ], 'test.pdf', {
				type: 'application/pdf',
			} );
			const view = await renderHero( sessionA );
			await act( async () => {
				view.bridge().ask( 'Check test.pdf', [ file ] );
			} );
			await waitFor( () =>
				expect( screen.getByRole( 'alert' ) ).toHaveTextContent(
					'Genie did not answer. Please try again.'
				)
			);
			const upload = requests[ 0 ].body.attachments![ 0 ];
			if ( scenario !== 'same-operation' ) {
				await actual.sendTurn( {
					...SESSION_CONFIG,
					messages: requests[ 0 ].body.messages,
					uploads: [
						scenario === 'other-file'
							? { ...upload, data: 'ZmlsZUI=' }
							: upload,
					],
					page:
						scenario === 'other-context'
							? { type: 'product', product_id: 2067 }
							: SESSION_CONFIG.page,
					fetcher: transport,
				} );
			}
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			);
			await waitFor( () =>
				expect( requests ).toHaveLength(
					scenario === 'same-operation' ? 1 : 3
				)
			);
			await waitFor( () =>
				expect( screen.queryByRole( 'alert' ) ).toBeNull()
			);
			expect( send ).toHaveBeenCalledTimes(
				scenario === 'same-operation' ? 1 : 2
			);
			expect( requests ).toHaveLength(
				scenario === 'same-operation' ? 1 : 3
			);
			expect(
				new Set( requests.map( ( request ) => request.id ) ).size
			).toBe( scenario === 'same-operation' ? 1 : 3 );
			expect( requests.at( -1 )!.body.attachments ).toEqual( [ upload ] );
			expect( requests.at( -1 )!.body.page ).toEqual(
				SESSION_CONFIG.page
			);
		} finally {
			delete window.linkerPublicProtectionConfig;
			delete window.linkerPublicProtection;
			vi.unstubAllGlobals();
		}
	}
);
