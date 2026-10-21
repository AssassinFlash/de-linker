/**
 * The C&I result: the load profile at a glance, the cap options, the sized
 * power and energy with matching systems, or the indicative ranges and the
 * inquiry.
 */

/**
 * WordPress dependencies
 */
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { ProductCard, type CardBadge } from '../../shared/ProductCard';
import { formatNumber, formatRange } from '../format';
import { verdictText } from '../solution/Solution';
import { stockBadge } from '../stock';
import { Table } from '../Table';
import type {
	CommercialResult as Result,
	Locale,
	StoreProduct,
} from '../types';

/**
 * The load duration curve: every 15-minute value of the profile, highest
 * first, with the target peak where one is set. The plot stretches to the
 * width; its labels are text, so they stay readable on a phone.
 * @param root0
 * @param root0.values
 * @param root0.peak
 * @param root0.hours
 * @param root0.cap
 * @param root0.locale
 */
function Curve( {
	values,
	peak,
	hours,
	cap,
	locale,
}: {
	values: number[];
	peak: number;
	hours: number;
	cap: number | null;
	locale: Locale;
} ) {
	const x = ( index: number ) =>
		( index / Math.max( 1, values.length - 1 ) ) * 1000;
	const y = ( kw: number ) => 300 - ( kw / peak ) * 300;
	const line = values
		.map(
			( kw, index ) =>
				`${ x( index ).toFixed( 1 ) },${ y( kw ).toFixed( 1 ) }`
		)
		.join( ' ' );
	const shown = cap !== null && cap > 0 && cap < peak;
	return (
		<figure className="linker-curve">
			<div className="linker-curve__frame">
				<div className="linker-curve__y" aria-hidden="true">
					<span>{ `${ formatNumber( peak, locale ) } kW` }</span>
					<span>0</span>
				</div>
				<div className="linker-curve__plot">
					<svg
						viewBox="0 0 1000 300"
						preserveAspectRatio="none"
						role="img"
						aria-label={ __(
							'Load duration curve: the year sorted from highest to lowest load',
							'linker-tools'
						) }
					>
						<polygon
							className="linker-curve__area"
							points={ `0,300 ${ line } 1000,300` }
						/>
						<polyline
							className="linker-curve__line"
							points={ line }
						/>
						{ shown ? (
							<line
								className="linker-curve__cap"
								x1="0"
								x2="1000"
								y1={ y( cap ) }
								y2={ y( cap ) }
							/>
						) : null }
					</svg>
					{ shown ? (
						<span
							className="linker-curve__cap-label"
							style={ { top: `${ ( y( cap ) / 300 ) * 100 }%` } }
						>
							{ sprintf(
								/* translators: %s: target peak in kW */
								__( 'Target peak %s kW', 'linker-tools' ),
								formatNumber( cap, locale )
							) }
						</span>
					) : null }
				</div>
				<div className="linker-curve__x" aria-hidden="true">
					<span>0 h</span>
					<span>{ `${ formatNumber( hours, locale ) } h` }</span>
				</div>
			</div>
			<figcaption>
				{ __(
					'Load duration curve: every 15-minute value of the profile, from the highest to the lowest.',
					'linker-tools'
				) }
			</figcaption>
		</figure>
	);
}

/**
 * A system's card badges: its stock state over its whole build (inverter and
 * battery, when it has one), then the release verdict.
 * @param system
 * @param products
 */
function systemBadges(
	system: Result[ 'systems' ][ number ],
	products: Map< number, StoreProduct >
): CardBadge[] {
	const badges: CardBadge[] = [];
	const stock = stockBadge( [
		products.get( system.inverter.id ),
		...( system.battery ? [ products.get( system.battery.id ) ] : [] ),
	] );
	if ( stock ) {
		badges.push( stock );
	}
	if ( system.release ) {
		badges.push( {
			tone: 'info',
			text: verdictText( system.release.verdict ),
		} );
	}
	return badges;
}

export interface CommercialResultProps {
	result: Result;
	locale: Locale;
	/** The target peak the result was calculated for, if any. */
	cap: number | null;
	/** Store data of the systems' inverters, for their image and page. */
	products: Map< number, StoreProduct >;
	onChooseCap: ( cap: number ) => void;
}

