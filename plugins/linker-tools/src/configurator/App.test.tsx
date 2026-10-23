/**
 * The residential flow end to end in the DOM, on the engine's recorded answers.
 */

/**
 * External dependencies
 */
import {
	act,
	fireEvent,
	render,
	screen,
	waitFor,
	within,
} from '@testing-library/react';
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
import { SolutionWriteError, saveSolution } from './api/solutions';
import { App } from './App';
import { EngineError } from './api/engine';

// The account's route (#11) is mocked: these tests assert the states around
// the save, not the request itself (solutions.test.ts holds that contract).
vi.mock( './api/solutions', async ( original ) => ( {
	...( await original< typeof import( './api/solutions' ) >() ),
	saveSolution: vi.fn(),
} ) );
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

test( 'an in-stock solution keeps its In stock badge', async () => {
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	expect( await screen.findAllByText( 'In stock' ) ).toHaveLength( 2 );
	expect( screen.queryByText( 'Currently unavailable' ) ).toBeNull();
} );

test( 'a solution states that a product is currently unavailable', async () => {
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			// The inverter and the battery the recorded answer proposes.
			store={ fakeStore( 'added', [ 3556, 3611 ] ).store }
		/>
	);
	await calculate();
	expect(
		await screen.findAllByText( 'Currently unavailable' )
	).toHaveLength( 2 );
	expect( screen.queryByText( 'In stock' ) ).toBeNull();
} );

test( 'German says a product is currently unavailable', async () => {
	setLocaleData( german.locale_data.messages, 'linker-tools' );
	const { engine } = fakeEngine( { locale: 'de' } );
	render(
		<App
			config={ config( 'de' ) }
			engine={ engine }
			store={ fakeStore( 'added', [ 3556, 3611 ] ).store }
		/>
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
		await screen.findAllByText( 'Derzeit nicht verfügbar' )
	).toHaveLength( 2 );
	expect( screen.queryByText( 'Auf Lager' ) ).toBeNull();
} );

test( 'German keeps the In stock badge for an available solution', async () => {
	setLocaleData( german.locale_data.messages, 'linker-tools' );
	const { engine } = fakeEngine( { locale: 'de' } );
	render(
		<App
			config={ config( 'de' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	fill( /Postleitzahl des Standorts/, '80538' );
	fill( /Jahresverbrauch des Haushalts/, '5000' );
	fill( /PV-Leistung/, '10' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'System berechnen' } )
		);
	} );
	expect( await screen.findAllByText( 'Auf Lager' ) ).toHaveLength( 2 );
	expect( screen.queryByText( 'Derzeit nicht verfügbar' ) ).toBeNull();
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
			'The addition could not be confirmed. The solution draft may already contain these products.'
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
	[ 'unverified', 'Hinzufügen nicht bestätigt.' ],
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
		expect(
			screen.getByText(
				'Das Hinzufügen konnte nicht bestätigt werden. Die Produkte können bereits im Lösungsentwurf stehen.'
			)
		).toBeInTheDocument();
		await act( async () => {
			fireEvent.click(
				screen.getByRole( 'button', { name: 'Lösung speichern' } )
			);
		} );
		expect(
			await screen.findByText( /In Ihrem Konto gespeichert\./ )
		).toBeInTheDocument();
		expect( vi.mocked( saveSolution ) ).toHaveBeenCalledWith(
			'/wp-json/',
			'n',
			expect.objectContaining( { kind: 'residential' } ),
			'de'
		);
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
	expect( save ).toHaveBeenCalledWith(
		'/wp-json/',
		'n',
		expect.objectContaining( { kind: 'residential' } ),
		'en'
	);
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

test( 'the add result and the save result stay separate sentences', async () => {
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
	const addAll = await screen.findByRole( 'button', {
		name: 'Add all to solution draft',
	} );
	await act( async () => {
		fireEvent.click( addAll );
	} );
	await screen.findByText( 'All products are in your solution draft.' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Save solution' } )
		);
	} );
	await screen.findByText( /The solution could not be saved\. Try again\./ );
	const failed = screen
		.getByText( /All products are in your solution draft\./ )
		.closest( 'p' );
	expect( failed?.textContent ).toBe(
		'All products are in your solution draft. The solution could not be saved. Try again.'
	);

	save.mockResolvedValue( { id: 70, url: '/my-account/solutions/70/' } );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Save solution' } )
		);
	} );
	await screen.findByText( /Saved to your account\./ );
	const saved = screen
		.getByText( /All products are in your solution draft\./ )
		.closest( 'p' );
	expect( saved?.textContent ).toBe(
		'All products are in your solution draft. Saved to your account. Open saved solution'
	);
} );

