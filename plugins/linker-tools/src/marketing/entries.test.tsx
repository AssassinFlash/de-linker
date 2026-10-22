// @vitest-environment jsdom
/** Real binder → App → turn consumer; native identity HTTP plus history/model clients are explicit fixtures. */
import {
	act,
	fireEvent,
	render,
	screen,
	waitFor,
	cleanup,
} from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { App, resetTurnLane } from '../genie/App';
import { readConfig } from '../genie/config';
import { bindMarketingEntries } from './entries';
import {
	currentOwnedRaw,
	seedOwnedFailure,
} from '../genie/testing/nativeIdentity';
import { ENTRY_KEY } from '../genie/shared/entryDraft';
import { sendTurn, selectConversation, readThread } from '../genie/api/turn';
vi.mock( '../genie/api/turn', async ( original ) => {
	const actual = await original< typeof import( '../genie/api/turn' ) >();
	return {
		...actual,
		readThread: vi.fn( async () => ( { messages: [], turn: null } ) ),
		listConversations: vi.fn( async () => ( {
			currentId: 0,
			conversations: [],
			ok: true,
		} ) ),
		selectConversation: vi.fn( async () => ( {
			currentId: 2,
			conversations: [],
			ok: true,
		} ) ),
		sendTurn: vi.fn( async () => ( {
			blocks: [ { type: 'text', text: 'A grounded answer.', refs: [] } ],
			done: true,
		} ) ),
	};
} );
const SCOPE = 'a'.repeat( 64 );
let stop: () => void;
let currentScope = SCOPE;
let scopeOK = true;
beforeEach( () => {
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieFailureJournal;
	delete ( window as unknown as Record< string, unknown > )
		.__linkerGenieNativeScope;
	sessionStorage.clear();
	resetTurnLane();
	currentScope = SCOPE;
	scopeOK = true;
	vi.mocked( sendTurn ).mockReset();
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: null,
		blocks: [ { type: 'text', text: 'A grounded answer.', refs: [] } ],
	} );
	vi.mocked( readThread ).mockResolvedValue( { messages: [], turn: null } );
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( {
			ok: scopeOK,
			json: async () => ( { scope: currentScope } ),
		} ) )
	);
} );
afterEach( () => {
	stop?.();
	cleanup();
	document.body.innerHTML = '';
	vi.unstubAllGlobals();
	resetTurnLane();
} );
function setup() {
	document.body.innerHTML =
		'<section id="system-search"><textarea class="lk-dialog-prompt"></textarea><a href="/genie/" class="lk-send-btn">Send query</a><button data-linker-assistant-open="attach" disabled>Attach</button><button data-linker-assistant-open="voice">Voice</button></section>';
	const mount = document.createElement( 'div' );
	const config = readConfig( mount );
	render( <App config={ config } /> );
	stop = bindMarketingEntries( document, config );
	const send = () =>
		fireEvent.click( document.querySelector( '.lk-send-btn' )! );
	const source =
		document.querySelector< HTMLTextAreaElement >( '.lk-dialog-prompt' )!;
	const deliver = async () => {
		// Same dock routing as production; lazy script boot itself is a separate fixture.
		window.addEventListener( 'linker-genie-ask', forward );
	};
	function forward( event: Event ) {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: ( event as CustomEvent ).detail,
			} )
		);
	}
	window.addEventListener( 'linker-genie-ask', forward );
	const unbind = stop;
	stop = () => {
		unbind();
		window.removeEventListener( 'linker-genie-ask', forward );
	};
	return {
		send,
		source,
		deliver,
		composer: () =>
			screen.getByRole< HTMLTextAreaElement >( 'textbox', {
				name: 'Ask Genie',
			} ),
	};
}
test( 'typed marketing question reaches one actual turn, same-tick gestures do not duplicate', async () => {
	const { source, send } = setup();
	source.value = 'Which battery works with SAJ H2?';
	await act( async () => {
		send();
		send();
	} );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect(
		vi.mocked( sendTurn ).mock.calls[ 0 ]?.[ 0 ].messages.at( -1 )
	).toEqual( { role: 'user', content: 'Which battery works with SAJ H2?' } );
	await waitFor( () =>
		expect( screen.getByText( 'A grounded answer.' ) ).toBeTruthy()
	);
	expect( source.value ).toBe( '' );
} );
test( 'IME and Shift Enter preserve editing; whitespace has no turn', async () => {
	const { source, send } = setup();
	source.value = '正在输入';
	fireEvent.keyDown( source, {
		key: 'Enter',
		isComposing: true,
		keyCode: 229,
	} );
	fireEvent.keyDown( source, { key: 'Enter', shiftKey: true } );
	source.value = '  ';
	await act( async () => send() );
	expect( sendTurn ).not.toHaveBeenCalled();
} );
test( 'attach opens a draft with exact text and no turn; canceled picker keeps it', async () => {
	const { source, composer } = setup();
	source.value = 'Read this schematic first.';
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Attach' } ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Read this schematic first.' )
	);
	expect(
		screen.getByRole( 'button', { name: 'Choose a file' } )
	).toBeTruthy();
	expect( sendTurn ).not.toHaveBeenCalled();
	fireEvent.change( document.querySelector( 'input[type=file]' )!, {
		target: { files: [] },
	} );
	expect( composer().value ).toBe( 'Read this schematic first.' );
} );
test( 'existing composer is preserved and separate send parks it without leaking its text', async () => {
	const { source, send, composer } = setup();
	act( () => window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) ) );
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	fireEvent.change( composer(), {
		target: { value: 'Existing unsent note' },
	} );
	source.value = 'New product question';
	await act( async () => send() );
	await screen.findByText( 'Question from this page' );
	await waitFor( () =>
		expect( composer().value ).toBe( 'Existing unsent note' )
	);
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Send question separately' } )
		)
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect(
		vi.mocked( sendTurn ).mock.calls[ 0 ]?.[ 0 ].messages.at( -1 )?.content
	).toBe( 'New product question' );
	await screen.findByText( 'Current unsent draft' );
	await waitFor( () =>
		expect(
			screen.getByRole< HTMLButtonElement >( 'button', {
				name: 'Restore unsent draft',
			} ).disabled
		).toBe( false )
	);
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Existing unsent note' )
	);
} );
test( 'scope failure keeps source text and sends nothing', async () => {
	const { source, send } = setup();
	source.value = 'Keep this exact question';
	scopeOK = false;
	await act( async () => send() );
	await waitFor( () =>
		expect(
			document.querySelector( '#system-search [role=status]' )
				?.textContent
		).toBe( 'Genie could not load.' )
	);
	expect( source.value ).toBe( 'Keep this exact question' );
	expect( sendTurn ).not.toHaveBeenCalled();
} );
test( 'ack-loss replay does not send twice and failure ownership stores entry identity', async () => {
	const { source, send } = setup();
	source.value = 'Same accepted attempt';
	let payload: unknown;
	window.addEventListener( 'linker-genie-ask', capture, { once: true } );
	function capture( event: Event ) {
		payload = ( event as CustomEvent ).detail;
	}
	await act( async () => send() );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', { detail: payload } )
		);
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', { detail: payload } )
		);
	} );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	expect(
		JSON.parse( sessionStorage.getItem( ENTRY_KEY )! ).claimed
	).toHaveLength( 1 );
} );

