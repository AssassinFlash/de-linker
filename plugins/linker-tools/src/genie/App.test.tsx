// @vitest-environment jsdom
import {
	installNativeIdentityFixture,
	renderOwned,
	seedOwnedFailure,
	currentOwnedRaw,
} from './testing/nativeIdentity';

/**
 * One turn through the app: the disclosure once, the ask chips, and the card
 * states of add-to-draft (docs/specs/13-genie.md).
 */

/**
 * External dependencies
 */
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { __, resetLocaleData, setLocaleData } from '@wordpress/i18n';
import germanMessages from '../../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';

/**
 * Internal dependencies
 */
import type { GenieConfig } from './config';
import { App, reportRecoveryUrl, resetTurnLane, type Dictation } from './App';
import { PlanningSourcesCard } from './components/PlanningSourcesCard';
import type { PlanningSourcesBlock } from './api/turn';

vi.mock( './api/turn', async ( importOriginal ) => {
	const actual = await importOriginal< typeof import( './api/turn' ) >();
	return {
		// The real message rule, so a restored thread is spelled the same way
		// a live one is; the calls around it are doubles.
		assistantMessage: actual.assistantMessage,
		emailOutcome: actual.emailOutcome,
		isTurnConflict: actual.isTurnConflict,
		isUnfinishedStream: actual.isUnfinishedStream,
		turnConflictText: actual.turnConflictText,
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
		TurnError: actual.TurnError,
		UnfinishedStreamError: actual.UnfinishedStreamError,
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
vi.mock( './api/inquiry', () => ( {
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
import { readContact, sendContact } from './api/contact';
import { readInquiry, sendInquiry } from './api/inquiry';
import {
	deleteConversation,
	emailConversation,
	listConversations,
	readThread,
	selectConversation,
	sendTurn,
	sendVote,
	TurnError,
	UnfinishedStreamError,
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

// The mounted App owns one challenge slot and the pre-dispatch cancellation of
// its own turn, so every turn carries that binding rather than a DOM guess.
const ownedVerification = () =>
	expect.objectContaining( {
		slot: expect.any( Function ),
		signal: expect.any( AbortSignal ),
		beforeDispatch: expect.any( Function ),
		onDispatch: expect.any( Function ),
	} );

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
		inquiryUrl: '/wp-json/linker-ai/v1/genie/inquiry',
		prompts: [
			'Ask Genie',
			'I need a three-phase hybrid inverter for a home.',
		],
	};
}

installNativeIdentityFixture();

beforeEach( () => {
	sessionStorage.clear();
	resetTurnLane();
	vi.mocked( readThread )
		.mockReset()
		.mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( listConversations )
		.mockReset()
		.mockResolvedValue( { currentId: 0, conversations: [], ok: true } );
	vi.mocked( sendTurn ).mockReset();
} );

afterEach( () => {
	sessionStorage.clear();
	resetTurnLane();
	delete window.linkerPublicProtection;
	delete window.linkerPublicProtectionConfig;
} );

test( 'fresh report URLs carry only the exact saved project and run', () => {
	const project = 'a'.repeat( 32 );
	const run = 'b'.repeat( 32 );
	const href = `${ window.location.origin }/configurator/?project=${ project }&run=${ run }&nonce=private&question=private#lp-calculations`;
	const page = {
		type: 'other' as const,
		url: href,
		planning_project_id: project,
		planning_revision: 5,
		planning_run_ids: [ run ],
		planning_unsaved: false,
	};
	expect( reportRecoveryUrl( page, page, href ) ).toBe(
		`${ window.location.origin }/configurator/?project=${ project }&run=${ run }#lp-calculations`
	);
	const doubled = href.replace( '/configurator/', '//outside.example/' );
	const doubledPage = { ...page, url: doubled };
	expect(
		new URL( reportRecoveryUrl( doubledPage, doubledPage, doubled )! )
			.origin
	).toBe( window.location.origin );
	expect(
		reportRecoveryUrl( page, { ...page, planning_revision: 6 }, href )
	).toBeNull();
	expect(
		reportRecoveryUrl( page, { ...page, planning_unsaved: true }, href )
	).toBeNull();
	expect(
		reportRecoveryUrl(
			page,
			{ ...page, planning_run_ids: [ 'c'.repeat( 32 ) ] },
			href
		)
	).toBeNull();
	const secondRun = 'c'.repeat( 32 );
	const compareHref = `${ window.location.origin }/configurator/?project=${ project }&compare=${ run },${ secondRun }`;
	const comparison = {
		...page,
		url: compareHref,
		planning_run_ids: [ run, secondRun ],
	};
	expect(
		new URL(
			reportRecoveryUrl( comparison, comparison, compareHref )!
		).searchParams.get( 'compare' )
	).toBe( `${ run },${ secondRun }` );
	expect(
		reportRecoveryUrl(
			{ ...comparison, planning_run_ids: [ run, run ] },
			comparison,
			compareHref
		)
	).toBeNull();
	expect(
		reportRecoveryUrl(
			page,
			page,
			href.replace( `run=${ run }`, `run=${ 'c'.repeat( 32 ) }` )
		)
	).toBeNull();
	expect(
		reportRecoveryUrl(
			page,
			page,
			href.replace( window.location.origin, 'https://outside.example' )
		)
	).toBeNull();
} );

test( 'a refused saved-report question can be copied and opened in a fresh report tab', async () => {
	const original = window.location.href;
	const project = 'a'.repeat( 32 );
	const run = 'b'.repeat( 32 );
	window.history.replaceState(
		{},
		'',
		`/configurator/?project=${ project }&run=${ run }&nonce=private#lp-calculations`
	);
	const page = {
		type: 'other' as const,
		title: 'Saved report',
		url: window.location.href,
		planning_project_id: project,
		planning_revision: 5,
		planning_run_ids: [ run ],
		planning_unsaved: false,
	};
	const writeText = vi.fn( async () => undefined );
	Object.defineProperty( navigator, 'clipboard', {
		configurable: true,
		value: { writeText },
	} );
	vi.mocked( sendTurn ).mockRejectedValue(
		new Error( 'verification_widget_300030' )
	);
	try {
		await renderOwned( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		act( () =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-planning-context', {
					detail: { page },
				} )
			)
		);
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'My exact report question' },
		} );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
		);
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'My exact report question'
		);
		const link = screen.getByRole( 'link', {
			name: 'Open saved report in a new tab',
		} );
		expect( link ).toHaveAttribute(
			'href',
			`${ window.location.origin }/configurator/?project=${ project }&run=${ run }#lp-calculations`
		);
		expect( link ).toHaveAttribute( 'target', '_blank' );
		expect( link ).toHaveAttribute( 'rel', 'noopener noreferrer' );
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Copy question' } )
		);
		await waitFor( () =>
			expect( writeText ).toHaveBeenCalledWith(
				'My exact report question'
			)
		);
		expect( await screen.findByText( 'Copied' ) ).toBeVisible();
		expect( sendTurn ).toHaveBeenCalledTimes( 1 );
		const next = {
			...page,
			planning_run_ids: [ 'c'.repeat( 32 ) ],
			url: page.url.replace( run, 'c'.repeat( 32 ) ),
		};
		window.history.replaceState( {}, '', next.url );
		const staleClick = new MouseEvent( 'click', {
			bubbles: true,
			cancelable: true,
		} );
		link.dispatchEvent( staleClick );
		expect( staleClick.defaultPrevented ).toBe( true );
		act( () =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-planning-context', {
					detail: { page: next },
				} )
			)
		);
		expect(
			screen.queryByRole( 'link', {
				name: 'Open saved report in a new tab',
			} )
		).toBeNull();
		expect(
			screen.getByText( /The report selection has changed/ )
		).toBeVisible();
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'My exact report question'
		);
	} finally {
		window.history.replaceState( {}, '', original );
	}
} );

test( 'a selection changed while verification waits cannot open the wrong report', async () => {
	const original = window.location.href;
	const project = 'a'.repeat( 32 );
	const run = 'b'.repeat( 32 );
	window.history.replaceState(
		{},
		'',
		`/configurator/?project=${ project }&run=${ run }#lp-calculations`
	);
	const page = {
		type: 'other' as const,
		title: 'Report',
		url: window.location.href,
		planning_project_id: project,
		planning_revision: 5,
		planning_run_ids: [ run ],
		planning_unsaved: false,
	};
	let reject!: ( error: Error ) => void;
	vi.mocked( sendTurn ).mockImplementation(
		() =>
			new Promise( ( _resolve, fail ) => {
				reject = fail;
			} )
	);
	try {
		await renderOwned( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		act( () =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-planning-context', {
					detail: { page },
				} )
			)
		);
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Keep my original question' },
		} );
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
		await waitFor( () => expect( sendTurn ).toHaveBeenCalledOnce() );
		const next = {
			...page,
			planning_run_ids: [ 'c'.repeat( 32 ) ],
			url: page.url.replace( run, 'c'.repeat( 32 ) ),
		};
		window.history.replaceState( {}, '', next.url );
		act( () =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-planning-context', {
					detail: { page: next },
				} )
			)
		);
		await act( async () =>
			reject( new Error( 'verification_widget_300030' ) )
		);
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'Keep my original question'
		);
		expect(
			screen.getByText( /The report selection has changed/ )
		).toBeVisible();
		expect(
			screen.queryByRole( 'link', {
				name: 'Open saved report in a new tab',
			} )
		).toBeNull();
	} finally {
		window.history.replaceState( {}, '', original );
	}
} );

test( 'the actual verification adapter exposes saved-report recovery without dispatching', async () => {
	const actual =
		await vi.importActual< typeof import( './api/turn' ) >( './api/turn' );
	const { webcrypto } = await import( 'node:crypto' );
	vi.stubGlobal( 'crypto', webcrypto );
	const original = window.location.href;
	const project = 'a'.repeat( 32 );
	const run = 'b'.repeat( 32 );
	window.history.replaceState(
		{},
		'',
		`/configurator/?project=${ project }&run=${ run }#lp-calculations`
	);
	const page = {
		type: 'other' as const,
		title: 'Report',
		url: window.location.href,
		planning_project_id: project,
		planning_revision: 5,
		planning_run_ids: [ run ],
		planning_unsaved: false,
	};
	window.linkerPublicProtectionConfig = {
		api: '/proof',
		nonce: 'synthetic',
		mode: 'enforce',
		language: 'en',
	};
	window.linkerPublicProtection = {
		proof: vi.fn( async () => {
			throw new Error( 'verification_widget_300030' );
		} ),
		reset: vi.fn(),
	};
	const transport = vi.fn< typeof fetch >();
	vi.mocked( sendTurn ).mockImplementationOnce( ( request ) =>
		actual.sendTurn( { ...request, fetcher: transport } )
	);
	try {
		await renderOwned( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		act( () =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-planning-context', {
					detail: { page },
				} )
			)
		);
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Saved report question' },
		} );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
		);
		expect(
			await screen.findByRole( 'link', {
				name: 'Open saved report in a new tab',
			} )
		).toBeVisible();
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'Saved report question'
		);
		expect( transport ).not.toHaveBeenCalled();
	} finally {
		window.history.replaceState( {}, '', original );
		delete window.linkerPublicProtection;
		delete window.linkerPublicProtectionConfig;
	}
} );

