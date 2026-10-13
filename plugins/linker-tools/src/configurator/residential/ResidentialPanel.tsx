/**
 * Residential flow: inputs (with the optional roof step), the proposed system,
 * the design report. States of the result: empty, computing, error, no
 * candidate, solution; the solution can be added to the draft and saved.
 */

/**
 * WordPress dependencies
 */
import {
	lazy,
	Suspense,
	useEffect,
	useMemo,
	useRef,
	useState,
} from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { EngineError, type EngineClient } from '../api/engine';
import { saveSolution } from '../api/solutions';
import type { AddStatus, StoreClient } from '../api/store';
import type { Config } from '../config';
import { MobileNavigation } from '../MobileNavigation';
import { ReportView } from '../report/ReportView';
import { NoCandidate } from '../solution/NoCandidate';
import { Solution, type SaveState } from '../solution/Solution';
import type {
	ResidentialInput,
	ResidentialResult,
	StoreProduct,
} from '../types';
import {
	ResidentialForm,
	type ResidentialValues,
	type RoofSelection,
} from './ResidentialForm';
// The map libraries load only when the roof step opens.
const RoofStep = lazy( () =>
	import( '../roof/RoofStep' ).then( ( module ) => ( {
		default: module.RoofStep,
	} ) )
);

type Status = 'empty' | 'computing' | 'error' | 'done';

export interface ResidentialPanelProps {
	config: Config;
	engine: EngineClient;
	store: StoreClient;
	/** Stories and tests start from given inputs. */
	defaults?: Partial< ResidentialValues >;
	initialRoof?: RoofSelection | null;
}

function errorText( error: unknown ): string {
	if ( error instanceof EngineError ) {
		if ( error.kind === 'unavailable' ) {
			return __(
				'The yield service did not answer. Try again in a minute.',
				'linker-tools'
			);
		}
		if ( error.kind === 'invalid' && error.field === 'plz' ) {
			return __(
				'We do not know this postcode. Check it and try again.',
				'linker-tools'
			);
		}
	}
	return __( 'The calculation failed. Try again.', 'linker-tools' );
}

