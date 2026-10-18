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