test( 'German keeps the add result and the save result apart', async () => {
	setLocaleData( german.locale_data.messages, 'linker-tools' );
	const save = vi.mocked( saveSolution );
	save.mockRejectedValue( new Error( 'save 403' ) );
	const { engine } = fakeEngine( { locale: 'de' } );
	render(
		<App
			config={ config( 'de' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	fill( /Postleitzahl des Standorts/, '80538' );
	fill( /Jahresverbrauch des Haushalts/, '5000' );
	fill( /PV-Leistung/, '10' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'System berechnen' } )
		);
	} );
	const add = await screen.findByRole( 'button', {
		name: 'Alles zum Lösungsentwurf hinzufügen',
	} );
	await act( async () => {
		fireEvent.click( add );
	} );
	await screen.findByText( 'Alle Produkte sind in Ihrem Lösungsentwurf.' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Lösung speichern' } )
		);
	} );
	await screen.findByText( /Die Lösung konnte nicht gespeichert werden\./ );
	const failed = screen
		.getByText( /Alle Produkte sind in Ihrem Lösungsentwurf\./ )
		.closest( 'p' );
	expect( failed?.textContent ).toBe(
		'Alle Produkte sind in Ihrem Lösungsentwurf. Die Lösung konnte nicht gespeichert werden. Versuchen Sie es erneut.'
	);

	save.mockResolvedValue( { id: 71, url: '/de/mein-konto/solutions/71/' } );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Lösung speichern' } )
		);
	} );
	await screen.findByText( /In Ihrem Konto gespeichert\./ );
	const status = screen
		.getByText( /Alle Produkte sind in Ihrem Lösungsentwurf\./ )
		.closest( 'p' );
	expect( status?.textContent ).toBe(
		'Alle Produkte sind in Ihrem Lösungsentwurf. In Ihrem Konto gespeichert. Gespeicherte Lösung öffnen'
	);
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

// "Ask Genie" on the design report (#496): save first, then open the dock on
// the saved solution. The event is the dock loader's own contract.

function genieAsks() {
	const asks: { message?: string; solution?: number }[] = [];
	const listener = ( event: Event ) => {
		asks.push( ( event as CustomEvent ).detail );
	};
	window.addEventListener( 'linker-genie-ask', listener );
	return {
		asks,
		stop: () => window.removeEventListener( 'linker-genie-ask', listener ),
	};
}

test( 'Ask Genie saves the solution first and opens Genie on it', async () => {
	const save = vi.mocked( saveSolution );
	save.mockResolvedValue( { id: 61, url: '/my-account/solutions/61/' } );
	const asks = genieAsks();
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const ask = await screen.findByRole( 'button', { name: 'Ask Genie' } );
	await act( async () => {
		fireEvent.click( ask );
	} );
	expect( save ).toHaveBeenCalledTimes( 1 );
	expect( asks.asks ).toEqual( [
		{ message: 'What are the figures in my saved solution?', solution: 61 },
	] );
	asks.stop();
} );

test( 'Ask Genie reuses the solution this session already saved', async () => {
	const save = vi.mocked( saveSolution );
	save.mockResolvedValue( { id: 61, url: '/my-account/solutions/61/' } );
	const asks = genieAsks();
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Save solution' } )
		);
	} );
	await screen.findByText( 'Saved to your account.' );
	await act( async () => {
		fireEvent.click( screen.getByRole( 'button', { name: 'Ask Genie' } ) );
	} );
	expect( save ).toHaveBeenCalledTimes( 1 );
	expect( asks.asks ).toEqual( [
		{ message: 'What are the figures in my saved solution?', solution: 61 },
	] );
	asks.stop();
} );

