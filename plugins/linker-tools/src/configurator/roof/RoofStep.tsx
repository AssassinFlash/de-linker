/**
 * The roof step: the state's official aerial image, a click on the roof, the
 * official LoD2 outline with its planes, and the modules that fit. Where no
 * outline exists, the user draws the plane and gives its tilt and facing.
 */

/**
 * External dependencies
 */
import {
	LngLatBounds,
	Map as MapLibreMap,
	NavigationControl,
	type GeoJSONSource,
	type MapMouseEvent,
} from 'maplibre-gl';
import { TerraDraw, TerraDrawPolygonMode } from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';
import 'maplibre-gl/dist/maplibre-gl.css';

/**
 * WordPress dependencies
 */
import { useEffect, useRef, useState } from '@wordpress/element';
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { EngineError, type EngineClient } from '../api/engine';
import { formatNumber } from '../format';
import type { RoofSelection } from '../residential/ResidentialForm';
import type { Locale, Place, RoofPlane, RoofResult } from '../types';
import {
	defaultChoice,
	exclusionText,
	facingName,
	outlineFeatures,
	planeFeatures,
	totals,
} from './geometry';

type Status =
	| 'loading'
	| 'ready'
	| 'looking'
	| 'found'
	| 'none'
	| 'unavailable'
	| 'error';

const ZOOM = 19; // one house fills the map at this zoom on a 390 px wide phone
const EMPTY: GeoJSON.FeatureCollection = {
	type: 'FeatureCollection',
	features: [],
};

export interface RoofStepProps {
	plz: string;
	locale: Locale;
	engine: EngineClient;
	onApply: ( roof: RoofSelection ) => void;
	onClose: () => void;
}

