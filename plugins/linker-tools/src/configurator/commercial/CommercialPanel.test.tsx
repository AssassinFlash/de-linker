/**
 * C&I: indicative ranges with an inquiry, or a sizing from the load profile.
 */

/**
 * External dependencies
 */
import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import {
	fakeEngine,
	fakeStore,
	fixtures,
} from '../../../tests/configurator/fakes';
import { App } from '../App';

const config = {
	engineUrl: '',
	restUrl: '/wp-json/',
	restNonce: '',
	locale: 'en' as const,
	openRoof: false,
};

async function run(
	outcome: 'sized' | 'indicative',
	fill: () => Promise< void > = async () => undefined
) {
	const { engine, calls } = fakeEngine( {
		locale: 'en',
		commercial: outcome,
	} );
	render(
		<App
			config={ config }
			engine={ engine }
			store={ fakeStore().store }
			initialSegment="commercial"
		/>
	);
	fireEvent.change( screen.getByLabelText( /Postcode of the site/ ), {
		target: { value: '80538' },
	} );
	fireEvent.change( screen.getByLabelText( /Grid connection capacity/ ), {
		target: { value: '250' },
	} );
	fireEvent.change( screen.getByLabelText( /Annual consumption/ ), {
		target: { value: '380000' },
	} );
	await fill();
	await act( async () => {
		fireEvent.click(
			screen.getByRole( 'button', { name: 'Calculate storage' } )
		);
	} );
	return calls;
}

test( 'without a profile: indicative ranges and an inquiry to the team', async () => {
	const calls = await run( 'indicative' );
	expect( calls[ 0 ].body ).toEqual(
		expect.objectContaining( {
			grid_connection_kva: 250,
			goals: [ 'peak_shaving' ],
		} )
	);
	expect(
		await screen.findByText( 'Usable energy, indicative' )
	).toBeInTheDocument();
	expect(
		screen.getByRole( 'link', { name: 'Send us an inquiry' } )
	).toHaveAttribute(
		'href',
		expect.stringMatching( /^mailto:sales@de-linker\.com/ )
	);
} );

test( 'with a profile: options, the sized battery and systems from the range', async () => {
	const calls = await run( 'sized', async () => {
		fireEvent.change( screen.getByLabelText( /Target peak/ ), {
			target: { value: '150' },
		} );
		const file = new File(
			[ fixtures.loadProfile ],
			'load-profile-15min.csv',
			{ type: 'text/csv' }
		);
		await act( async () => {
			fireEvent.change(
				screen.getByLabelText( /15-minute load profile/ ),
				{ target: { files: [ file ] } }
			);
		} );
		expect(
			await screen.findByText( 'load-profile-15min.csv' )
		).toBeInTheDocument();
	} );
	expect( calls[ 0 ].body ).toEqual(
		expect.objectContaining( {
			target_peak_kw: 150,
			load_profile_unit: 'kW',
			load_profile_csv: fixtures.loadProfile,
		} )
	);
	expect( await screen.findByText( 'Battery power' ) ).toBeInTheDocument();
	expect(
		await screen.findAllByRole( 'link', {
			name: 'GoodWe GW80K-ET-G10 + GW61.4-BAT-AC-G10',
		} )
	).not.toHaveLength( 0 );
	expect(
		screen.getByRole( 'table', {
			name: 'Peak shaving options from your load profile',
		} )
	).toBeInTheDocument();
	expect(
		screen.getByRole( 'heading', { name: 'Systems from our range' } )
	).toBeInTheDocument();
} );

test( 'commercial inputs stay in one expanded form', () => {
	render(
		<App
			config={ config }
			engine={ fakeEngine( { locale: 'en' } ).engine }
			store={ fakeStore().store }
			initialSegment="commercial"
		/>
	);
	expect( screen.getByRole( 'heading', { name: 'Inputs' } ) ).toBeVisible();
	expect( screen.getAllByRole( 'group', { name: 'Goals' } ) ).toHaveLength(
		1
	);
	expect( screen.getByLabelText( 'Peak shaving' ) ).toBeVisible();
	expect(
		screen.getByRole( 'button', { name: 'Calculate storage' } )
	).toBeVisible();
	expect(
		screen.queryByRole( 'button', { name: 'Continue' } )
	).not.toBeInTheDocument();
} );