test( 'recovery keeps attachments in the original tab and copies only the question', async () => {
	const original = window.location.href;
	const project = 'a'.repeat( 32 );
	const run = 'b'.repeat( 32 );
	window.history.replaceState(
		{},
		'',
		`/configurator/?project=${ project }&run=${ run }#lp-calculations`
	);
	const page = {
		type: 'other' as const,
		title: 'Report',
		url: window.location.href,
		planning_project_id: project,
		planning_revision: 5,
		planning_run_ids: [ run ],
		planning_unsaved: false,
	};
	const writeText = vi.fn( async () => undefined );
	Object.defineProperty( navigator, 'clipboard', {
		configurable: true,
		value: { writeText },
	} );
	vi.mocked( sendTurn ).mockRejectedValue(
		new Error( 'verification_widget_300030' )
	);
	try {
		await renderOwned( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		act( () =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-planning-context', {
					detail: { page },
				} )
			)
		);
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Question with a file' },
		} );
		fireEvent.change(
			document.querySelector( 'input[type="file"]' ) as HTMLInputElement,
			{
				target: {
					files: [
						new File( [ '%PDF-1.7' ], 'datasheet.pdf', {
							type: 'application/pdf',
						} ),
					],
				},
			}
		);
		const send = screen.getByRole( 'button', { name: 'Send' } );
		await waitFor( () => expect( send ).toBeEnabled() );
		await act( async () => fireEvent.click( send ) );
		expect( screen.getByText( 'datasheet.pdf' ) ).toBeVisible();
		expect(
			screen.getByText(
				'Attachments stay in this tab. Attach them again in the new tab.'
			)
		).toBeVisible();
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Copy question' } )
		);
		await waitFor( () =>
			expect( writeText ).toHaveBeenCalledWith( 'Question with a file' )
		);
		const href = screen
			.getByRole( 'link', { name: 'Open saved report in a new tab' } )
			.getAttribute( 'href' );
		expect( href ).not.toContain( 'datasheet' );
		expect( href ).not.toContain( 'Question' );
	} finally {
		window.history.replaceState( {}, '', original );
	}
} );

test.each( [
	[ true, 'verification_widget_300030' ],
	[ false, 'linker_admission_quota' ],
] )(
	'recovery is unavailable for an unsaved report or a different refusal',
	async ( unsaved, reason ) => {
		const original = window.location.href;
		const project = 'a'.repeat( 32 );
		const run = 'b'.repeat( 32 );
		window.history.replaceState(
			{},
			'',
			`/configurator/?project=${ project }&run=${ run }#lp-calculations`
		);
		const page = {
			type: 'other' as const,
			title: 'Report',
			url: window.location.href,
			planning_project_id: project,
			planning_revision: 5,
			planning_run_ids: [ run ],
			planning_unsaved: unsaved,
		};
		vi.mocked( sendTurn ).mockRejectedValue(
			unsaved ? new Error( reason ) : new TurnError( 429, reason )
		);
		try {
			await renderOwned( <App config={ config() } /> );
			fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
			act( () =>
				window.dispatchEvent(
					new CustomEvent( 'linker-genie-planning-context', {
						detail: { page },
					} )
				)
			);
			fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
				target: { value: 'Keep this question' },
			} );
			await act( async () =>
				fireEvent.click(
					screen.getByRole( 'button', { name: 'Send' } )
				)
			);
			expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
				'Keep this question'
			);
			expect(
				screen.queryByRole( 'link', {
					name: 'Open saved report in a new tab',
				} )
			).toBeNull();
		} finally {
			window.history.replaceState( {}, '', original );
		}
	}
);

test( 'German recovery uses the generated German script catalog', async () => {
	const original = window.location.href;
	const project = 'a'.repeat( 32 );
	const run = 'b'.repeat( 32 );
	window.history.replaceState(
		{},
		'',
		`/de/konfigurator/?project=${ project }&run=${ run }#lp-calculations`
	);
	const page = {
		type: 'other' as const,
		title: 'Bericht',
		url: window.location.href,
		planning_project_id: project,
		planning_revision: 5,
		planning_run_ids: [ run ],
		planning_unsaved: false,
	};
	setLocaleData( germanMessages.locale_data.messages, 'linker-tools' );
	vi.mocked( sendTurn ).mockRejectedValue(
		new Error( 'verification_widget_300030' )
	);
	try {
		await renderOwned( <App config={ config( 'de' ) } /> );
		fireEvent.click(
			screen.getByRole( 'button', { name: __( 'Open', 'linker-tools' ) } )
		);
		act( () =>
			window.dispatchEvent(
				new CustomEvent( 'linker-genie-planning-context', {
					detail: { page },
				} )
			)
		);
		fireEvent.change( screen.getByLabelText( 'Genie fragen' ), {
			target: { value: 'Meine Frage zum Bericht' },
		} );
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', {
					name: __( 'Send', 'linker-tools' ),
				} )
			)
		);
		expect(
			screen.getByRole( 'button', { name: 'Frage kopieren' } )
		).toBeVisible();
		expect(
			screen.getByRole( 'link', {
				name: 'Gespeicherten Bericht in neuem Tab öffnen',
			} )
		).toBeVisible();
		expect(
			screen.getByText(
				/Kopieren Sie Ihre Frage und öffnen Sie den Bericht/
			)
		).toBeVisible();
		expect( screen.getByLabelText( 'Genie fragen' ) ).toHaveValue(
			'Meine Frage zum Bericht'
		);
	} finally {
		resetLocaleData( {}, 'linker-tools' );
		window.history.replaceState( {}, '', original );
	}
} );

test( 'saved source card shows exact UTC ranges without private bindings or sizing choices', async () => {
	const project = 'a'.repeat( 32 ),
		run = 'b'.repeat( 32 );
	const block: PlanningSourcesBlock = {
		type: 'planning_sources',
		schema_version: 1,
		status: 'available',
		binding: {
			planning_project_id: project,
			planning_revision: 12,
			planning_run_ids: [ run ],
			runs: [
				{
					id: run,
					revision: 11,
					manifest_sha256: 'c'.repeat( 64 ),
					result_sha256: 'd'.repeat( 64 ),
				},
			],
		},
		results: [
			{
				revision: 11,
				groups: [
					{
						kind: 'pv',
						role: 'selected',
						input_quantity: 'pv_available_ac',
						source_scope: 'whole_reference',
						timezone: 'Europe/Paris',
						radiation_database: 'PVGIS-SARAH3',
						meteorological_database: 'ERA5',
						weather_selection_period: {
							start_year: 2014,
							end_year: 2023,
						},
						synthetic_calculation_year: 2023,
						periods_utc: [
							{
								start_utc: '2023-01-01T00:00:00+00:00',
								end_utc: '2024-01-01T00:00:00+00:00',
							},
						],
					},
					{
						kind: 'energy',
						role: 'selected',
						timezone: null,
						periods_utc: [
							{
								start_utc: '2023-06-16T09:00:00+00:00',
								end_utc: '2023-06-16T11:00:00+00:00',
							},
						],
					},
				],
			},
		],
		url: `https://de-linker.test/solution-configurator/?project=${ project }&run=${ run }#lp-calculations`,
	};
	block.results[ 0 ].groups.splice( 1, 0, {
		...block.results[ 0 ].groups[ 0 ],
		input_quantity: 'pv_available_dc',
		source_scope: 'selected_dc_group',
		meteorological_database: null,
	} );
	const { container, rerender, unmount } = await renderOwned(
		<PlanningSourcesCard
			block={ block }
			configuratorLinks={ {
				en: 'https://de-linker.test/solution-configurator/',
				de: '',
				current: '',
			} }
		/>
	);
	expect( screen.getByText( 'Saved revision 11' ) ).toBeInTheDocument();
	for ( const value of [
		'PVGIS-SARAH3',
		'ERA5',
		'2014–2023',
		'2023-01-01T00:00:00+00:00',
		'2024-01-01T00:00:00+00:00',
		'2023-06-16T09:00:00+00:00',
		'2023-06-16T11:00:00+00:00',
	] ) {
		expect( screen.getAllByText( value ).length ).toBeGreaterThan( 0 );
	}
	expect(
		screen.getAllByText( 'Not recorded in this saved result' ).length
	).toBeGreaterThan( 0 );
	expect( screen.getByText( 'AC' ) ).toBeInTheDocument();
	expect( screen.getByText( 'DC' ) ).toBeInTheDocument();
	expect( screen.getByText( 'Whole PV reference' ) ).toBeInTheDocument();
	expect( screen.getByText( 'Selected DC group' ) ).toBeInTheDocument();
	expect(
		screen.getByRole( 'link', { name: 'Open saved result' } )
	).toHaveAttribute( 'href', block.url );
	expect( container.textContent ).not.toContain( project );
	expect( container.textContent ).not.toContain( run );
	expect( container.textContent ).not.toContain( 'Backup' );
	const annual = structuredClone( block );
	annual.results[ 0 ].groups = [ annual.results[ 0 ].groups[ 0 ] ];
	delete annual.results[ 0 ].groups[ 0 ].weather_selection_period;
	delete annual.results[ 0 ].groups[ 0 ].synthetic_calculation_year;
	annual.results[ 0 ].groups[ 0 ].meteorological_database = null;
	annual.results[ 0 ].groups[ 0 ].input_quantity = null;
	annual.results[ 0 ].groups[ 0 ].source_scope = null;
	rerender( <PlanningSourcesCard block={ annual } /> );
	expect(
		screen.queryByText( 'Weather selection period' )
	).not.toBeInTheDocument();
	expect(
		screen.queryByText( 'Synthetic calculation year' )
	).not.toBeInTheDocument();
	expect(
		screen.getAllByText( 'Not identified in this saved result' )
	).toHaveLength( 2 );
	rerender(
		<PlanningSourcesCard
			block={ {
				type: 'planning_sources',
				schema_version: 1,
				status: 'unavailable',
			} }
		/>
	);
	expect(
		screen.getByText(
			'The saved calculation details could not be verified for this response.'
		)
	).toBeInTheDocument();
	expect( container.querySelector( 'time' ) ).toBeNull();
	expect( container.querySelector( 'a' ) ).toBeNull();
	unmount();
	const unavailable: Awaited< ReturnType< typeof readThread > > = {
		conversationId: 12,
		messages: [
			{ role: 'user', content: 'Explain the saved result.' },
			{ role: 'assistant', content: 'Saved explanation' },
		],
		turn: {
			meta: null,
			blocks: [
				{ type: 'text', text: 'Saved explanation', refs: [] },
				{
					type: 'planning_sources',
					schema_version: 1,
					status: 'unavailable',
				},
			],
		},
	};
	const verified = {
		...unavailable,
		messages: unavailable.messages.map( ( message ) => ( { ...message } ) ),
		turn: {
			meta: null,
			blocks: [
				{ type: 'text' as const, text: 'Saved explanation', refs: [] },
				block,
			],
		},
	};
	vi.mocked( readThread )
		.mockResolvedValueOnce( unavailable )
		.mockResolvedValueOnce( verified );
	const opened = await renderOwned( <App config={ config() } /> );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	} );
	await waitFor( () =>
		expect(
			screen.getAllByText( '2023-06-16T09:00:00+00:00' )
		).toHaveLength( 1 )
	);
	expect( readThread ).toHaveBeenCalledTimes( 2 );
	expect( vi.mocked( readThread ).mock.calls[ 1 ][ 4 ] ).toMatchObject( {
		allowExistingOwnerBootstrap: true,
	} );
	expect( screen.getByText( 'Saved explanation' ) ).toBeInTheDocument();
	fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	} );
	expect( readThread ).toHaveBeenCalledTimes( 2 ); // No repeat after successful verification.
	opened.unmount();
	resetTurnLane();
	vi.mocked( readThread )
		.mockReset()
		.mockResolvedValue( { messages: [], turn: null } );
	let finishProof!: (
		value: Awaited< ReturnType< typeof readThread > >
	) => void;
	let finishSwitch!: (
		value: Awaited< ReturnType< typeof selectConversation > >
	) => void;
	vi.mocked( readThread )
		.mockResolvedValueOnce( unavailable )
		.mockImplementationOnce(
			() =>
				new Promise( ( resolve ) => {
					finishProof = resolve;
				} )
		);
	vi.mocked( selectConversation ).mockImplementationOnce(
		() =>
			new Promise( ( resolve ) => {
				finishSwitch = resolve;
			} )
	);
	const interrupted = await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await waitFor( () => expect( readThread ).toHaveBeenCalledTimes( 2 ) );
	fireEvent.click(
		screen.getByRole( 'button', { name: 'New conversation' } )
	);
	await act( async () => {
		finishProof( verified );
	} );
	await waitFor( () =>
		expect( selectConversation ).toHaveBeenCalledTimes( 1 )
	);
	// The next native history operation is still pending: a late proof must
	// never insert the prior calculation's dates during this transition.
	expect( screen.queryByText( '2023-06-16T09:00:00+00:00' ) ).toBeNull();
	await act( async () => {
		finishSwitch( { currentId: 0, conversations: [], ok: true } );
	} );
	interrupted.unmount();
} );