test( 'a different question arriving during a turn stays owned and runs once after it', async () => {
	let finish!: ( value: Awaited< ReturnType< typeof sendTurn > > ) => void;
	vi.mocked( sendTurn ).mockImplementationOnce(
		() =>
			new Promise( ( resolve ) => {
				finish = resolve;
			} )
	);
	const { source, send } = setup();
	source.value = 'First question';
	await act( async () => send() );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	source.value = 'Next question';
	await act( async () => send() );
	await screen.findByText( 'Next question' );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	await act( async () =>
		finish( {
			meta: null,
			blocks: [ { type: 'text', text: 'First answer', refs: [] } ],
		} )
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 2 ) );
	expect(
		vi.mocked( sendTurn ).mock.calls[ 1 ]?.[ 0 ].messages.at( -1 )?.content
	).toBe( 'Next question' );
} );
test( 'a newly typed identical question is a distinct attempt after acceptance', async () => {
	const { source, send } = setup();
	source.value = 'Ask again';
	await act( async () => send() );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	await screen.findByText( 'A grounded answer.' );
	source.value = 'Ask again';
	await act( async () => send() );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 2 ) );
} );
test( 'unsent refresh restores text and explicit missing-file state, with no automatic turn', async () => {
	sessionStorage.setItem(
		ENTRY_KEY,
		JSON.stringify( {
			v: 1,
			scope: SCOPE,
			entries: [],
			claimed: [],
			composer: { text: 'Unsent with PDF', missing: [ 'schematic.pdf' ] },
			parked: null,
		} )
	);
	const { composer } = setup();
	act( () => window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) ) );
	await waitFor( () => expect( composer().value ).toBe( 'Unsent with PDF' ) );
	expect(
		screen.getByText( 'Select schematic.pdf again before sending.' )
	).toBeTruthy();
	expect( sendTurn ).not.toHaveBeenCalled();
	fireEvent.keyDown( composer(), { key: 'Enter' } );
	expect( sendTurn ).not.toHaveBeenCalled();
} );
test( 'old-scope recovery is never displayed to the next principal', async () => {
	sessionStorage.setItem(
		ENTRY_KEY,
		JSON.stringify( {
			v: 1,
			scope: 'b'.repeat( 64 ),
			entries: [],
			claimed: [],
			composer: { text: 'Other principal private text', missing: [] },
			parked: null,
		} )
	);
	const { composer } = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	expect( composer().value ).toBe( '' );
	expect( document.body.textContent ).not.toContain(
		'Other principal private text'
	);
	expect( sessionStorage.getItem( ENTRY_KEY ) ).toBeNull();
	expect( sendTurn ).not.toHaveBeenCalled();
} );
test( 'supported voice entry presents one explicit action without a duplicate instruction', async () => {
	const start = vi.fn();
	vi.stubGlobal(
		'SpeechRecognition',
		class {
			start = start;
			stop() {}
		}
	);
	const { source, composer } = setup();
	source.value = 'Keep my voice draft';
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Keep my voice draft' )
	);
	const prompt = document.querySelector( '.linker-genie-app__photo-prompt' );
	expect( prompt ).not.toBeNull();
	expect( prompt?.querySelector( 'p' ) ).toBeNull();
	expect( prompt?.querySelector( 'button' )?.textContent ).toBe( 'Dictate' );
	expect( start ).not.toHaveBeenCalled();
	expect( sendTurn ).not.toHaveBeenCalled();
} );
test( 'voice unsupported keeps source words as an editable draft', async () => {
	const { source, composer } = setup();
	source.value = 'Keep my introduction';
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Keep my introduction' )
	);
	expect(
		screen.getByText(
			'Dictation is not available in this browser. You can type your question.'
		)
	).toBeTruthy();
	expect(
		document.querySelector( '.linker-genie-app__photo-prompt p' )
			?.textContent
	).toBe(
		'Dictation is not available in this browser. You can type your question.'
	);
	expect(
		document.querySelector( '.linker-genie-app__photo-prompt button' )
	).toBeNull();
	expect( sendTurn ).not.toHaveBeenCalled();
} );
test( 'storage failure leaves source owned and never falsely acknowledges a turn', async () => {
	const { source, send } = setup();
	source.value = 'Do not lose me';
	const native = Storage.prototype.setItem;
	vi.spyOn( Storage.prototype, 'setItem' ).mockImplementation( function (
		this: Storage,
		key,
		value
	) {
		if ( key === ENTRY_KEY ) {
			throw new DOMException( 'quota', 'QuotaExceededError' );
		}
		native.call( this, key, value );
	} );
	await act( async () => send() );
	expect( source.value ).toBe( 'Do not lose me' );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'transport failure retains entry identity and exact failed text for the existing retry', async () => {
	vi.mocked( sendTurn ).mockRejectedValueOnce( new Error( 'upstream' ) );
	const { source, send, composer } = setup();
	source.value = 'Original failed question';
	await act( async () => send() );
	await screen.findByText( 'Genie did not answer. Please try again.' );
	expect( composer().value ).toBe( 'Original failed question' );
	const failure = JSON.parse( currentOwnedRaw()! );
	expect( failure.entryId ).toBeTruthy();
	expect( failure.entryScope ).toBe( SCOPE );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 2 ) );
	expect(
		vi
			.mocked( sendTurn )
			.mock.calls[ 1 ]?.[ 0 ].messages.filter(
				( item ) => item.role === 'user'
			)
	).toEqual( [ { role: 'user', content: 'Original failed question' } ] );
} );

