/**
 * Residential inputs: consumption, PV array (or the roof step), phases,
 * backup supply, heat pump and electric car, an existing inverter, postcode.
 */

/**
 * External dependencies
 */
import { useForm } from 'react-hook-form';

/**
 * WordPress dependencies
 */
import { useEffect } from '@wordpress/element';
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { formatNumber } from '../format';
import schema from '../schema/residential-input.schema.json';
import type { Locale, PlaneInput, ResidentialInput } from '../types';
import { schemaResolver } from '../validation';
import { Field } from '../Field';

export interface RoofSelection {
	kwp: number;
	planes: PlaneInput[];
	location: { latitude: number; longitude: number };
	modules: number;
	address: string | null;
	/** Official LoD2 planes (the report credits the state's data) or drawn ones. */
	source: 'lod2' | 'drawn';
}

export interface ResidentialValues {
	plz: string;
	annual_kwh: string;
	pv_kwp: string;
	phase: '1' | '3';
	backup: 'none' | 'needed' | 'needed_accessory_ok';
	backup_load_kw: string;
	backup_hours: string;
	heat_pump: boolean;
	electric_vehicle: boolean;
	existing_inverter: string;
}

export const EMPTY: ResidentialValues = {
	plz: '',
	annual_kwh: '',
	pv_kwp: '',
	phase: '3',
	backup: 'none',
	backup_load_kw: '',
	backup_hours: '',
	heat_pump: false,
	electric_vehicle: false,
	existing_inverter: '',
};

function number( text: string ): number | undefined {
	const value = text.trim().replace( ',', '.' );
	return value === '' ? undefined : Number( value );
}

export function toInput(
	values: ResidentialValues,
	locale: Locale,
	roof: RoofSelection | null
): ResidentialInput {
	const input: ResidentialInput = {
		locale,
		plz: values.plz.trim(),
		annual_kwh: number( values.annual_kwh ) as number,
		pv_kwp: roof ? roof.kwp : ( number( values.pv_kwp ) as number ),
		phase: values.phase === '1' ? 1 : 3,
		backup: values.backup,
		heat_pump: values.heat_pump,
		electric_vehicle: values.electric_vehicle,
	};
	if ( roof ) {
		input.planes = roof.planes;
		input.location = roof.location;
		input.roof_source = roof.source;
	}
	if ( values.backup !== 'none' ) {
		const load = number( values.backup_load_kw );
		const hours = number( values.backup_hours );
		if ( load !== undefined ) {
			input.backup_load_kw = load;
		}
		if ( hours !== undefined ) {
			input.backup_hours = hours;
		}
	}
	if ( values.existing_inverter.trim() ) {
		input.existing_inverter = values.existing_inverter.trim();
	}
	return input;
}

export interface ResidentialFormProps {
	locale: Locale;
	defaults?: Partial< ResidentialValues >;
	roof: RoofSelection | null;
	busy: boolean;
	onOpenRoof: ( plz: string ) => void;
	onRemoveRoof: () => void;
	onSubmit: ( input: ResidentialInput ) => void;
}