test( 'full-page source recovery waits for visible owned restore and runs once', async () => {
	const saved: Awaited< ReturnType< typeof readThread > > = {
		conversationId: 12,
		messages: [
			{ role: 'user', content: 'Explain the saved result.' },
			{ role: 'assistant', content: '' },
		],
		turn: {
			meta: null,
			blocks: [
				{
					type: 'planning_sources',
					schema_version: 1,
					status: 'unavailable',
				},
			],
		},
	};
	const previous = Object.getOwnPropertyDescriptor(
		document,
		'visibilityState'
	);
	let visibility = 'hidden';
	Object.defineProperty( document, 'visibilityState', {
		configurable: true,
		get: () => visibility,
	} );
	try {
		vi.mocked( readThread ).mockResolvedValue( saved );
		const hidden = await renderOwned(
			<App config={ { ...config(), surface: 'workspace' } } />
		);
		expect( readThread ).toHaveBeenCalledTimes( 1 );
		await act( async () => {
			document.dispatchEvent( new Event( 'visibilitychange' ) );
		} );
		expect( readThread ).toHaveBeenCalledTimes( 1 ); // Hidden mount cannot refresh native owner proof.
		visibility = 'visible';
		await act( async () => {
			document.dispatchEvent( new Event( 'visibilitychange' ) );
		} );
		await waitFor( () => expect( readThread ).toHaveBeenCalledTimes( 2 ) );
		expect( vi.mocked( readThread ).mock.calls[ 1 ][ 4 ] ).toMatchObject( {
			allowExistingOwnerBootstrap: true,
		} );
		visibility = 'hidden';
		await act( async () => {
			document.dispatchEvent( new Event( 'visibilitychange' ) );
		} );
		visibility = 'visible';
		await act( async () => {
			document.dispatchEvent( new Event( 'visibilitychange' ) );
		} );
		expect( readThread ).toHaveBeenCalledTimes( 2 ); // Failed verification is not a retry loop.
		hidden.unmount();
		resetTurnLane();
		vi.mocked( readThread ).mockClear();
		const cold = await renderOwned(
			<App config={ { ...config(), surface: 'workspace' } } />
		);
		await waitFor( () => expect( readThread ).toHaveBeenCalledTimes( 2 ) );
		expect( vi.mocked( readThread ).mock.calls[ 0 ][ 4 ] ).toMatchObject( {
			allowExistingOwnerBootstrap: false,
		} );
		expect( vi.mocked( readThread ).mock.calls[ 1 ][ 4 ] ).toMatchObject( {
			allowExistingOwnerBootstrap: true,
		} );
		await act( async () => {
			document.dispatchEvent( new Event( 'visibilitychange' ) );
		} );
		expect( readThread ).toHaveBeenCalledTimes( 2 );
		cold.unmount();
	} finally {
		if ( previous ) {
			Object.defineProperty( document, 'visibilityState', previous );
		} else {
			Reflect.deleteProperty( document, 'visibilityState' );
		}
	}
} );

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
	await renderOwned( <App config={ config() } /> );
	expect( readThread ).toHaveBeenCalledWith(
		expect.any( String ),
		'n',
		undefined,
		expect.any( Object ),
		expect.objectContaining( { allowExistingOwnerBootstrap: false } )
	);
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => undefined );
	// Opening a legacy conversation does not repeat history/journal restore.
	expect( readThread ).toHaveBeenCalledTimes( 1 );

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

	expect( sendTurn ).toHaveBeenCalledWith( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		onOperation: expect.any( Function ),
		restUrl: '/wp-json/',
		nonce: 'n',
		locale: 'en',
		messages: [
			{
				role: 'user',
				content: 'I need a three-phase hybrid inverter for a home.',
			},
		],
		page: { type: 'category' },
		// No file was picked: the turn carries none.
		uploads: [],
		verification: ownedVerification(),
		plannerNonce: undefined,
	} );
	expect( await screen.findByText( 'Three-phase' ) ).toBeInTheDocument();
	expect(
		screen.getByRole( 'group', { name: 'Reply with an option' } )
	).toBeInTheDocument();
	// The disclosure is still there exactly once after the turn.
	expect(
		screen.getAllByText(
			"Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system."
		)
	).toHaveLength( 1 );
	const bridge = () =>
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-planning-context', {
				detail: {
					page: {
						type: 'configurator',
						planning_project_id: 'a'.repeat( 32 ),
						planning_revision: 12,
					},
					plannerNonce: 'bridge-proof',
				},
			} )
		);
	window.addEventListener( 'linker-genie-planning-context-request', bridge, {
		once: true,
	} );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { refresh: true },
			} )
		);
	} );
	await waitFor( () =>
		expect( readThread ).toHaveBeenCalledWith(
			expect.any( String ),
			'n',
			undefined,
			expect.any( Object ),
			expect.objectContaining( {
				plannerNonce: 'bridge-proof',
				allowExistingOwnerBootstrap: false,
			} )
		)
	);
} );

test( 'a German turn keeps the thread and renders the chips in German', async () => {
	const { parseStream } =
		await vi.importActual< typeof import( './api/turn' ) >( './api/turn' );
	vi.mocked( sendTurn ).mockImplementation( async () =>
		Promise.resolve( parseStream( GERMAN_STREAM ) )
	);
	await renderOwned( <App config={ config( 'de' ) } /> );
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
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Ask Genie' } ) );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue( 'Ask Genie' );
	expect(
		screen.queryByText( 'Ask Genie', {
			selector: '.linker-genie-app__message',
		} )
	).toBeNull();
} );

test.each( [
	'completed',
	'completed-with-next-draft',
	'other-conversation',
	'other-operation-attachment',
	'other-operation-context',
	'missing-operation',
	'missing-id',
	'changed-prefix',
	'historical',
	'unfinished',
] )( 'retry requires a witnessed completed request: %s', async ( scenario ) => {
	const before = [
		{ role: 'user' as const, content: 'SAJ' },
		{ role: 'assistant' as const, content: 'Which product?' },
	];
	const question = 'Show me the B2-10.0-HV1 product and its datasheet.';
	vi.mocked( readThread ).mockResolvedValue( {
		conversationId: 563,
		messages: before,
		turn: null,
	} );
	vi.mocked( sendTurn ).mockImplementation( async ( request ) => {
		request.onOperation?.( '56300000-0000-4000-8000-000000000001' );
		throw new Error( 'network result unknown' );
	} );
	const workspace = scenario === 'completed-with-next-draft';
	await renderOwned(
		<App
			config={ {
				...config(),
				surface: workspace ? 'workspace' : 'helper',
			} }
		/>
	);
	if ( ! workspace ) {
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	}
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: question },
	} );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	// The real reader parses the proxy's complete stream and appends its
	// assistant message; the first HTTP request failed after it was stored.
	const actual =
		await vi.importActual< typeof import( './api/turn' ) >( './api/turn' );
	const recoveredId = scenario === 'other-conversation' ? 564 : 563;
	const operationId = scenario.startsWith( 'other-operation' )
		? '56300000-0000-4000-8000-000000000002'
		: '56300000-0000-4000-8000-000000000001';
	const stored = await actual.readThread(
		'/thread',
		'n',
		async () =>
			new Response(
				JSON.stringify( {
					conversation_id:
						scenario === 'missing-id' ? undefined : recoveredId,
					operation_id:
						scenario === 'missing-operation'
							? undefined
							: operationId,
					messages: [
						...( scenario === 'changed-prefix'
							? [
									{
										role: 'user',
										content: 'another context',
									},
									before[ 1 ],
								]
							: before ),
						...( scenario === 'historical'
							? []
							: [ { role: 'user', content: question } ] ),
					],
					stream:
						scenario === 'unfinished'
							? 'event: block\ndata: {"type":"text","text":"Partial","refs":[]}\n\n'
							: 'event: block\ndata: {"type":"text","text":"The stored answer.","refs":[]}\n\nevent: done\ndata: {"ok":true}\n\n',
				} ),
				{ status: 200 }
			)
	);
	vi.mocked( readThread ).mockResolvedValue( stored );
	let finishRetry!: () => void;
	if ( scenario === 'completed-with-next-draft' ) {
		vi.mocked( readThread ).mockImplementationOnce(
			() =>
				new Promise( ( resolve ) => {
					finishRetry = () => resolve( stored );
				} )
		);
	}
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) );
	} );
	async function acceptNextDraftDuringRetry() {
		await waitFor( () => expect( finishRetry ).toBeTypeOf( 'function' ) );
		expect(
			screen.getByRole( 'button', { name: 'Attach a file' } )
		).toBeVisible();
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Next accepted question' },
		} );
		fireEvent.change( document.querySelector( 'input[type="file"]' )!, {
			target: {
				files: [
					new File( [ '%PDF-1.7 next' ], 'next.pdf', {
						type: 'application/pdf',
					} ),
				],
			},
		} );
		await waitFor( () => {
			expect( screen.queryByText( 'Preparing file…' ) ).toBeNull();
			expect( screen.getByText( 'next.pdf' ) ).toBeInTheDocument();
		} );
		await act( async () => finishRetry() );
	}
	const nextDraft = scenario === 'completed-with-next-draft';
	if ( nextDraft ) {
		await acceptNextDraftDuringRetry();
	}
	const completed = scenario.startsWith( 'completed' );
	expect( sendTurn ).toHaveBeenCalledTimes( completed ? 1 : 2 );
	if ( ! completed ) {
		return;
	}
	expect(
		await screen.findByText( 'The stored answer.' )
	).toBeInTheDocument();
	expect( screen.queryByRole( 'alert' ) ).toBeNull();
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
		nextDraft ? 'Next accepted question' : ''
	);
	expect( screen.queryByText( 'next.pdf' ) !== null ).toBe( nextDraft );
	const raw = currentOwnedRaw();
	const record = raw ? JSON.parse( raw ) : null;
	expect(
		record && {
			text: record.text,
			editing: record.editing,
			uploads: record.uploads,
		}
	).toEqual(
		nextDraft
			? {
					text: 'Next accepted question',
					editing: true,
					uploads: [
						{
							name: 'next.pdf',
							type: 'application/pdf',
							data: btoa( '%PDF-1.7 next' ),
						},
					],
				}
			: null
	);
	// The same words typed as a new question remain a deliberate new turn.
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: question },
	} );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	expect( sendTurn ).toHaveBeenCalledTimes( 2 );
} );

