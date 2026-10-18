// @vitest-environment jsdom

/**
 * The home hero's controls (ticket #232): every one of them opens the
 * conversation in place — never a navigation — the close restores the
 * resting hero, and the way back appears once the hero is out of sight and
 * hands the same conversation to the dock.
 */

/**
 * External dependencies
 */
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { Turn, TurnMessage } from '../genie/api/turn';
import type { Upload } from '../genie/attachments/prepare';
import type { GenieConfig } from '../genie/config';
import { startHero } from './controller';
import { HeroSession, type HeroSessionConfig } from './session';

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

const HERO = `
<section class="hero-cinematic">
  <div class="hero-stage">
    <p class="hero-badge">Solar &amp; battery storage</p>
    <h1 class="hero-title">Linking Value.</h1>
    <p class="hero-subtitle">We link storage systems.</p>
    <div class="hero-dialog">
      <textarea class="hero-prompt" placeholder="Search equipment models, battery pairings, or datasheets..." rows="2"></textarea>
      <div class="hero-dialog-footer">
        <button type="button" data-linker-assistant-open="nameplate">Identify by nameplate photo</button>
        <button type="button" data-linker-assistant-open="attach">Attach</button>
        <button type="button" data-linker-assistant-open="voice">Voice</button>
        <a class="hero-send" href="/linker-advisor/">Send</a>
      </div>
    </div>
    <div class="hero-capsules">
      <a class="hero-capsule" href="/linker-advisor/">10 kW storage systems</a>
    </div>
    <p class="hero-footnote">On file.</p>
  </div>
</section>`;

function reply( text: string ): Turn {
	return {
		meta: {
			turn_id: 3,
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
	turnUrl: CONFIG.turnUrl,
	threadUrl: CONFIG.threadUrl,
	nonce: CONFIG.restNonce,
	locale: CONFIG.locale,
	page: CONFIG.page,
};

function session( stored: TurnMessage[] = [] ) {
	const read = vi.fn( async () => ( {
		messages: [ ...stored ],
		turn: null,
	} ) );
	const send = vi.fn(
		async (
			_turnUrl: string,
			_nonce: string,
			_locale: string,
			messages: TurnMessage[],
			_page?: unknown,
			_uploads?: Upload[]
		) => {
			void _page;
			void _uploads;
			return reply( `Answer ${ messages.length }` );
		}
	);
	return {
		session: new HeroSession( SESSION_CONFIG, read, send ),
		read,
		send,
	};
}

function start( heroSession: HeroSession ) {
	const hero = document.querySelector< HTMLElement >( '.hero-cinematic' )!;
	const stop = startHero( hero, { config: CONFIG, session: heroSession } );
	return { hero, stop };
}

beforeEach( () => {
	document.body.innerHTML = HERO;
	window.history.replaceState( null, '', '/' );
} );

afterEach( () => {
	document.body.innerHTML = '';
} );

test( 'the resting hero is left exactly as it was', () => {
	const { hero } = start( session().session );

	expect( hero.classList.contains( 'linker-genie-hero--open' ) ).toBe(
		false
	);
	expect(
		document.querySelector( '.linker-genie-hero__surface' )
	).toBeNull();
	expect( document.querySelector( '.linker-genie-hero-pill' ) ).toBeNull();
} );

test( 'typing and Enter unfolds the conversation in place', async () => {
	const answers = session();
	const { hero } = start( answers.session );
	const prompt =
		document.querySelector< HTMLTextAreaElement >( '.hero-prompt' )!;
	prompt.value = 'saj';

	await act( async () => {
		fireEvent.keyDown( prompt, { key: 'Enter' } );
	} );

	expect( hero.classList.contains( 'linker-genie-hero--open' ) ).toBe( true );
	expect(
		document.querySelector( '.linker-genie-hero__surface' )
	).not.toBeNull();
	await waitFor( () => expect( answers.send ).toHaveBeenCalledTimes( 1 ) );
	expect( answers.send.mock.calls[ 0 ][ 3 ][ 0 ] ).toEqual( {
		role: 'user',
		content: 'saj',
	} );
	expect(
		screen.getByText( "Genie - Linker's AI assistant" )
	).toBeInTheDocument();
} );

test( 'an empty Enter leaves the resting hero alone', async () => {
	const answers = session();
	const { hero } = start( answers.session );

	await act( async () => {
		fireEvent.keyDown( document.querySelector( '.hero-prompt' )!, {
			key: 'Enter',
		} );
	} );

	expect( hero.classList.contains( 'linker-genie-hero--open' ) ).toBe(
		false
	);
	expect( answers.send ).not.toHaveBeenCalled();
} );

test( 'the send button opens in place and never navigates', async () => {
	const answers = session();
	start( answers.session );
	const prompt =
		document.querySelector< HTMLTextAreaElement >( '.hero-prompt' )!;
	prompt.value = 'Which battery pairs with the SAJ?';
	const sendButton =
		document.querySelector< HTMLAnchorElement >( '.hero-send' )!;

	let prevented = false;
	sendButton.addEventListener( 'click', ( event ) => {
		prevented = event.defaultPrevented;
	} );
	await act( async () => {
		fireEvent.click( sendButton );
	} );

	expect( prevented ).toBe( true );
	await waitFor( () => expect( answers.send ).toHaveBeenCalledTimes( 1 ) );
} );

test( 'a capsule opens in place with its own question and never navigates', async () => {
	const answers = session();
	start( answers.session );
	const capsule =
		document.querySelector< HTMLAnchorElement >( '.hero-capsule' )!;

	let prevented = false;
	capsule.addEventListener( 'click', ( event ) => {
		prevented = event.defaultPrevented;
	} );
	await act( async () => {
		fireEvent.click( capsule );
	} );

	expect( prevented ).toBe( true );
	await waitFor( () => expect( answers.send ).toHaveBeenCalledTimes( 1 ) );
	expect( answers.send.mock.calls[ 0 ][ 3 ][ 0 ] ).toEqual( {
		role: 'user',
		content: '10 kW storage systems',
	} );
} );

test( 'the close button restores the resting hero and keeps the conversation', async () => {
	const answers = session( [
		{ role: 'user', content: 'saj' },
		{ role: 'assistant', content: 'Here are the SAJ models.' },
	] );
	const { hero } = start( answers.session );
	await act( async () => {
		fireEvent.click(
			document.querySelector< HTMLAnchorElement >( '.hero-capsule' )!
		);
	} );
	await screen.findByText( 'Here are the SAJ models.' );

	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
	} );

	expect( hero.classList.contains( 'linker-genie-hero--open' ) ).toBe(
		false
	);
	expect(
		document.querySelector( '.linker-genie-hero__surface' )
	).toBeNull();
	expect(
		document.querySelector< HTMLTextAreaElement >( '.hero-prompt' )!
			.placeholder
	).toBe( 'Search equipment models, battery pairings, or datasheets...' );
} );

