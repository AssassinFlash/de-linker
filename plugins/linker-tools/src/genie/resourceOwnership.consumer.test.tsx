// @vitest-environment jsdom
/** Resource rejection returns the same ordinary attempt to its real editor. */
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
import { FailureJournal } from './shared/ownedFailure';
import { startHero } from '../hero/controller';

vi.mock( './api/turn', async ( original ) => {
	const actual = await original< typeof import( './api/turn' ) >();
	return { ...actual, sendTurn: vi.fn() };
} );

const scope = 'a'.repeat( 64 );
const question = 'Original resource-refused project question';
const answer = {
	meta: null,
	blocks: [
		{ type: 'text' as const, text: 'Current authorized answer', refs: [] },
	],
};
let stop = () => {};

beforeEach( () => {
	sessionStorage.clear();
	for ( const key of [
		'__linkerGenieFailureJournal',
		'__linkerGenieNativeScope',
	] ) {
		delete ( window as unknown as Record< string, unknown > )[ key ];
	}
	resetTurnLane();
	vi.mocked( sendTurn ).mockReset();
	vi.stubGlobal(
		'fetch',
		vi.fn( async ( url ) => {
			if ( String( url ).includes( '/entry-context' ) ) {
				return { ok: true, json: async () => ( { scope } ) };
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
				`Unexpected consumer request: ${ String( url ) }`
			);
		} )
	);
} );

afterEach( () => {
	stop();
	cleanup();
	document.body.innerHTML = '';
	sessionStorage.clear();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	resetTurnLane();
} );

async function mount( surface: 'dock' | 'home' ) {
	const mountPoint = document.createElement( 'div' );
	mountPoint.dataset.restNonce = 'native-owner';
	mountPoint.dataset.requestPageUrl = '/proforma-request/';
	const config = readConfig( mountPoint );
	if ( surface === 'dock' ) {
		const ui = render( <App config={ config } /> );
		stop = ui.unmount;
		await act( async () =>
			window.dispatchEvent( new CustomEvent( 'linker-genie-open' ) )
		);
	} else {
		document.body.innerHTML = `
<section class="hero-cinematic"><div class="hero-stage">
  <div class="hero-dialog">
    <textarea class="hero-prompt" placeholder="Ask Genie"></textarea>
    <div class="hero-dialog-footer"><a class="hero-send" href="/genie/">Send</a></div>
  </div>
</div></section>`;
		const hero =
			document.querySelector< HTMLElement >( '.hero-cinematic' )!;
		await act( async () => {
			stop = startHero( hero, { config } );
		} );
	}
	const field = () =>
		surface === 'home'
			? document.querySelector< HTMLTextAreaElement >( '.hero-prompt' )!
			: screen.getByRole< HTMLTextAreaElement >( 'textbox', {
					name: 'Ask Genie',
				} );
	await waitFor( () => expect( field() ).not.toBeDisabled() );
	return {
		field,
		send: () =>
			surface === 'home'
				? document.querySelector( '.hero-send' )!
				: screen.getByRole( 'button', { name: 'Send' } ),
	};
}

for ( const surface of [ 'dock', 'home' ] as const ) {
	test( `${ surface }: successful resubmit of quota-returned text consumes its original attempt`, async () => {
		let resolve!: ( value: typeof answer ) => void;
		vi.mocked( sendTurn )
			.mockRejectedValueOnce(
				new TurnError( 429, 'linker_admission_quota' )
			)
			.mockImplementationOnce(
				() => new Promise( ( done ) => ( resolve = done ) )
			);
		const ui = await mount( surface );
		fireEvent.input( ui.field(), { target: { value: question } } );
		await act( async () => fireEvent.click( ui.send() ) );
		expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
			'Genie is temporarily unavailable.'
		);
		expect( ui.field().value ).toBe( question );
		expect(
			screen.getByRole( 'link', { name: 'Send an inquiry' } )
		).toHaveAttribute( 'href', '/proforma-request/' );
		const journal = new FailureJournal( sessionStorage, {
			scope,
			persistent: true,
		} );
		const originalAttempt = journal.candidate()!.cursor.owner.attempt;
		await act( async () => fireEvent.click( ui.send() ) );
		await waitFor( () => expect( resolve ).toBeTypeOf( 'function' ) );
		const submittedAttempt = journal.candidate()!.cursor.owner.attempt;
		await act( async () => resolve( answer ) );
		await screen.findAllByText( 'Current authorized answer' );
		expect( sendTurn ).toHaveBeenCalledTimes( 2 );
		expect( submittedAttempt ).toBe( originalAttempt );
		expect( journal.candidate() ).toBeNull();
	} );

	test( `${ surface }: deliberately clearing the quota-returned text consumes that exact original attempt`, async () => {
		vi.mocked( sendTurn ).mockRejectedValueOnce(
			new TurnError( 429, 'linker_admission_quota' )
		);
		const ui = await mount( surface );
		fireEvent.input( ui.field(), { target: { value: question } } );
		await act( async () => fireEvent.click( ui.send() ) );
		await screen.findByRole( 'alert' );
		expect( ui.field().value ).toBe( question );
		const journal = new FailureJournal( sessionStorage, {
			scope,
			persistent: true,
		} );
		expect( journal.candidate()?.record.text ).toBe( question );
		fireEvent.input( ui.field(), { target: { value: '' } } );
		await act( async () =>
			window.dispatchEvent( new Event( 'pagehide' ) )
		);
		expect( ui.field().value ).toBe( '' );
		expect( journal.candidate() ).toBeNull();
		expect( sendTurn ).toHaveBeenCalledTimes( 1 );
	} );
}
