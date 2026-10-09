/**
 * Roof planes as map features, and the words for a plane's facing.
 */

/**
 * WordPress dependencies
 */
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { Ring, RoofPlane } from '../types';

export type PlaneState = 'chosen' | 'usable' | 'excluded';

export interface PlaneFeatures {
	planes: GeoJSON.FeatureCollection;
	modules: GeoJSON.FeatureCollection;
}

function polygon(
	ring: Ring,
	properties: Record< string, unknown >
): GeoJSON.Feature {
	return {
		type: 'Feature',
		properties,
		geometry: { type: 'Polygon', coordinates: [ ring ] },
	};
}

export function outlineFeatures( rings: Ring[] ): GeoJSON.FeatureCollection {
	return {
		type: 'FeatureCollection',
		features: rings.map( ( ring ) => polygon( ring, {} ) ),
	};
}

export function planeFeatures(
	planes: RoofPlane[],
	chosen: Set< number >
): PlaneFeatures {
	const state = ( plane: RoofPlane ): PlaneState => {
		if ( chosen.has( plane.id ) ) {
			return 'chosen';
		}
		return plane.usable ? 'usable' : 'excluded';
	};
	return {
		planes: {
			type: 'FeatureCollection',
			features: planes.map( ( plane ) =>
				polygon( plane.polygon, {
					id: plane.id,
					state: state( plane ),
				} )
			),
		},
		modules: {
			type: 'FeatureCollection',
			features: planes
				.filter( ( plane ) => chosen.has( plane.id ) )
				.flatMap( ( plane ) =>
					plane.module_polygons.map( ( ring ) =>
						polygon( ring, { plane: plane.id } )
					)
				),
		},
	};
}

/**
 * "south", "south-west", ... for a facing in degrees (north 0, east 90).
 * @param azimuth
 */
export function facingName( azimuth: number ): string {
	const names = [
		__( 'north', 'linker-tools' ),
		__( 'north-east', 'linker-tools' ),
		__( 'east', 'linker-tools' ),
		__( 'south-east', 'linker-tools' ),
		__( 'south', 'linker-tools' ),
		__( 'south-west', 'linker-tools' ),
		__( 'west', 'linker-tools' ),
		__( 'north-west', 'linker-tools' ),
	];
	return names[ Math.round( ( ( azimuth % 360 ) + 360 ) / 45 ) % 8 ];
}

export function exclusionText( reason: string | null ): string {
	switch ( reason ) {
		case 'roof_faces_north':
			return __( 'faces north', 'linker-tools' );
		case 'roof_too_steep':
			return __( 'steeper than 60°', 'linker-tools' );
		case 'roof_geometry':
			return __( 'outline cannot be used', 'linker-tools' );
		default:
			return '';
	}
}

export function defaultChoice( planes: RoofPlane[] ): Set< number > {
	return new Set(
		planes.filter( ( p ) => p.usable && p.modules > 0 ).map( ( p ) => p.id )
	);
}

export function totals( planes: RoofPlane[], chosen: Set< number > ) {
	const picked = planes.filter( ( plane ) => chosen.has( plane.id ) );
	return {
		modules: picked.reduce( ( sum, plane ) => sum + plane.modules, 0 ),
		kwp:
			Math.round(
				picked.reduce( ( sum, plane ) => sum + plane.kwp, 0 ) * 100
			) / 100,
		planes: picked,
	};
}

/**
 * Where the chosen planes come from: one official LoD2 plane makes the roof
 * official data, which the report credits under the state's licence.
 *
 * @param picked The chosen planes.
 * @param drawn  Ids of the planes the user drew.
 */
export function roofSource(
	picked: RoofPlane[],
	drawn: Set< number >
): 'lod2' | 'drawn' {
	return picked.some( ( plane ) => ! drawn.has( plane.id ) )
		? 'lod2'
		: 'drawn';
}
