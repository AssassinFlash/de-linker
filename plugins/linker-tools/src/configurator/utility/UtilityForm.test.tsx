/**
 * Utility-scale projects go to the team as an e-mail with the details.
 */

/**
 * External dependencies
 */
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import { App } from '../App';
import { inquiryLink } from './UtilityForm';

test( 'the inquiry carries every filled field', () => {
	const link = inquiryLink(
		[
			[ 'Site', '06108 Halle' ],
			[ 'Power (MW)', '20' ],
			[ 'Timeline', ' ' ],
		],
		'Utility-scale storage inquiry'
	);
	expect(
		link.startsWith(
			'mailto:sales@de-linker.com?subject=Utility-scale%20storage%20inquiry&body='
		)
	).toBe( true );
	expect( decodeURIComponent( link.split( 'body=' )[ 1 ] ) ).toBe(
		'Site: 06108 Halle\nPower (MW): 20'
	);
} );

test( 'the utility inquiry stays one expanded form addressed to the team', () => {
	render(
		<App
			config={ {
				engineUrl: '',
				restUrl: '/wp-json/',
				restNonce: '',
				locale: 'en',
				openRoof: false,
			} }
			initialSegment="utility"
		/>
	);
	expect(
		screen.getByRole( 'heading', { name: 'Utility-scale inquiry' } )
	).toBeVisible();
	expect( screen.getByLabelText( 'Power (MW)' ) ).toBeVisible();
	expect(
		screen.getByRole( 'link', { name: 'Write to our team' } )
	).toHaveAttribute(
		'href',
		expect.stringMatching( /^mailto:sales@de-linker\.com/ )
	);
} );
