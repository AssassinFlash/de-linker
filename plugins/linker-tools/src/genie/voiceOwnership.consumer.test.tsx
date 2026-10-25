// @vitest-environment jsdom
/** Actual dock/browser recognition keeps its accepted editor across native checks. */
import {
	act,
	cleanup,
	fireEvent,
	render,
	screen,
	waitFor,
} from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { App, resetTurnLane } from './App';
import { readConfig } from './config';
import { sendTurn, TurnError } from './api/turn';
import type { Dictation } from './shared/dictation';
import { FailureJournal, failureBucketKey } from './shared/ownedFailure';

vi.mock( './api/turn', async ( original ) => {
	const actual = await original< typeof import( './api/turn' ) >();
	return { ...actual, sendTurn: vi.fn() };
} );
const scopeA = 'a'.repeat( 64 );
const scopeB = 'b'.repeat( 64 );
const words = 'Newly accepted B voice project details';
let principal: 'A' | 'B';
let stop = () => {};
let onStart = () => {};
let sessions: NativeRecognition[];
class NativeRecognition implements Dictation {
	lang = '';
	onresult: Dictation[ 'onresult' ] = null;
	onend: Dictation[ 'onend' ] = null;
	onerror: Dictation[ 'onerror' ] = null;
	stop = vi.fn();
	constructor() {
		sessions.push( this );
	}
	start() {
		onStart();
	}
}
beforeEach( () => {
	sessionStorage.clear();
	for ( const key of [
		'__linkerGenieFailureJournal',
		'__linkerGenieNativeScope',
	] ) {
		delete ( window as unknown as Record< string, unknown > )[ key ];
	}
	resetTurnLane();
	principal = 'A';
	sessions = [];
	onStart = () => {};
	vi.mocked( sendTurn ).mockReset();
	vi.stubGlobal( 'SpeechRecognition', NativeRecognition );
	vi.stubGlobal(
		'fetch',
		vi.fn( async ( url ) => {
			if ( String( url ).includes( '/entry-context' ) ) {
				return {
					ok: true,
					json: async () => ( {
						scope: principal === 'A' ? scopeA : scopeB,
					} ),
				};
			}
			if ( String( url ).endsWith( '/conversations' ) ) {
				return {
					ok: true,
					json: async () => ( { conversations: [], current_id: 0 } ),
				};
			}
			if ( String( url ).endsWith( '/conversation' ) ) {
				return {
					ok: true,
					json: async () => ( { messages: [], stream: '' } ),
				};
			}
			throw new Error(
				`Unexpected actual consumer request: ${ String( url ) }`
			);
		} )
	);
} );
afterEach( async () => {
	await act( async () => stop() );
	stop = () => {};
	cleanup();
	document.body.innerHTML = '';
	sessionStorage.clear();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	resetTurnLane();
} );
const field = () =>
	screen.getByRole< HTMLTextAreaElement >( 'textbox', { name: 'Ask Genie' } );
async function mount() {
	const mountPoint = document.createElement( 'div' );
	mountPoint.dataset.restNonce = 'native-browser-voice-fixture';
	mountPoint.dataset.requestPageUrl = '/proforma-request/';
	const ui = render( <App config={ readConfig( mountPoint ) } /> );
	stop = ui.unmount;
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( field() ).not.toBeDisabled() );
}
async function hear( session: NativeRecognition, text = words ) {
	await act( async () =>
		session.onresult?.( { results: [ [ { transcript: text } ] ] } )
	);
}
async function checkpoint() {
	await act( async () => window.dispatchEvent( new Event( 'pagehide' ) ) );
}
function candidate( scope = scopeA ) {
	return new FailureJournal( sessionStorage, {
		scope,
		persistent: true,
	} ).candidate()?.record;
}
async function startVoice() {
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Dictate' } ) )
	);
	return sessions[ sessions.length - 1 ];
}

