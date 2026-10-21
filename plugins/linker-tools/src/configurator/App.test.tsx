/**
 * The residential flow end to end in the DOM, on the engine's recorded answers.
 */

/**
 * External dependencies
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';

/**
 * WordPress dependencies
 */
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import german from '../../languages/linker-tools-de_DE_formal-ff47dbd6ce1b77b210b406f2367c7ea7.json';
import germanGenie from '../../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';
import { fakeEngine, fakeStore } from '../../tests/configurator/fakes';
import { saveSolution } from './api/solutions';
import { App } from './App';

// The account's route (#11) is mocked: these tests assert the states around
// the save, not the request itself (solutions.test.ts holds that contract).
vi.mock( './api/solutions', () => ( { saveSolution: vi.fn() } ) );
import type { Config } from './config';
import type { Locale } from './types';

function config( locale: Locale ): Config {
	return {
		engineUrl: 'https://engine.test',
		restUrl: '/wp-json/',
		restNonce: 'n',
		locale,
		openRoof: false,
	};
}

function fill( label: RegExp, value: string ) {
	fireEvent.change( screen.getByLabelText( label ), { target: { value } } );
}

async function calculate() {
	fill( /Postcode of the site/, '80538' );
	fill( /Annual household consumption/, '5000' );
	fill( /PV array/, '10' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Calculate system' } )
		);
	} );
}

afterEach( () => {
	resetLocaleData( {}, 'linker-tools' );
} );

test( 'a size-hint mount fills the named residential fields and leaves the rest at their defaults', () => {
	const { engine } = fakeEngine( { locale: 'en' } );
	const { store } = fakeStore();
	render(
		<App
			config={ {
				...config( 'en' ),
				defaults: {
					pv_kwp: '10',
					annual_kwh: '4500',
					backup: 'needed',
					plz: '80538',
				},
			} }
			engine={ engine }
			store={ store }
		/>
	);

	expect( screen.getByLabelText( 'Postcode of the site' ) ).toHaveValue(
		'80538'
	);
	expect(
		screen.getByLabelText( /Annual household consumption/ )
	).toHaveValue( '4500' );
	expect( screen.getByLabelText( /PV array/ ) ).toHaveValue( '10' );
	expect( screen.getByLabelText( 'Three-phase' ) ).toBeChecked();
	expect( screen.getByLabelText( 'Single-phase' ) ).not.toBeChecked();
	expect( screen.getByLabelText( 'Backup supply' ) ).toHaveValue( 'needed' );
	expect(
		screen.getByLabelText( 'Heat pump (installed or planned)' )
	).not.toBeChecked();
} );

test( 'a plain visit leaves the residential defaults unchanged', () => {
	const { engine } = fakeEngine( { locale: 'en' } );
	const { store } = fakeStore();
	render(
		<App config={ config( 'en' ) } engine={ engine } store={ store } />
	);

	expect( screen.getByLabelText( 'Postcode of the site' ) ).toHaveValue( '' );
	expect(
		screen.getByLabelText( /Annual household consumption/ )
	).toHaveValue( '' );
	expect( screen.getByLabelText( /PV array/ ) ).toHaveValue( '' );
	expect( screen.getByLabelText( 'Three-phase' ) ).toBeChecked();
	expect( screen.getByLabelText( 'Backup supply' ) ).toHaveValue( 'none' );
} );