test( 'phone helper owns keyboard focus, Help consumes its first Escape, sheet then returns focus', async () => {
	vi.stubGlobal( 'innerWidth', 390 );
	vi.spyOn( HTMLElement.prototype, 'getClientRects' ).mockImplementation(
		() => [ new DOMRect( 0, 0, 100, 44 ) ] as unknown as DOMRectList
	);
	const { source, composer } = setup();
	source.focus();
	await act( async () =>
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { opener: source },
			} )
		)
	);
	const dialog = screen.getByRole( 'dialog' );
	expect( dialog.getAttribute( 'aria-modal' ) ).toBe( 'true' );
	await waitFor( () =>
		expect( source.ownerDocument.activeElement ).toBe( composer() )
	);
	expect(
		document.querySelector< HTMLElement >( '#system-search' )?.inert
	).toBe( true );
	const details =
		document.querySelector< HTMLDetailsElement >( '.linker-genie-help' )!;
	details.querySelector< HTMLElement >( 'summary' )!.focus();
	fireEvent.keyDown( details.querySelector( 'summary' )!, { key: 'Tab' } );
	expect( dialog.contains( source.ownerDocument.activeElement ) ).toBe(
		true
	);
	details.open = true;
	fireEvent.keyDown( details.querySelector( 'summary' )!, { key: 'Escape' } );
	expect( details.open ).toBe( false );
	expect( screen.getByRole( 'dialog' ) ).toBeTruthy();
	await act( async () => fireEvent.keyDown( composer(), { key: 'Escape' } ) );
	expect( screen.queryByRole( 'dialog' ) ).toBeNull();
	expect(
		document.querySelector< HTMLElement >( '#system-search' )?.inert
	).toBe( false );
	expect( source.ownerDocument.activeElement ).toBe( source );
} );
test( 'desktop dock is nonmodal and closing does not steal intentional background focus', async () => {
	vi.stubGlobal( 'innerWidth', 1440 );
	vi.spyOn( HTMLElement.prototype, 'getClientRects' ).mockImplementation(
		() => [ new DOMRect( 0, 0, 100, 44 ) ] as unknown as DOMRectList
	);
	const { source } = setup();
	source.focus();
	await act( async () =>
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-open', {
				detail: { opener: source },
			} )
		)
	);
	expect( screen.getByRole( 'dialog' ).hasAttribute( 'aria-modal' ) ).toBe(
		false
	);
	const other = document.createElement( 'button' );
	other.textContent = 'Other page action';
	document.body.append( other );
	other.focus();
	await act( async () => fireEvent.keyDown( other, { key: 'Escape' } ) );
	expect( source.ownerDocument.activeElement ).toBe( other );
	expect( screen.queryByRole( 'dialog' ) ).toBeNull();
} );