test( 'Ask Genie does not open Genie when the solution could not be saved', async () => {
	const save = vi.mocked( saveSolution );
	save.mockRejectedValue( new Error( 'save 500' ) );
	const asks = genieAsks();
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const ask = await screen.findByRole( 'button', { name: 'Ask Genie' } );
	await act( async () => {
		fireEvent.click( ask );
	} );
	// One sentence, at the report where the customer clicked; the Save
	// status does not repeat it.
	await screen.findByText( 'The solution could not be saved. Try again.' );
	expect(
		screen.getAllByText( 'The solution could not be saved. Try again.' )
	).toHaveLength( 1 );
	expect( asks.asks ).toEqual( [] );
	asks.stop();
} );

test( 'a guest save has no account solution, and the report asks for a sign-in', async () => {
	const save = vi.mocked( saveSolution );
	save.mockResolvedValue( { id: 0, url: '/my-account/saved-solutions/' } );
	const asks = genieAsks();
	const { engine } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const ask = await screen.findByRole( 'button', { name: 'Ask Genie' } );
	await act( async () => {
		fireEvent.click( ask );
	} );
	expect(
		await screen.findByText(
			/Your saved solution stays in this browser for now/
		)
	).toBeInTheDocument();
	expect( screen.getByRole( 'link', { name: 'Sign in' } ) ).toHaveAttribute(
		'href',
		'/my-account/saved-solutions/'
	);
	expect( asks.asks ).toEqual( [] );
	asks.stop();
} );

test( 'German Ask Genie asks in German', async () => {
	setLocaleData( german.locale_data.messages, 'linker-tools' );
	setLocaleData( germanGenie.locale_data.messages, 'linker-tools' );
	const save = vi.mocked( saveSolution );
	save.mockResolvedValue( {
		id: 61,
		url: '/de/mein-konto/gespeicherte-loesungen/',
	} );
	const asks = genieAsks();
	const { engine } = fakeEngine( { locale: 'de' } );
	render(
		<App
			config={ config( 'de' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	fill( /Postleitzahl des Standorts/, '80538' );
	fill( /Jahresverbrauch des Haushalts/, '5000' );
	fill( /PV-Leistung/, '10' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'System berechnen' } )
		);
	} );
	const ask = await screen.findByRole( 'button', { name: 'Genie fragen' } );
	await act( async () => {
		fireEvent.click( ask );
	} );
	expect( asks.asks ).toEqual( [
		{
			message: 'Welche Kennzahlen enthält meine gespeicherte Lösung?',
			solution: 61,
		},
	] );
	asks.stop();
} );

test( 'Ask Genie while a save is in flight awaits that save, not a second one', async () => {
	const save = vi.mocked( saveSolution );
	let finish: ( value: { id: number; url: string } ) => void = () => {
		throw new Error( 'not started' );
	};
	save.mockReturnValue(
		new Promise( ( resolve ) => {
			finish = resolve;
		} )
	);
	const asks = genieAsks();
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
	const askButton = await screen.findByRole( 'button', {
		name: 'Ask Genie',
	} );
	await act( async () => {
		fireEvent.click( saveButton );
		fireEvent.click( askButton );
	} );
	expect( save ).toHaveBeenCalledTimes( 1 );
	await act( async () => {
		finish( { id: 61, url: '/my-account/solutions/61/' } );
	} );
	expect( asks.asks ).toEqual( [
		{ message: 'What are the figures in my saved solution?', solution: 61 },
	] );
	asks.stop();
} );