export function ResidentialPanel( {
	config,
	engine,
	store,
	defaults,
	initialRoof = null,
}: ResidentialPanelProps ) {
	const [ roof, setRoof ] = useState< RoofSelection | null >( initialRoof );
	const [ roofPlz, setRoofPlz ] = useState< string | null >( null );
	const [ input, setInput ] = useState< ResidentialInput | null >( null );
	const [ result, setResult ] = useState< ResidentialResult | null >( null );
	const [ status, setStatus ] = useState< Status >( 'empty' );
	const [ error, setError ] = useState( '' );
	const [ products, setProducts ] = useState< Map< number, StoreProduct > >(
		new Map()
	);
	const [ statuses, setStatuses ] = useState< Map< number, AddStatus > >(
		new Map()
	);
	const [ adding, setAdding ] = useState( false );
	const [ addOutcome, setAddOutcome ] = useState<
		'none' | 'complete' | 'partial'
	>( 'none' );
	const [ saveState, setSaveState ] = useState< SaveState >( 'idle' );
	const [ savedUrl, setSavedUrl ] = useState< string | null >( null );
	const results = useRef< HTMLDivElement >( null );
	const reportReady = status === 'done' && !! result?.selected;
	const mobileSteps = useMemo(
		() => [
			{
				id: 'linker-inputs-section',
				label: __( 'Inputs', 'linker-tools' ),
			},
			{
				id: 'linker-solution-section',
				label: __( 'Solution', 'linker-tools' ),
			},
			...( reportReady
				? [
						{
							id: 'linker-report-section',
							label: __( 'Design report', 'linker-tools' ),
						},
					]
				: [] ),
		],
		[ reportReady ]
	);

	useEffect( () => {
		if ( config.openRoof && defaults?.plz ) {
			setRoofPlz( defaults.plz );
		}
	}, [ config.openRoof, defaults?.plz ] );

	async function calculate( next: ResidentialInput ) {
		setInput( next );
		setStatus( 'computing' );
		setError( '' );
		setStatuses( new Map() );
		setAddOutcome( 'none' );
		setSaveState( 'idle' );
		results.current?.scrollIntoView( {
			block: 'start',
			behavior: 'smooth',
		} );
		try {
			const answer = await engine.residential( next );
			setResult( answer );
			setStatus( 'done' );
			const ids = ( answer.selected?.lines ?? [] )
				.map( ( line ) => line.product?.id )
				.filter( ( id ): id is number => id !== undefined );
			const found = await store
				.products( ids, config.locale )
				.catch( () => [] );
			setProducts(
				new Map( found.map( ( product ) => [ product.id, product ] ) )
			);
		} catch ( failure ) {
			setError( errorText( failure ) );
			setStatus( 'error' );
		}
	}

	function draftLines() {
		return ( result?.selected?.lines ?? [] )
			.filter( ( line ) => line.product )
			.map( ( line ) => ( {
				productId: line.product!.id,
				quantity: line.quantity,
			} ) );
	}

	async function addAll() {
		setAdding( true );
		setAddOutcome( 'none' );
		const complete = await store.addAll( draftLines(), ( id, state ) =>
			setStatuses( ( current ) => new Map( current ).set( id, state ) )
		);
		setAddOutcome( complete ? 'complete' : 'partial' );
		setAdding( false );
	}

	async function save() {
		if ( ! input || ! result?.selected ) {
			return;
		}
		setSaveState( 'saving' );
		try {
			const saved = await saveSolution(
				config.restUrl,
				config.restNonce,
				{
					kind: 'residential',
					title: `${ result.selected.inverter.brand } ${ result.selected.inverter.model }, ${ input.plz }`,
					input,
					lines: draftLines(),
				}
			);
			setSavedUrl( saved.url );
			setSaveState( 'saved' );
		} catch {
			setSaveState( 'failed' );
		}
	}

	return (
		<div className="linker-flow">
			<section
				id="linker-inputs-section"
				className="linker-section"
				aria-labelledby="linker-inputs-title"
			>
				<div className="linker-block__head">
					<h2
						className="linker-section__title"
						id="linker-inputs-title"
					>
						{ __( 'Inputs', 'linker-tools' ) }
					</h2>
					<p className="linker-block__step">
						{ __(
							'Step 2 · The figures that size the system',
							'linker-tools'
						) }
					</p>
				</div>
				<ResidentialForm
					locale={ config.locale }
					defaults={ defaults }
					roof={ roof }
					busy={ status === 'computing' }
					onOpenRoof={ setRoofPlz }
					onRemoveRoof={ () => setRoof( null ) }
					onSubmit={ calculate }
				/>
				{ roofPlz ? (
					<Suspense
						fallback={
							<p className="linker-empty" role="status">
								{ __( 'Loading the map…', 'linker-tools' ) }
							</p>
						}
					>
						<RoofStep
							plz={ roofPlz }
							locale={ config.locale }
							engine={ engine }
							onApply={ ( selection ) => {
								setRoof( selection );
								setRoofPlz( null );
							} }
							onClose={ () => setRoofPlz( null ) }
						/>
					</Suspense>
				) : null }
			</section>
			<section
				id="linker-solution-section"
				className="linker-section"
				aria-labelledby="linker-solution-title"
				aria-busy={ status === 'computing' }
				ref={ results }
			>
				<div className="linker-block__head">
					<h2
						className="linker-section__title"
						id="linker-solution-title"
					>
						{ __( 'Solution', 'linker-tools' ) }
					</h2>
					<p className="linker-block__step">
						{ __(
							'Step 3 · The released system for these inputs',
							'linker-tools'
						) }
					</p>
				</div>
				{ status === 'empty' ? (
					<p className="linker-empty">
						{ __(
							'Enter the household and calculate: the proposed system appears here.',
							'linker-tools'
						) }
					</p>
				) : null }
				{ status === 'computing' ? (
					<div
						className="linker-empty linker-empty--busy"
						role="status"
					>
						<span className="linker-spinner" aria-hidden="true" />
						{ __(
							'Calculating yield, storage and the released system…',
							'linker-tools'
						) }
					</div>
				) : null }
				{ status === 'error' ? (
					<div
						className="linker-empty linker-empty--error"
						role="alert"
					>
						<p>{ error }</p>
						{ input ? (
							<button
								type="button"
								className="linker-button linker-button--secondary"
								onClick={ () => calculate( input ) }
							>
								{ __( 'Try again', 'linker-tools' ) }
							</button>
						) : null }
					</div>
				) : null }
				{ status === 'done' && result && ! result.selected ? (
					<NoCandidate
						result={ result }
						onBack={ () =>
							document
								.getElementById( 'linker-inputs-title' )
								?.scrollIntoView( { behavior: 'smooth' } )
						}
					/>
				) : null }
				{ status === 'done' && result?.selected && input ? (
					<Solution
						result={ result }
						locale={ config.locale }
						products={ products }
						statuses={ statuses }
						adding={ adding }
						addOutcome={ addOutcome }
						saveState={ saveState }
						savedUrl={ savedUrl }
						onSwapInverter={ ( id ) =>
							calculate( {
								...input,
								inverter_id: id,
								battery_id: undefined,
							} )
						}
						onSwapBattery={ ( id ) =>
							calculate( { ...input, battery_id: id } )
						}
						onAddAll={ addAll }
						onSave={ save }
					/>
				) : null }
			</section>
			{ status === 'done' && result?.selected && input ? (
				<section
					id="linker-report-section"
					className="linker-section"
					aria-labelledby="linker-report-title"
				>
					<div className="linker-block__head">
						<h2
							className="linker-section__title"
							id="linker-report-title"
						>
							{ result.report.title }
						</h2>
						<p className="linker-block__step">
							{ __( 'Design report', 'linker-tools' ) }
						</p>
					</div>
					<ReportView
						report={ result.report }
						input={ input }
						engine={ engine }
					/>
				</section>
			) : null }
			<MobileNavigation steps={ mobileSteps } />
		</div>
	);
}