test( 'a 502 keeps the question across a reload and retries once', async () => {
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn ).mockRejectedValue(
		new TurnError( 502, 'linker_genie_upstream' )
	);
	const first = await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const field = screen.getByLabelText( 'Ask Genie' );
	fireEvent.change( field, { target: { value: 'EV chargers' } } );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( field ).toHaveValue( 'EV chargers' );
	expect(
		screen.queryByText( 'EV chargers', {
			selector: '.linker-genie-app__message',
		} )
	).toBeNull();

	first.unmount();
	resetTurnLane();
	vi.mocked( sendTurn ).mockReset();
	let release!: ( value: Awaited< ReturnType< typeof sendTurn > > ) => void;
	vi.mocked( sendTurn ).mockImplementation(
		() =>
			new Promise( ( resolve ) => {
				release = resolve;
			} )
	);
	await renderOwned( <App config={ config() } /> );
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue( 'EV chargers' );
	const retry = screen.getByRole( 'button', { name: 'Try again' } );
	fireEvent.click( retry );
	fireEvent.click( retry );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]![ 0 ].messages ).toEqual( [
		{ role: 'user', content: 'EV chargers' },
	] );
	await act( async () => {
		release( {
			meta: null,
			blocks: [ { type: 'text', text: 'Recovered.', refs: [] } ],
		} );
	} );
	expect( await screen.findByText( 'Recovered.' ) ).toBeInTheDocument();
	expect(
		screen.queryByText( 'Genie did not answer. Please try again.' )
	).toBeNull();
} );

test( 'a cut stream keeps the question, hides the partial answer, and retries the stored turn', async () => {
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn ).mockRejectedValue( new UnfinishedStreamError() );
	const first = await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'backup for 10 kW' },
	} );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( screen.getByText( 'backup for 10 kW' ) ).toBeInTheDocument();
	expect( screen.queryByText( '10 kW from a cut stream' ) ).toBeNull();
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue( '' );

	first.unmount();
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [ { role: 'user', content: 'backup for 10 kW' } ],
		turn: null,
	} );
	vi.mocked( sendTurn ).mockReset();
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: null,
		blocks: [ { type: 'text', text: 'A hybrid covers that.', refs: [] } ],
	} );
	await renderOwned( <App config={ config() } /> );
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( screen.getByText( 'backup for 10 kW' ) ).toBeInTheDocument();
	expect( screen.queryByText( '10 kW from a cut stream' ) ).toBeNull();
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue( '' );
	fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]![ 0 ].messages ).toEqual( [
		{ role: 'user', content: 'backup for 10 kW' },
	] );
	expect(
		await screen.findByText( 'A hybrid covers that.' )
	).toBeInTheDocument();
} );

test( 'a cut stream keeps the file on the composer, and a new question sends it', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	const datasheet = new File( [ '%PDF-1.7' ], 'gw10k-et-datenblatt.pdf', {
		type: 'application/pdf',
	} );
	const upload = {
		name: 'gw10k-et-datenblatt.pdf',
		type: 'application/pdf' as const,
		data: btoa( '%PDF-1.7' ),
	};
	vi.mocked( sendTurn )
		.mockRejectedValueOnce( new UnfinishedStreamError() )
		.mockResolvedValueOnce( {
			meta: null,
			blocks: [
				{ type: 'text', text: 'The datasheet matches.', refs: [] },
			],
		} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Check this datasheet' },
	} );
	fireEvent.change( document.querySelector( 'input[type="file"]' )!, {
		target: { files: [ datasheet ] },
	} );
	const send = screen.getByRole( 'button', { name: 'Send' } );
	await waitFor( () => expect( send ).toBeEnabled() );
	await act( async () => {
		fireEvent.click( send );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue( '' );
	expect( screen.getByText( 'gw10k-et-datenblatt.pdf' ) ).toBeInTheDocument();
	expect(
		screen.getByRole( 'button', {
			name: 'Remove attachment gw10k-et-datenblatt.pdf',
		} )
	).toBeInTheDocument();

	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'What about this file?' },
	} );
	await act( async () => {
		fireEvent.click( send );
	} );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 2 ) );
	expect( vi.mocked( sendTurn ).mock.calls[ 1 ]![ 0 ].messages ).toEqual( [
		{
			role: 'user',
			content: 'Check this datasheet\nAttached: gw10k-et-datenblatt.pdf',
		},
		{
			role: 'user',
			content: 'What about this file?\nAttached: gw10k-et-datenblatt.pdf',
		},
	] );
	expect( vi.mocked( sendTurn ).mock.calls[ 1 ]![ 0 ].uploads ).toEqual( [
		upload,
	] );
	expect(
		await screen.findByText( 'The datasheet matches.' )
	).toBeInTheDocument();
} );

test( 'a cut stream drops a file the visitor removes, and retry does not send it', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockRejectedValueOnce( new UnfinishedStreamError() )
		.mockResolvedValueOnce( {
			meta: null,
			blocks: [
				{ type: 'text', text: 'Sent without the file.', refs: [] },
			],
		} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Check this datasheet' },
	} );
	fireEvent.change( document.querySelector( 'input[type="file"]' )!, {
		target: {
			files: [
				new File( [ '%PDF-1.7' ], 'gw10k-et-datenblatt.pdf', {
					type: 'application/pdf',
				} ),
			],
		},
	} );
	const send = screen.getByRole( 'button', { name: 'Send' } );
	await waitFor( () => expect( send ).toBeEnabled() );
	await act( async () => {
		fireEvent.click( send );
	} );
	fireEvent.click(
		await screen.findByRole( 'button', {
			name: 'Remove attachment gw10k-et-datenblatt.pdf',
		} )
	);
	expect( screen.queryByText( 'gw10k-et-datenblatt.pdf' ) ).toBeNull();
	fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 2 ) );
	expect( vi.mocked( sendTurn ).mock.calls[ 1 ]![ 0 ].uploads ).toEqual( [] );
	expect( vi.mocked( sendTurn ).mock.calls[ 1 ]![ 0 ].messages ).toEqual( [
		{
			role: 'user',
			content: 'Check this datasheet\nAttached: gw10k-et-datenblatt.pdf',
		},
	] );
} );

test( 'a 502 keeps an attached file across a reload', async () => {
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn ).mockRejectedValue(
		new TurnError( 502, 'linker_genie_upstream' )
	);
	const first = await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Check this datasheet' },
	} );
	const fileInput = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	fireEvent.change( fileInput, {
		target: {
			files: [
				new File( [ '%PDF-1.7' ], 'gw10k-et-datenblatt.pdf', {
					type: 'application/pdf',
				} ),
			],
		},
	} );
	const send = screen.getByRole( 'button', { name: 'Send' } );
	await waitFor( () => expect( send ).toBeEnabled() );
	await act( async () => {
		fireEvent.click( send );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
	expect( screen.getByText( 'gw10k-et-datenblatt.pdf' ) ).toBeInTheDocument();
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
		'Check this datasheet'
	);

	first.unmount();
	resetTurnLane();
	await renderOwned( <App config={ config() } /> );
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect(
		await screen.findByText( 'gw10k-et-datenblatt.pdf' )
	).toBeInTheDocument();
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
		'Check this datasheet'
	);
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);
} );

test( 'a conflicting turn re-reads, keeps the question and refreshes the rail', async () => {
	resetTurnLane();
	const server = [
		{ role: 'user' as const, content: 'Which inverter?' },
		{
			role: 'assistant' as const,
			content: 'The hybrid inverter is three-phase.',
		},
	];
	vi.mocked( readThread ).mockResolvedValue( {
		messages: server,
		turn: null,
		contacts: [],
		inquiries: [],
	} );
	vi.mocked( sendTurn )
		.mockClear()
		.mockRejectedValue(
			new TurnError( 409, 'linker_genie_turn_conflict' )
		);
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await waitFor( () => expect( listConversations ).toHaveBeenCalled() );
	vi.mocked( listConversations ).mockClear();
	const field = screen.getByLabelText( 'Ask Genie' );
	fireEvent.change( field, { target: { value: 'EV chargers' } } );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'The conversation changed while Genie was answering. Send your question again.'
	);
	expect(
		screen.queryByText( 'Genie did not answer. Please try again.' )
	).toBeNull();
	expect( field ).toHaveValue( 'EV chargers' );
	expect(
		screen.queryByText( 'EV chargers', {
			selector: '.linker-genie-app__message',
		} )
	).toBeNull();
	expect( sendTurn ).toHaveBeenCalledWith( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		onOperation: expect.any( Function ),
		restUrl: '/wp-json/',
		nonce: 'n',
		locale: 'en',
		messages: [ ...server, { role: 'user', content: 'EV chargers' } ],
		page: { type: 'category' },
		uploads: [],
		verification: ownedVerification(),
		plannerNonce: undefined,
	} );
	await waitFor( () => expect( listConversations ).toHaveBeenCalled() );
} );

test( 'the next send uses the thread re-read from the server', async () => {
	resetTurnLane();
	vi.mocked( readThread )
		.mockResolvedValueOnce( { messages: [], turn: null } )
		.mockResolvedValue( {
			messages: [
				{ role: 'user', content: 'Peer question' },
				{ role: 'assistant', content: 'Peer answer' },
			],
			turn: null,
		} );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [
				{ type: 'text', text: 'Stored with the peer.', refs: [] },
			],
		} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'I need a three-phase hybrid inverter for a home.',
			} )
		);
	} );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]![ 0 ].messages ).toEqual( [
		{ role: 'user', content: 'Peer question' },
		{ role: 'assistant', content: 'Peer answer' },
		{
			role: 'user',
			content: 'I need a three-phase hybrid inverter for a home.',
		},
	] );
} );

test( 'a conflicting attachment turn keeps the upload', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockClear()
		.mockRejectedValue(
			new TurnError( 409, 'linker_genie_turn_conflict' )
		);
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const fileInput = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	const datasheet = new File( [ '%PDF-1.7' ], 'gw10k-et-datenblatt.pdf', {
		type: 'application/pdf',
	} );
	fireEvent.change( fileInput, { target: { files: [ datasheet ] } } );
	await screen.findByText( 'gw10k-et-datenblatt.pdf' );
	const send = screen.getByRole( 'button', { name: 'Send' } );
	await waitFor( () => expect( send ).toBeEnabled() );
	await act( async () => {
		fireEvent.click( send );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'The conversation changed while Genie was answering. Send your question again.'
	);
	expect( screen.getByText( 'gw10k-et-datenblatt.pdf' ) ).toBeInTheDocument();
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
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
	await renderOwned( <App config={ config() } /> );
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

	await renderOwned( <App config={ config() } /> );
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

test( 'the dock reads the thread the home hero wrote and says where it began (#232)', async () => {
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
			blocks: [
				{ type: 'text', text: 'These three fit.', refs: [ '3556' ] },
			],
		},
	} );

	await renderOwned( <App config={ config() } /> );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { refresh: true, fromHome: true },
			} )
		);
	} );

	await waitFor( () =>
		expect(
			screen.getByText( 'Which inverters fit a three-phase home?' )
		).toBeInTheDocument()
	);
	expect( screen.getByText( 'Asked from the homepage' ) ).toBeInTheDocument();
} );

test( 'a first visit with no stored conversation opens empty', async () => {
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	await renderOwned( <App config={ config() } /> );
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
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);
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
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);
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
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
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
		await renderOwned( <App config={ config() } /> );
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
	await renderOwned( <App config={ config() } /> );
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
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]![ 0 ].messages ).toEqual( [
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
	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);
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
	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);
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
	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);
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

	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);

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
test( 'the open dock head carries the icon group', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	await renderOwned( <App config={ config() } /> );
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
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	await renderOwned( <App config={ config() } /> );
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
test( 'the dock footer carries the site links, locale-aware', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	const { unmount } = await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.click( screen.getByText( 'Help & privacy' ) );
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
	await renderOwned( <App config={ config( 'de' ) } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.click( screen.getByText( 'Help & privacy' ) );
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
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	await renderOwned( <App config={ config() } /> );
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

// A picked file rides apart from the messages (#236): its name in the
// question, its bytes in the turn's attachments; the chip takes it back out.
test( 'an attached file rides with the turn and its name in the question', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);
	const fileInput = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	const attach = screen.getByRole( 'button', { name: 'Attach a file' } );
	expect( attach ).toBeVisible();
	const pickerClick = vi.spyOn( fileInput, 'click' );
	fireEvent.click( attach );
	expect( pickerClick ).toHaveBeenCalledOnce();
	expect( fileInput.accept ).toContain( 'image/heic' );
	expect( fileInput.accept ).toContain( 'application/pdf' );
	const datasheet = new File( [ '%PDF-1.7' ], 'gw10k-et-datenblatt.pdf', {
		type: 'application/pdf',
	} );
	fireEvent.change( fileInput, { target: { files: [ datasheet ] } } );
	await screen.findByText( 'gw10k-et-datenblatt.pdf' );
	// The send key arms on an attachment alone, and the chip removes it.
	const send = screen.getByRole( 'button', { name: 'Send' } );
	await waitFor( () => expect( send ).toBeEnabled() );
	fireEvent.click(
		screen.getByRole( 'button', {
			name: 'Remove attachment gw10k-et-datenblatt.pdf',
		} )
	);
	expect( screen.queryByText( 'gw10k-et-datenblatt.pdf' ) ).toBeNull();
	expect( send ).toBeDisabled();
	fireEvent.change( fileInput, { target: { files: [ datasheet ] } } );
	await waitFor( () => expect( send ).toBeEnabled() );
	await act( async () => {
		fireEvent.click( send );
	} );
	const call = vi.mocked( sendTurn ).mock.calls[ 0 ]!;
	expect( call[ 0 ].messages ).toEqual( [
		{ role: 'user', content: 'Attached: gw10k-et-datenblatt.pdf' },
	] );
	expect( call[ 0 ].uploads ).toEqual( [
		{
			name: 'gw10k-et-datenblatt.pdf',
			type: 'application/pdf',
			data: btoa( '%PDF-1.7' ),
		},
	] );
	// The sent attachment leaves the composer.
	expect( screen.queryByText( 'gw10k-et-datenblatt.pdf' ) ).toBeNull();
} );

// A file that is not a photo or a PDF never leaves the browser.
test( 'a file Genie cannot read is refused before it is sent', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const fileInput = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	fireEvent.change( fileInput, {
		target: { files: [ new File( [ 'x' ], 'parts.xlsx' ) ] },
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'This file type cannot be sent. Genie reads photos (JPEG, PNG, WebP or HEIC), PDFs and parts lists (CSV or .xlsx).'
	);
	expect( screen.getByRole( 'button', { name: 'Send' } ) ).toBeDisabled();
} );

// The proxy's refusal (past the hourly allowance) is said as such, not as
// Genie failing to answer.
test( 'a refusal of the proxy names its reason', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockClear()
		.mockRejectedValue(
			new TurnError( 429, 'linker_genie_attachment_throttled' )
		);
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const fileInput = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	fireEvent.change( fileInput, {
		target: {
			files: [
				new File( [ '%PDF-1.7' ], 'ds.pdf', {
					type: 'application/pdf',
				} ),
			],
		},
	} );
	const send = screen.getByRole( 'button', { name: 'Send' } );
	await waitFor( () => expect( send ).toBeEnabled() );
	await act( async () => {
		fireEvent.click( send );
	} );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'You have reached the hourly limit for files. Please try again later; typed questions still work.'
	);
	expect(
		screen.queryByText( 'Genie did not answer. Please try again.' )
	).toBeNull();
	// Nothing was sent: the question is not in the thread.
	expect( screen.queryByText( 'Attached: ds.pdf' ) ).toBeNull();
} );

// A nameplate the service matched exactly: the card offers the product
// and what works with it; each sends a message naming the model, and
// "No, type the model" hands the field back to the customer.
test( 'a nameplate card confirms the device by a message naming it', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValueOnce( {
			meta: null,
			blocks: [
				{
					type: 'text',
					text: 'Your nameplate reads SAJ H2-10K-T3.',
					refs: [],
				},
			],
			attachments: [
				{
					id: 'att1',
					name: 'plate.jpg',
					kind: 'nameplate',
					brand: 'SAJ',
					model: 'H2-10K-T3',
					product_type: 'Hybrid inverter',
					match: 'exact',
					products: [ { product_id: 4107, label: 'H2-10K-T3' } ],
				},
			],
		} )
		.mockResolvedValue( {
			meta: null,
			blocks: [
				{ type: 'text', text: 'These batteries work.', refs: [] },
			],
		} );
	await renderOwned( <App config={ config() } /> );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { message: 'What is this?' },
			} )
		);
	} );
	expect(
		await screen.findByText(
			'In our range: SAJ H2-10K-T3. Is this your device?'
		)
	).toBeVisible();
	expect( screen.getByText( 'Hybrid inverter' ) ).toBeVisible();
	fireEvent.click(
		screen.getByRole( 'button', { name: 'No, type the model' } )
	);
	expect( screen.getByRole( 'textbox', { name: 'Ask Genie' } ) ).toHaveValue(
		'My device is the '
	);
	expect(
		screen.getByRole( 'textbox', { name: 'Ask Genie' } )
	).toHaveFocus();
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Yes, what works with it?' } )
		);
	} );
	const last = vi.mocked( sendTurn ).mock.calls.at( -1 );
	expect( last?.[ 0 ].messages.at( -1 ) ).toEqual( {
		role: 'user',
		content: "Yes, it's the SAJ H2-10K-T3. What works with it?",
	} );
} );

// A nameplate that could not be read: another photo, or the model typed.
test( 'an unreadable nameplate offers another photo or the model typed', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [ { role: 'user', content: 'Attached: plate.jpg' } ],
		turn: {
			meta: null,
			blocks: [
				{ type: 'text', text: 'I could not read it.', refs: [] },
			],
			attachments: [
				{
					id: 'att1',
					name: 'plate.jpg',
					kind: 'nameplate',
					match: 'unreadable',
					products: [],
				},
			],
		},
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect(
		await screen.findByText( 'The model could not be read.' )
	).toBeVisible();
	const picker = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	const click = vi.spyOn( picker, 'click' );
	fireEvent.click(
		screen.getByRole( 'button', { name: 'Choose another photo' } )
	);
	expect( click ).toHaveBeenCalled();
	expect(
		screen.getByRole( 'button', { name: 'Type the model' } )
	).toBeVisible();
} );

// The preview card's nameplate suggestion opens Genie with the photo picker
// on offer: a picker opens only on the visitor's own click.
test( 'opened for a nameplate photo, the dock offers the picker', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	await renderOwned( <App config={ config() } /> );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', { detail: { attach: true } } )
		);
	} );
	const choose = await screen.findByRole( 'button', {
		name: 'Choose a photo',
	} );
	const picker = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	const click = vi.spyOn( picker, 'click' );
	fireEvent.click( choose );
	expect( click ).toHaveBeenCalled();
} );

// The preview card's parts-list suggestion opens Genie with the file picker on
// offer, and the picker accepts a list file (#251).
test( 'opened for a parts list, the dock offers the file picker', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	await renderOwned( <App config={ config() } /> );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { attach: true, list: true },
			} )
		);
	} );
	const choose = await screen.findByRole( 'button', {
		name: 'Choose a file',
	} );
	expect(
		screen.getByText( /checks every line of a parts list/ )
	).toBeInTheDocument();
	const picker = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	expect( picker.accept ).toContain( 'text/csv' );
	expect( picker.accept ).toContain( '.xlsx' );
	const click = vi.spyOn( picker, 'click' );
	fireEvent.click( choose );
	expect( click ).toHaveBeenCalled();
} );