test( 'entry-derived attachment composer cannot send private A text as principal B', async () => {
	const { source, composer } = setup();
	source.value = 'Customer A private schematic description';
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Attach' } ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe(
			'Customer A private schematic description'
		)
	);
	currentScope = 'b'.repeat( 64 );
	await act( async () =>
		fireEvent.click( document.querySelector( '.linker-genie-app__send' )! )
	);
	expect( sendTurn ).not.toHaveBeenCalled();
	expect( composer().value ).toBe( '' );
} );
test( 'entry failed Retry cannot deliver private A question as principal B', async () => {
	vi.mocked( sendTurn ).mockRejectedValueOnce( new Error( 'upstream' ) );
	const { source, send } = setup();
	source.value = 'Customer A private failed question';
	await act( async () => send() );
	await screen.findByText( 'Genie did not answer. Please try again.' );
	currentScope = 'b'.repeat( 64 );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );
test( 'claim quota failure after source persistence keeps source owned and retries once', async () => {
	const { source, send } = setup();
	source.value = 'Original source owner';
	const native = Storage.prototype.setItem;
	let writes = 0;
	vi.spyOn( Storage.prototype, 'setItem' ).mockImplementation( function (
		this: Storage,
		key,
		value
	) {
		if ( key === ENTRY_KEY && ++writes === 2 ) {
			throw new DOMException( 'quota', 'QuotaExceededError' );
		}
		native.call( this, key, value );
	} );
	await act( async () => send() );
	await waitFor( () =>
		expect(
			document.querySelector( '#system-search [role=status]' )
				?.textContent
		).toBe( 'Genie could not load.' )
	);
	expect( source.value ).toBe( 'Original source owner' );
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () => send() );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
} );
test( 'park quota failure keeps prior composer and incoming question separate and retryable', async () => {
	const { source, send, composer } = setup();
	act( () => window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) ) );
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	fireEvent.change( composer(), {
		target: { value: 'Original unsent owner' },
	} );
	source.value = 'Incoming product question';
	await act( async () => send() );
	await screen.findByText( 'Question from this page' );
	const native = Storage.prototype.setItem;
	let failed = false;
	vi.spyOn( Storage.prototype, 'setItem' ).mockImplementation( function (
		this: Storage,
		key,
		value
	) {
		if ( key === ENTRY_KEY && ! failed ) {
			failed = true;
			throw new DOMException( 'quota', 'QuotaExceededError' );
		}
		native.call( this, key, value );
	} );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Send question separately' } )
		)
	);
	expect( composer().value ).toBe( 'Original unsent owner' );
	expect( screen.getByText( 'Incoming product question' ) ).toBeTruthy();
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Send question separately' } )
		)
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect( screen.getByText( 'Original unsent owner' ) ).toBeTruthy();
} );
test( 'missing-file-only draft is an occupied owner and is parked by a separate question', async () => {
	sessionStorage.setItem(
		ENTRY_KEY,
		JSON.stringify( {
			v: 1,
			scope: SCOPE,
			entries: [],
			claimed: [],
			composer: { text: '', missing: [ 'schematic.pdf' ] },
			parked: null,
		} )
	);
	const { source, send } = setup();
	act( () => window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) ) );
	await screen.findByText( 'Select schematic.pdf again before sending.' );
	source.value = 'New independent question';
	await act( async () => send() );
	await screen.findByRole( 'button', { name: 'Keep current draft' } );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Send question separately' } )
		)
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect(
		screen.getByText( 'Select schematic.pdf again before sending.' )
	).toBeTruthy();
	expect(
		JSON.parse( sessionStorage.getItem( ENTRY_KEY )! ).parked.missing
	).toEqual( [ 'schematic.pdf' ] );
} );
test( 'delayed parked restore quarantines input and retains both explicitly exchanged owners', async () => {
	const { source, send, composer } = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	fireEvent.change( composer(), {
		target: { value: 'Original parked requirement' },
	} );
	source.value = 'Separate first question';
	await act( async () => send() );
	await screen.findByText( 'Question from this page' );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Send question separately' } )
		)
	);
	await screen.findByText( 'A grounded answer.' );
	fireEvent.change( composer(), {
		target: { value: 'New accepted replacement' },
	} );
	let release!: ( value: unknown ) => void;
	vi.stubGlobal(
		'fetch',
		vi.fn(
			() =>
				new Promise( ( resolve ) => {
					release = resolve;
				} )
		)
	);
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	await waitFor( () => expect( release ).toBeTypeOf( 'function' ) );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	expect(
		JSON.parse( sessionStorage.getItem( ENTRY_KEY )! ).parked.text
	).toBe( 'Original parked requirement' );
	vi.stubGlobal(
		'fetch',
		vi.fn( async () => ( {
			ok: true,
			json: async () => ( { scope: SCOPE } ),
		} ) )
	);
	await act( async () =>
		release( { ok: true, json: async () => ( { scope: SCOPE } ) } )
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Original parked requirement' )
	);
	expect(
		JSON.parse( sessionStorage.getItem( ENTRY_KEY )! ).parked.text
	).toBe( 'New accepted replacement' );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'an attachment-derived ordinary failure keeps scope and cannot paint A text after B remount', async () => {
	const privateText = 'Private A attachment draft';
	const { source, composer } = setup();
	source.value = privateText;
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Attach' } ) )
	);
	await waitFor( () => expect( composer().value ).toBe( privateText ) );
	vi.mocked( sendTurn ).mockRejectedValueOnce( new Error( 'upstream' ) );
	await act( async () =>
		fireEvent.click( document.querySelector( '.linker-genie-app__send' )! )
	);
	await screen.findByText( 'Genie did not answer. Please try again.' );
	const record = JSON.parse( currentOwnedRaw()! );
	expect( record.entryId ).toBeTruthy();
	expect( record.entryScope ).toBe( SCOPE );
	stop();
	cleanup();
	currentScope = 'b'.repeat( 64 );
	const painted = vi.spyOn( HTMLTextAreaElement.prototype, 'value', 'set' );
	const next = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( next.composer().disabled ).toBe( false ) );
	expect( painted ).not.toHaveBeenCalledWith( privateText );
	expect( next.composer().value ).toBe( '' );
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
} );