test( 'a household becomes a released system with its report', async () => {
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	const { store, added } = fakeStore();
	render(
		<App config={ config( 'en' ) } engine={ engine } store={ store } />
	);
	await calculate();

	expect( calls[ 0 ] ).toEqual( {
		name: 'residential',
		body: expect.objectContaining( {
			plz: '80538',
			annual_kwh: 5000,
			pv_kwp: 10,
			phase: 3,
			locale: 'en',
		} ),
	} );
	const products = await screen.findByRole( 'heading', {
		name: 'Linker products',
	} );
	expect( products ).toBeVisible();
	const cards = screen.getAllByRole( 'article' );
	expect(
		within( cards[ 0 ] ).getByText( 'Hybrid inverter' )
	).toBeInTheDocument();
	expect(
		within( cards[ 1 ] ).getByText( 'Released by the manufacturer' )
	).toBeInTheDocument();
	expect(
		screen.getByRole( 'heading', { name: 'Design report' } )
	).toBeInTheDocument();
	expect(
		screen.getByRole( 'heading', { name: 'Bill of materials' } )
	).toBeInTheDocument();
	expect(
		screen.getAllByRole( 'link', {
			name: 'GW_ESA-5-30kW_Datasheet-EN.pdf',
		} )[ 0 ]
	).toHaveAttribute(
		'href',
		'https://de-linker.com/wp-content/uploads/2026/09/GW_ESA-5-30kW_Datasheet-EN.pdf'
	);
	const installer = screen.getAllByRole( 'table' )[ 0 ];
	expect( within( installer ).getAllByRole( 'cell' )[ 0 ] ).toHaveAttribute(
		'data-label',
		'Item'
	);

	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Add all to solution draft' } )
		);
	} );
	expect(
		await screen.findByText( 'All products are in your solution draft.' )
	).toBeInTheDocument();
	expect( added.map( ( line ) => line.quantity ) ).toEqual( [ 1, 1 ] );
	for ( const card of screen.getAllByRole( 'article' ) ) {
		expect( within( card ).getByRole( 'status' ) ).toHaveTextContent(
			'In your solution draft'
		);
	}
} );

test( 'a draft that does not confirm shows it in the cards', async () => {
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore( 'unverified' ).store }
		/>
	);
	await calculate();
	const add = await screen.findByRole( 'button', {
		name: 'Add all to solution draft',
	} );
	await act( async () => {
		fireEvent.click( add );
	} );
	expect(
		await screen.findByText(
			'Some products are not confirmed in your solution draft. See the cards above.'
		)
	).toBeInTheDocument();
} );

test( 'swapping the inverter asks the engine for that inverter', async () => {
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const select = await screen.findByLabelText( 'Other inverter' );
	const other = within( select ).getAllByRole(
		'option'
	)[ 1 ] as HTMLOptionElement;
	await act( async () => {
		fireEvent.change( select, { target: { value: other.value } } );
	} );
	expect( calls.at( -1 )?.body ).toEqual(
		expect.objectContaining( { inverter_id: Number( other.value ) } )
	);
} );

test( 'no candidate explains the excluding rules and what to relax', async () => {
	const { engine } = fakeEngine( { locale: 'en', residential: 'none' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	expect(
		await screen.findByText( 'No system in our range meets every rule' )
	).toBeInTheDocument();
	expect(
		screen.getByText( 'What would change the result:' )
	).toBeInTheDocument();
} );

test( 'an unavailable yield service offers a retry', async () => {
	const { engine, calls } = fakeEngine( {
		locale: 'en',
		residential: 'unavailable',
	} );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	expect(
		await screen.findByText(
			'The yield service did not answer. Try again in a minute.'
		)
	).toBeInTheDocument();
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Try again' } ) );
	} );
	expect(
		calls.filter( ( call ) => call.name === 'residential' )
	).toHaveLength( 2 );
} );

test( 'inputs are checked against the engine schema before any request', async () => {
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	fill( /Postcode of the site/, '8053' );
	fill( /Annual household consumption/, '120' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Calculate system' } )
		);
	} );
	expect(
		screen.getByText( 'Enter a German postcode with five digits.' )
	).toBeInTheDocument();
	expect( screen.getByText( 'Enter at least 500.' ) ).toBeInTheDocument();
	expect( calls ).toHaveLength( 0 );
} );

test( 'German wording comes from the translation file', async () => {
	setLocaleData( german.locale_data.messages, 'linker-tools' );
	const { engine } = fakeEngine( { locale: 'de' } );
	const { store, langs } = fakeStore();
	render(
		<App config={ config( 'de' ) } engine={ engine } store={ store } />
	);
	expect( screen.getByRole( 'heading', { level: 1 } ) ).toHaveTextContent(
		'Lösungskonfigurator'
	);
	fill( /Postleitzahl des Standorts/, '80538' );
	fill( /Jahresverbrauch des Haushalts/, '5000' );
	fill( /PV-Leistung/, '10' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'System berechnen' } )
		);
	} );
	expect(
		await screen.findByRole( 'button', {
			name: 'Alles zum Lösungsentwurf hinzufügen',
		} )
	).toBeInTheDocument();
	expect(
		screen.getByRole( 'heading', { name: 'Auslegungsbericht' } )
	).toBeInTheDocument();
	expect( langs ).toEqual( [ 'de' ] );
} );

