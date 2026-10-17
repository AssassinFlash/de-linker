/**
 * A document block is a link with its label, never a URL in the text (#233).
 */

/**
 * External dependencies
 */
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import { DocumentLink } from './DocumentLink';

const PDF = 'https://de-linker.test/uploads/SAJ-H2-user-manual.pdf';

test( 'the document opens at its page in a new tab', () => {
	render(
		<DocumentLink
			block={ {
				type: 'document',
				ref: 'c1',
				label: 'SAJ H2 user manual · p. 42',
				url: `${ PDF }#page=42`,
			} }
		/>
	);
	const link = screen.getByRole( 'link', {
		name: 'SAJ H2 user manual · p. 42',
	} );
	expect( link.getAttribute( 'href' ) ).toBe( `${ PDF }#page=42` );
	expect( link.getAttribute( 'target' ) ).toBe( '_blank' );
	expect( link.getAttribute( 'rel' ) ).toBe( 'noopener noreferrer' );
} );

test( 'an unhydrated document renders nothing', () => {
	const { container } = render(
		<DocumentLink
			block={ { type: 'document', ref: 'c1', label: null, url: null } }
		/>
	);
	expect( container.innerHTML ).toBe( '' );
} );