test( 'a save that resolves after a recalculation is not reused for the new design', async () => {
	const save = vi.mocked( saveSolution );
	let finishOld: ( value: { id: number; url: string } ) => void = () => {
		throw new Error( 'not started' );
	};
	save.mockReturnValueOnce(
		new Promise( ( resolve ) => {
			finishOld = resolve;
		} )
	);
	save.mockResolvedValueOnce( {
		id: 62,
		url: '/my-account/solutions/62/',
	} );
	const asks = genieAsks();
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
	expect( save ).toHaveBeenCalledTimes( 1 );

	// A different design while that save is still in flight.
	fill( /PV array/, '12' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Calculate system' } )
		);
	} );
	await waitFor( () =>
		expect(
			calls.filter( ( call ) => call.name === 'residential' )
		).toHaveLength( 2 )
	);
	// The old save resolves after the new report exists: it must not become
	// the current design's saved solution.
	await act( async () => {
		finishOld( { id: 61, url: '/my-account/solutions/61/' } );
	} );
	expect( screen.queryByText( 'Saved to your account.' ) ).toBeNull();

	const askButton = await screen.findByRole( 'button', {
		name: 'Ask Genie',
	} );
	await act( async () => {
		fireEvent.click( askButton );
	} );
	// A fresh save of the new design, and Genie opens on that one.
	expect( save ).toHaveBeenCalledTimes( 2 );
	expect( asks.asks ).toEqual( [
		{ message: 'What are the figures in my saved solution?', solution: 62 },
	] );
	asks.stop();
} );

test( 'an Ask started before a recalculation does not hand over the previous design', async () => {
	const save = vi.mocked( saveSolution );
	let finishOld: ( value: { id: number; url: string } ) => void = () => {
		throw new Error( 'not started' );
	};
	save.mockReturnValueOnce(
		new Promise( ( resolve ) => {
			finishOld = resolve;
		} )
	);
	save.mockResolvedValueOnce( {
		id: 62,
		url: '/my-account/solutions/62/',
	} );
	const asks = genieAsks();
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const askButton = await screen.findByRole( 'button', {
		name: 'Ask Genie',
	} );
	await act( async () => {
		fireEvent.click( askButton );
	} );
	expect( save ).toHaveBeenCalledTimes( 1 );

	fill( /PV array/, '12' );
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Calculate system' } )
		);
	} );
	await waitFor( () =>
		expect(
			calls.filter( ( call ) => call.name === 'residential' )
		).toHaveLength( 2 )
	);
	await act( async () => {
		finishOld( { id: 61, url: '/my-account/solutions/61/' } );
	} );
	// The old ask resolved after the customer left that design: no handover.
	expect( asks.asks ).toEqual( [] );

	const nextAsk = await screen.findByRole( 'button', {
		name: 'Ask Genie',
	} );
	await act( async () => {
		fireEvent.click( nextAsk );
	} );
	await waitFor( () =>
		expect( asks.asks ).toEqual( [
			{
				message: 'What are the figures in my saved solution?',
				solution: 62,
			},
		] )
	);
	asks.stop();
} );

const CHANGED = 'This solution needs a new calculation before the next step.';
const CURRENT_UNAVAILABLE =
	'The current product data could not be checked. Your entries are still here.';

test.each( [
	[ 'stale', CHANGED ],
	[ 'publication', CURRENT_UNAVAILABLE ],
] as const )(
	'current-product %s failure keeps entries and does not blame the yield service',
	async ( outcome, message ) => {
		const { engine } = fakeEngine( { locale: 'en', residential: outcome } );
		render(
			<App
				config={ config( 'en' ) }
				engine={ engine }
				store={ fakeStore().store }
			/>
		);
		await calculate();
		expect( await screen.findByText( message ) ).toBeInTheDocument();
		expect( screen.getByLabelText( 'Postcode of the site' ) ).toHaveValue(
			'80538'
		);
		expect(
			screen.queryByText(
				'The yield service did not answer. Try again in a minute.'
			)
		).toBeNull();
	}
);

test.each( [
	[
		'stale',
		'Für den nächsten Schritt muss diese Lösung neu berechnet werden.',
	],
	[
		'publication',
		'Die aktuellen Produktdaten konnten nicht geprüft werden. Ihre Angaben bleiben erhalten.',
	],
] as const )(
	'German current-product %s uses the shipped locale and preserves entries',
	async ( outcome, message ) => {
		setLocaleData( german.locale_data.messages, 'linker-tools' );
		const { engine } = fakeEngine( {
			locale: 'de',
			residential: outcome,
		} );
		render(
			<App
				config={ config( 'de' ) }
				engine={ engine }
				store={ fakeStore().store }
			/>
		);
		fill( /Postleitzahl des Standorts/, '80538' );
		fill( /Jahresverbrauch des Haushalts/, '5000' );
		fill( /PV-Leistung/, '10' );
		await act( async () =>
			fireEvent.click(
				screen.getByRole( 'button', { name: 'System berechnen' } )
			)
		);
		expect( await screen.findByText( message ) ).toBeInTheDocument();
		expect(
			screen.getByLabelText( 'Postleitzahl des Standorts' )
		).toHaveValue( '80538' );
	}
);