test( 'temporary scope outage preserves entry composer and files for a fresh retry', async () => {
	const { source, composer } = setup();
	source.value = 'Keep this scoped schematic';
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Attach' } ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe(
			source.value || 'Keep this scoped schematic'
		)
	);
	const file = new File( [ '%PDF-1.4' ], 'keep.pdf', {
		type: 'application/pdf',
	} );
	await act( async () =>
		fireEvent.change( document.querySelector( 'input[type=file]' )!, {
			target: { files: [ file ] },
		} )
	);
	await waitFor( () =>
		expect( screen.getByText( 'keep.pdf' ) ).toBeTruthy()
	);
	await waitFor( () => {
		expect( screen.queryByText( 'Preparing file…' ) ).toBeNull();
		expect(
			document.querySelector( '.linker-genie-app__send' )
		).not.toBeDisabled();
	} );

	scopeOK = false;
	await act( async () =>
		fireEvent.click( document.querySelector( '.linker-genie-app__send' )! )
	);
	expect( sendTurn ).not.toHaveBeenCalled();
	expect( composer().value ).toBe( '' );
	expect( composer().disabled ).toBe( true );
	expect( screen.queryByText( 'keep.pdf' ) ).toBeNull();
	expect( screen.getByRole( 'button', { name: 'Try again' } ) ).toBeTruthy();
	scopeOK = true;
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Keep this scoped schematic' )
	);
	expect( screen.getByText( 'keep.pdf' ) ).toBeTruthy();
	expect( sendTurn ).not.toHaveBeenCalled();
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect(
		vi.mocked( sendTurn ).mock.calls[ 0 ]?.[ 0 ].uploads?.[ 0 ]?.name
	).toBe( 'keep.pdf' );
} );

test( 'temporary scope outage on Retry keeps the exact failed entry retryable', async () => {
	const { source, send, composer } = setup();
	source.value = 'Keep failed scoped requirement';
	vi.mocked( sendTurn ).mockRejectedValueOnce( new Error( 'upstream' ) );
	await act( async () => send() );
	await screen.findByRole( 'button', { name: 'Try again' } );
	scopeOK = false;
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	expect( composer().value ).toBe( '' );
	expect( composer().disabled ).toBe( true );
	expect( JSON.parse( currentOwnedRaw()! ).entryScope ).toBe( SCOPE );
	scopeOK = true;
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Keep failed scoped requirement' )
	);
	expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) )
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 2 ) );
} );

