/**
 * The click that finishes a drawn plane closes the polygon in TerraDraw's
 * canvas pointerup listener and then arrives at MapLibre as a click, after
 * the finish handler has turned the mode static. That click must not select
 * the building under it; the next genuine click still selects.
 *
 * jsdom has neither pointer events nor MapLibre's loop, so the test dispatches
 * the pointer events and the fake adapter closes the polygon on pointerup the
 * way TerraDraw does; the acceptance walk owns that ordering premise.
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
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { fakeEngine } from '../../../tests/configurator/fakes';
import { EngineError } from '../api/engine';
import type { RoofPlane } from '../types';
import { RoofStep } from './RoofStep';

interface ClickEvent {
	lngLat: { lat: number; lng: number };
	originalEvent: MouseEvent;
}

const harness = vi.hoisted( () => {
	class FakeMap {
		readonly canvas: HTMLCanvasElement;
		readonly fitBounds = vi.fn();
		readonly sources = new Map<
			string,
			{ setData: ( data: unknown ) => void }
		>();
		private readonly listeners = new Map<
			string,
			Array< ( event: ClickEvent ) => void >
		>();

		constructor( options: { container: HTMLElement } ) {
			this.canvas = document.createElement( 'canvas' );
			options.container.append( this.canvas );
			for ( const id of [ 'outline', 'planes', 'modules' ] ) {
				this.sources.set( id, { setData: vi.fn() } );
			}
			instances.push( this );
		}

		on( name: string, callback: ( event: ClickEvent ) => void ) {
			const listeners = this.listeners.get( name ) ?? [];
			listeners.push( callback );
			this.listeners.set( name, listeners );
		}

		once() {}

		addControl() {}

		remove() {}

		getCanvas() {
			return this.canvas;
		}

		getSource( id: string ) {
			return this.sources.get( id );
		}

		emit( name: string, event: ClickEvent ) {
			for ( const callback of this.listeners.get( name ) ?? [] ) {
				callback( event );
			}
		}
	}

	class FakeAdapter {
		readonly map: FakeMap;

		constructor( options: { map: FakeMap } ) {
			this.map = options.map;
		}
	}

	type FinishHandler = (
		id: string,
		event: { mode: string; action: string }
	) => void;

	class FakeTerraDraw {
		mode = 'static';
		snapshot: Array< {
			id: string;
			geometry: { type: string; coordinates: number[][][] };
		} > = [];
		private readonly canvas: HTMLCanvasElement;
		private readonly handlers = new Map< string, FinishHandler >();
		private armed: string | null = null;
		// The adapter binds its listeners to the map canvas; the app's capture
		// listener on the same canvas therefore sees the pointerup first.
		private readonly onPointerUp = () => {
			if ( this.armed ) {
				const id = this.armed;
				this.armed = null;
				this.finish( id );
			}
		};

		constructor( options: { adapter: FakeAdapter } ) {
			this.canvas = options.adapter.map.getCanvas();
			terras.push( this );
		}

		start() {
			this.canvas.addEventListener( 'pointerup', this.onPointerUp );
		}

		stop() {
			this.canvas.removeEventListener( 'pointerup', this.onPointerUp );
		}

		clear() {}

		on( name: string, callback: FinishHandler ) {
			this.handlers.set( name, callback );
		}

		getMode() {
			return this.mode;
		}

		setMode( mode: string ) {
			this.mode = mode;
		}

		getSnapshot() {
			return this.snapshot;
		}

		/**
		 * Marks the next pointerup as the one that closes the polygon.
		 *
		 * @param id The feature id the finish handler receives.
		 */
		arm( id: string ) {
			this.armed = id;
		}

		/**
		 * What terra-draw calls from its canvas pointerup listener.
		 *
		 * @param id The finished feature's id.
		 */
		finish( id: string ) {
			this.handlers.get( 'finish' )?.( id, {
				mode: 'polygon',
				action: 'draw',
			} );
		}
	}

	const maps: FakeMap[] = [];
	const instances = maps;
	const terras: FakeTerraDraw[] = [];
	return { FakeAdapter, FakeMap, FakeTerraDraw, maps, terras };
} );

vi.mock( 'maplibre-gl', () => ( {
	Map: harness.FakeMap,
	LngLatBounds: class {
		extend() {}
	},
	NavigationControl: class {},
} ) );

vi.mock( 'terra-draw', () => ( {
	TerraDraw: harness.FakeTerraDraw,
	TerraDrawPolygonMode: class {},
} ) );

vi.mock( 'terra-draw-maplibre-gl-adapter', () => ( {
	TerraDrawMapLibreGLAdapter: harness.FakeAdapter,
} ) );

const DRAWN: RoofPlane = {
	id: 3,
	polygon: [
		[ 11.5885, 48.1401 ],
		[ 11.5886, 48.1401 ],
		[ 11.5886, 48.1402 ],
		[ 11.5885, 48.1401 ],
	],
	tilt_deg: 35,
	azimuth_deg: 180,
	area_m2: 90,
	usable: true,
	excluded_reason: null,
	modules: 20,
	kwp: 9.2,
	module_polygons: [],
};

const RING = [
	[ 11.5885, 48.1401 ],
	[ 11.5886, 48.1401 ],
	[ 11.5886, 48.1402 ],
	[ 11.5885, 48.1401 ],
];