test( 'German refused atomic add keeps its new-calculation status in the shipped locale', async () => {
	setLocaleData( german.locale_data.messages, 'linker-tools' );
	const { engine, calls } = fakeEngine( { locale: 'de' } );
	const { store, added } = fakeStore( 'stale' );
	render(
		<App config={ config( 'de' ) } engine={ engine } store={ store } />
	);
	fill( /Postleitzahl des Standorts/, '80538' );
	fill( /Jahresverbrauch des Haushalts/, '5000' );
	fill( /PV-Leistung/, '10' );
	await act( async () =>
		fireEvent.click(
			screen.getByRole( 'button', { name: 'System berechnen' } )
		)
	);
	const add = await screen.findByRole( 'button', {
		name: 'Alles zum Lösungsentwurf hinzufügen',
	} );
	await act( async () => fireEvent.click( add ) );
	expect(
		await screen.findByText(
			'Für den nächsten Schritt muss diese Lösung neu berechnet werden.'
		)
	).toBeInTheDocument();
	expect(
		screen.getAllByText( 'Neue Berechnung erforderlich.' )
	).toHaveLength( 2 );
	expect( added ).toEqual( [] );
	expect(
		calls.filter( ( call ) => call.name === 'residential' )
	).toHaveLength( 1 );
} );

test( 'an old result rejected by atomic add asks for a new calculation and adds nothing', async () => {
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	const { store, added } = fakeStore( 'stale' );
	render(
		<App config={ config( 'en' ) } engine={ engine } store={ store } />
	);
	await calculate();
	const add = await screen.findByRole( 'button', {
		name: 'Add all to solution draft',
	} );
	await act( async () => fireEvent.click( add ) );
	expect( await screen.findByText( CHANGED ) ).toBeInTheDocument();
	expect( added ).toEqual( [] );
	expect(
		calls.filter( ( call ) => call.name === 'residential' )
	).toHaveLength( 1 );
	expect(
		screen.queryByText( 'All products are in your solution draft.' )
	).toBeNull();
} );

test( 'a save refused for publication displays re-selection without replacing the screen', async () => {
	vi.mocked( saveSolution ).mockRejectedValue(
		new SolutionWriteError( true )
	);
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	render(
		<App
			config={ config( 'en' ) }
			engine={ engine }
			store={ fakeStore().store }
		/>
	);
	await calculate();
	const save = await screen.findByRole( 'button', { name: 'Save solution' } );
	await act( async () => fireEvent.click( save ) );
	expect( await screen.findByText( CHANGED ) ).toBeInTheDocument();
	expect(
		calls.filter( ( call ) => call.name === 'residential' )
	).toHaveLength( 1 );
	expect(
		screen.queryByText( 'The solution could not be saved. Try again.' )
	).toBeNull();
} );

test.each( [ 'Download PDF', 'Ask Genie' ] )(
	'%s on a stale screen preserves it and asks for re-selection',
	async ( action ) => {
		const { engine, calls } = fakeEngine( { locale: 'en' } );
		engine.reportPdf = vi
			.fn()
			.mockRejectedValue( new EngineError( 'stale' ) );
		render(
			<App
				config={ config( 'en' ) }
				engine={ engine }
				store={ fakeStore().store }
			/>
		);
		await calculate();
		const button = await screen.findByRole( 'button', { name: action } );
		await act( async () => fireEvent.click( button ) );
		expect( await screen.findByText( CHANGED ) ).toBeInTheDocument();
		expect(
			calls.filter( ( call ) => call.name === 'residential' )
		).toHaveLength( 1 );
		expect(
			screen.queryByText( 'The PDF could not be created. Try again.' )
		).toBeNull();
	}
);
