/**
 * Commercial and industrial: the intake form, then either a sizing from the
 * 15-minute load profile or indicative ranges with an inquiry.
 */

/**
 * External dependencies
 */
import { useForm } from 'react-hook-form';

/**
 * WordPress dependencies
 */
import { useCallback, useEffect, useMemo, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { EngineClient } from '../api/engine';
import type { StoreClient } from '../api/store';
import type { Config } from '../config';
import { Field } from '../Field';
import { FilePicker } from '../FilePicker';
import { MobileNavigation } from '../MobileNavigation';
import schema from '../schema/commercial-input.schema.json';
import type { StepNumber } from '../Steps';
import type {
	CommercialInput,
	CommercialResult as Result,
	Goal,
	Locale,
	StoreProduct,
} from '../types';
import { schemaResolver } from '../validation';
import { CommercialResult } from './CommercialResult';

export interface CommercialValues {
	plz: string;
	grid_connection_kva: string;
	annual_kwh: string;
	goals: Goal[];
	peak_kw: string;
	target_peak_kw: string;
	pv_kwp: string;
	backup_load_kw: string;
	backup_hours: string;
	load_profile_unit: 'kW' | 'kWh';
	installation: 'indoor' | 'outdoor' | 'unknown';
	notes: string;
}

const EMPTY: CommercialValues = {
	plz: '',
	grid_connection_kva: '',
	annual_kwh: '',
	goals: [ 'peak_shaving' ],
	peak_kw: '',
	target_peak_kw: '',
	pv_kwp: '',
	backup_load_kw: '',
	backup_hours: '',
	load_profile_unit: 'kW',
	installation: 'unknown',
	notes: '',
};

function number( text: string ): number | undefined {
	const value = text.trim().replace( ',', '.' );
	return value === '' ? undefined : Number( value );
}

export function toCommercialInput(
	values: CommercialValues,
	locale: Locale,
	profile: string | null
): CommercialInput {
	const input: CommercialInput = {
		locale,
		plz: values.plz.trim(),
		grid_connection_kva: number( values.grid_connection_kva ) as number,
		annual_kwh: number( values.annual_kwh ) as number,
		goals: values.goals,
		load_profile_unit: values.load_profile_unit,
		site: { installation: values.installation, notes: values.notes.trim() },
	};
	const optional = [
		'peak_kw',
		'target_peak_kw',
		'pv_kwp',
		'backup_load_kw',
		'backup_hours',
	] as const;
	for ( const key of optional ) {
		const value = number( values[ key ] );
		if ( value !== undefined ) {
			input[ key ] = value;
		}
	}
	if ( profile ) {
		input.load_profile_csv = profile;
	}
	return input;
}

export interface CommercialPanelProps {
	config: Config;
	engine: EngineClient;
	store: StoreClient;
	defaults?: Partial< CommercialValues >;
	/** The section the customer is at, for the page's step rail. */
	onStep?: ( step: StepNumber ) => void;
}

export function CommercialPanel( {
	config,
	engine,
	store,
	defaults,
	onStep,
}: CommercialPanelProps ) {
	const locale = config.locale;
	const [ profile, setProfile ] = useState< {
		name: string;
		text: string;
	} | null >( null );
	const [ result, setResult ] = useState< Result | null >( null );
	const [ cap, setCap ] = useState< number | null >( null );
	const [ products, setProducts ] = useState< Map< number, StoreProduct > >(
		new Map()
	);
	const [ busy, setBusy ] = useState( false );
	const [ failure, setFailure ] = useState( '' );
	const [ viewed, setViewed ] = useState( 0 );
	const {
		register,
		handleSubmit,
		watch,
		setValue,
		getValues,
		formState: { errors },
	} = useForm< CommercialValues >( {
		defaultValues: { ...EMPTY, ...defaults },
		resolver: schemaResolver(
			schema,
			( values: CommercialValues ) =>
				toCommercialInput( values, locale, profile?.text ?? null ),
			locale
		),
	} );
	const goals = watch( 'goals' );
	const mobileSteps = useMemo(
		() => [
			{
				id: 'linker-ci-inputs-section',
				label: __( 'Inputs', 'linker-tools' ),
			},
			{
				id: 'linker-ci-result-section',
				label: __( 'Result', 'linker-tools' ),
			},
		],
		[]
	);
	const railCurrent = useCallback( ( index: number ) => {
		setViewed( index );
	}, [] );
	// As on the residential side: the calculation moves the rail to the
	// result, and the result section is the furthest this flow goes. Before a
	// calculation the rail stays at the inputs.
	const flowStep = result || failure || busy ? 2 : 1;
	const step = flowStep === 1 ? 1 : Math.max( flowStep, viewed + 1 );
	useEffect( () => {
		onStep?.( step as StepNumber );
	}, [ step, onStep ] );

	async function run( values: CommercialValues ) {
		setBusy( true );
		setFailure( '' );
		try {
			const input = toCommercialInput(
				values,
				locale,
				profile?.text ?? null
			);
			const answer = await engine.commercial( input );
			setResult( answer );
			setCap( input.target_peak_kw ?? null );
			// The card states the stock of the whole system it draws, so the
			// battery is read beside its inverter.
			const ids = [
				...new Set(
					answer.systems.flatMap( ( system ) =>
						system.battery
							? [ system.inverter.id, system.battery.id ]
							: [ system.inverter.id ]
					)
				),
			];
			const found = ids.length
				? await store.products( ids, config.locale ).catch( () => [] )
				: [];
			setProducts(
				new Map( found.map( ( product ) => [ product.id, product ] ) )
			);
		} catch {
			setFailure(
				__(
					'The load profile could not be read, or the calculation failed. Check the file and try again.',
					'linker-tools'
				)
			);
		}
		setBusy( false );
	}

	async function chooseCap( target: number ) {
		setValue( 'target_peak_kw', String( Math.round( target * 10 ) / 10 ) );
		if ( ! getValues( 'goals' ).includes( 'peak_shaving' ) ) {
			setValue( 'goals', [ ...getValues( 'goals' ), 'peak_shaving' ] );
		}
		await run( getValues() );
	}

	return (
		<div className="linker-flow">
			<section
				id="linker-ci-inputs-section"
				className="linker-section"
				aria-labelledby="linker-ci-title"
			>
				<div className="linker-block__head">
					<h2 className="linker-section__title" id="linker-ci-title">
						{ __( 'Inputs', 'linker-tools' ) }
					</h2>
					<p className="linker-block__step">
						{ __(
							'Step 2 · The figures that size the storage',
							'linker-tools'
						) }
					</p>
				</div>
				<form
					className="linker-form"
					noValidate
					onSubmit={ handleSubmit( run ) }
				>
					<fieldset className="linker-group">
						<legend>{ __( 'Site', 'linker-tools' ) }</legend>
						<div className="linker-form__grid">
							<Field
								id="linker-ci-plz"
								label={ __(
									'Postcode of the site',
									'linker-tools'
								) }
								error={ errors.plz?.message }
							>
								<input
									id="linker-ci-plz"
									inputMode="numeric"
									maxLength={ 5 }
									{ ...register( 'plz' ) }
								/>
							</Field>
							<Field
								id="linker-ci-grid"
								label={ __(
									'Grid connection capacity',
									'linker-tools'
								) }
								unit="kVA"
								error={ errors.grid_connection_kva?.message }
							>
								<input
									id="linker-ci-grid"
									inputMode="decimal"
									{ ...register( 'grid_connection_kva' ) }
								/>
							</Field>
							<Field
								id="linker-ci-annual"
								label={ __(
									'Annual consumption',
									'linker-tools'
								) }
								unit="kWh"
								error={ errors.annual_kwh?.message }
							>
								<input
									id="linker-ci-annual"
									inputMode="decimal"
									{ ...register( 'annual_kwh' ) }
								/>
							</Field>
						</div>
					</fieldset>
					<fieldset className="linker-group">
						<legend>{ __( 'Goals', 'linker-tools' ) }</legend>
						<div className="linker-form__grid">
							<div className="linker-form__choice linker-cards-choice">
								<label htmlFor="linker-ci-goal-peak_shaving">
									<input
										id="linker-ci-goal-peak_shaving"
										type="checkbox"
										value="peak_shaving"
										{ ...register( 'goals' ) }
									/>
									{ __( 'Peak shaving', 'linker-tools' ) }
								</label>
								<label htmlFor="linker-ci-goal-self_consumption">
									<input
										id="linker-ci-goal-self_consumption"
										type="checkbox"
										value="self_consumption"
										{ ...register( 'goals' ) }
									/>
									{ __(
										'Self-consumption of PV',
										'linker-tools'
									) }
								</label>
								<label htmlFor="linker-ci-goal-backup">
									<input
										id="linker-ci-goal-backup"
										type="checkbox"
										value="backup"
										{ ...register( 'goals' ) }
									/>
									{ __( 'Backup supply', 'linker-tools' ) }
								</label>
								<p className="linker-field__error" role="alert">
									{ errors.goals?.message ?? '' }
								</p>
							</div>
							{ goals.includes( 'peak_shaving' ) ? (
								<>
									<Field
										id="linker-ci-peak"
										label={ __(
											'Annual peak from the bill',
											'linker-tools'
										) }
										unit="kW"
										hint={ __(
											'Optional when you upload the load profile.',
											'linker-tools'
										) }
										error={ errors.peak_kw?.message }
									>
										<input
											id="linker-ci-peak"
											inputMode="decimal"
											{ ...register( 'peak_kw' ) }
										/>
									</Field>
									<Field
										id="linker-ci-target"
										label={ __(
											'Target peak',
											'linker-tools'
										) }
										unit="kW"
										error={ errors.target_peak_kw?.message }
									>
										<input
											id="linker-ci-target"
											inputMode="decimal"
											{ ...register( 'target_peak_kw' ) }
										/>
									</Field>
								</>
							) : null }
							{ goals.includes( 'self_consumption' ) ? (
								<Field
									id="linker-ci-pv"
									label={ __(
										'PV array, existing or planned',
										'linker-tools'
									) }
									unit="kWp"
									error={ errors.pv_kwp?.message }
								>
									<input
										id="linker-ci-pv"
										inputMode="decimal"
										{ ...register( 'pv_kwp' ) }
									/>
								</Field>
							) : null }
							{ goals.includes( 'backup' ) ? (
								<>
									<Field
										id="linker-ci-backup"
										label={ __(
											'Load to keep running',
											'linker-tools'
										) }
										unit="kW"
										error={ errors.backup_load_kw?.message }
									>
										<input
											id="linker-ci-backup"
											inputMode="decimal"
											{ ...register( 'backup_load_kw' ) }
										/>
									</Field>
									<Field
										id="linker-ci-hours"
										label={ __(
											'For how long',
											'linker-tools'
										) }
										unit="h"
										error={ errors.backup_hours?.message }
									>
										<input
											id="linker-ci-hours"
											inputMode="decimal"
											{ ...register( 'backup_hours' ) }
										/>
									</Field>
								</>
							) : null }
							<FilePicker
								id="linker-ci-profile"
								label={ __(
									'15-minute load profile (CSV, optional)',
									'linker-tools'
								) }
								button={ __( 'Choose file', 'linker-tools' ) }
								accept=".csv,text/csv,text/plain"
								chosen={
									profile?.name ??
									__( 'No file chosen', 'linker-tools' )
								}
								hint={ __(
									'One value per line, optionally after a timestamp; the last number of each line counts.',
									'linker-tools'
								) }
								onChoose={ async ( file ) =>
									setProfile(
										file
											? {
													name: file.name,
													text: await file.text(),
												}
											: null
									)
								}
							/>
							<Field
								id="linker-ci-unit"
								label={ __(
									'Values in the file',
									'linker-tools'
								) }
							>
								<select
									id="linker-ci-unit"
									{ ...register( 'load_profile_unit' ) }
								>
									<option value="kW">
										{ __(
											'Average power in kW',
											'linker-tools'
										) }
									</option>
									<option value="kWh">
										{ __(
											'Energy per 15 minutes in kWh',
											'linker-tools'
										) }
									</option>
								</select>
							</Field>
							<Field
								id="linker-ci-site"
								label={ __(
									'Installation place',
									'linker-tools'
								) }
							>
								<select
									id="linker-ci-site"
									{ ...register( 'installation' ) }
								>
									<option value="unknown">
										{ __( 'Not decided', 'linker-tools' ) }
									</option>
									<option value="indoor">
										{ __( 'Indoors', 'linker-tools' ) }
									</option>
									<option value="outdoor">
										{ __( 'Outdoors', 'linker-tools' ) }
									</option>
								</select>
							</Field>
							<Field
								id="linker-ci-notes"
								label={ __(
									'Site conditions',
									'linker-tools'
								) }
								hint={ __(
									'Space, access, fire protection: anything we should know.',
									'linker-tools'
								) }
							>
								<textarea
									id="linker-ci-notes"
									rows={ 3 }
									maxLength={ 500 }
									{ ...register( 'notes' ) }
								/>
							</Field>
						</div>
					</fieldset>
					<div className="linker-form__submit">
						<button
							type="submit"
							className="linker-button linker-button--primary"
							disabled={ busy }
							aria-busy={ busy }
						>
							{ busy
								? __( 'Calculating…', 'linker-tools' )
								: __( 'Calculate storage', 'linker-tools' ) }
						</button>
					</div>
				</form>
			</section>
			<section
				id="linker-ci-result-section"
				className="linker-section"
				aria-labelledby="linker-ci-result-title"
				aria-busy={ busy }
			>
				<div className="linker-block__head">
					<h2
						className="linker-section__title"
						id="linker-ci-result-title"
					>
						{ __( 'Result', 'linker-tools' ) }
					</h2>
					<p className="linker-block__step">
						{ __(
							'Step 3 · Sized storage, or indicative ranges',
							'linker-tools'
						) }
					</p>
				</div>
				{ failure ? (
					<p
						className="linker-empty linker-empty--error"
						role="alert"
					>
						{ failure }
					</p>
				) : null }
				{ ! result && ! failure ? (
					<p className="linker-empty">
						{ __(
							'With a 15-minute load profile we size the storage; without one you get indicative ranges.',
							'linker-tools'
						) }
					</p>
				) : null }
				{ result ? (
					<CommercialResult
						result={ result }
						locale={ locale }
						cap={ cap }
						products={ products }
						onChooseCap={ chooseCap }
					/>
				) : null }
			</section>
			<MobileNavigation steps={ mobileSteps } onCurrent={ railCurrent } />
		</div>
	);
}
