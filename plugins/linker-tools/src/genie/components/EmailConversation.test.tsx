/** Pending security checks acknowledge storage without claiming delivery or inviting duplicates. */
import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { EmailConversation, LinkResult } from './EmailConversation';

test( 'a pending copy is a status and does not permit another request', () => {
	const start = vi.fn();
	render(
		<EmailConversation
			phase="pending"
			to="tester@example.test"
			limit={ 3 }
			onStart={ start }
			onCancel={ vi.fn() }
			onSend={ vi.fn() }
		/>
	);
	expect( screen.getByRole( 'status' ) ).toHaveTextContent(
		'Your email request is saved and awaiting automatic checks. You do not need to submit it again.'
	);
	const button = screen.getByRole( 'button', {
		name: 'Email me this conversation',
	} );
	expect( button ).toBeDisabled();
	fireEvent.click( button );
	expect( start ).not.toHaveBeenCalled();
	expect( screen.queryByText( /is on its way/ ) ).not.toBeInTheDocument();
} );

test( 'a confirmed address also acknowledges pending checks without claiming dispatch', () => {
	render( <LinkResult outcome="pending" /> );
	expect( screen.getByRole( 'status' ) ).toHaveTextContent(
		'Your email request is saved and awaiting automatic checks.'
	);
	expect( screen.queryByRole( 'alert' ) ).not.toBeInTheDocument();
	expect( screen.queryByText( /is on its way/ ) ).not.toBeInTheDocument();
} );