test( 'out of sight, the way back appears and hands the same conversation to the dock', async () => {
	const answers = session( [
		{ role: 'user', content: 'saj' },
		{ role: 'assistant', content: 'Here are the SAJ models.' },
	] );
	const { hero } = start( answers.session );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) );
	} );
	await waitFor( () => expect( answers.read ).toHaveBeenCalled() );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
	} );

	hero.getBoundingClientRect = () =>
		( {
			bottom: -20,
			top: -600,
			height: 580,
		} ) as DOMRect;
	fireEvent.scroll( window );

	const pill = document.querySelector< HTMLButtonElement >(
		'.linker-genie-hero-pill'
	)!;
	expect( pill ).not.toBeNull();
	expect( pill.hidden ).toBe( false );

	const heard: CustomEvent[] = [];
	const listen = ( event: Event ) => heard.push( event as CustomEvent );
	window.addEventListener( 'linker-genie-ask', listen );
	fireEvent.click( pill );
	window.removeEventListener( 'linker-genie-ask', listen );

	expect( heard ).toHaveLength( 1 );
	expect( heard[ 0 ].detail ).toEqual( {
		refresh: true,
		fromHome: true,
	} );
	expect( answers.send ).not.toHaveBeenCalled();
	expect( hero.classList.contains( 'linker-genie-hero--open' ) ).toBe(
		false
	);
} );

test( 'Continue in the side panel hands over and folds the hero', async () => {
	const answers = session( [
		{ role: 'user', content: 'saj' },
		{ role: 'assistant', content: 'Here are the SAJ models.' },
	] );
	const { hero } = start( answers.session );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) );
	} );
	await waitFor( () => expect( answers.read ).toHaveBeenCalled() );

	const heard: CustomEvent[] = [];
	const listen = ( event: Event ) => heard.push( event as CustomEvent );
	window.addEventListener( 'linker-genie-ask', listen );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'Continue in the side panel',
			} )
		);
	} );
	window.removeEventListener( 'linker-genie-ask', listen );

	expect( heard[ 0 ].detail ).toEqual( {
		refresh: true,
		fromHome: true,
	} );
	expect( hero.classList.contains( 'linker-genie-hero--open' ) ).toBe(
		false
	);
} );

test( 'the nameplate button opens a photo picker and sends the picked photo', async () => {
	const answers = session();
	start( answers.session );
	const click = vi
		.spyOn( HTMLInputElement.prototype, 'click' )
		.mockImplementation( () => undefined );

	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', {
				name: 'Identify by nameplate photo',
			} )
		);
	} );

	expect( click ).toHaveBeenCalledTimes( 1 );
	const input =
		document.querySelector< HTMLInputElement >( 'input[type="file"]' )!;
	expect( input.accept ).toContain( 'image/jpeg' );
	expect( input.accept ).not.toContain( 'application/pdf' );

	const file = new File( [ 'plain text' ], 'notes.txt', {
		type: 'text/plain',
	} );
	Object.defineProperty( input, 'files', {
		configurable: true,
		value: { 0: file, length: 1 },
	} );
	await act( async () => {
		fireEvent.change( input );
	} );

	// A file Genie cannot read is refused before any turn.
	await waitFor( () =>
		expect(
			document.querySelector( '.linker-genie-app__attachment--refused' )
		).not.toBeNull()
	);
	expect( answers.send ).not.toHaveBeenCalled();
	click.mockRestore();
} );

test( 'the attach button opens the file picker and a PDF is sent with the turn', async () => {
	const answers = session();
	start( answers.session );
	vi.spyOn( HTMLInputElement.prototype, 'click' ).mockImplementation(
		() => undefined
	);

	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Attach' } ) );
	} );

	const input =
		document.querySelector< HTMLInputElement >( 'input[type="file"]' )!;
	expect( input.accept ).toContain( 'application/pdf' );
	const file = new File( [ '%PDF-1.4\n%%EOF' ], 'datasheet.pdf', {
		type: 'application/pdf',
	} );
	Object.defineProperty( input, 'files', {
		configurable: true,
		value: { 0: file, length: 1 },
	} );
	await act( async () => {
		fireEvent.change( input );
	} );

	await waitFor( () => expect( answers.send ).toHaveBeenCalledTimes( 1 ) );
	const [ , , , messages, , uploads ] = answers.send.mock.calls[ 0 ];
	expect( messages[ messages.length - 1 ] ).toEqual( {
		role: 'user',
		content: 'Attached: datasheet.pdf',
	} );
	expect( uploads ).toHaveLength( 1 );
} );

test( 'the voice button opens the conversation in place', async () => {
	const answers = session();
	const { hero } = start( answers.session );

	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) );
	} );

	expect( hero.classList.contains( 'linker-genie-hero--open' ) ).toBe( true );
	expect(
		document.querySelector( '.linker-genie-hero__surface' )
	).not.toBeNull();
	expect( answers.send ).not.toHaveBeenCalled();
} );

test( 'the dock opening hides the way back until it closes again', async () => {
	const answers = session( [
		{ role: 'user', content: 'saj' },
		{ role: 'assistant', content: 'Here are the SAJ models.' },
	] );
	const { hero } = start( answers.session );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Voice' } ) );
	} );
	await waitFor( () => expect( answers.read ).toHaveBeenCalled() );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Close' } ) );
	} );
	hero.getBoundingClientRect = () =>
		( { bottom: -20, top: -600, height: 580 } ) as DOMRect;
	fireEvent.scroll( window );
	const pill = document.querySelector< HTMLButtonElement >(
		'.linker-genie-hero-pill'
	)!;
	expect( pill.hidden ).toBe( false );

	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-state', {
				detail: { open: true },
			} )
		);
	} );
	expect( pill.hidden ).toBe( true );

	await act( async () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-state', {
				detail: { open: false },
			} )
		);
	} );
	expect( pill.hidden ).toBe( false );
} );