export function RoofStep( {
	plz,
	locale,
	engine,
	onApply,
	onClose,
}: RoofStepProps ) {
	const container = useRef< HTMLDivElement >( null );
	const map = useRef< MapLibreMap | null >( null );
	// The overlay sources can take data once the map's style has been read.
	const [ ready, setReady ] = useState( false );
	const draw = useRef< TerraDraw | null >( null );
	const [ place, setPlace ] = useState< Place | null >( null );
	const [ status, setStatus ] = useState< Status >( 'loading' );
	const [ result, setResult ] = useState< RoofResult | null >( null );
	const [ planes, setPlanes ] = useState< RoofPlane[] >( [] );
	const [ chosen, setChosen ] = useState< Set< number > >( new Set() );
	const [ clicked, setClicked ] = useState< {
		latitude: number;
		longitude: number;
	} | null >( null );
	const [ drawing, setDrawing ] = useState( false );
	const [ tilt, setTilt ] = useState( '35' );
	const [ azimuth, setAzimuth ] = useState( '180' );

	useEffect( () => {
		let cancelled = false;
		engine
			.place( plz )
			.then( ( found ) => {
				if ( ! cancelled ) {
					setPlace( found );
					setStatus( 'ready' );
				}
			} )
			.catch( () => ! cancelled && setStatus( 'error' ) );
		return () => {
			cancelled = true;
		};
	}, [ engine, plz ] );

	useEffect( () => {
		if ( ! place || ! container.current ) {
			return;
		}
		const imagery = place.imagery;
		// MapLibre paints with colour values, not CSS variables: the site's
		// tokens are read from the page, with their live values as fallback.
		const page = getComputedStyle( container.current );
		const token = ( name: string, fallback: string ) =>
			page.getPropertyValue( name ).trim() || fallback;
		const instance = new MapLibreMap( {
			container: container.current,
			center: [ place.longitude, place.latitude ],
			zoom: ZOOM - 2,
			maxZoom: 21,
			attributionControl: { compact: false },
			style: {
				version: 8,
				sources: {
					...( imagery
						? {
								dop: {
									type: 'raster',
									tiles: imagery.tiles,
									tileSize: 256,
									maxzoom: 20,
									attribution: `© ${ imagery.credit }, ${ imagery.licence }`,
								},
							}
						: {} ),
					outline: { type: 'geojson', data: EMPTY },
					planes: { type: 'geojson', data: EMPTY },
					modules: { type: 'geojson', data: EMPTY },
				},
				layers: [
					{
						id: 'paper',
						type: 'background',
						paint: {
							'background-color': token(
								'--proto-neutral-200',
								'#e2e5e5'
							),
						},
					},
					...( imagery
						? [
								{
									id: 'dop',
									type: 'raster' as const,
									source: 'dop',
								},
							]
						: [] ),
					{
						id: 'planes',
						type: 'fill',
						source: 'planes',
						paint: {
							'fill-color': [
								'match',
								[ 'get', 'state' ],
								'chosen',
								token( '--proto-teal-600', '#0c7f73' ),
								'usable',
								token( '--proto-teal-300', '#7fcbbf' ),
								token( '--proto-neutral-400', '#9aa3a3' ),
							],
							'fill-opacity': 0.35,
						},
					},
					{
						id: 'modules',
						type: 'fill',
						source: 'modules',
						paint: {
							'fill-color': token(
								'--proto-teal-900',
								'#053530'
							),
							'fill-opacity': 0.75,
							'fill-outline-color': token(
								'--proto-teal-50',
								'#f1f9f8'
							),
						},
					},
					{
						id: 'outline',
						type: 'line',
						source: 'outline',
						paint: {
							'line-color': token(
								'--proto-neutral-0',
								'#ffffff'
							),
							'line-width': 2,
						},
					},
				],
			},
		} );
		instance.addControl(
			new NavigationControl( { showCompass: false } ),
			'top-right'
		);
		// The overlay sources exist as soon as the inline style is read; the
		// map's `load` event would also wait for every aerial tile.
		instance.once( 'styledata', () => {
			if ( map.current === instance ) {
				setReady( true );
			}
		} );
		// A click selects a roof, except while a plane is drawn corner by corner.
		instance.on( 'click', ( event: MapMouseEvent ) => {
			if ( draw.current?.getMode() === 'polygon' ) {
				return;
			}
			setClicked( {
				latitude: event.lngLat.lat,
				longitude: event.lngLat.lng,
			} );
		} );
		map.current = instance;
		return () => {
			setReady( false );
			draw.current?.stop();
			draw.current = null;
			instance.remove();
			map.current = null;
		};
	}, [ place ] );

	useEffect( () => {
		if ( ! clicked ) {
			return;
		}
		let cancelled = false;
		setStatus( 'looking' );
		engine
			.roof( plz, clicked.latitude, clicked.longitude, locale )
			.then( ( found ) => {
				if ( cancelled ) {
					return;
				}
				setResult( found );
				setPlanes( found.planes );
				setChosen( defaultChoice( found.planes ) );
				setStatus( found.found ? 'found' : 'none' );
				const ring = found.outline[ 0 ];
				if ( found.found && ring && map.current ) {
					const bounds = new LngLatBounds();
					ring.forEach( ( point ) => bounds.extend( point ) );
					map.current.fitBounds( bounds, {
						padding: 48,
						maxZoom: ZOOM + 1,
						duration: 0,
					} );
				}
			} )
			.catch( ( error ) => {
				if ( ! cancelled ) {
					setStatus(
						error instanceof EngineError &&
							error.kind === 'unavailable'
							? 'unavailable'
							: 'error'
					);
				}
			} );
		return () => {
			cancelled = true;
		};
	}, [ clicked, engine, plz, locale ] );

	useEffect( () => {
		const instance = map.current;
		if ( ! instance || ! ready ) {
			return;
		}
		const features = planeFeatures( planes, chosen );
		(
			instance.getSource( 'planes' ) as GeoJSONSource | undefined
		 )?.setData( features.planes );
		(
			instance.getSource( 'modules' ) as GeoJSONSource | undefined
		 )?.setData( features.modules );
		(
			instance.getSource( 'outline' ) as GeoJSONSource | undefined
		 )?.setData( outlineFeatures( result?.outline ?? [] ) );
	}, [ planes, chosen, result, ready ] );

	function startDrawing() {
		const instance = map.current;
		if ( ! instance ) {
			return;
		}
		if ( ! draw.current ) {
			const terra = new TerraDraw( {
				adapter: new TerraDrawMapLibreGLAdapter( { map: instance } ),
				modes: [ new TerraDrawPolygonMode() ],
			} );
			terra.start();
			terra.on( 'finish', ( id ) => {
				const feature = terra
					.getSnapshot()
					.find( ( item ) => item.id === id );
				if ( feature?.geometry.type !== 'Polygon' ) {
					return;
				}
				const ring = (
					feature.geometry.coordinates[ 0 ] as [ number, number ][]
				 ).map(
					( [ lng, lat ] ) => [ lng, lat ] as [ number, number ]
				);
				terra.clear();
				setDrawing( false );
				terra.setMode( 'static' );
				addDrawn( ring );
			} );
			draw.current = terra;
		}
		draw.current.setMode( 'polygon' );
		setDrawing( true );
	}

	async function addDrawn( ring: [ number, number ][] ) {
		setStatus( 'looking' );
		try {
			const plane = await engine.pack(
				ring,
				Number( tilt ) || 0,
				( Number( azimuth ) || 0 ) % 360
			);
			const id = Math.max( 0, ...planes.map( ( p ) => p.id ) ) + 100;
			const drawn = { ...plane, id };
			setPlanes( ( current ) => [ ...current, drawn ] );
			setChosen( ( current ) => new Set( [ ...current, id ] ) );
			setStatus( 'found' );
		} catch {
			setStatus( 'error' );
		}
	}

	function toggle( id: number ) {
		setChosen( ( current ) => {
			const next = new Set( current );
			if ( next.has( id ) ) {
				next.delete( id );
			} else {
				next.add( id );
			}
			return next;
		} );
	}

	const sum = totals( planes, chosen );
	const position =
		clicked ??
		( place
			? { latitude: place.latitude, longitude: place.longitude }
			: null );

	function apply() {
		if ( ! position || sum.kwp <= 0 ) {
			return;
		}
		onApply( {
			kwp: sum.kwp,
			modules: sum.modules,
			planes: sum.planes.map( ( plane ) => ( {
				kwp: plane.kwp,
				tilt_deg: plane.tilt_deg,
				azimuth_deg: plane.azimuth_deg,
			} ) ),
			location: position,
			address: result?.address ?? null,
		} );
	}

	const message: Record< Status, string > = {
		loading: __( 'Loading the aerial image…', 'linker-tools' ),
		ready: __(
			'Click the roof of the building in the aerial image.',
			'linker-tools'
		),
		looking: __( 'Reading the official building model…', 'linker-tools' ),
		found: result?.address
			? sprintf(
					/* translators: %s: street address of the building */
					__( 'Official building model: %s', 'linker-tools' ),
					result.address
				)
			: __( 'Official building model found.', 'linker-tools' ),
		none: __(
			'No building at this point. Click on a roof, or draw the plane yourself.',
			'linker-tools'
		),
		unavailable: __(
			'No official building model is available here. Draw the roof plane yourself.',
			'linker-tools'
		),
		error: __( 'The roof could not be loaded. Try again.', 'linker-tools' ),
	};

	return (
		<section className="linker-roof" aria-labelledby="linker-roof-title">
			<header className="linker-roof__header">
				<h3 id="linker-roof-title">{ __( 'Roof', 'linker-tools' ) }</h3>
				<button
					type="button"
					className="linker-button linker-button--quiet"
					onClick={ onClose }
				>
					{ __( 'Close roof step', 'linker-tools' ) }
				</button>
			</header>
			<div className="linker-roof__layout">
				<div
					className="linker-roof__map"
					ref={ container }
					role="application"
					aria-label={ __(
						'Aerial image: click a roof to select it',
						'linker-tools'
					) }
				/>
				<div className="linker-roof__panel">
					<p className="linker-roof__status" role="status">
						{ drawing
							? __(
									'Click the corners of the plane; click the first corner again to finish.',
									'linker-tools'
								)
							: message[ status ] }
					</p>
					{ planes.length > 0 ? (
						<ul className="linker-planes">
							{ planes.map( ( plane ) => (
								<li
									key={ plane.id }
									className={
										plane.usable
											? ''
											: 'linker-planes__excluded'
									}
								>
									<label
										htmlFor={ `linker-plane-${ plane.id }` }
									>
										<input
											id={ `linker-plane-${ plane.id }` }
											type="checkbox"
											checked={ chosen.has( plane.id ) }
											disabled={
												! plane.usable ||
												plane.modules === 0
											}
											onChange={ () =>
												toggle( plane.id )
											}
										/>
										<span>
											{ sprintf(
												/* translators: 1: compass direction, 2: tilt in degrees */
												__(
													'Facing %1$s, tilt %2$s°',
													'linker-tools'
												),
												facingName( plane.azimuth_deg ),
												formatNumber(
													Math.round(
														plane.tilt_deg
													),
													locale
												)
											) }
										</span>
										<span className="linker-planes__count">
											{ plane.usable
												? sprintf(
														/* translators: %d: number of modules */
														_n(
															'%d module',
															'%d modules',
															plane.modules,
															'linker-tools'
														),
														plane.modules
													)
												: exclusionText(
														plane.excluded_reason
													) }
										</span>
									</label>
								</li>
							) ) }
						</ul>
					) : null }
					<p className="linker-roof__total">
						{ sprintf(
							/* translators: 1: number of modules, 2: kWp */
							__(
								'Selected: %1$s modules, %2$s kWp',
								'linker-tools'
							),
							formatNumber( sum.modules, locale ),
							formatNumber( sum.kwp, locale, 2 )
						) }
					</p>
					<fieldset className="linker-roof__draw">
						<legend>
							{ __( 'Draw a plane yourself', 'linker-tools' ) }
						</legend>
						<label htmlFor="linker-draw-tilt">
							{ __( 'Tilt', 'linker-tools' ) }
							<input
								id="linker-draw-tilt"
								inputMode="decimal"
								value={ tilt }
								onChange={ ( event ) =>
									setTilt( event.target.value )
								}
							/>
							°
						</label>
						<label htmlFor="linker-draw-facing">
							{ __( 'Facing (south 180°)', 'linker-tools' ) }
							<input
								id="linker-draw-facing"
								inputMode="decimal"
								value={ azimuth }
								onChange={ ( event ) =>
									setAzimuth( event.target.value )
								}
							/>
							°
						</label>
						<button
							type="button"
							className="linker-button linker-button--secondary"
							onClick={ startDrawing }
							disabled={ ! place || drawing }
						>
							{ __( 'Draw plane', 'linker-tools' ) }
						</button>
					</fieldset>
					<div className="linker-roof__actions">
						<button
							type="button"
							className="linker-button linker-button--primary"
							onClick={ apply }
							disabled={ sum.kwp <= 0 }
						>
							{ __( 'Use this roof', 'linker-tools' ) }
						</button>
					</div>
					{ result ? (
						<details className="linker-roof__notes">
							<summary>
								{ __(
									'Assumptions of the module count',
									'linker-tools'
								) }
							</summary>
							<p>
								{ sprintf(
									/* translators: 1: module model, 2: module power in Wp */
									__(
										'Reference module %1$s with %2$s Wp; the module you install can fit differently.',
										'linker-tools'
									),
									result.module,
									formatNumber( result.module_wp, locale )
								) }
							</p>
							<ul>
								{ result.assumptions.map( ( text ) => (
									<li key={ text }>{ text }</li>
								) ) }
							</ul>
							<p>{ `${ result.source } · ${ result.licence }` }</p>
						</details>
					) : null }
				</div>
			</div>
		</section>
	);
}