test( 'a native same-owner check before the first voice byte does not discard the accepted editor', async () => {
	await mount();
	const voice = await startVoice();
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await hear( voice );
	expect( field() ).toHaveValue( words );
	await checkpoint();
	expect( candidate() ).toMatchObject( {
		editing: true,
		text: words,
		question: words,
	} );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'B voice accepted before React commits remains owned after showStored revalidates its empty snapshot', async () => {
	vi.mocked( sendTurn ).mockRejectedValueOnce(
		new TurnError( 429, 'linker_admission_quota' )
	);
	await mount();
	fireEvent.input( field(), {
		target: { value: 'Original A resource-refused question' },
	} );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await screen.findByRole( 'link', { name: 'Send an inquiry' } );
	const original = vi.mocked( fetch ).getMockImplementation()!;
	let scheduled = false;
	let started = false;
	vi.mocked( fetch ).mockImplementation( async ( url, options ) => {
		if ( String( url ).includes( '/entry-context' ) && principal === 'B' ) {
			return {
				ok: true,
				json: async () => {
					if ( ! scheduled ) {
						scheduled = true;
						queueMicrotask( () =>
							queueMicrotask( () =>
								queueMicrotask( () => {
									screen
										.getByRole( 'button', {
											name: 'Dictate',
										} )
										.dispatchEvent(
											new MouseEvent( 'click', {
												bubbles: true,
												cancelable: true,
											} )
										);
								} )
							)
						);
					}
					return { scope: scopeB };
				},
			} as Response;
		}
		return original( url, options );
	} );
	onStart = () => {
		started = true;
	};
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( started ).toBe( true );
	expect( sessions ).toHaveLength( 1 );
	await hear( sessions[ 0 ] );
	expect( field() ).toHaveValue( words );
	await checkpoint();
	expect( candidate( scopeB ) ).toMatchObject( {
		editing: true,
		text: words,
	} );
	expect(
		sessionStorage.getItem( 'linker-genie-inquiry-handoff:v2:' + scopeB )
	).toBeNull();
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	await act( async () => stop() );
	stop = () => {};
	await mount();
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( field() ).toHaveValue( words );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'explicitly clearing voice text cancels that recognition, so a late result cannot recreate it', async () => {
	await mount();
	const voice = await startVoice();
	await hear( voice );
	fireEvent.input( field(), { target: { value: '' } } );
	await checkpoint();
	await hear( voice, 'Canceled voice must not return' );
	expect( field() ).toHaveValue( '' );
	expect( candidate() ).toBeUndefined();
	expect( voice.stop ).toHaveBeenCalledTimes( 1 );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'switching native owners stops A and cannot paint or persist its late voice into B', async () => {
	await mount();
	const oldVoice = await startVoice();
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await hear( oldVoice, 'Private A late dictation' );
	expect( field() ).toHaveValue( '' );
	expect( candidate( scopeB ) ).toBeUndefined();
	expect( oldVoice.stop ).toHaveBeenCalledTimes( 1 );
	const current = await startVoice();
	await hear( current );
	await checkpoint();
	expect( candidate( scopeB ) ).toMatchObject( {
		editing: true,
		text: words,
	} );
} );

test( 'Close stops recognition and reopening does not accept its late result', async () => {
	await mount();
	const voice = await startVoice();
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) )
	);
	await hear( voice );
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	expect( field() ).toHaveValue( '' );
	await checkpoint();
	expect( candidate() ).toBeUndefined();
	expect( voice.stop ).toHaveBeenCalledTimes( 1 );
} );

test( 'an old same-owner onEnd cannot release the stop handle of a newer recognition', async () => {
	await mount();
	const oldVoice = await startVoice();
	await act( async () => oldVoice.onend?.() );
	const current = await startVoice();
	await act( async () => oldVoice.onend?.() );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Stop dictation' } )
		)
	);
	expect( sessions ).toHaveLength( 2 );
	expect( current.stop ).toHaveBeenCalledTimes( 1 );
} );

test( 'New conversation invalidates an active voice before it can write into the new thread', async () => {
	await mount();
	const voice = await startVoice();
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'New conversation' } )
		)
	);
	await hear( voice );
	expect( field() ).toHaveValue( '' );
	await checkpoint();
	expect( candidate() ).toBeUndefined();
	expect( voice.stop ).toHaveBeenCalledTimes( 1 );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