// A list file sent from the parts-list prompt says what it is: a photo of a
// handwritten list carries no name a service could read (#251).
test( 'a file sent from the list prompt says it is a parts list', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 0,
			failures: [],
			language: 'en',
		},
		blocks: [ { type: 'text', text: 'ok', refs: [] } ],
	} );
	await renderOwned( <App config={ config() } /> );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { attach: true, list: true },
			} )
		);
	} );
	const picker = document.querySelector(
		'input[type="file"]'
	) as HTMLInputElement;
	const file = new File( [ 'SAJ H2-10K-T3,2' ], 'parts.csv', {
		type: 'text/csv',
	} );
	await act( async () => {
		fireEvent.change( picker, { target: { files: [ file ] } } );
	} );
	await screen.findByText( 'parts.csv' );
	await waitFor( () =>
		expect( screen.getByRole( 'button', { name: 'Send' } ) ).toBeEnabled()
	);
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	const messages = vi.mocked( sendTurn ).mock.calls.at( -1 )?.[ 0 ].messages;
	expect( messages?.at( -1 )?.content ).toContain( 'Here is my parts list.' );
	expect( messages?.at( -1 )?.content ).toContain( 'Attached: parts.csv' );
} );

// A list file that could not be read offers the file picker again, not a
// photo picker (#251).
test( 'an unreadable list offers another file', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 0,
			failures: [],
			language: 'en',
		},
		blocks: [ { type: 'text', text: 'ok', refs: [] } ],
		attachments: [
			{
				id: 'att1',
				name: 'parts.csv',
				kind: 'list',
				failed: 'unreadable_list',
			},
		],
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Attached: parts.csv' },
		} );
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	expect(
		await screen.findByText( 'parts.csv could not be read.' )
	).toBeInTheDocument();
	expect(
		screen.getByRole( 'button', { name: 'Choose a file' } )
	).toBeInTheDocument();
	expect(
		screen.queryByRole( 'button', { name: 'Choose another photo' } )
	).not.toBeInTheDocument();
} );

// The dictation button is the browser's own speech recognition: it writes
// what it hears into the field and stops cleanly.
test( 'the dictation button writes what the browser hears', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
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
		await renderOwned( <App config={ config() } /> );
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
test( 'no speech recognition, no dictation button', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect( screen.queryByRole( 'button', { name: 'Dictate' } ) ).toBeNull();
} );

// The mobile sheet's backdrop: a tap off the card folds the dock away.
test( 'the dock mask folds the sheet', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	const states: boolean[] = [];
	const onState = ( event: Event ) => {
		states.push(
			( event as CustomEvent< { open: boolean } > ).detail.open
		);
	};
	window.addEventListener( 'linker-genie-state', onState );
	try {
		await renderOwned( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		// The backdrop remains a pointer target, outside the keyboard sequence.
		const mask = document.querySelector< HTMLButtonElement >(
			'.linker-genie-dock-mask'
		)!;
		expect( mask.tabIndex ).toBe( -1 );
		fireEvent.click( mask );
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
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	await renderOwned(
		<App config={ { ...config(), surface: 'workspace' } } />
	);
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
		await renderOwned(
			<App config={ { ...config(), surface: 'workspace' } } />
		);
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
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	await renderOwned( <App config={ config() } /> );
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
	await renderOwned( <App config={ config() } /> );
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

test( 'a new conversation clears the stored failure and its alert', async () => {
	resetTurnLane();
	seedOwnedFailure( {
		v: 1,
		kind: 'upstream',
		text: 'EV chargers',
		question: 'EV chargers',
		uploads: [],
		omitted: [],
	} );
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( selectConversation ).mockResolvedValue( {
		currentId: 10,
		ok: true,
		conversations: [],
	} );
	await renderOwned( <App config={ config() } /> );
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);

	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'New conversation' } )
		);
	} );

	await waitFor( () =>
		expect(
			screen.queryByText( 'Genie did not answer. Please try again.' )
		).toBeNull()
	);
	expect( currentOwnedRaw() ).toBeNull();
} );

test( 'deleting the conversation on screen clears the stored failure too', async () => {
	resetTurnLane();
	seedOwnedFailure( {
		v: 1,
		kind: 'upstream',
		text: 'EV chargers',
		question: 'EV chargers',
		uploads: [],
		omitted: [],
	} );
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 9,
		ok: true,
		conversations: [
			{ id: 9, title: 'Third question', updated: '2026-10-18 10:02:00' },
		],
	} );
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( deleteConversation ).mockResolvedValue( {
		currentId: 0,
		ok: true,
		conversations: [],
	} );
	await renderOwned( <App config={ config() } /> );
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie did not answer. Please try again.'
	);

	fireEvent.click( screen.getByRole( 'button', { name: 'Conversations' } ) );
	fireEvent.click(
		await screen.findByRole( 'button', {
			name: 'Delete conversation: Third question',
		} )
	);
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Delete' } ) );
	} );

	await waitFor( () =>
		expect(
			screen.queryByText( 'Genie did not answer. Please try again.' )
		).toBeNull()
	);
	expect( currentOwnedRaw() ).toBeNull();
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
	await renderOwned( <App config={ config() } /> );
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
			'A confirmation link is on its way to tester@example.test.'
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
	await renderOwned( <App config={ { ...config(), signedIn: true } } /> );
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
		contacts: [],
	} );
	vi.mocked( emailConversation ).mockResolvedValue( {
		outcome: 'throttled',
		to: '',
		limit: 3,
	} );
	await renderOwned( <App config={ { ...config(), signedIn: true } } /> );
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
		contacts: [],
	} );
	vi.mocked( emailConversation ).mockResolvedValue( {
		outcome: 'capped',
		to: '',
		limit: 3,
	} );
	await renderOwned( <App config={ { ...config(), signedIn: true } } /> );
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
		await renderOwned(
			<App config={ { ...config(), surface: 'workspace' } } />
		);
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
	// A fresh guest: no stored thread or history from the tests above.
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 0,
		conversations: [],
		ok: true,
	} );
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
	await renderOwned( <App config={ config() } /> );
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
	expect( sendTurn ).toHaveBeenLastCalledWith( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		onOperation: expect.any( Function ),
		restUrl: '/wp-json/',
		nonce: 'n',
		locale: 'en',
		messages: [
			{ role: 'user', content: 'Can I talk to a person?' },
			{
				role: 'assistant',
				content:
					'Someone from the Linker team can get in touch with you by email.',
				turnId: undefined,
			},
			{ role: 'user', content: 'Which battery fits the SAJ H2?' },
		],
		page: { type: 'category' },
		// No file was picked (#236): the turn carries none.
		uploads: [],
		verification: ownedVerification(),
		plannerNonce: undefined,
	} );
} );

const CONTACT_TURN = {
	meta: {
		turn_id: 31,
		grounded: true,
		fallback: false,
		attempts: 0,
		failures: [],
		language: 'en' as const,
	},
	blocks: [
		{
			type: 'text' as const,
			text: 'Someone from the Linker team can get in touch with you by email.',
			refs: [],
		},
		{ type: 'contact' as const, reason: 'asked' as const },
	],
};

// Review round 1 of #243: the sent card is the confirmation, so it stays in
// the conversation on the next turns, not only under the latest answer.
test( 'the sent contact card stays in the history on the next turn', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 0,
		conversations: [],
		ok: true,
	} );
	vi.mocked( sendContact ).mockResolvedValue( {
		ok: true,
		email: 'maria@example.test',
		receipt: true,
	} );
	vi.mocked( sendTurn ).mockResolvedValueOnce( CONTACT_TURN );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Can I talk to a person?' },
		} );
		fireEvent.submit(
			screen
				.getByLabelText( 'Ask Genie' )
				.closest( 'form' ) as HTMLFormElement
		);
	} );
	fireEvent.change( await screen.findByLabelText( 'Your email address' ), {
		target: { value: 'maria@example.test' },
	} );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Contact me' } ) );
	} );
	expect(
		await screen.findByText( 'Your request is with the Linker team' )
	).toBeInTheDocument();
	// From now on the route says this conversation's request is sent: a card
	// that mounts again while the next turn runs reports it once more.
	vi.mocked( readContact ).mockResolvedValue( {
		started: '100',
		startedNonce: 'sig',
		email: null,
		sent: { email: 'maria@example.test', receipt: true },
		mailbox: 'sales@de-linker.com',
	} );
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: { ...CONTACT_TURN.meta, turn_id: 32, attempts: 1 },
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
	expect(
		screen.getAllByText( 'Your request is with the Linker team' )
	).toHaveLength( 1 );
	expect( screen.queryByRole( 'button', { name: 'Contact me' } ) ).toBeNull();
} );

test( 'a reload shows the sent card in the history, once', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{ role: 'user', content: 'Can I talk to a person?' },
			{
				role: 'assistant',
				content:
					'Someone from the Linker team can get in touch with you by email.',
			},
		],
		turn: CONTACT_TURN,
		contacts: [ { after: 1, email: 'maria@example.test', receipt: false } ],
	} );
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 5,
		conversations: [],
		ok: true,
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect(
		await screen.findByText( 'Your request is with the Linker team' )
	).toBeInTheDocument();
	expect(
		screen.getAllByText( 'Your request is with the Linker team' )
	).toHaveLength( 1 );
	expect(
		screen.getByText(
			'The team replies to maria@example.test within one business day.'
		)
	).toBeInTheDocument();
	// The receipt cap held the receipt back, and the card says so.
	expect(
		screen.getByText( 'We have not sent a confirmation email.' )
	).toBeInTheDocument();
	expect( screen.queryByRole( 'button', { name: 'Contact me' } ) ).toBeNull();
} );

const INQUIRY_TURN = {
	meta: {
		turn_id: 41,
		grounded: true,
		fallback: false,
		attempts: 1,
		failures: [],
		language: 'en' as const,
	},
	blocks: [
		{
			type: 'text' as const,
			text: 'Check the details in the confirmation card and send the inquiry there.',
			refs: [],
		},
		{ type: 'action' as const, name: 'send_inquiry' as const, args: {} },
	],
};

const SENT_INQUIRY = {
	order: 9,
	number: '9',
	status: 'inquiry-received',
	receipt: true,
	email: 'maria@example.test',
	url: 'https://de-linker.test/checkout/order-received/9/?key=abc',
};