export function ResidentialForm( {
	locale,
	defaults,
	roof,
	busy,
	onOpenRoof,
	onRemoveRoof,
	onSubmit,
}: ResidentialFormProps ) {
	const {
		register,
		handleSubmit,
		watch,
		setValue,
		trigger,
		getValues,
		setFocus,
		formState: { errors },
	} = useForm< ResidentialValues >( {
		defaultValues: { ...EMPTY, ...defaults },
		resolver: schemaResolver(
			schema,
			( values: ResidentialValues ) => toInput( values, locale, roof ),
			locale
		),
	} );
	const backup = watch( 'backup' );

	useEffect( () => {
		if ( roof ) {
			setValue( 'pv_kwp', formatNumber( roof.kwp, locale, 2 ) );
		}
	}, [ roof, setValue, locale ] );

	async function openRoof() {
		if ( await trigger( 'plz' ) ) {
			onOpenRoof( getValues( 'plz' ).trim() );
		} else {
			setFocus( 'plz' );
		}
	}

	return (
		<form
			className="linker-form"
			noValidate
			onSubmit={ handleSubmit( ( values ) =>
				onSubmit( toInput( values, locale, roof ) )
			) }
		>
			<div className="linker-form__grid">
				<Field
					id="linker-plz"
					label={ __( 'Postcode of the site', 'linker-tools' ) }
					error={ errors.plz?.message }
				>
					<input
						id="linker-plz"
						inputMode="numeric"
						autoComplete="postal-code"
						maxLength={ 5 }
						{ ...register( 'plz' ) }
					/>
				</Field>
				<Field
					id="linker-annual"
					label={ __(
						'Annual household consumption',
						'linker-tools'
					) }
					unit="kWh"
					hint={ __(
						'Without heat pump and electric car; tick them below.',
						'linker-tools'
					) }
					error={ errors.annual_kwh?.message }
				>
					<input
						id="linker-annual"
						inputMode="decimal"
						{ ...register( 'annual_kwh' ) }
					/>
				</Field>
				<Field
					id="linker-kwp"
					label={ __( 'PV array', 'linker-tools' ) }
					unit="kWp"
					error={ errors.pv_kwp?.message }
				>
					<input
						id="linker-kwp"
						inputMode="decimal"
						readOnly={ !! roof }
						aria-describedby="linker-roof-summary"
						{ ...register( 'pv_kwp' ) }
					/>
				</Field>
				<div className="linker-form__roof" id="linker-roof-summary">
					{ roof ? (
						<>
							<p>
								{ sprintf(
									/* translators: 1: number of modules, 2: number of roof planes, 3: kWp */
									_n(
										'From the roof: %1$s modules on %2$s plane, %3$s kWp.',
										'From the roof: %1$s modules on %2$s planes, %3$s kWp.',
										roof.planes.length,
										'linker-tools'
									),
									formatNumber( roof.modules, locale ),
									formatNumber( roof.planes.length, locale ),
									formatNumber( roof.kwp, locale, 2 )
								) }
								{ roof.address ? ` ${ roof.address }` : '' }
							</p>
							<button
								type="button"
								className="linker-button linker-button--quiet"
								onClick={ openRoof }
							>
								{ __( 'Change roof', 'linker-tools' ) }
							</button>
							<button
								type="button"
								className="linker-button linker-button--quiet"
								onClick={ onRemoveRoof }
							>
								{ __( 'Enter kWp instead', 'linker-tools' ) }
							</button>
						</>
					) : (
						<button
							type="button"
							className="linker-button linker-button--secondary"
							onClick={ openRoof }
						>
							{ __(
								'No PV figure yet? Estimate from the roof',
								'linker-tools'
							) }
						</button>
					) }
				</div>
				<fieldset className="linker-form__choice">
					<legend>{ __( 'Grid connection', 'linker-tools' ) }</legend>
					<label htmlFor="linker-phase-3">
						<input
							id="linker-phase-3"
							type="radio"
							value="3"
							{ ...register( 'phase' ) }
						/>
						{ __( 'Three-phase', 'linker-tools' ) }
					</label>
					<label htmlFor="linker-phase-1">
						<input
							id="linker-phase-1"
							type="radio"
							value="1"
							{ ...register( 'phase' ) }
						/>
						{ __( 'Single-phase', 'linker-tools' ) }
					</label>
				</fieldset>
				<Field
					id="linker-backup"
					label={ __( 'Backup supply', 'linker-tools' ) }
				>
					<select id="linker-backup" { ...register( 'backup' ) }>
						<option value="none">
							{ __( 'Not needed', 'linker-tools' ) }
						</option>
						<option value="needed">
							{ __( 'Needed', 'linker-tools' ) }
						</option>
						<option value="needed_accessory_ok">
							{ __(
								'Needed, an accessory is fine',
								'linker-tools'
							) }
						</option>
					</select>
				</Field>
				{ backup !== 'none' ? (
					<>
						<Field
							id="linker-backup-load"
							label={ __(
								'Load to keep running',
								'linker-tools'
							) }
							unit="kW"
							hint={ __(
								'Optional; sizes a reserve on top.',
								'linker-tools'
							) }
							error={ errors.backup_load_kw?.message }
						>
							<input
								id="linker-backup-load"
								inputMode="decimal"
								{ ...register( 'backup_load_kw' ) }
							/>
						</Field>
						<Field
							id="linker-backup-hours"
							label={ __( 'For how long', 'linker-tools' ) }
							unit="h"
							error={ errors.backup_hours?.message }
						>
							<input
								id="linker-backup-hours"
								inputMode="decimal"
								{ ...register( 'backup_hours' ) }
							/>
						</Field>
					</>
				) : null }
				<fieldset className="linker-form__choice">
					<legend>
						{ __( 'Additional consumers', 'linker-tools' ) }
					</legend>
					<label htmlFor="linker-heat-pump">
						<input
							id="linker-heat-pump"
							type="checkbox"
							{ ...register( 'heat_pump' ) }
						/>
						{ __(
							'Heat pump (installed or planned)',
							'linker-tools'
						) }
					</label>
					<label htmlFor="linker-ev">
						<input
							id="linker-ev"
							type="checkbox"
							{ ...register( 'electric_vehicle' ) }
						/>
						{ __(
							'Electric car (installed or planned)',
							'linker-tools'
						) }
					</label>
				</fieldset>
				<Field
					id="linker-existing"
					label={ __(
						'Existing inverter (retrofit)',
						'linker-tools'
					) }
					hint={ __(
						'Optional. Enter its model and we list only batteries released for it.',
						'linker-tools'
					) }
					error={ errors.existing_inverter?.message }
				>
					<input
						id="linker-existing"
						autoComplete="off"
						{ ...register( 'existing_inverter' ) }
					/>
				</Field>
			</div>
			<div className="linker-form__submit">
				<button
					type="submit"
					className="linker-button linker-button--primary"
					disabled={ busy }
					aria-busy={ busy }
				>
					{ busy
						? __( 'Calculating…', 'linker-tools' )
						: __( 'Calculate system', 'linker-tools' ) }
				</button>
			</div>
		</form>
	);
}