test( 'verified scoped pending failure reclaimed by composer stays scoped after edited ordinary send', async () => {
	sessionStorage.setItem(
		'linker-genie-turn-failure',
		JSON.stringify( {
			v: 1,
			kind: null,
			text: 'Scoped pending original',
			question: 'Scoped pending original',
			uploads: [],
			omitted: [],
			entryId: 'pending-entry',
			entryScope: SCOPE,
		} )
	);
	const { composer } = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Scoped pending original' )
	);
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	fireEvent.change( composer(), {
		target: { value: 'Edited scoped original' },
	} );
	vi.mocked( sendTurn ).mockRejectedValueOnce( new Error( 'upstream' ) );
	await act( async () =>
		fireEvent.click( document.querySelector( '.linker-genie-app__send' )! )
	);
	await screen.findByRole( 'button', { name: 'Try again' } );
	expect( JSON.parse( currentOwnedRaw()! ).owner.scope ).toBe( SCOPE );
} );

test( 'parked restore after a conversation switch reclaims scope for edited ordinary failure', async () => {
	const { source, send, composer } = setup();
	act( () => window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) ) );
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	fireEvent.change( composer(), {
		target: { value: 'Original parked private requirement' },
	} );
	source.value = 'Separate current question';
	await act( async () => send() );
	await screen.findByText( 'Question from this page' );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Send question separately' } )
		)
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'New conversation' } )
		)
	);
	expect( selectConversation ).toHaveBeenCalled();
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Restore unsent draft' } )
		)
	);
	await waitFor( () =>
		expect( composer().value ).toBe( 'Original parked private requirement' )
	);
	vi.mocked( sendTurn ).mockRejectedValueOnce( new Error( 'upstream' ) );
	await act( async () =>
		fireEvent.click( document.querySelector( '.linker-genie-app__send' )! )
	);
	await screen.findByRole( 'button', { name: 'Try again' } );
	expect( JSON.parse( currentOwnedRaw()! ).entryScope ).toBe( SCOPE );
	stop();
	cleanup();
	currentScope = 'b'.repeat( 64 );
	const painted = vi.spyOn( HTMLTextAreaElement.prototype, 'value', 'set' );
	const next = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( next.composer().disabled ).toBe( false ) );
	expect( painted ).not.toHaveBeenCalledWith(
		'Original parked private requirement'
	);
	expect( next.composer().value ).toBe( '' );
} );

for ( const record of [ 'unsent', 'failure' ] as const ) {
	test( `initial ${ record } scope outage hides private text and offers an actual recovery retry`, async () => {
		const original = 'Private recovery original';
		if ( record === 'unsent' ) {
			sessionStorage.setItem(
				ENTRY_KEY,
				JSON.stringify( {
					v: 1,
					scope: SCOPE,
					entries: [],
					claimed: [],
					composer: { text: original, missing: [ 'missing.pdf' ] },
					parked: null,
				} )
			);
		} else {
			sessionStorage.setItem(
				'linker-genie-turn-failure',
				JSON.stringify( {
					v: 1,
					kind: null,
					text: original,
					question: original,
					uploads: [],
					omitted: [],
					entryId: 'scope-restore',
					entryScope: SCOPE,
				} )
			);
		}
		scopeOK = false;
		const painted = vi.spyOn(
			HTMLTextAreaElement.prototype,
			'value',
			'set'
		);
		const { composer } = setup();
		await act( async () =>
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
		);
		await screen.findByRole( 'button', { name: 'Try again' } );
		expect( painted ).not.toHaveBeenCalledWith( original );
		expect( composer().value ).toBe( '' );
		expect(
			sessionStorage.getItem(
				record === 'unsent' ? ENTRY_KEY : 'linker-genie-turn-failure'
			)
		).not.toBeNull();
		scopeOK = true;
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			)
		);
		await waitFor( () => expect( composer().value ).toBe( original ) );
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}

for ( const record of [ 'unsent', 'failure' ] as const ) {
	test( `scope recovery accepts a new edit only after verification of the ${ record } composer edit`, async () => {
		const original = 'Original hidden recovery';
		if ( record === 'unsent' ) {
			sessionStorage.setItem(
				ENTRY_KEY,
				JSON.stringify( {
					v: 1,
					scope: SCOPE,
					entries: [],
					claimed: [],
					composer: { text: original, missing: [] },
					parked: null,
				} )
			);
		} else {
			sessionStorage.setItem(
				'linker-genie-turn-failure',
				JSON.stringify( {
					v: 1,
					kind: null,
					text: original,
					question: original,
					uploads: [],
					omitted: [],
					entryId: 'review-scope',
					entryScope: SCOPE,
				} )
			);
		}
		scopeOK = false;
		const { composer } = setup();
		await act( async () =>
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
		);
		await screen.findByRole( 'button', { name: 'Try again' } );
		expect( composer().disabled ).toBe( true );
		fireEvent.change( composer(), {
			target: {
				value: 'New draft typed while verification was unavailable',
			},
		} );
		scopeOK = true;
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Try again' } )
			)
		);
		await waitFor( () => expect( composer().disabled ).toBe( false ) );
		expect( composer().value ).toBe( original );
		fireEvent.change( composer(), {
			target: { value: 'New accepted draft after verification' },
		} );
		expect( composer().value ).toBe(
			'New accepted draft after verification'
		);
		expect( sendTurn ).not.toHaveBeenCalled();
	} );
}

