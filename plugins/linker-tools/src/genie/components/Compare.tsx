/** The same published selection facts and product identities as the catalog comparison. */
import { useEffect, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';
import type { ReactNode } from 'react';
import type { CardState } from '../../shared/ProductCard';
import type { Locale } from '../../configurator/types';
import './catalog.css';

interface Pairing {
	model: string;
	verdict: string;
	conditions: string[];
	accessories: string[];
}
interface Column {
	product_id: number;
	title: string;
	url: string;
	facts: { device_class: string };
	presentation: {
		model: string | null;
		brand: string | null;
		series: string | null;
		image: string;
		sku: string;
		storage: Pairing[];
		in_stock: boolean;
		price_line: string;
		price_reason: string | null;
		datasheet: { title: string; url: string } | null;
	};
}
interface Spec {
	field: string;
	label: string;
	values: Record< string, string | number | { min: number; max: number } >;
}
interface Comparison {
	products: Column[];
	rows: Spec[];
}
interface Props {
	products: number[];
	locale: Locale;
	restUrl: string;
	nonce: string;
	proofs: Record< string, string >;
	quantities: Record< string, number >;
	statusFor: ( id: number ) => { state: CardState; text: string };
	onAdd: ( id: number, quantity: number ) => void;
}
function valueText(
	value: Spec[ 'values' ][ string ] | undefined,
	locale: Locale
): string {
	if ( value === undefined || value === 'unknown' ) return '—';
	const format = new Intl.NumberFormat( locale, {
		maximumFractionDigits: 6,
	} );
	if ( typeof value === 'number' ) return format.format( value );
	if ( typeof value === 'object' )
		return format.format( value.min ) + '–' + format.format( value.max );
	if ( value === 'home' ) return __( 'Residential', 'linker-tools' );
	if ( value === 'commercial' ) return __( 'Commercial', 'linker-tools' );
	return value;
}

export function Compare( {
	products,
	restUrl,
	nonce,
	locale,
	quantities,
	proofs,
	statusFor,
	onAdd,
}: Props ) {
	const [ attempt, retry ] = useState( 0 );
	const query = new URLSearchParams( {
		'input[lang]': locale,
		'input[presentation]': 'true',
	} );
	products.forEach( ( id ) =>
		query.append( 'input[product_ids][]', String( id ) )
	);
	const url =
		restUrl.replace( /\/?$/, '/' ) +
		'wp-abilities/v1/abilities/linker/compare-products/run?' +
		query;
	const [ result, setResult ] = useState< {
		url: string;
		nonce: string;
		attempt: number;
		data: Comparison | null;
	} >();
	useEffect( () => {
		const controller = new AbortController();
		async function load() {
			try {
				const response = await fetch( url, {
					credentials: 'same-origin',
					cache: 'no-store',
					headers: { 'X-WP-Nonce': nonce },
					signal: controller.signal,
				} );
				if ( ! response.ok ) throw Error( String( response.status ) );
				const data: Comparison = await response.json();
				if ( ! controller.signal.aborted )
					setResult( { url, nonce, attempt, data } );
			} catch {
				if ( ! controller.signal.aborted )
					setResult( { url, nonce, attempt, data: null } );
			}
		}
		void load();
		return () => controller.abort();
	}, [ url, nonce, attempt ] );
	if (
		result?.url !== url ||
		result.nonce !== nonce ||
		result.attempt !== attempt
	)
		return <p>{ __( 'Loading comparison…', 'linker-tools' ) }</p>;
	if ( ! result.data )
		return (
			<p role="alert">
				{ __( 'Could not load this comparison.', 'linker-tools' ) }{ ' ' }
				<button type="button" onClick={ () => retry( ( n ) => n + 1 ) }>
					{ __( 'Try again', 'linker-tools' ) }
				</button>
			</p>
		);
	if ( ! result.data.products.length )
		return (
			<p>
				{ __(
					'These products are no longer available for comparison.',
					'linker-tools'
				) }
			</p>
		);
	const { products: columns, rows } = result.data;
	const groups = [
		{
			name: __( 'Inverters', 'linker-tools' ),
			columns: columns.filter( ( c ) =>
				[ 'inverters', 'all-in-one-systems' ].includes(
					c.facts.device_class
				)
			),
			keys: [ 'application', 'phase', 'ac_power_kw', 'pv_input_kw' ],
			storage: true,
		},
		{
			name: __( 'Battery storage', 'linker-tools' ),
			columns: columns.filter( ( c ) =>
				[
					'home-storage',
					'battery-systems',
					'all-in-one-systems',
				].includes( c.facts.device_class )
			),
			keys: [ 'application', 'usable_kwh', 'nominal_kwh', 'kwh_range' ],
			storage: false,
		},
		{
			name: __( 'Equipment', 'linker-tools' ),
			columns: columns.filter(
				( c ) =>
					! [
						'inverters',
						'all-in-one-systems',
						'home-storage',
						'battery-systems',
					].includes( c.facts.device_class )
			),
			keys: [ 'application' ],
			storage: false,
		},
	];
	return (
		<div className="genie-comparisons">
			{ groups
				.filter( ( group ) => group.columns.length )
				.map( ( group ) => {
					const row = (
						key: string,
						title: string,
						render: ( c: Column ) => ReactNode
					) => (
						<tr key={ key }>
							<th scope="row">{ title }</th>
							{ group.columns.map( ( c ) => (
								<td key={ c.product_id }>{ render( c ) }</td>
							) ) }
						</tr>
					);
					return (
						<section
							key={ group.name }
							className="genie-comparison"
						>
							<h3>
								{ __( 'Product comparison', 'linker-tools' ) } ·{ ' ' }
								{ group.name }
							</h3>
							<div
								className="genie-comparison__scroll"
								role="region"
								aria-label={ group.name }
								tabIndex={ 0 }
							>
								<table aria-label={ group.name }>
									<colgroup>
										<col className="genie-comparison__label" />
										{ group.columns.map( ( c ) => (
											<col key={ c.product_id } />
										) ) }
									</colgroup>
									<thead>
										<tr>
											<th scope="col">
												{ __(
													'Specification',
													'linker-tools'
												) }
											</th>
											{ group.columns.map( ( c ) => (
												<th
													scope="col"
													key={ c.product_id }
												>
													<a href={ c.url }>
														<span className="genie-comparison__brand">
															{ c.presentation
																.image && (
																<img
																	alt=""
																	src={
																		c
																			.presentation
																			.image
																	}
																	width={ 32 }
																	height={
																		32
																	}
																/>
															) }
															{
																c.presentation
																	.brand
															}
														</span>
														<strong className="genie-comparison__model">
															{ c.presentation
																.model ||
																c.title }
														</strong>
														{ c.presentation
															.sku && (
															<span className="genie-comparison__sku">
																{
																	c
																		.presentation
																		.sku
																}
															</span>
														) }
													</a>
												</th>
											) ) }
										</tr>
									</thead>
									<tbody>
										{ row(
											'brand',
											__(
												'Brand / Series',
												'linker-tools'
											),
											( c ) =>
												[
													c.presentation.brand,
													c.presentation.series,
												]
													.filter( Boolean )
													.join( ' · ' ) || '—'
										) }
										{ rows
											.filter( ( r ) =>
												group.keys.includes( r.field )
											)
											.map( ( r ) =>
												row( r.field, r.label, ( c ) =>
													valueText(
														r.values[
															c.product_id
														],
														locale
													)
												)
											) }
										{ group.storage &&
											row(
												'storage',
												__(
													'Compatible storage',
													'linker-tools'
												),
												( c ) =>
													c.presentation.storage
														.length ? (
														<ul>
															{ c.presentation.storage.map(
																( item ) => (
																	<li
																		key={
																			item.model
																		}
																	>
																		{
																			item.model
																		}
																		{ item.verdict ===
																			'released_with_accessory' && (
																			<span>
																				{ ' ' }
																				·{ ' ' }
																				{ __(
																					'Accessory required',
																					'linker-tools'
																				) }
																				{ item
																					.accessories
																					.length
																					? ' (' +
																						item.accessories.join(
																							', '
																						) +
																						')'
																					: '' }
																			</span>
																		) }
																		{ item.conditions.map(
																			(
																				note
																			) => (
																				<small
																					key={
																						note
																					}
																				>
																					{
																						note
																					}
																				</small>
																			)
																		) }
																	</li>
																)
															) }
														</ul>
													) : (
														'—'
													)
											) }
										{ row(
											'availability',
											__(
												'Availability',
												'linker-tools'
											),
											( c ) => (
												<span
													className="genie-comparison__stock"
													data-available={
														c.presentation.in_stock
													}
												>
													{ c.presentation.in_stock
														? __(
																'In stock',
																'linker-tools'
															)
														: __(
																'Currently unavailable',
																'linker-tools'
															) }
												</span>
											)
										) }
										{ row(
											'price',
											__(
												'Partner pricing',
												'linker-tools'
											),
											( c ) =>
												c.presentation.price_reason ===
												'login'
													? __(
															'Net price after sign-in',
															'linker-tools'
														)
													: c.presentation
															.price_line || '—'
										) }
										{ row(
											'pdf',
											__( 'Datasheet', 'linker-tools' ),
											( c ) =>
												c.presentation.datasheet ? (
													<a
														className="genie-comparison__pdf"
														href={
															c.presentation
																.datasheet.url
														}
														title={
															c.presentation
																.datasheet.title
														}
														target="_blank"
														rel="noopener noreferrer"
													>
														{ __(
															'Datasheet',
															'linker-tools'
														) }{ ' ' }
														↗
													</a>
												) : (
													'—'
												)
										) }
										{ row(
											'draft',
											__(
												'Solution draft',
												'linker-tools'
											),
											( c ) => {
												const id = c.product_id,
													status = statusFor( id ),
													quantity = quantities[ id ];
												const added =
													status.state === 'added' &&
													status.text ===
														__(
															'In your solution draft.',
															'linker-tools'
														);
												if (
													! proofs[ id ] ||
													! quantity
												)
													return (
														<a href={ c.url }>
															{ __(
																'View product',
																'linker-tools'
															) }
														</a>
													);
												return (
													<>
														<button
															type="button"
															className="genie-comparison__add"
															disabled={
																added ||
																status.state ===
																	'pending'
															}
															onClick={ () =>
																onAdd(
																	id,
																	quantity
																)
															}
														>
															{ added
																? __(
																		'✓ In draft',
																		'linker-tools'
																	)
																: __(
																		'+ Add to draft',
																		'linker-tools'
																	) }
														</button>
														{ status.text &&
															! added && (
																<small role="status">
																	{
																		status.text
																	}
																</small>
															) }
													</>
												);
											}
										) }
									</tbody>
								</table>
							</div>
						</section>
					);
				} ) }
		</div>
	);
}
