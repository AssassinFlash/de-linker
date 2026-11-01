import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { CopyReply } from './CopyReply';

test( 'Copy response copies the complete original answer and confirms success', async () => {
	const writeText = vi.fn( async () => undefined );
	Object.defineProperty( navigator, 'clipboard', {
		configurable: true,
		value: { writeText },
	} );
	render( <CopyReply text="The **complete** response." /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Copy response' } ) );
	expect( await screen.findByRole( 'status' ) ).toHaveTextContent( 'Copied' );
	expect( writeText ).toHaveBeenCalledWith( 'The **complete** response.' );
} );

test( 'Copy question explains how to recover when clipboard access fails', async () => {
	const writeText = vi.fn( async () => {
		throw new Error( 'clipboard unavailable' );
	} );
	Object.defineProperty( navigator, 'clipboard', {
		configurable: true,
		value: { writeText },
	} );
	render( <CopyReply text="The question stays in the composer." question /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Copy question' } ) );
	expect( await screen.findByRole( 'status' ) ).toHaveTextContent(
		'Copy failed. Select the text and copy it manually.'
	);
	expect( writeText ).toHaveBeenCalledWith(
		'The question stays in the composer.'
	);
} );