async function mount( pack: () => Promise< RoofPlane > ) {
	const { engine, calls } = fakeEngine( { locale: 'en' } );
	engine.pack = pack;
	render(
		<RoofStep
			plz="80538"
			locale="en"
			engine={ engine }
			onApply={ vi.fn() }
			onClose={ vi.fn() }
		/>
	);
	await screen.findByText(
		'Click the roof of the building in the aerial image.'
	);
	// The ready text commits before the map's passive effect necessarily runs.
	// Wait for this mounted canvas before dispatching pointer events to it.
	await waitFor( () =>
		expect(
			screen.getByRole( 'application' ).querySelector( 'canvas' )
		).toBeInTheDocument()
	);
	const map = harness.maps[ harness.maps.length - 1 ];
	return { calls, engine, map };
}

function startDrawing() {
	fireEvent.click( screen.getByRole( 'button', { name: 'Draw plane' } ) );
	const terra = harness.terras[ harness.terras.length - 1 ];
	terra.snapshot = [
		{ id: 'drawn', geometry: { type: 'Polygon', coordinates: [ RING ] } },
	];
	terra.arm( 'drawn' );
	return terra;
}

function pointer(
	map: InstanceType< typeof harness.FakeMap >,
	x: number,
	y: number
) {
	act( () => {
		map.canvas.dispatchEvent(
			new MouseEvent( 'pointerdown', {
				bubbles: true,
				clientX: x,
				clientY: y,
			} )
		);
		map.canvas.dispatchEvent(
			new MouseEvent( 'pointerup', {
				bubbles: true,
				clientX: x,
				clientY: y,
			} )
		);
	} );
}

function mapClick(
	map: InstanceType< typeof harness.FakeMap >,
	x: number,
	y: number,
	lat: number,
	lng: number
) {
	act( () => {
		map.emit( 'click', {
			lngLat: { lat, lng },
			originalEvent: new MouseEvent( 'click', {
				clientX: x,
				clientY: y,
			} ),
		} );
	} );
}

function roofCalls( calls: { name: string; body: unknown }[] ) {
	return calls.filter( ( call ) => call.name === 'roof' );
}

test( 'the finishing click keeps the drawn plane and the next click selects', async () => {
	const { calls, map } = await mount( async () => DRAWN );

	// A genuine click on the building selects it before drawing starts.
	pointer( map, 120, 120 );
	mapClick( map, 120, 120, 48.1401, 11.5885 );
	await screen.findByText( 'Official building model: Triftstraße 5' );
	expect( roofCalls( calls ) ).toHaveLength( 1 );
	expect(
		screen.getByText( 'Selected: 14 modules, 6.44 kWp' )
	).toBeInTheDocument();

	// The click on the first corner closes the plane inside pointerup, and
	// MapLibre reports the same gesture as a click afterwards.
	startDrawing();
	pointer( map, 200, 200 );
	await screen.findByText( 'The plane you drew is in the list.' );
	mapClick( map, 200, 200, 48.1401, 11.5885 );

	expect( roofCalls( calls ) ).toHaveLength( 1 );
	expect(
		screen.getByText( 'The plane you drew is in the list.' )
	).toBeInTheDocument();
	const planes = screen
		.getByText( 'Facing south, tilt 35°' )
		.closest( 'ul' ) as HTMLElement;
	expect( within( planes ).getAllByRole( 'checkbox' ) ).toHaveLength( 17 );
	expect(
		screen.getByText( 'Selected: 34 modules, 15.64 kWp' )
	).toBeInTheDocument();

	// A new click elsewhere is a roof selection, not part of the drawing.
	pointer( map, 90, 260 );
	mapClick( map, 90, 260, 48.1403, 11.5887 );
	await waitFor( () => expect( roofCalls( calls ) ).toHaveLength( 2 ) );
	expect( roofCalls( calls )[ 1 ].body ).toEqual( {
		plz: '80538',
		latitude: 48.1403,
		longitude: 11.5887,
	} );

	// The time window is bounded: the finishing spot is a selection again
	// once the gesture's half second has passed (600 ms here).
	await new Promise( ( resolve ) => setTimeout( resolve, 600 ) );
	pointer( map, 200, 200 );
	mapClick( map, 200, 200, 48.1401, 11.5885 );
	await waitFor( () => expect( roofCalls( calls ) ).toHaveLength( 3 ) );
} );

test( 'a refused plane keeps its sentence after the finishing click', async () => {
	const { calls, map } = await mount( async () => {
		throw new EngineError( 'invalid' );
	} );

	startDrawing();
	pointer( map, 200, 200 );
	const refusal =
		'Draw the plane on one roof: this one is too large or outside Germany.';
	await screen.findByText( refusal );
	mapClick( map, 200, 200, 48.1401, 11.5885 );

	expect( roofCalls( calls ) ).toHaveLength( 0 );
	expect( screen.getByText( refusal ) ).toBeInTheDocument();

	// The refusal belongs to the drawing, not to the click after it.
	pointer( map, 90, 260 );
	mapClick( map, 90, 260, 48.1403, 11.5887 );
	await waitFor( () => expect( roofCalls( calls ) ).toHaveLength( 1 ) );
} );