export function CommercialResult( {
	result,
	locale,
	cap,
	products,
	onChooseCap,
}: CommercialResultProps ) {
	const load = result.load;
	return (
		<div className="linker-solution">
			{ load ? (
				<div className="linker-load">
					<dl className="linker-figures">
						<div>
							<dt>{ __( 'Annual peak', 'linker-tools' ) }</dt>
							<dd>{ `${ formatNumber( load.peak_kw, locale ) } kW` }</dd>
						</div>
						<div>
							<dt>
								{ __( 'Consumption per year', 'linker-tools' ) }
							</dt>
							<dd>{ `${ formatNumber( load.annual_kwh, locale ) } kWh` }</dd>
						</div>
						<div>
							<dt>{ __( 'Full-load hours', 'linker-tools' ) }</dt>
							<dd>{ `${ formatNumber( load.full_load_hours, locale ) } h` }</dd>
						</div>
						<div>
							<dt>
								{ __( 'Days in the profile', 'linker-tools' ) }
							</dt>
							<dd>{ formatNumber( load.days, locale ) }</dd>
						</div>
					</dl>
					<Curve
						values={ load.duration_curve_kw }
						peak={ load.peak_kw }
						hours={ load.days * 24 }
						cap={ result.status === 'sized' ? cap : null }
						locale={ locale }
					/>
				</div>
			) : null }
			{ result.power_kw_range && result.energy_kwh_range ? (
				<dl className="linker-figures linker-figures--key">
					<div>
						<dt>
							{ result.status === 'sized'
								? __( 'Battery power', 'linker-tools' )
								: __(
										'Battery power, indicative',
										'linker-tools'
									) }
						</dt>
						<dd>
							{ formatRange(
								result.power_kw_range,
								locale,
								'kW'
							) }
						</dd>
					</div>
					<div>
						<dt>
							{ result.status === 'sized'
								? __( 'Usable energy', 'linker-tools' )
								: __(
										'Usable energy, indicative',
										'linker-tools'
									) }
						</dt>
						<dd>
							{ formatRange(
								result.energy_kwh_range,
								locale,
								'kWh'
							) }
						</dd>
					</div>
				</dl>
			) : null }
			<ul className="linker-basis-list">
				{ result.basis.map( ( text ) => (
					<li key={ text }>{ text }</li>
				) ) }
			</ul>
			{ result.warnings.length > 0 ? (
				<ul className="linker-notes">
					{ result.warnings.map( ( text ) => (
						<li key={ text }>{ text }</li>
					) ) }
				</ul>
			) : null }
			{ result.options.length > 0 ? (
				<Table
					caption={ __(
						'Peak shaving options from your load profile',
						'linker-tools'
					) }
					columns={ [
						{ label: __( 'Cap', 'linker-tools' ), numeric: true },
						{ label: __( 'Power', 'linker-tools' ), numeric: true },
						{
							label: __( 'Usable energy', 'linker-tools' ),
							numeric: true,
						},
						{
							label: __( 'Peaks per year', 'linker-tools' ),
							numeric: true,
						},
						{ label: __( 'Action', 'linker-tools' ), hidden: true },
					] }
					rows={ result.options.map( ( option ) => ( {
						key: String( option.cap_kw ),
						cells: [
							`${ formatNumber( option.cap_kw, locale ) } kW`,
							`${ formatNumber( option.power_kw, locale ) } kW`,
							`${ formatNumber( option.energy_kwh, locale ) } kWh`,
							formatNumber( option.events, locale ),
							<button
								key="size"
								type="button"
								className="linker-button linker-button--quiet"
								onClick={ () => onChooseCap( option.cap_kw ) }
							>
								{ sprintf(
									/* translators: %s: cap in kW */
									__( 'Size for %s kW', 'linker-tools' ),
									formatNumber( option.cap_kw, locale )
								) }
							</button>,
						],
					} ) ) }
				/>
			) : null }
			{ result.systems.length > 0 ? (
				<>
					<h3 className="linker-section__subtitle">
						{ __( 'Systems from our range', 'linker-tools' ) }
					</h3>
					<div className="linker-cards">
						{ result.systems.map( ( system, index ) => (
							<ProductCard
								key={ `${ system.inverter.id }-${ system.battery?.id ?? 0 }` }
								id={ `linker-system-${ index }` }
								role={ __( 'System', 'linker-tools' ) }
								title={ `${ system.inverter.brand } ${ system.inverter.model }${ system.battery ? ` + ${ system.battery.model }` : '' }` }
								url={
									products.get( system.inverter.id )
										?.permalink
								}
								image={
									products.get( system.inverter.id )
										?.images[ 0 ]
								}
								model={ sprintf(
									/* translators: 1: power in kW, 2: energy in kWh */
									__(
										'%1$s kW, %2$s kWh usable',
										'linker-tools'
									),
									formatNumber( system.power_kw, locale ),
									formatNumber( system.usable_kwh, locale )
								) }
								badges={ systemBadges( system, products ) }
								facts={ system.lines.map( ( line ) => ( {
									label: line.label,
									value: `${ formatNumber( line.quantity, locale ) } × ${ line.product?.model ?? '' }`,
								} ) ) }
							/>
						) ) }
					</div>
				</>
			) : null }
			<div className="linker-actions">
				<a
					className="linker-button linker-button--primary"
					href={ result.inquiry }
				>
					{ result.status === 'sized'
						? __( 'Send this to our team', 'linker-tools' )
						: __( 'Send us an inquiry', 'linker-tools' ) }
				</a>
			</div>
		</div>
	);
}