test( 'delayed verified failure is retained beside a newly accepted composer', async () => {
	seedOwnedFailure( {
		kind: 'upstream',
		text: 'Old verified failed draft',
		question: 'Old verified failed draft',
	} );
	let release!: ( value: Awaited< ReturnType< typeof readThread > > ) => void;
	vi.mocked( readThread ).mockImplementationOnce(
		() =>
			new Promise( ( resolve ) => {
				release = resolve;
			} )
	);
	const { composer } = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	fireEvent.change( composer(), {
		target: { value: 'Freshly typed replacement draft' },
	} );
	await act( async () => release( { messages: [], turn: null } ) );
	await screen.findByText( 'Old verified failed draft' );
	expect( composer().value ).toBe( 'Freshly typed replacement draft' );
	expect(
		sessionStorage.getItem( 'linker-genie-turn-failure:v2:' + SCOPE )
	).toContain( 'Old verified failed draft' );
	expect( sendTurn ).not.toHaveBeenCalled();
} );

test( 'deferred failure stays owned and actionable after a newer attachment finishes preparing', async () => {
	seedOwnedFailure( {
		kind: 'upstream',
		text: 'Old owner waiting for upload',
		question: 'Old owner waiting for upload',
	} );
	let release!: ( value: Awaited< ReturnType< typeof readThread > > ) => void;
	vi.mocked( readThread ).mockImplementationOnce(
		() =>
			new Promise( ( resolve ) => {
				release = resolve;
			} )
	);
	const reads: Array< () => void > = [];
	const native = FileReader.prototype.readAsArrayBuffer;
	const spy = vi
		.spyOn( FileReader.prototype, 'readAsArrayBuffer' )
		.mockImplementation( function ( this: FileReader, file: Blob ) {
			reads.push( () => native.call( this, file ) );
		} );
	try {
		const { composer } = setup();
		await act( async () =>
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
		);
		await waitFor( () => expect( composer().disabled ).toBe( false ) );
		fireEvent.change( composer(), {
			target: { value: 'New upload draft' },
		} );
		fireEvent.change( document.querySelector( 'input[type=file]' )!, {
			target: {
				files: [
					new File( [ '%PDF-1.4 new' ], 'new.pdf', {
						type: 'application/pdf',
					} ),
				],
			},
		} );
		await act( async () => release( { messages: [], turn: null } ) );
		await screen.findByText( 'Old owner waiting for upload' );
		expect( sendTurn ).not.toHaveBeenCalled();
		await act( async () => reads.forEach( ( read ) => read() ) );
		await waitFor( () =>
			expect(
				screen.getByRole( 'button', { name: 'Send' } )
			).toBeEnabled()
		);
		expect( composer().value ).toBe( 'New upload draft' );
		await act( async () =>
			fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) )
		);
		await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
		expect( currentOwnedRaw() ).toContain( 'Old owner waiting for upload' );
		expect(
			vi.mocked( sendTurn ).mock.calls[ 0 ]?.[ 0 ].uploads?.[ 0 ]?.name
		).toBe( 'new.pdf' );
	} finally {
		spy.mockRestore();
	}
} );

test( 'App initially pending identity cannot overwrite sole old scoped failure', async () => {
	const raw = JSON.stringify( {
		v: 1,
		kind: null,
		text: 'Only prior scoped App original',
		question: 'Only prior scoped App original',
		uploads: [],
		omitted: [],
		entryId: 'old-app-pending',
		entryScope: SCOPE,
	} );
	sessionStorage.setItem( 'linker-genie-turn-failure', raw );
	const releases: Array< ( value: unknown ) => void > = [];
	vi.stubGlobal(
		'fetch',
		vi.fn( () => new Promise( ( resolve ) => releases.push( resolve ) ) )
	);
	const { composer } = setup();
	try {
		await act( async () =>
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
		);
		await waitFor( () => expect( releases.length ).toBeGreaterThan( 0 ) );
		expect( composer().disabled ).toBe( true );
		fireEvent.change( composer(), {
			target: { value: 'New prompt during first scope lookup' },
		} );
		await act( async () =>
			fireEvent.click(
				document.querySelector( '.linker-genie-app__send' )!
			)
		);
		expect( sendTurn ).not.toHaveBeenCalled();
		expect( sessionStorage.getItem( 'linker-genie-turn-failure' ) ).toBe(
			raw
		);
	} finally {
		await act( async () =>
			releases.forEach( ( resolve ) =>
				resolve( { ok: true, json: async () => ( { scope: SCOPE } ) } )
			)
		);
	}
} );