test( 'the inquiry card follows the answer and the sent card stays on the next turn', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
		inquiries: [],
	} );
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 0,
		conversations: [],
		ok: true,
	} );
	vi.mocked( sendTurn ).mockResolvedValueOnce( INQUIRY_TURN );
	vi.mocked( sendInquiry ).mockResolvedValue( {
		ok: true,
		inquiry: SENT_INQUIRY,
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Please send an inquiry.' },
		} );
		fireEvent.submit(
			screen
				.getByLabelText( 'Ask Genie' )
				.closest( 'form' ) as HTMLFormElement
		);
	} );
	fireEvent.change( await screen.findByLabelText( 'Name' ), {
		target: { value: 'Maria Weber' },
	} );
	fireEvent.change( screen.getByLabelText( 'Reply email' ), {
		target: { value: 'maria@example.test' },
	} );
	fireEvent.click(
		screen.getByLabelText(
			'I agree that my details may be used to respond to this message.'
		)
	);
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Send inquiry' } )
		);
	} );
	expect(
		await screen.findByText( 'Inquiry #9 · Inquiry received' )
	).toBeInTheDocument();
	expect(
		screen.queryByRole( 'button', { name: 'Send inquiry' } )
	).toBeNull();

	// From now on the route says this conversation's inquiry is sent: the
	// next turn keeps the sent card in the history.
	vi.mocked( readInquiry ).mockResolvedValue( {
		conversation: 5,
		started: '100',
		startedNonce: 'sig',
		account: null,
		lines: [],
		linesDigest: 'digest-2',
		message: '',
		summary: '',
		sent: SENT_INQUIRY,
		pageUrl: 'https://de-linker.test/inquiry/',
	} );
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: { ...INQUIRY_TURN.meta, turn_id: 42 },
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
	expect(
		screen.getAllByText( 'Inquiry #9 · Inquiry received' )
	).toHaveLength( 1 );
	expect(
		screen.queryByRole( 'button', { name: 'Send inquiry' } )
	).toBeNull();
} );

test( 'a reload shows the sent inquiry in the history, once', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [
			{ role: 'user', content: 'Please send an inquiry.' },
			{
				role: 'assistant',
				content:
					'Check the details in the confirmation card and send the inquiry there.',
			},
		],
		turn: INQUIRY_TURN,
		contacts: [],
		inquiries: [ { ...SENT_INQUIRY, after: 1 } ],
	} );
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 5,
		conversations: [],
		ok: true,
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	expect(
		await screen.findByText( 'Inquiry #9 · Inquiry received' )
	).toBeInTheDocument();
	expect(
		screen.getAllByText( 'Inquiry #9 · Inquiry received' )
	).toHaveLength( 1 );
	expect(
		screen.getByText( 'Your inquiry is with the Linker team' )
	).toBeInTheDocument();
	expect(
		screen.queryByRole( 'button', { name: 'Send inquiry' } )
	).toBeNull();
} );

test( 'an assistant reply renders its semantic Markdown instead of raw markers', async () => {
	resetTurnLane();
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: null,
		blocks: [
			{
				type: 'text',
				text: 'Choose the **hybrid inverter**.\n\n- Check phase\n- Check battery compatibility',
				refs: [],
			},
		],
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'I need a three-phase hybrid inverter for a home.',
			} )
		);
	} );
	expect( ( await screen.findByText( 'hybrid inverter' ) ).tagName ).toBe(
		'STRONG'
	);
	expect(
		screen.getByText( 'Check battery compatibility' ).closest( 'ul' )
	).not.toBeNull();
} );

test( 'a second submit while a turn is in flight does not send another', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	let finish!: ( value: Awaited< ReturnType< typeof sendTurn > > ) => void;
	vi.mocked( sendTurn )
		.mockClear()
		.mockImplementation(
			() =>
				new Promise( ( resolve ) => {
					finish = resolve;
				} )
		);
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'EV chargers' },
	} );
	const form = screen
		.getByRole( 'button', { name: 'Send' } )
		.closest( 'form' );
	if ( ! form ) {
		throw new Error( 'composer form missing' );
	}
	await act( async () => {
		fireEvent.submit( form );
	} );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Wallboxen' },
	} );
	fireEvent.submit( form );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	await act( async () =>
		finish( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} )
	);
} );

test( 'waiting for the unchanged turn request gives an accessible thinking status', async () => {
	let finish!: ( value: Awaited< ReturnType< typeof sendTurn > > ) => void;
	vi.mocked( sendTurn ).mockImplementation(
		() =>
			new Promise( ( resolve ) => {
				finish = resolve;
			} )
	);
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.click( screen.getByRole( 'button', { name: 'Ask Genie' } ) );
	await waitFor( () =>
		expect( screen.getByRole( 'status' ) ).toHaveTextContent(
			'Genie is thinking…'
		)
	);
	expect( screen.getByRole( 'button', { name: 'Send' } ) ).toBeDisabled();
	await act( async () =>
		finish( {
			meta: {
				grounded: true,
				fallback: false,
				attempts: 1,
				failures: [],
				language: 'en',
			},
			blocks: [ { type: 'text', text: 'A complete answer.', refs: [] } ],
		} )
	);
	expect( screen.queryByRole( 'status' ) ).toBeNull();
	expect( screen.getByText( 'A complete answer.' ) ).toBeInTheDocument();
} );

test( 'the saved solution handed over with the open rides every turn (#496)', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( {
		messages: [],
		turn: null,
		contacts: [],
	} );
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'Fixture answer.', refs: [] } ],
		} );
	await renderOwned( <App config={ config() } /> );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: {
					message: 'What does my saved solution say?',
					solution: 61,
				},
			} )
		);
	} );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalled() );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ][ 0 ].page ).toEqual( {
		type: 'category',
		solution_id: 61,
	} );
	// A later question in the same conversation carries it too.
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { message: 'And the yield?' },
			} )
		);
	} );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 2 ) );
	expect( vi.mocked( sendTurn ).mock.calls[ 1 ][ 0 ].page ).toEqual( {
		type: 'category',
		solution_id: 61,
	} );
} );

test( 'a delayed explicit refresh cannot overwrite a newer ask outside the shared turn lane', async () => {
	resetTurnLane();
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	await renderOwned( <App config={ config() } /> );
	await act( async () => undefined );
	let release!: ( value: Awaited< ReturnType< typeof readThread > > ) => void;
	vi.mocked( readThread ).mockImplementationOnce(
		() =>
			new Promise( ( resolve ) => {
				release = resolve;
			} )
	);
	vi.mocked( sendTurn )
		.mockClear()
		.mockResolvedValue( {
			meta: null,
			blocks: [ { type: 'text', text: 'The newer answer.', refs: [] } ],
		} );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { refresh: true },
			} )
		);
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { message: 'A newer question' },
			} )
		);
	} );
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () => {
		release( {
			messages: [ { role: 'user', content: 'An older question' } ],
			turn: null,
		} );
	} );
	expect( screen.getByText( 'The newer answer.' ) ).toBeVisible();
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'a resource refusal retains the question and file and offers native inquiry', async () => {
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.mocked( sendTurn ).mockRejectedValue(
		new TurnError( 429, 'linker_admission_quota' )
	);
	await renderOwned(
		<App config={ { ...config(), requestPageUrl: '/proforma-request/' } } />
	);
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Keep my inverter question' },
	} );
	fireEvent.change(
		document.querySelector( 'input[type="file"]' ) as HTMLInputElement,
		{
			target: {
				files: [
					new File( [ '%PDF-1.7' ], 'synthetic-datasheet.pdf', {
						type: 'application/pdf',
					} ),
				],
			},
		}
	);
	const send = screen.getByRole( 'button', { name: 'Send' } );
	await waitFor( () => expect( send ).toBeEnabled() );
	await act( async () => fireEvent.click( send ) );
	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie is temporarily unavailable.'
	);
	expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
		'Keep my inverter question'
	);
	expect( screen.getByText( 'synthetic-datasheet.pdf' ) ).toBeInTheDocument();
	expect(
		screen.getByRole( 'link', { name: 'Send an inquiry' } )
	).toHaveAttribute( 'href', '/proforma-request/' );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'the real Genie composer labels a pending proof as unsent and restores its question on verification failure', async () => {
	const actual =
		await vi.importActual< typeof import( './api/turn' ) >( './api/turn' );
	const { webcrypto } = await import( 'node:crypto' );
	vi.stubGlobal( 'crypto', webcrypto );
	window.linkerPublicProtectionConfig = {
		api: '/proof',
		nonce: 'n',
		mode: 'enforce',
		language: 'en',
	};
	let failProof: ( error: Error ) => void = () => undefined;
	const proof = vi.fn( async ( action: string, container: HTMLElement ) => {
		container.dispatchEvent(
			new CustomEvent( 'linker:protection', {
				detail: { action, state: 'retrying' },
			} )
		);
		return new Promise< string >( ( _resolve, reject ) => {
			failProof = ( error ) => {
				container.dispatchEvent(
					new CustomEvent( 'linker:protection', {
						detail: { action, state: 'failed' },
					} )
				);
				reject( error );
			};
		} );
	} );
	window.linkerPublicProtection = { proof, reset: vi.fn() };
	const transport = vi.fn< typeof fetch >();
	vi.mocked( sendTurn ).mockImplementationOnce( ( request ) =>
		actual.sendTurn( { ...request, fetcher: transport } )
	);
	try {
		await renderOwned( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'My question awaiting verification' },
		} );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
		);
		await waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
		expect(
			screen.getByText( 'My question awaiting verification' )
		).toBeVisible();
		expect(
			screen.getByText(
				'Verification is being retried. No request has been sent in this attempt.'
			)
		).toBeVisible();
		expect( transport ).not.toHaveBeenCalled();
		expect(
			screen.queryByText( 'Genie is thinking…' )
		).not.toBeInTheDocument();
		expect( screen.getByText( 'Checking verification…' ) ).toBeVisible();
		expect(
			document.querySelector( '.linker-genie-wait__lines' )
		).toBeNull();
		expect(
			screen
				.getByText( 'Checking verification…' )
				.closest( '.linker-genie-app__message--assistant' )
		).toBeNull();

		const slot = document.querySelector< HTMLElement >(
			'[data-linker-resource-verification-slot]'
		)!;
		const widget = document.querySelector(
			'[data-linker-resource-verification="genie"]'
		);
		expect( widget?.parentElement ).toBe( slot );

		await act( async () =>
			failProof( new Error( 'verification_widget_300030' ) )
		);
		await waitFor( () =>
			expect( screen.getByRole( 'alert' ) ).toHaveTextContent(
				'Verification could not be completed. No request has been sent in this attempt.'
			)
		);
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'My question awaiting verification'
		);
		expect(
			screen.queryByText( 'Genie did not answer. Please try again.' )
		).not.toBeInTheDocument();
		expect( transport ).not.toHaveBeenCalled();
		expect( slot.hidden ).toBe( true );
		expect( slot.children ).toHaveLength( 0 );
	} finally {
		delete window.linkerPublicProtection;
		delete window.linkerPublicProtectionConfig;
	}
} );

