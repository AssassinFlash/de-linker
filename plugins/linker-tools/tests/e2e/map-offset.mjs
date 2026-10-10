/**
 * Where a position sits on the roof step's map when it opens: pixels from the
 * map's centre (the postcode's position) at the opening zoom. The roof tests
 * and the acceptance screenshots click the building the engine's recorded
 * answer reads, so the outline they show is the one under the click.
 */

/** RoofStep.tsx opens at ZOOM - 2. */
export const OPENING_ZOOM = 17;

// Web Mercator; MapLibre's world is 512 px wide at zoom 0.
function project( [ longitude, latitude ], zoom ) {
	const size = 512 * 2 ** zoom;
	const sin = Math.sin( ( latitude * Math.PI ) / 180 );
	return [
		( ( longitude + 180 ) / 360 ) * size,
		( 0.5 - Math.log( ( 1 + sin ) / ( 1 - sin ) ) / ( 4 * Math.PI ) ) *
			size,
	];
}

/**
 * The area centroid of a ring of [longitude, latitude] points.
 *
 * @param {number[][]} ring Closed or open ring.
 * @return {number[]} [longitude, latitude]
 */
function centroid( ring ) {
	let area = 0;
	let x = 0;
	let y = 0;
	ring.forEach( ( [ x1, y1 ], index ) => {
		const [ x2, y2 ] = ring[ ( index + 1 ) % ring.length ];
		const cross = x1 * y2 - x2 * y1;
		area += cross;
		x += ( x1 + x2 ) * cross;
		y += ( y1 + y2 ) * cross;
	} );
	return [ x / ( 3 * area ), y / ( 3 * area ) ];
}

/**
 * Pixels from the map's centre to the middle of the largest roof plane of a
 * recorded roof answer (a point on that building), at the opening zoom.
 *
 * @param {{latitude: number, longitude: number}}              place The postcode's position, the map's centre.
 * @param {{planes: {area_m2: number, polygon: number[][]}[]}} roof  The engine's roof answer.
 * @return {{x: number, y: number}} Offset in CSS pixels.
 */
export function roofClick( place, roof ) {
	const largest = roof.planes.reduce( ( a, b ) =>
		b.area_m2 > a.area_m2 ? b : a
	);
	const [ cx, cy ] = project(
		[ place.longitude, place.latitude ],
		OPENING_ZOOM
	);
	const [ px, py ] = project( centroid( largest.polygon ), OPENING_ZOOM );
	return { x: px - cx, y: py - cy };
}
