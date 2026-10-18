/** Presentation only: the complete answer exists before its visual reveal. */
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { Reply } from './Reply';

afterEach( () => {
	vi.unstubAllGlobals();
	vi.useRealTimers();
} );

test( 'a received answer can be revealed gradually or shown immediately without losing its formatting', () => {
	vi.useFakeTimers();
	vi.stubGlobal( 'matchMedia', () => ( { matches: false } ) );
	render(
		<Reply
			text={
				'Choose the **hybrid inverter**.\n\n- Phase\n- Battery compatibility'
			}
			animate
		/>
	);
	const reveal = screen.getByTestId( 'reply-reveal' );
	expect( reveal ).not.toHaveTextContent( 'Battery compatibility' );
	act( () => vi.advanceTimersByTime( 100 ) );
	expect( reveal.textContent!.length ).toBeGreaterThan( 2 );
	fireEvent.click(
		screen.getByRole( 'button', { name: 'Show full response' } )
	);
	act( () => vi.advanceTimersByTime( 100 ) );
	expect( screen.getByText( 'hybrid inverter' ).tagName ).toBe( 'STRONG' );
	expect( screen.getByRole( 'list' ).children ).toHaveLength( 2 );
	expect(
		screen.queryByRole( 'button', { name: 'Show full response' } )
	).toBeNull();
} );

test( 'reduced motion shows the whole response without a reveal control', () => {
	vi.stubGlobal( 'matchMedia', () => ( { matches: true } ) );
	render( <Reply text="The complete answer." animate /> );
	expect( screen.getByText( 'The complete answer.' ) ).toBeVisible();
	expect(
		screen.queryByRole( 'button', { name: 'Show full response' } )
	).toBeNull();
} );