test.each( [
	[
		'unverified',
		'Gesendet, aber im Entwurf noch nicht sichtbar. Bitte prüfen Sie den Entwurf.',
	],
	[ 'retry', 'Nicht hinzugefügt. Versuchen Sie es erneut.' ],
] as const )(
	'German configurator keeps its wording alongside Genie (%s)',
	async ( status, wording ) => {
		setLocaleData( german.locale_data.messages, 'linker-tools' );
		setLocaleData( germanGenie.locale_data.messages, 'linker-tools' );
		vi.mocked( saveSolution ).mockResolvedValue( {
			id: 61,
			url: '/de/mein-konto/solutions/61/',
		} );
		const { engine } = fakeEngine( { locale: 'de' } );
		render(
			<App
				config={ config( 'de' ) }
				engine={ engine }
				store={ fakeStore( status ).store }
			/>
		);
		fill( /Postleitzahl des Standorts/, '80538' );
		fill( /Jahresverbrauch des Haushalts/, '5000' );
		fill( /PV-Leistung/, '10' );
		fireEvent.click(
			screen.getByRole( 'button', { name: 'System berechnen' } )
		);
		const add = await screen.findByRole( 'button', {
			name: 'Alles zum Lösungsentwurf hinzufügen',
		} );
		await act( async () => {
			fireEvent.click( add );
		} );
		expect(
			( await screen.findAllByText( wording ) ).length
		).toBeGreaterThan( 0 );
		await act( async () => {
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Lösung speichern' } )
			);
		} );
		expect(
			await screen.findByText( /In Ihrem Konto gespeichert\./ )
		).toBeInTheDocument();
	}
);

test( 'a saved solution names the account and links to it', async () => {
	const save = vi.mocked( saveSolution );
	save.mockResolvedValue( { id: 61, url: '/my-account/solutions/61/' } );
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const saveButton = await screen.findByRole( 'button', {
		name: 'Save solution',
	} );
	await act( async () => {
		fireEvent.click( saveButton );
	} );
	expect(
		await screen.findByText( 'Saved to your account.' )
	).toBeInTheDocument();
	expect(
		screen.getByRole( 'link', { name: 'Open saved solution' } )
	).toHaveAttribute( 'href', '/my-account/solutions/61/' );
	expect( save ).toHaveBeenCalledTimes( 1 );
	const body = save.mock.calls[ 0 ][ 2 ];
	expect( body ).toEqual(
		expect.objectContaining( { kind: 'residential' } )
	);
	const reportPdf = body.reportPdf;
	expect( reportPdf ).toBeInstanceOf( Blob );
	if ( ! reportPdf ) {
		throw new Error( 'missing report' );
	}
	expect( await reportPdf.text() ).toBe( '%PDF-1.4' );
	expect( calls ).toContainEqual( {
		name: 'pdf',
		body: {
			input: expect.objectContaining( { plz: '80538' } ),
			logo: null,
		},
	} );
} );

test( 'a design report that cannot be built is not saved without it', async () => {
	const save = vi.mocked( saveSolution );
	const { engine } = fakeEngine( { locale: 'en' } );
	engine.reportPdf = vi.fn().mockRejectedValue( new Error( 'pdf' ) );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const saveButton = await screen.findByRole( 'button', {
		name: 'Save solution',
	} );
	await act( async () => {
		fireEvent.click( saveButton );
	} );
	expect(
		await screen.findByText( 'The solution could not be saved. Try again.' )
	).toBeInTheDocument();
	expect( save ).not.toHaveBeenCalled();
} );

test( 'a refused save says so and can be tried again', async () => {
	const save = vi.mocked( saveSolution );
	save.mockRejectedValue( new Error( 'save 403' ) );
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const saveButton = await screen.findByRole( 'button', {
		name: 'Save solution',
	} );
	await act( async () => {
		fireEvent.click( saveButton );
	} );
	expect(
		await screen.findByText( 'The solution could not be saved. Try again.' )
	).toBeInTheDocument();
	save.mockClear();
	save.mockResolvedValue( { id: 62, url: '/my-account/solutions/62/' } );
	await act( async () => {
		fireEvent.click( saveButton );
	} );
	expect(
		await screen.findByText( 'Saved to your account.' )
	).toBeInTheDocument();
} );