test( 'a cached proof immediately dispatches through the real adapter and changes the mounted composer to thinking', async () => {
	const actual =
		await vi.importActual< typeof import( './api/turn' ) >( './api/turn' );
	const { webcrypto } = await import( 'node:crypto' );
	vi.stubGlobal( 'crypto', webcrypto );
	window.linkerPublicProtectionConfig = {
		api: '/proof',
		nonce: 'n',
		mode: 'enforce',
		language: 'en',
	};
	const cached = Promise.resolve( 'already-verified-proof' );
	const proof = vi.fn( () => cached );
	window.linkerPublicProtection = { proof, reset: vi.fn() };
	let finish: ( response: Response ) => void = () => undefined;
	const transport = vi.fn< typeof fetch >(
		async () =>
			new Promise< Response >( ( resolve ) => {
				finish = resolve;
			} )
	);
	vi.mocked( sendTurn ).mockImplementationOnce( ( request ) =>
		actual.sendTurn( { ...request, fetcher: transport } )
	);
	try {
		await renderOwned( <App config={ config() } /> );
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'Cached proof dispatch' },
		} );
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
		await waitFor( () => expect( transport ).toHaveBeenCalledOnce() );
		expect( proof ).toHaveBeenCalledOnce();
		expect( screen.getByText( 'Genie is thinking…' ) ).toBeVisible();
		expect(
			document.querySelector( '.linker-genie-wait__lines' )
		).not.toBeNull();
		expect(
			screen.queryByText( 'Checking verification…' )
		).not.toBeInTheDocument();
		await act( async () =>
			finish(
				new Response(
					JSON.stringify( {
						stream: 'event: block\ndata: {"type":"text","text":"Cached answer","refs":[]}\n\nevent: done\ndata: {"ok":true}\n\n',
					} )
				)
			)
		);
		await screen.findByText( 'Cached answer' );
	} finally {
		delete window.linkerPublicProtection;
		delete window.linkerPublicProtectionConfig;
	}
} );

async function protectedComposer(
	proof: NonNullable< Window[ 'linkerPublicProtection' ] >[ 'proof' ],
	fetcher: typeof fetch,
	surface: 'helper' | 'workspace' = 'helper'
) {
	const actual =
		await vi.importActual< typeof import( './api/turn' ) >( './api/turn' );
	const { webcrypto } = await import( 'node:crypto' );
	vi.stubGlobal( 'crypto', webcrypto );
	window.linkerPublicProtectionConfig = {
		api: '/proof',
		nonce: 'n',
		mode: 'enforce',
		language: 'en',
	};
	const cancel = vi.fn( () => true );
	window.linkerPublicProtection = { proof, cancel, reset: vi.fn() };
	vi.mocked( sendTurn ).mockImplementation( ( request ) =>
		actual.sendTurn( { ...request, fetcher } )
	);
	await renderOwned( <App config={ { ...config(), surface } } /> );
	if ( surface === 'helper' ) {
		fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	}
	return { cancel };
}

test( 'closing verification restores the question on reopening without a failure banner, and its late proof cannot dispatch', async () => {
	let finishProof: ( value: string ) => void = () => undefined;
	const proof = vi.fn(
		async () =>
			new Promise< string >( ( resolve ) => {
				finishProof = resolve;
			} )
	);
	const transport = vi.fn< typeof fetch >(
		async () =>
			new Response(
				JSON.stringify( {
					stream: 'event: block\ndata: {"type":"text","text":"Answer after reopening","refs":[]}\n\nevent: done\ndata: {"ok":true}\n\n',
				} )
			)
	);
	const { cancel } = await protectedComposer( proof, transport );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Keep my question across close' },
	} );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	await waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
	await waitFor( () => expect( cancel ).toHaveBeenCalledOnce() );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await waitFor( () =>
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'Keep my question across close'
		)
	);
	// Closing withdrew the attempt before anything was sent, so reopening owes
	// the customer their question and no account of a failure that never was.
	expect( screen.queryByRole( 'alert' ) ).not.toBeInTheDocument();
	expect(
		screen.queryByText( 'Genie did not answer. Please try again.' )
	).not.toBeInTheDocument();
	expect(
		screen.queryByText( /Verification could not be completed/ )
	).not.toBeInTheDocument();
	await act( async () => finishProof( 'late-old-proof' ) );
	expect( transport ).not.toHaveBeenCalled();
	expect( screen.queryByRole( 'alert' ) ).not.toBeInTheDocument();
	proof.mockResolvedValueOnce( 'fresh-proof' );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	await screen.findByText( 'Answer after reopening' );
	expect( transport ).toHaveBeenCalledOnce();
} );

test.each( [ 400, 503, 'network' ] as const )(
	'a dispatched %s outcome clears its verification display without misreporting an unknown result as unsent',
	async ( outcome ) => {
		const transport = vi.fn< typeof fetch >( async () => {
			if ( outcome === 'network' ) {
				throw new TypeError( 'synthetic lost response' );
			}
			return new Response(
				JSON.stringify( { code: 'linker_admission_unavailable' } ),
				{ status: outcome }
			);
		} );
		await protectedComposer( async () => 'cached-proof', transport );
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: `Retain ${ outcome } question` },
		} );
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
		await waitFor( () => expect( transport ).toHaveBeenCalledOnce() );
		await screen.findByRole( 'alert' );
		const slot = document.querySelector< HTMLElement >(
			'[data-linker-resource-verification-slot]'
		)!;
		expect( slot.hidden ).toBe( true );
		expect( slot.textContent ).toBe( '' );
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			`Retain ${ outcome } question`
		);
		const expected =
			outcome === 'network'
				? 'Genie did not answer. Please try again.'
				: 'Genie is temporarily unavailable.';
		expect( screen.getByRole( 'alert' ) ).toHaveTextContent( expected );
		expect( screen.getByRole( 'alert' ) ).not.toHaveTextContent(
			'No request has been sent'
		);
	}
);

test( 'a history switch cancels the old verification owner before a late proof can dispatch', async () => {
	let finishProof: ( value: string ) => void = () => undefined;
	const proof = vi.fn(
		async () =>
			new Promise< string >( ( resolve ) => {
				finishProof = resolve;
			} )
	);
	const transport = vi.fn< typeof fetch >();
	let selected = false;
	const conversations = [
		{ id: 2, title: 'Other saved conversation', updated: '2026-10-28' },
	];
	vi.mocked( listConversations ).mockResolvedValue( {
		currentId: 1,
		conversations,
		ok: true,
	} );
	vi.mocked( selectConversation ).mockImplementation( async () => {
		selected = true;
		return { currentId: 2, conversations, ok: true };
	} );
	vi.mocked( readThread ).mockImplementation( async () =>
		selected
			? {
					messages: [
						{ role: 'user', content: 'Other saved question' },
					],
					turn: null,
				}
			: { messages: [], turn: null }
	);
	await protectedComposer( proof, transport, 'workspace' );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Previous owner question' },
	} );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	await waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	fireEvent.click(
		await screen.findByRole( 'button', {
			name: 'Other saved conversation',
		} )
	);
	await screen.findByText( 'Other saved question' );
	await act( async () => finishProof( 'late-previous-owner-proof' ) );
	expect( transport ).not.toHaveBeenCalled();
	expect( screen.getByLabelText( 'Ask Genie' ) ).not.toHaveValue(
		'Previous owner question'
	);
} );

test( 'a confirmed older source card stays with its earlier answer while a newer planning request is unverified', async () => {
	const project = 'a'.repeat( 32 ),
		oldRun = 'b'.repeat( 32 ),
		newRun = 'c'.repeat( 32 );
	const source: PlanningSourcesBlock = {
		type: 'planning_sources',
		schema_version: 1,
		status: 'available',
		binding: {
			planning_project_id: project,
			planning_revision: 4,
			planning_run_ids: [ oldRun ],
			runs: [
				{
					id: oldRun,
					revision: 4,
					manifest_sha256: 'd'.repeat( 64 ),
					result_sha256: 'e'.repeat( 64 ),
				},
			],
		},
		results: [ { revision: 4, groups: [] } ],
		url: `/solution-configurator/?project=${ project }&run=${ oldRun }#lp-calculations`,
	};
	vi.mocked( readThread ).mockResolvedValue( {
		conversationId: 12,
		messages: [
			{ role: 'user', content: 'Earlier project question' },
			{ role: 'assistant', content: 'Earlier confirmed response' },
		],
		turn: {
			meta: null,
			blocks: [
				{ type: 'text', text: 'Earlier confirmed response', refs: [] },
				source,
				{
					type: 'action',
					name: 'open_configurator',
					args: { url: source.url },
				},
			],
		},
	} );
	const proof = vi.fn( async () => new Promise< string >( () => {} ) );
	const transport = vi.fn< typeof fetch >();
	const { cancel } = await protectedComposer( proof, transport );
	await act( async () =>
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-planning-context', {
				detail: {
					page: {
						type: 'tool',
						title: 'Current selected project',
						planning_project_id: project,
						planning_revision: 5,
						planning_run_ids: [ newRun ],
					},
					plannerNonce: 'synthetic',
				},
			} )
		)
	);
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Explain the newly selected revision five' },
	} );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	await waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	try {
		const card = screen.getByRole( 'region', {
			name: 'Calculation sources and periods',
		} );
		expect(
			screen
				.getByRole( 'link', { name: 'Open the configurator' } )
				.closest( 'li' )
		).toBe( card.closest( 'li' ) );
		expect( card.closest( 'li' ) ).toHaveTextContent(
			'Earlier confirmed response'
		);
		expect(
			card.compareDocumentPosition(
				screen.getByText( 'Explain the newly selected revision five' )
			)
		).toBe( Node.DOCUMENT_POSITION_FOLLOWING );
		expect(
			screen.getByText(
				'This source card belongs to an earlier response, not the current request.'
			)
		).toBeVisible();
		expect( screen.getByText( 'Saved revision 4' ) ).toBeVisible();
		expect( transport ).not.toHaveBeenCalled();
	} finally {
		fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
		await waitFor( () => expect( cancel ).toHaveBeenCalledOnce() );
	}
} );

test( 'the visible cancel-verification action restores the draft without closing Genie or dispatching a late proof', async () => {
	let finish: ( value: string ) => void = () => undefined;
	const proof = vi.fn(
		async () =>
			new Promise< string >( ( resolve ) => {
				finish = resolve;
			} )
	);
	const transport = vi.fn< typeof fetch >();
	const { cancel } = await protectedComposer( proof, transport );
	fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
		target: { value: 'Keep the unsent verification draft' },
	} );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	await waitFor( () => expect( proof ).toHaveBeenCalledOnce() );
	fireEvent.click(
		screen.getByRole( 'button', { name: 'Cancel verification' } )
	);
	await waitFor( () =>
		expect( screen.getByLabelText( 'Ask Genie' ) ).toHaveValue(
			'Keep the unsent verification draft'
		)
	);
	expect( screen.queryByRole( 'alert' ) ).not.toBeInTheDocument();
	expect( screen.getByRole( 'button', { name: 'Send' } ) ).toBeEnabled();
	expect( cancel ).toHaveBeenCalledOnce();
	await act( async () => finish( 'synthetic-late-proof' ) );
	expect( transport ).not.toHaveBeenCalled();
} );