/** Hold only the next actual native context read; later requests keep their real fixture. */
async function pendingCheck() {
	const original = vi.mocked( fetch ).getMockImplementation()!;
	let held = false;
	let release!: () => void;
	vi.mocked( fetch ).mockImplementation( async ( url, options ) => {
		if ( String( url ).includes( '/entry-context' ) && ! held ) {
			held = true;
			return {
				ok: true,
				json: () =>
					new Promise( ( resolve ) => {
						release = () =>
							resolve( {
								scope: principal === 'A' ? scopeA : scopeB,
							} );
					} ),
			} as Response;
		}
		return original( url, options );
	} );
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await waitFor( () => expect( field() ).toBeDisabled() );
	expect( held ).toBe( true );
	return async () => act( async () => release() );
}
for ( const ended of [ false, true ] ) {
	test( `an accepted transcript waits for native same-owner verification${ ended ? ' even if recognition naturally ends first' : '' }`, async () => {
		await mount();
		const voice = await startVoice();
		const release = await pendingCheck();
		expect( voice.stop ).not.toHaveBeenCalled();
		await hear( voice, 'First pending phrase' );
		await hear( voice, 'Second pending phrase' );
		await act( async () => {
			if ( ended ) {
				voice.onend?.();
			}
		} );
		expect( field() ).toHaveValue( '' );
		await release();
		await waitFor( () => expect( field() ).not.toBeDisabled() );
		expect( field() ).toHaveValue(
			'First pending phrase Second pending phrase'
		);
		await checkpoint();
		expect( candidate() ).toMatchObject( {
			editing: true,
			text: 'First pending phrase Second pending phrase',
		} );
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}
for ( const action of [
	'Stop dictation',
	'Close',
	'New conversation',
	'different native owner',
] ) {
	test( `${ action } cancels queued voice bytes before native verification returns`, async () => {
		await mount();
		const voice = await startVoice();
		const release = await pendingCheck();
		await hear( voice, 'Canceled private pending phrase' );
		await act( async () => {
			if ( action === 'different native owner' ) {
				principal = 'B';
			} else {
				fireEvent.click(
					screen.getByRole( 'button', { name: action } )
				);
			}
		} );
		await release();
		await act( async () =>
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
		);
		await waitFor( () => expect( field() ).not.toBeDisabled() );
		expect( field() ).toHaveValue( '' );
		await checkpoint();
		expect(
			candidate( principal === 'B' ? scopeB : scopeA )
		).toBeUndefined();
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}

for ( const ended of [ false, true ] ) {
	test( `pending accepted voice survives pagehide and a fresh A remount${ ended ? ' after natural recognition end' : '' } without an automatic turn`, async () => {
		await mount();
		const voice = await startVoice();
		const release = await pendingCheck();
		await hear( voice, words );
		if ( ended ) {
			await act( async () => voice.onend?.() );
		}
		expect( field() ).toHaveValue( '' );
		await checkpoint();
		await act( async () => stop() );
		stop = () => {};
		await release();
		await mount();
		await act( async () =>
			fireEvent.click(
				await screen.findByRole( 'button', {
					name: 'Restore unsent draft',
				} )
			)
		);
		expect( field() ).toHaveValue( words );
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}

test( 'pending heard A words remain quarantined in B and are explicitly restorable only after fresh A', async () => {
	await mount();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, words );
	principal = 'B';
	await release();
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	expect( field() ).toHaveValue( '' );
	expect( screen.queryByText( words ) ).not.toBeInTheDocument();
	expect( candidate( scopeB ) ).toBeUndefined();
	await act( async () => stop() );
	stop = () => {};
	principal = 'A';
	await mount();
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( field() ).toHaveValue( words );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'A1 success consumes only A1 after A2 pending voice synchronously checkpoints', async () => {
	let answer!: ( value: Awaited< ReturnType< typeof sendTurn > > ) => void;
	vi.mocked( sendTurn ).mockImplementationOnce(
		() =>
			new Promise( ( resolve ) => {
				answer = resolve;
			} )
	);
	await mount();
	fireEvent.input( field(), { target: { value: 'A1 original question' } } );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, words );
	await act( async () =>
		answer( {
			meta: null,
			blocks: [ { type: 'text', text: 'A1 answered', refs: [] } ],
		} )
	);
	await release();
	await screen.findByText( 'A1 answered' );
	await checkpoint();
	const raw = sessionStorage.getItem( failureBucketKey( scopeA ) );
	const records = JSON.parse( raw! ).records;
	expect( Object.values( records ) ).toHaveLength( 1 );
	expect( candidate() ).toMatchObject( { editing: true, text: words } );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

async function attachPdf() {
	fireEvent.change(
		document.querySelector< HTMLInputElement >( 'input[type="file"]' )!,
		{
			target: {
				files: [
					new File(
						[ '%PDF-1.4\naccepted fixture\n%%EOF' ],
						'voice-project.pdf',
						{ type: 'application/pdf' }
					),
				],
			},
		}
	);
	await screen.findByText( 'voice-project.pdf' );
	await waitFor( () =>
		expect(
			screen.queryByText( 'Preparing file…' )
		).not.toBeInTheDocument()
	);
	await waitFor( () =>
		expect(
			screen.getByRole( 'button', { name: 'Send' } )
		).not.toBeDisabled()
	);
}

test( 'pagehide retains prepared PDF and displayed text together with pending voice under the original attempt', async () => {
	await mount();
	fireEvent.input( field(), { target: { value: 'Displayed project text' } } );
	await attachPdf();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Pending site requirement' );
	await checkpoint();
	await act( async () => stop() );
	stop = () => {};
	await release();
	await mount();
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( field().value ).toContain( 'Displayed project text' );
	expect( field().value ).toContain( 'Pending site requirement' );
	await screen.findByText( 'voice-project.pdf' );
	expect( candidate()?.uploads ).toHaveLength( 1 );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'explicit Stop removes only undisplayed voice and preserves displayed text plus the prepared PDF', async () => {
	await mount();
	fireEvent.input( field(), {
		target: { value: 'Keep displayed project text' },
	} );
	await attachPdf();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Remove queued phrase' );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Stop dictation' } )
		)
	);
	await release();
	await checkpoint();
	expect( field() ).toHaveValue( 'Keep displayed project text' );
	expect( candidate() ).toMatchObject( {
		text: 'Keep displayed project text',
	} );
	expect( candidate()?.uploads ).toHaveLength( 1 );
	expect( JSON.stringify( candidate() ) ).not.toContain(
		'Remove queued phrase'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'Stop cannot overwrite a later revision of the same attempt', async () => {
	await mount();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Original queued phrase' );
	const journal = new FailureJournal( sessionStorage, {
		scope: scopeA,
		persistent: true,
	} );
	const current = journal.candidate()!;
	expect( current ).toBeTruthy();
	const later = journal.save(
		{
			phase: 'editing',
			kind: null,
			draft: {
				...current.record,
				text: 'Later accepted revision',
				question: 'Later accepted revision',
			},
		},
		current.cursor
	);
	expect( later.conflict ).toBe( false );
	const raw = sessionStorage.getItem( failureBucketKey( scopeA ) );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Stop dictation' } )
		)
	);
	expect( sessionStorage.getItem( failureBucketKey( scopeA ) ) ).toBe( raw );
	await release();
	await checkpoint();
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	expect( sessionStorage.getItem( failureBucketKey( scopeA ) ) ).toBe( raw );
	expect( candidate()?.text ).toBe( 'Later accepted revision' );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'explicit Stop preserves an existing reselection name without keeping the undisplayed phrase', async () => {
	new FailureJournal( sessionStorage, {
		scope: scopeA,
		persistent: true,
	} ).begin( {
		phase: 'editing',
		kind: null,
		draft: {
			editing: true,
			text: '',
			question: 'missing-schematic.pdf',
			uploads: [],
			omitted: [ 'missing-schematic.pdf' ],
		},
	} );
	await mount();
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	await screen.findByText(
		'Select missing-schematic.pdf again before sending.'
	);
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Undisplayed phrase' );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Stop dictation' } )
		)
	);
	await release();
	expect( candidate() ).toMatchObject( {
		editing: true,
		text: '',
		question: 'missing-schematic.pdf',
		omitted: [ 'missing-schematic.pdf' ],
	} );
	expect( JSON.stringify( candidate() ) ).not.toContain(
		'Undisplayed phrase'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'a pending voice storage failure retains only original A memory ownership and shows the existing warning after explicit restore', async () => {
	await mount();
	const voice = await startVoice();
	const release = await pendingCheck();
	const original = Storage.prototype.setItem;
	const unavailable = vi
		.spyOn( Storage.prototype, 'setItem' )
		.mockImplementation( function ( this: Storage, key, value ) {
			if ( key === failureBucketKey( scopeA ) ) {
				throw new DOMException( 'Fixture quota', 'QuotaExceededError' );
			}
			return original.call( this, key, value );
		} );
	await hear( voice, words );
	await act( async () => stop() );
	stop = () => {};
	unavailable.mockRestore();
	principal = 'B';
	await release();
	await mount();
	expect( field() ).toHaveValue( '' );
	expect( screen.queryByText( words ) ).not.toBeInTheDocument();
	expect( candidate( scopeB ) ).toBeUndefined();
	await act( async () => stop() );
	stop = () => {};
	principal = 'A';
	await mount();
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( field() ).toHaveValue( words );
	await screen.findByText(
		'This question could not be saved. It may be lost if you refresh or leave this page.'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'a second pending phrase cannot overwrite a later accepted revision or its reselection names, including after verification and pagehide', async () => {
	await mount();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Original queued phrase' );
	const journal = new FailureJournal( sessionStorage, {
		scope: scopeA,
		persistent: true,
	} );
	const current = journal.candidate()!;
	expect( current ).toBeTruthy();
	const later = journal.save(
		{
			phase: 'editing',
			kind: null,
			draft: {
				...current.record,
				text: 'Later accepted revision',
				question: 'Later accepted revision',
				omitted: [ 'later-schematic.pdf' ],
			},
		},
		current.cursor
	);
	expect( later.conflict ).toBe( false );
	const raw = sessionStorage.getItem( failureBucketKey( scopeA ) );
	await hear( voice, 'Second queued phrase' );
	expect( sessionStorage.getItem( failureBucketKey( scopeA ) ) ).toBe( raw );
	await release();
	await checkpoint();
	expect( sessionStorage.getItem( failureBucketKey( scopeA ) ) ).toBe( raw );
	expect( candidate() ).toMatchObject( {
		text: 'Later accepted revision',
		omitted: [ 'later-schematic.pdf' ],
	} );
	expect( field() ).toHaveValue( '' );
	expect( voice.stop ).toHaveBeenCalledTimes( 1 );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'pending voice continues across a different retained attempt without replacing that other draft', async () => {
	await mount();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Original queued phrase' );
	const journal = new FailureJournal( sessionStorage, {
		scope: scopeA,
		persistent: true,
	} );
	const own = journal.candidate()!;
	const other = journal.begin( {
		phase: 'editing',
		kind: null,
		draft: {
			editing: true,
			text: 'Other accepted draft',
			question: 'Other accepted draft',
			uploads: [],
			omitted: [ 'other-schematic.pdf' ],
		},
	} );
	expect( other.conflict ).toBe( false );
	expect( other.cursor.owner.attempt ).not.toBe( own.cursor.owner.attempt );
	const otherRecord = JSON.parse(
		sessionStorage.getItem( failureBucketKey( scopeA ) )!
	).records[ other.cursor.owner.attempt ];
	await hear( voice, 'Second accepted phrase' );
	await release();
	expect( field() ).toHaveValue(
		'Original queued phrase Second accepted phrase'
	);
	const records = JSON.parse(
		sessionStorage.getItem( failureBucketKey( scopeA ) )!
	).records;
	expect( records[ own.cursor.owner.attempt ].record.text ).toBe(
		'Original queued phrase Second accepted phrase'
	);
	expect( records[ other.cursor.owner.attempt ] ).toEqual( otherRecord );
	expect( voice.stop ).not.toHaveBeenCalled();
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'pending voice continues when an earlier distinct attempt is successfully consumed', async () => {
	await mount();
	const journal = new FailureJournal( sessionStorage, {
		scope: scopeA,
		persistent: true,
	} );
	const other = journal.begin( {
		phase: 'failed',
		kind: 'upstream',
		draft: {
			text: 'Earlier independent question',
			question: 'Earlier independent question',
			uploads: [],
			omitted: [],
		},
	} );
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Original queued phrase' );
	const own = journal.candidate()!;
	const earlier = journal.rebase( other.cursor )!;
	expect( journal.consume( earlier.cursor ) ).toBe( true );
	await hear( voice, 'Second accepted phrase' );
	await release();
	expect( field() ).toHaveValue(
		'Original queued phrase Second accepted phrase'
	);
	const records = JSON.parse(
		sessionStorage.getItem( failureBucketKey( scopeA ) )!
	).records;
	expect( Object.keys( records ) ).toEqual( [ own.cursor.owner.attempt ] );
	expect( records[ own.cursor.owner.attempt ].record.text ).toBe(
		'Original queued phrase Second accepted phrase'
	);
	expect( voice.stop ).not.toHaveBeenCalled();
	expect( sendTurn ).not.toHaveBeenCalled();
} );

for ( const prefix of [ false, true ] ) {
	test( `Stop after another attempt changes the bucket cancels only queued words${ prefix ? ' and retains displayed text and PDF' : '' }`, async () => {
		await mount();
		if ( prefix ) {
			fireEvent.input( field(), {
				target: { value: 'Keep accepted prefix' },
			} );
			await attachPdf();
		}
		const voice = await startVoice();
		const release = await pendingCheck();
		await hear( voice, 'Cancel pending words' );
		const journal = new FailureJournal( sessionStorage, {
			scope: scopeA,
			persistent: true,
		} );
		const own = journal.candidate()!;
		const other = journal.begin( {
			phase: 'editing',
			kind: null,
			draft: {
				editing: true,
				text: 'Other accepted draft',
				question: 'Other accepted draft',
				uploads: [],
				omitted: [ 'other-schematic.pdf' ],
			},
		} );
		const otherRecord = JSON.parse(
			sessionStorage.getItem( failureBucketKey( scopeA ) )!
		).records[ other.cursor.owner.attempt ];
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Stop dictation' } )
			)
		);
		await release();
		const records = JSON.parse(
			sessionStorage.getItem( failureBucketKey( scopeA ) )!
		).records;
		expect( records[ other.cursor.owner.attempt ] ).toEqual( otherRecord );
		const expectedPrefix = expect.objectContaining( {
			text: 'Keep accepted prefix',
			uploads: [
				expect.objectContaining( { name: 'voice-project.pdf' } ),
			],
		} );
		expect( records[ own.cursor.owner.attempt ]?.record ).toEqual(
			prefix ? expectedPrefix : undefined
		);
		expect( JSON.stringify( records ) ).not.toContain(
			'Cancel pending words'
		);
		expect( field() ).toHaveValue( prefix ? 'Keep accepted prefix' : '' );
		expect( voice.stop ).toHaveBeenCalledTimes( 1 );
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}

test( 'a target whose bytes changed without a revision bump is not a safe independent-attempt rebase', async () => {
	await mount();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'Original queued phrase' );
	const raw = sessionStorage.getItem( failureBucketKey( scopeA ) )!;
	const bucket = JSON.parse( raw );
	const attempt = Object.keys( bucket.records )[ 0 ];
	bucket.records[ attempt ].record.text = 'Externally changed bytes';
	bucket.records[ attempt ].record.question = 'Externally changed bytes';
	const changed = JSON.stringify( bucket );
	sessionStorage.setItem( failureBucketKey( scopeA ), changed );
	await hear( voice, 'A later stale phrase' );
	await release();
	await checkpoint();
	expect( sessionStorage.getItem( failureBucketKey( scopeA ) ) ).toBe(
		changed
	);
	expect( field() ).toHaveValue( '' );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'a temporarily unreadable checkpoint retains the next heard phrase under original A memory ownership', async () => {
	await mount();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'First accepted phrase' );
	const original = Storage.prototype.getItem;
	const unavailable = vi
		.spyOn( Storage.prototype, 'getItem' )
		.mockImplementation( function ( this: Storage, key ) {
			if ( key === failureBucketKey( scopeA ) ) {
				throw new DOMException(
					'Fixture transient read failure',
					'SecurityError'
				);
			}
			return original.call( this, key );
		} );
	await hear( voice, 'Second accepted phrase' );
	unavailable.mockRestore();
	await release();
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
	await checkpoint();
	expect( candidate() ).toMatchObject( {
		editing: true,
		text: 'First accepted phrase Second accepted phrase',
	} );
	expect( candidate( scopeB ) ).toBeUndefined();
	await screen.findByText(
		'This question could not be saved. It may be lost if you refresh or leave this page.'
	);
	expect( voice.stop ).not.toHaveBeenCalled();
	await act( async () => stop() );
	stop = () => {};
	principal = 'B';
	await mount();
	expect( field() ).toHaveValue( '' );
	expect(
		screen.queryByText( 'First accepted phrase Second accepted phrase' )
	).not.toBeInTheDocument();
	await act( async () => stop() );
	stop = () => {};
	principal = 'A';
	await mount();
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

async function divergentVoiceCopies() {
	await mount();
	await attachPdf();
	const voice = await startVoice();
	const release = await pendingCheck();
	await hear( voice, 'First accepted phrase' );
	const journal = new FailureJournal( sessionStorage, {
		scope: scopeA,
		persistent: true,
	} );
	const first = journal.candidate()!;
	const original = Storage.prototype.getItem;
	let fail = true;
	let laterRaw: string | null = null;
	const unavailable = vi
		.spyOn( Storage.prototype, 'getItem' )
		.mockImplementation( function ( this: Storage, key ) {
			if ( key === failureBucketKey( scopeA ) && fail ) {
				fail = false;
				// Another accepted native callback settles before this read fails.
				const later = journal.save(
					{
						phase: 'editing',
						kind: null,
						draft: {
							...first.record,
							text: 'Later durable project revision',
							question: 'Later durable project revision',
							omitted: [ 'later-schematic.pdf' ],
						},
					},
					first.cursor
				);
				expect( later.conflict ).toBe( false );
				laterRaw = original.call( this, key );
				throw new DOMException(
					'Fixture transient read failure',
					'SecurityError'
				);
			}
			return original.call( this, key );
		} );
	await hear( voice, 'Second accepted phrase' );
	unavailable.mockRestore();
	await release();
	return { journal, laterRaw, voice };
}

test( 'a newer durable revision remains intact and reachable beside the unsaved voice copy after a read failure', async () => {
	const { journal, laterRaw } = await divergentVoiceCopies();
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
	expect( sessionStorage.getItem( failureBucketKey( scopeA ) ) ).toBe(
		laterRaw
	);
	await screen.findByText(
		'This question could not be saved. It may be lost if you refresh or leave this page.'
	);
	const retained = journal.candidate()!;
	expect( journal.consume( retained.cursor ) ).toBe( false );
	expect( sessionStorage.getItem( failureBucketKey( scopeA ) ) ).toBe(
		laterRaw
	);
	await screen.findByText( 'Later durable project revision' );
	await screen.findByText( 'later-schematic.pdf' );
	principal = 'B';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	expect( field() ).toHaveValue( '' );
	expect(
		screen.queryByText( 'Later durable project revision' )
	).not.toBeInTheDocument();
	expect(
		screen.queryByText( 'later-schematic.pdf' )
	).not.toBeInTheDocument();
	expect(
		screen.queryByText( 'First accepted phrase Second accepted phrase' )
	).not.toBeInTheDocument();
	expect( candidate( scopeB ) ).toBeUndefined();
	principal = 'A';
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	await restoreOwned();
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
	await screen.findByText( 'Later durable project revision' );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

async function restoreOwned() {
	await act( async () =>
		fireEvent.click(
			await screen.findByRole( 'button', {
				name: 'Restore unsent draft',
			} )
		)
	);
}
async function unmountCurrent() {
	await act( async () => stop() );
	stop = () => {};
}

test( 'both existing variants restore with their files and missing names, then memory success leaves durable reachable', async () => {
	const { voice } = await divergentVoiceCopies();
	await screen.findByText( 'Later durable project revision' );
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	await hear(
		voice,
		'Old recognition must not select its original memory version'
	);
	expect( field() ).toHaveValue( 'Later durable project revision' );
	await screen.findByText(
		'Select later-schematic.pdf again before sending.'
	);
	await screen.findByText( 'First accepted phrase Second accepted phrase' );
	await restoreOwned();
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
	await screen.findByText( 'Later durable project revision' );
	await screen.findByText( 'later-schematic.pdf' );
	expect(
		screen.getByRole( 'button', {
			name: 'Remove attachment voice-project.pdf',
		} )
	).toBeInTheDocument();
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: null,
		blocks: [
			{
				type: 'text',
				text: 'Selected memory version answered',
				refs: [],
			},
		],
	} );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await screen.findByText( 'Selected memory version answered' );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	await unmountCurrent();
	await mount();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	await screen.findByText(
		'Select later-schematic.pdf again before sending.'
	);
	expect(
		screen.getByRole( 'button', {
			name: 'Remove attachment voice-project.pdf',
		} )
	).toBeInTheDocument();
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'selected durable success preserves the unsaved memory version for fresh A and exposes neither to B', async () => {
	await divergentVoiceCopies();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Remove' } ) )
	);
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: null,
		blocks: [
			{
				type: 'text',
				text: 'Selected durable version answered',
				refs: [],
			},
		],
	} );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await screen.findByText( 'Selected durable version answered' );
	await unmountCurrent();
	principal = 'B';
	await mount();
	expect( field() ).toHaveValue( '' );
	expect(
		screen.queryByText( 'First accepted phrase Second accepted phrase' )
	).not.toBeInTheDocument();
	expect(
		screen.queryByText( 'Later durable project revision' )
	).not.toBeInTheDocument();
	expect( candidate( scopeB ) ).toBeUndefined();
	await unmountCurrent();
	principal = 'A';
	await mount();
	await restoreOwned();
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
	expect(
		screen.getByRole( 'button', {
			name: 'Remove attachment voice-project.pdf',
		} )
	).toBeInTheDocument();
	await screen.findByText(
		'This question could not be saved. It may be lost if you refresh or leave this page.'
	);
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'clearing the selected memory text and file consumes only it, leaving the newer durable selection restorable', async () => {
	await divergentVoiceCopies();
	fireEvent.input( field(), { target: { value: '' } } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'Remove attachment voice-project.pdf',
			} )
		)
	);
	await checkpoint();
	await unmountCurrent();
	await mount();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	await screen.findByText(
		'Select later-schematic.pdf again before sending.'
	);
	expect(
		screen.getByRole( 'button', {
			name: 'Remove attachment voice-project.pdf',
		} )
	).toBeInTheDocument();
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'clearing selected durable text, missing name and file leaves the unsaved memory version restorable', async () => {
	await divergentVoiceCopies();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Remove' } ) )
	);
	fireEvent.input( field(), { target: { value: '' } } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'Remove attachment voice-project.pdf',
			} )
		)
	);
	await checkpoint();
	await unmountCurrent();
	await mount();
	await restoreOwned();
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
	expect(
		screen.getByRole( 'button', {
			name: 'Remove attachment voice-project.pdf',
		} )
	).toBeInTheDocument();
	await screen.findByText(
		'This question could not be saved. It may be lost if you refresh or leave this page.'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'Restore cannot replace a newer memory revision with the stale mounted editor', async () => {
	const { journal } = await divergentVoiceCopies();
	const old = journal.candidate()!;
	const newer = journal.save(
		{
			phase: 'editing',
			kind: null,
			draft: {
				...old.record,
				text: 'Newer accepted memory revision',
				question: 'Newer accepted memory revision',
				omitted: [ 'newer-memory-schematic.pdf' ],
			},
		},
		old.cursor
	);
	expect( newer.conflict ).toBe( false );
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	const other = journal.alternative( journal.candidate()!.cursor );
	expect( other?.record.text ).toBe( 'Newer accepted memory revision' );
	expect( other?.record.omitted ).toEqual( [ 'newer-memory-schematic.pdf' ] );
	await restoreOwned();
	expect( field() ).toHaveValue( 'Newer accepted memory revision' );
	await screen.findByText(
		'Select newer-memory-schematic.pdf again before sending.'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'quota fallback from a restored durable editor retains the other actual memory copy', async () => {
	const { journal } = await divergentVoiceCopies();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	const original = Storage.prototype.setItem;
	const unavailable = vi
		.spyOn( Storage.prototype, 'setItem' )
		.mockImplementation( function ( this: Storage, key, value ) {
			if ( key === failureBucketKey( scopeA ) ) {
				throw new DOMException(
					'Fixture write unavailable',
					'QuotaExceededError'
				);
			}
			return original.call( this, key, value );
		} );
	fireEvent.input( field(), {
		target: { value: 'Selected durable edited during outage' },
	} );
	await checkpoint();
	unavailable.mockRestore();
	const active = journal.candidate()!;
	const other = journal.alternative( active.cursor );
	expect( [ active.record.text, other?.record.text ] ).toContain(
		'First accepted phrase Second accepted phrase'
	);
	expect( [ active.record.text, other?.record.text ] ).toContain(
		'Selected durable edited during outage'
	);
	const seen = new Set< string >();
	for ( let i = 0; i < 4; i++ ) {
		seen.add( field().value );
		await restoreOwned();
		expect(
			screen.getByRole( 'button', {
				name: 'Remove attachment voice-project.pdf',
			} )
		).toBeInTheDocument();
	}
	expect( [ ...seen ] ).toEqual(
		expect.arrayContaining( [
			'First accepted phrase Second accepted phrase',
			'Selected durable edited during outage',
			'Later durable project revision',
		] )
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'stale empty editor cannot consume a newer memory revision on pagehide', async () => {
	const { journal } = await divergentVoiceCopies();
	const old = journal.candidate()!;
	const newer = journal.save(
		{
			phase: 'editing',
			kind: null,
			draft: {
				...old.record,
				text: 'Newer accepted memory revision',
				question: 'Newer accepted memory revision',
				omitted: [ 'newer-memory-schematic.pdf' ],
			},
		},
		old.cursor
	);
	expect( newer.conflict ).toBe( false );
	fireEvent.input( field(), { target: { value: '' } } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'Remove attachment voice-project.pdf',
			} )
		)
	);
	await checkpoint();
	const active = journal.candidate();
	const other = active ? journal.alternative( active.cursor ) : null;
	expect(
		[ active?.record, other?.record ].some(
			( x ) =>
				x?.text === 'Newer accepted memory revision' &&
				x.omitted.includes( 'newer-memory-schematic.pdf' )
		)
	).toBe( true );
	await unmountCurrent();
	await mount();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Newer accepted memory revision' );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'an additionally edited stale UI and the newer memory revision both remain explicitly restorable', async () => {
	const { journal } = await divergentVoiceCopies();
	const old = journal.candidate()!;
	expect(
		journal.save(
			{
				phase: 'editing',
				kind: null,
				draft: {
					...old.record,
					text: 'Newer accepted memory revision',
					question: 'Newer accepted memory revision',
					omitted: [ 'newer-memory-schematic.pdf' ],
				},
			},
			old.cursor
		).conflict
	).toBe( false );
	fireEvent.input( field(), {
		target: { value: 'Additional accepted UI words' },
	} );
	await restoreOwned();
	expect( field() ).toHaveValue( 'Later durable project revision' );
	const seen = new Set< string >();
	for ( let i = 0; i < 4; i++ ) {
		seen.add( field().value );
		await restoreOwned();
	}
	expect( [ ...seen ] ).toEqual(
		expect.arrayContaining( [
			'Later durable project revision',
			'Newer accepted memory revision',
			'Additional accepted UI words',
		] )
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'sending a stale unchanged editor cannot promote the newly read memory revision', async () => {
	const { journal } = await divergentVoiceCopies();
	const old = journal.candidate()!;
	const newer = journal.save(
		{
			phase: 'editing',
			kind: null,
			draft: {
				...old.record,
				text: 'Newer accepted memory revision',
				question: 'Newer accepted memory revision',
				omitted: [ 'newer-memory-schematic.pdf' ],
			},
		},
		old.cursor
	);
	expect( newer.conflict ).toBe( false );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	expect( sendTurn ).not.toHaveBeenCalled();
	expect( journal.candidate()?.record ).toMatchObject( {
		text: 'Newer accepted memory revision',
		omitted: [ 'newer-memory-schematic.pdf' ],
	} );
	expect( field() ).toHaveValue(
		'First accepted phrase Second accepted phrase'
	);
} );

test( 'success consumes only the selected retained copy, leaving the other actual copies reachable for A and invisible to B', async () => {
	const { journal } = await divergentVoiceCopies();
	const old = journal.candidate()!;
	expect(
		journal.save(
			{
				phase: 'editing',
				kind: null,
				draft: {
					...old.record,
					text: 'Newer accepted memory revision',
					question: 'Newer accepted memory revision',
					omitted: [ 'newer-memory-schematic.pdf' ],
				},
			},
			old.cursor
		).conflict
	).toBe( false );
	fireEvent.input( field(), {
		target: { value: 'Additional accepted UI words' },
	} );
	await restoreOwned();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Newer accepted memory revision' );
	await restoreOwned();
	expect( field() ).toHaveValue( 'Additional accepted UI words' );
	expect( journal.candidate()?.cursor.retained ).toBe( true );
	vi.mocked( sendTurn ).mockResolvedValueOnce( {
		meta: null,
		blocks: [
			{
				type: 'text',
				text: 'Selected retained version answered',
				refs: [],
			},
		],
	} );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
	);
	await screen.findByText( 'Selected retained version answered' );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	await unmountCurrent();
	principal = 'B';
	await mount();
	expect( field() ).toHaveValue( '' );
	expect( candidate( scopeB ) ).toBeUndefined();
	expect(
		screen.queryByText( 'Newer accepted memory revision' )
	).not.toBeInTheDocument();
	await unmountCurrent();
	principal = 'A';
	await mount();
	await restoreOwned();
	const seen = new Set< string >();
	for ( let i = 0; i < 3; i++ ) {
		seen.add( field().value );
		await restoreOwned();
	}
	expect( [ ...seen ] ).toEqual(
		expect.arrayContaining( [
			'Later durable project revision',
			'Newer accepted memory revision',
		] )
	);
	expect( [ ...seen ] ).not.toContain( 'Additional accepted UI words' );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'clearing stale retained UI cannot delete a later retained revision or its missing file names', async () => {
	const { journal } = await divergentVoiceCopies();
	const old = journal.candidate()!;
	expect(
		journal.save(
			{
				phase: 'editing',
				kind: null,
				draft: {
					...old.record,
					text: 'Newer accepted memory revision',
					question: 'Newer accepted memory revision',
					omitted: [ 'newer-memory-schematic.pdf' ],
				},
			},
			old.cursor
		).conflict
	).toBe( false );
	fireEvent.input( field(), {
		target: { value: 'Additional accepted UI words' },
	} );
	await restoreOwned();
	await restoreOwned();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Additional accepted UI words' );
	const retained = journal.candidate()!;
	expect( retained.cursor.retained ).toBe( true );
	expect(
		journal.save(
			{
				phase: 'editing',
				kind: null,
				draft: {
					...retained.record,
					text: 'Newer retained project revision',
					question: 'Newer retained project revision',
					omitted: [ 'retained-schematic.pdf' ],
				},
			},
			retained.cursor
		).conflict
	).toBe( false );
	fireEvent.input( field(), { target: { value: '' } } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'Remove attachment voice-project.pdf',
			} )
		)
	);
	await checkpoint();
	await restoreOwned();
	expect( field() ).toHaveValue( 'Newer retained project revision' );
	await screen.findByText(
		'Select retained-schematic.pdf again before sending.'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );
