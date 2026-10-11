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
import { App } from './App';

vi.mock( './api/turn', () => ( {
	sendTurn: vi.fn(),
	sendVote: vi.fn( async () => true ),
} ) );
vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'GW10K-ETA' ),
} ) );
import { sendTurn, sendVote } from './api/turn';

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
		locale,
		pageType: 'category',
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		voteUrl: '/wp-json/linker-ai/v1/genie/turn',
		restUrl: '/wp-json/',
		restNonce: 'n',
		disclosure:
			"Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system.",
		accountUrl: '/my-account/',
		pendingAsk: '',
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
