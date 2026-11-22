import { render, screen, within, fireEvent } from '@testing-library/react';
import { expect, test, vi, afterEach } from 'vitest';
import { Compare } from './components/Compare';

afterEach( () => vi.unstubAllGlobals() );

test( 'a verified comparison shows real specs by equipment class and adds the signed quantity', async () => {
	const presentation = {
		model: 'H2-10K-T3',
		brand: 'SAJ',
		series: 'SAJ H2',
		image: '',
		sku: 'DLK-SAJ-H210KT3',
		in_stock: true,
		price_reason: 'login',
		price_line: '',
		datasheet: { url: '/manual.pdf', title: 'H2 technical data' },
		storage: [
			{
				model: 'Battery A',
				verdict: 'released_with_accessory',
				accessories: [ 'Control unit' ],
				conditions: [
					'Install the controller.',
					'Keep the matching cable.',
				],
			},
			{
				model: 'Battery B',
				verdict: 'released_with_accessory',
				accessories: [ 'Control unit' ],
				conditions: [ 'Install the controller.' ],
			},
		],
	};
	const fetcher = vi.fn( async () => ( {
		ok: true,
		json: async () => ( {
			products: [
				{
					product_id: 1,
					title: 'Hybrid inverter',
					url: '/inverter',
					facts: { device_class: 'inverters' },
					presentation,
				},
				{
					product_id: 2,
					title: 'Battery',
					url: '/battery',
					facts: { device_class: 'battery-systems' },
					presentation: {
						...presentation,
						model: 'BU2',
						sku: 'DLK-BU2',
						in_stock: false,
					},
				},
			],
			rows: [
				{
					field: 'ac_power_kw',
					label: 'Rated AC power (kW)',
					values: { 1: 10, 2: 'unknown' },
				},
				{
					field: 'usable_kwh',
					label: 'Usable energy (kWh)',
					values: { 1: 'unknown', 2: 5 },
				},
			],
		} ),
	} ) );
	vi.stubGlobal( 'fetch', fetcher );
	const add = vi.fn();
	render(
		<Compare
			products={ [ 1, 2 ] }
			restUrl="/wp-json/"
			nonce="test"
			locale="en"
			proofs={ { 1: 'signed' } }
			quantities={ { 1: 3 } }
			statusFor={ () => ( { state: 'idle', text: '' } ) }
			onAdd={ add }
		/>
	);
	const tables = await screen.findAllByRole( 'table' );
	expect( tables ).toHaveLength( 2 );
	const batteries = within( tables[ 0 ] );
	expect(
		batteries.getAllByText( 'Install the controller.', { exact: false } )
	).toHaveLength( 1 );
	expect(
		batteries
			.getByText( 'Keep the matching cable.', { exact: false } )
			.closest( 'li' )
	).toHaveTextContent( 'Battery A' );
	expect( within( tables[ 0 ] ).getByText( 'SAJ · H2' ) ).toBeVisible();
	expect( within( tables[ 0 ] ).getByText( '10' ) ).toBeVisible();
	expect(
		within( tables[ 0 ] ).queryByText( 'Usable energy (kWh)' )
	).toBeNull();
	expect(
		within( tables[ 1 ] ).getByText( 'Currently unavailable' )
	).toBeVisible();
	expect(
		within( tables[ 1 ] ).queryByText( 'Rated AC power (kW)' )
	).toBeNull();
	expect(
		within( tables[ 0 ] ).getByRole( 'link', { name: /Datasheet/ } )
	).toHaveAttribute( 'href', '/manual.pdf' );
	expect(
		within( tables[ 0 ] ).getByText( 'Net price after sign-in' )
	).toBeVisible();
	fireEvent.click(
		within( tables[ 0 ] ).getByRole( 'button', { name: /Add to draft/ } )
	);
	expect( add ).toHaveBeenCalledWith( 1, 3 );
	expect(
		within( tables[ 1 ] ).queryByRole( 'button', { name: /Add to draft/ } )
	).toBeNull();
	expect( fetcher ).toHaveBeenCalledTimes( 1 );
	expect( fetcher.mock.calls[ 0 ] ).toEqual( [
		expect.stringContaining( 'linker/compare-products/run' ),
		expect.objectContaining( { headers: { 'X-WP-Nonce': 'test' } } ),
	] );
} );

test( 'a withdrawn comparison needs no retry and sends no incomplete product request', () => {
	const fetcher = vi.fn();
	vi.stubGlobal( 'fetch', fetcher );
	render(
		<Compare
			products={ [] }
			locale="en"
			restUrl="/wp-json/"
			nonce="n"
			proofs={ {} }
			quantities={ {} }
			statusFor={ () => ( { state: 'idle', text: '' } ) }
			onAdd={ vi.fn() }
		/>
	);
	expect(
		screen.getByText(
			'These products are no longer available for comparison.'
		)
	).toBeVisible();
	expect( screen.queryByRole( 'button', { name: 'Try again' } ) ).toBeNull();
	expect( fetcher ).not.toHaveBeenCalled();
} );
