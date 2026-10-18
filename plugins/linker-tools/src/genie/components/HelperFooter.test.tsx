/** The helper's quiet AI note keeps support routes in a native disclosure. */
import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import { HelperFooter } from './HelperFooter';

for ( const german of [ false, true ] ) {
	test( `the ${ german ? 'German' : 'English' } footer keeps its links behind Help & privacy`, () => {
		render(
			<HelperFooter german={ german } disclosure="Full AI disclosure." />
		);
		expect( screen.getByText( 'Genie is an AI assistant.' ) ).toBeVisible();
		expect(
			screen.getByRole( 'link', { name: 'FAQ & Downloads' } )
		).not.toBeVisible();
		fireEvent.click( screen.getByText( 'Help & privacy' ) );
		expect(
			screen.getByRole( 'link', { name: 'FAQ & Downloads' } )
		).toHaveAttribute(
			'href',
			german ? '/de/faq-download/' : '/faq-download/'
		);
		expect(
			screen.getByRole( 'link', { name: 'Contact Linker' } )
		).toHaveAttribute( 'href', german ? '/de/kontakt/' : '/contact/' );
		expect(
			screen.getByRole( 'link', { name: 'Privacy Policy' } )
		).toHaveAttribute(
			'href',
			german ? '/de/datenschutz/' : '/privacy-policy/'
		);
	} );
}

test( 'Escape closes the support menu and restores its trigger focus', () => {
	render(
		<HelperFooter german={ false } disclosure="Full AI disclosure." />
	);
	const summary = screen.getByText( 'Help & privacy' );
	fireEvent.click( summary );
	fireEvent.keyDown( screen.getByRole( 'link', { name: 'Privacy Policy' } ), {
		key: 'Escape',
	} );
	expect(
		screen.getByRole( 'link', { name: 'Privacy Policy' } )
	).not.toBeVisible();
	expect( summary ).toHaveFocus();
} );