test( 'accepted external entry remains durable and unsettled while an older failure owns recovery', async () => {
	const raw = JSON.stringify( {
		v: 1,
		kind: null,
		text: 'Prior scoped owner held',
		question: 'Prior scoped owner held',
		uploads: [],
		omitted: [],
		entryId: 'prior-held',
		entryScope: SCOPE,
	} );
	sessionStorage.setItem( 'linker-genie-turn-failure', raw );
	let release!: ( value: unknown ) => void;
	let reads = 0;
	vi.stubGlobal(
		'fetch',
		vi.fn( () => {
			reads += 1;
			// Binder startup is the first lookup; App's shared failure verification is the second.
			return reads === 2
				? new Promise( ( resolve ) => {
						release = resolve;
					} )
				: Promise.resolve( {
						ok: true,
						json: async () => ( { scope: SCOPE } ),
					} );
		} )
	);
	const { source, send } = setup();
	await waitFor( () => expect( release ).toBeTypeOf( 'function' ) );
	source.value = 'Incoming distinct question';
	const ack = vi.fn();
	window.addEventListener( 'linker-genie-entry-state', ack );
	try {
		await act( async () => send() );
		await waitFor( () =>
			expect(
				JSON.parse( sessionStorage.getItem( ENTRY_KEY )! ).entries.some(
					( item: { text: string } ) =>
						item.text === 'Incoming distinct question'
				)
			).toBe( true )
		);
		expect( sendTurn ).not.toHaveBeenCalled();
		expect( sessionStorage.getItem( 'linker-genie-turn-failure' ) ).toBe(
			raw
		);
		expect(
			JSON.parse( sessionStorage.getItem( ENTRY_KEY )! ).entries.some(
				( entry: { text: string } ) =>
					entry.text === 'Incoming distinct question'
			)
		).toBe( true );
		expect(
			ack.mock.calls.some(
				( [ event ] ) => event.detail.phase === 'settled'
			)
		).toBe( false );
		await act( async () =>
			release( { ok: true, json: async () => ( { scope: SCOPE } ) } )
		);
		await screen.findByText( 'Question from this page' );
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', {
					name: 'Send question separately',
				} )
			)
		);
		await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
		expect(
			vi.mocked( sendTurn ).mock.calls[ 0 ]?.[ 0 ].messages.at( -1 )
				?.content
		).toBe( 'Incoming distinct question' );
		expect(
			JSON.parse( sessionStorage.getItem( ENTRY_KEY )! ).parked.text
		).toBe( 'Prior scoped owner held' );
	} finally {
		window.removeEventListener( 'linker-genie-entry-state', ack );
	}
} );

test( 'confirmed scope mismatch leaves old bytes inactive and allows the current principal to ask', async () => {
	sessionStorage.setItem(
		'linker-genie-turn-failure',
		JSON.stringify( {
			v: 1,
			kind: null,
			text: 'Private principal A original',
			question: 'Private principal A original',
			uploads: [],
			omitted: [],
			entryId: 'old-a',
			entryScope: SCOPE,
		} )
	);
	currentScope = 'b'.repeat( 64 );
	const { composer } = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	expect( sessionStorage.getItem( 'linker-genie-turn-failure' ) ).toContain(
		'Private principal A original'
	);
	expect( composer().value ).toBe( '' );
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	fireEvent.change( composer(), {
		target: { value: 'Current principal B new requirement' },
	} );
	await act( async () =>
		fireEvent.click( document.querySelector( '.linker-genie-app__send' )! )
	);
	await waitFor( () => expect( sendTurn ).toHaveBeenCalledTimes( 1 ) );
	expect(
		vi.mocked( sendTurn ).mock.calls[ 0 ]?.[ 0 ].messages.at( -1 )?.content
	).toBe( 'Current principal B new requirement' );
} );

test( 'a fresh marketing Attach under A cannot give its later edited bytes to the previously mounted B context', async () => {
	currentScope = 'b'.repeat( 64 );
	const { source, composer } = setup();
	await act( async () =>
		window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
	);
	await waitFor( () => expect( composer().disabled ).toBe( false ) );
	currentScope = SCOPE;
	source.value = 'A newly accepted private brief';
	await act( async () =>
		fireEvent.click( screen.getByRole( 'button', { name: 'Attach' } ) )
	);
	await waitFor( () =>
		expect(
			composer().value === 'A newly accepted private brief' ||
				!! screen.queryByRole( 'button', { name: 'Open as draft' } )
		).toBe( true )
	);
	if ( composer().value !== 'A newly accepted private brief' ) {
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Open as draft' } )
			)
		);
	}
	await waitFor( () =>
		expect( composer().value ).toBe( 'A newly accepted private brief' )
	);
	fireEvent.change( composer(), {
		target: { value: 'A edited private brief' },
	} );
	currentScope = 'b'.repeat( 64 );
	await act( async () => window.dispatchEvent( new Event( 'focus' ) ) );
	expect( composer().value ).toBe( '' );
	expect( document.body.textContent ).not.toContain(
		'A edited private brief'
	);
	expect( sendTurn ).not.toHaveBeenCalled();
} );
