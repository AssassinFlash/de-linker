/**
 * The proposed system: every Linker product as a card with its release basis,
 * the installer's scope, and the two actions: add all to the solution draft,
 * save the solution.
 */

/**
 * WordPress dependencies
 */
import { __, _n, _x, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { ProductCard, type CardState } from '../../shared/ProductCard';
import type { AddStatus } from '../api/store';
import { formatNumber, formatPercentRange, formatRange } from '../format';
import { Table } from '../Table';
import type {
	Line,
	Locale,
	ResidentialResult,
	StoreProduct,
	Verdict,
} from '../types';
import { Documents } from './Documents';

export type SaveState = 'idle' | 'saving' | 'saved' | 'failed';

export interface SolutionProps {
	result: ResidentialResult;
	locale: Locale;
	products: Map< number, StoreProduct >;
	statuses: Map< number, AddStatus >;
	adding: boolean;
	addOutcome: 'none' | 'complete' | 'partial';
	saveState: SaveState;
	savedUrl: string | null;
	onSwapInverter: ( id: number ) => void;
	onSwapBattery: ( id: number ) => void;
	onAddAll: () => void;
	onSave: () => void;
}

export function verdictText( verdict: Verdict ): string {
	switch ( verdict ) {
		case 'released':
			return __( 'Released by the manufacturer', 'linker-tools' );
		case 'released_with_accessory':
			return __( 'Released with accessory', 'linker-tools' );
		case 'not_released':
			return __( 'Not released', 'linker-tools' );
		default:
			return __( 'No release document', 'linker-tools' );
	}
}

function unitText( line: Line, locale: Locale ): string {
	const amount = formatNumber( line.quantity, locale );
	switch ( line.unit ) {
		case 'm':
			return `${ amount } m`;
		case 'pairs':
			return sprintf(
				/* translators: %s: number of connector pairs */
				_n( '%s pair', '%s pairs', line.quantity, 'linker-tools' ),
				amount
			);
		case 'set':
			return sprintf(
				/* translators: %s: number of sets */
				_n( '%s set', '%s sets', line.quantity, 'linker-tools' ),
				amount
			);
		default:
			return sprintf(
				/* translators: %s: number of pieces */
				_n( '%s pc', '%s pcs', line.quantity, 'linker-tools' ),
				amount
			);
	}
}

function cardStatus( status: AddStatus | undefined ): {
	state: CardState;
	text: string;
} {
	switch ( status ) {
		case 'pending':
			return { state: 'pending', text: __( 'Adding…', 'linker-tools' ) };
		case 'added':
			return {
				state: 'added',
				text: __( 'In your solution draft', 'linker-tools' ),
			};
		case 'unverified':
			return {
				state: 'unverified',
				text: _x(
					'Sent, but the draft does not show it yet. Please check.',
					'configurator',
					'linker-tools'
				),
			};
		case 'retry':
			return {
				state: 'retry',
				text: _x(
					'Not added. Try again.',
					'configurator',
					'linker-tools'
				),
			};
		default:
			return { state: 'idle', text: '' };
	}
}

function Swap( {
	id,
	label,
	value,
	options,
	onChange,
}: {
	id: string;
	label: string;
	value: number;
	options: { id: number; text: string }[];
	onChange: ( id: number ) => void;
} ) {
	return (
		<div className="linker-swap">
			<label htmlFor={ id }>{ label }</label>
			<select
				id={ id }
				value={ value }
				onChange={ ( event ) =>
					onChange( Number( event.target.value ) )
				}
			>
				{ options.map( ( option ) => (
					<option key={ option.id } value={ option.id }>
						{ option.text }
					</option>
				) ) }
			</select>
		</div>
	);
}

export function Solution( props: SolutionProps ) {
	const { result, locale, products, statuses } = props;
	const selected = result.selected;
	if ( ! selected ) {
		return null;
	}
	function swapFor( role: Line[ 'role' ], current: number ) {
		if ( role === 'inverter' && result.candidates.inverters.length > 1 ) {
			return (
				<Swap
					id="linker-swap-inverter"
					label={ __( 'Other inverter', 'linker-tools' ) }
					value={ current }
					options={ result.candidates.inverters.map(
						( candidate ) => ( {
							id: candidate.product.id,
							text: `${ candidate.product.brand } ${ candidate.product.model }`,
						} )
					) }
					onChange={ props.onSwapInverter }
				/>
			);
		}
		if ( role === 'battery' && result.candidates.batteries.length > 1 ) {
			return (
				<Swap
					id="linker-swap-battery"
					label={ __( 'Other battery', 'linker-tools' ) }
					value={ current }
					options={ result.candidates.batteries.map( ( choice ) => ( {
						id: choice.product.id,
						text: `${ choice.product.brand } ${ choice.product.model }, ${ formatNumber( choice.usable_kwh, locale, 2 ) } kWh`,
					} ) ) }
					onChange={ props.onSwapBattery }
				/>
			);
		}
		return undefined;
	}

	const ours = selected.lines.filter( ( line ) => line.product );
	const installer = selected.lines.filter( ( line ) => ! line.product );
	const battery = selected.battery;
	return (
		<div className="linker-solution">
			<dl className="linker-figures">
				<div>
					<dt>{ __( 'PV yield per year', 'linker-tools' ) }</dt>
					<dd>
						{ formatRange(
							result.yield.kwh_year_range,
							locale,
							'kWh'
						) }
					</dd>
				</div>
				<div>
					<dt>{ __( 'Usable storage', 'linker-tools' ) }</dt>
					<dd>
						{ battery
							? `${ formatNumber( battery.usable_kwh, locale, 2 ) } kWh`
							: __( 'None', 'linker-tools' ) }
					</dd>
				</div>
				{ result.metrics ? (
					<>
						<div>
							<dt>
								{ __( 'Self-sufficiency', 'linker-tools' ) }
							</dt>
							<dd>
								{ formatPercentRange(
									result.metrics.autarky_range,
									locale
								) }
							</dd>
						</div>
						<div>
							<dt>
								{ __( 'Self-consumption', 'linker-tools' ) }
							</dt>
							<dd>
								{ formatPercentRange(
									result.metrics.self_consumption_range,
									locale
								) }
							</dd>
						</div>
					</>
				) : null }
			</dl>
			{ result.warnings.length > 0 ? (
				<ul className="linker-notes">
					{ result.warnings.map( ( warning ) => (
						<li key={ warning }>{ warning }</li>
					) ) }
				</ul>
			) : null }
			<h3 className="linker-section__subtitle">
				{ __( 'Linker products', 'linker-tools' ) }
			</h3>
			<div className="linker-cards">
				{ ours.map( ( line, index ) => {
					const product = line.product!;
					const store = products.get( product.id );
					const badges = [];
					if ( store?.is_in_stock ) {
						badges.push( {
							tone: 'ok' as const,
							text: __( 'In stock', 'linker-tools' ),
						} );
					}
					if ( line.role === 'battery' && battery ) {
						badges.push( {
							tone: 'info' as const,
							text: verdictText( battery.release.verdict ),
						} );
						if ( battery.above_upper_limit ) {
							badges.push( {
								tone: 'warn' as const,
								text: __(
									'Above the HTW limit',
									'linker-tools'
								),
							} );
						}
					}
					return (
						<ProductCard
							key={ `${ line.role }-${ product.id }` }
							id={ `linker-line-${ index }` }
							role={ line.label }
							title={
								store?.name ??
								`${ product.brand } ${ product.model }`
							}
							model={ sprintf(
								/* translators: %s: model name of the product */
								__( 'Model %s', 'linker-tools' ),
								product.model
							) }
							url={ store?.permalink }
							image={ store?.images[ 0 ] }
							quantity={ unitText( line, locale ) }
							badges={ badges }
							status={ cardStatus( statuses.get( product.id ) ) }
							actions={ swapFor( line.role, product.id ) }
						>
							{ line.basis.length > 0 ? (
								<details className="linker-basis">
									<summary>
										{ __(
											'Why this product',
											'linker-tools'
										) }
									</summary>
									<ul>
										{ line.basis.map( ( reason ) => (
											<li key={ reason }>{ reason }</li>
										) ) }
									</ul>
									<Documents documents={ line.documents } />
								</details>
							) : null }
						</ProductCard>
					);
				} ) }
			</div>
			<div className="linker-actions" aria-live="polite">
				<button
					type="button"
					className="linker-button linker-button--primary"
					onClick={ props.onAddAll }
					disabled={ props.adding }
					aria-busy={ props.adding }
				>
					{ __( 'Add all to solution draft', 'linker-tools' ) }
				</button>
				<button
					type="button"
					className="linker-button linker-button--secondary"
					onClick={ props.onSave }
					disabled={ props.saveState === 'saving' }
					aria-busy={ props.saveState === 'saving' }
				>
					{ props.saveState === 'saving'
						? __( 'Saving…', 'linker-tools' )
						: __( 'Save solution', 'linker-tools' ) }
				</button>
				<p className="linker-actions__status">
					{ props.addOutcome === 'complete' ? (
						<>
							{ __(
								'All products are in your solution draft.',
								'linker-tools'
							) }{ ' ' }
						</>
					) : null }
					{ props.addOutcome === 'partial' ? (
						<>
							{ __(
								'Some products are not confirmed in your solution draft. See the cards above.',
								'linker-tools'
							) }{ ' ' }
						</>
					) : null }
					{ props.saveState === 'saved' ? (
						<>
							{ _x(
								'Saved to your account.',
								'configurator',
								'linker-tools'
							) }{ ' ' }
							{ props.savedUrl ? (
								<a href={ props.savedUrl }>
									{ __(
										'Open saved solution',
										'linker-tools'
									) }
								</a>
							) : null }
						</>
					) : null }
					{ props.saveState === 'failed'
						? __(
								'The solution could not be saved. Try again.',
								'linker-tools'
							)
						: null }
				</p>
			</div>
			<h3 className="linker-section__subtitle">
				{ __( "Installer's scope", 'linker-tools' ) }
			</h3>
			<p className="linker-section__note">
				{ __(
					'We do not supply these parts; the quantities follow the reference layout.',
					'linker-tools'
				) }
			</p>
			<Table
				columns={ [
					{ label: __( 'Item', 'linker-tools' ) },
					{ label: __( 'Quantity', 'linker-tools' ), numeric: true },
					{ label: __( 'Basis', 'linker-tools' ) },
				] }
				rows={ installer.map( ( line ) => ( {
					key: line.role,
					cells: [
						line.label,
						unitText( line, locale ),
						line.basis.map( ( reason ) => (
							<span key={ reason } className="linker-table__line">
								{ reason }
							</span>
						) ),
					],
				} ) ) }
			/>
		</div>
	);
}
