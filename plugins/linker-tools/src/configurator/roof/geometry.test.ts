/**
 * Roof planes on the map and in the panel.
 */

/**
 * External dependencies
 */
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import { fixtures } from '../../../tests/configurator/fakes';
import { defaultChoice, facingName, planeFeatures, totals } from './geometry';

const roof = fixtures.roof.en;

test( 'usable planes with modules are chosen first', () => {
	const chosen = defaultChoice( roof.planes );
	expect(
		[ ...chosen ].every(
			( id ) => roof.planes.find( ( p ) => p.id === id )!.usable
		)
	).toBe( true );
	expect( totals( roof.planes, chosen ).modules ).toBe( roof.modules );
} );

test( 'only chosen planes show their modules', () => {
	const chosen = defaultChoice( roof.planes );
	const features = planeFeatures( roof.planes, chosen );
	const expected = roof.planes
		.filter( ( p ) => chosen.has( p.id ) )
		.reduce( ( sum, p ) => sum + p.modules, 0 );
	expect( features.modules.features ).toHaveLength( expected );
	expect(
		features.planes.features.map( ( f ) => f.properties?.state )
	).toContain( 'excluded' );
} );

test.each( [
	[ 0, 'north' ],
	[ 99.5, 'east' ],
	[ 190, 'south' ],
	[ 279.5, 'west' ],
	[ 225, 'south-west' ],
] )( 'facing %s° reads %s', ( azimuth, name ) => {
	expect( facingName( azimuth ) ).toBe( name );
} );
