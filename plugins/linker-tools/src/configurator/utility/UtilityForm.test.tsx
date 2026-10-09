/**
 * Utility-scale projects go to the team as an e-mail with the details.
 */

/**
 * External dependencies
 */
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
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
