/**
 * External dependencies
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { AccountCard } from './AccountCard';
import type { Account } from './types';

const account: Account = {
	id: 17,
	company: 'Review Solar GmbH',
	country: 'Germany',
	businessType: 'Installer',
	contact: 'Maria Example',
	email: 'maria@example.test',
	registered: '2026-10-17 12:00',
	status: 'pending',
	statusLabel: 'Pending review',
	reason: '',
	audit: '',
	fields: [
		{
			key: 'company_website',
			label: 'Company website',
			value: 'https://example.test/legal/',
			website: true,
		},
	],
	signals: [],
	links: [],
	switchUrl: '',
	switchNote: 'User Switching is not active.',
};

test( 'restriction preserves the customer reason after a failure and can be retried', async () => {
	const save = vi
		.fn()
		.mockRejectedValueOnce( new Error( 'Network unavailable' ) )
		.mockResolvedValueOnce( undefined );
	render( <AccountCard account={ account } onSave={ save } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Restrict' } ) );
	const reason = screen.getByRole( 'textbox', {
		name: 'Reason for the customer',
	} );
	fireEvent.change( reason, {
		target: { value: 'Please provide the company website.' },
	} );
	fireEvent.click(
		screen.getByRole( 'button', { name: 'Restrict and notify customer' } )
	);
	await screen.findByText( 'Network unavailable' );
	expect( reason ).toHaveValue( 'Please provide the company website.' );
	fireEvent.click(
		screen.getByRole( 'button', { name: 'Restrict and notify customer' } )
	);
	await screen.findByText( 'Decision saved. You can change it at any time.' );
	expect( save ).toHaveBeenLastCalledWith(
		17,
		'restricted',
		'Please provide the company website.'
	);
} );

test( 'approval sends immediately without a countdown, and controls remain available', async () => {
	const save = vi.fn().mockResolvedValue( undefined );
	render(
		<AccountCard
			account={ {
				...account,
				status: 'rejected',
				reason: 'Old explanation',
			} }
			focused
			onSave={ save }
		/>
	);
	fireEvent.click( screen.getByRole( 'button', { name: 'Approve' } ) );
	await waitFor( () =>
		expect( save ).toHaveBeenCalledWith( 17, 'approved', '' )
	);
	await screen.findByText( 'Decision saved. You can change it at any time.' );
	expect( screen.getByRole( 'button', { name: 'Reject' } ) ).toBeEnabled();
	expect(
		screen.getByRole( 'link', { name: 'https://example.test/legal/' } )
	).toBeVisible();
} );

test( 'blank restriction reason never reaches the save callback', async () => {
	const save = vi.fn();
	render( <AccountCard account={ account } onSave={ save } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Reject' } ) );
	fireEvent.submit( screen.getByRole( 'textbox' ).closest( 'form' )! );
	await screen.findByRole( 'alert' );
	expect( save ).not.toHaveBeenCalled();
} );
