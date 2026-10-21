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
	useCallback,
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
import { saveSolution, type SavedSolution } from '../api/solutions';
import type { AddStatus, StoreClient } from '../api/store';
import type { Config } from '../config';
import { MobileNavigation } from '../MobileNavigation';
import { ReportView, type AskState } from '../report/ReportView';
import { NoCandidate } from '../solution/NoCandidate';
import { Solution, type SaveState } from '../solution/Solution';
import type { StepNumber } from '../Steps';
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
	/** The section the customer is at, for the page's step rail. */
	onStep?: ( step: StepNumber ) => void;
}

/**
 * The design a save describes: this input and the selection the engine made
 * from it. A save belongs to one design; a recalculation makes an older save's
 * record stale and it must not be offered as the current solution (#496).
 *
 * @param input    The configurator input.
 * @param selected The engine's selection for that input.
 */
function designKey(
	input: ResidentialInput,
	selected: NonNullable< ResidentialResult[ 'selected' ] >
): string {
	const lines = selected.lines
		.map( ( line ) => `${ line.product?.id ?? 0 }x${ line.quantity }` )
		.join( ',' );
	return `${ JSON.stringify( input ) }|${ selected.inverter.id }|${
		selected.battery?.product.id ?? 0
	}|${ lines }`;
}

function errorText( error: unknown ): string {
	if ( error instanceof EngineError ) {
		if ( error.kind === 'limited' ) {
			return __(
				'The calculation is temporarily unavailable. Your entries are still here. Please try again later.',
				'linker-tools'
			);
		}
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
	onStep,
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
	// The save this panel made and the design it belongs to, so "Ask Genie"
	// saves once and asks about the solution it already has (#496). A
	// recalculation clears it; a save of another design never fills it.
	const saved = useRef< { key: string; record: SavedSolution } | null >(
		null
	);
	const [ askState, setAskState ] = useState< AskState >( 'idle' );
	// A double click must not save twice: the state disables the button on the
	// next render, the ref guards the same tick; a save in flight is the one
	// promise both the Save button and Ask Genie await, and only for the design
	// it was started for.
	const askingKey = useRef< string | null >( null );
	const saveInFlight = useRef< {
		key: string;
		promise: Promise< SavedSolution | null >;
	} | null >( null );
	// Bumped by every calculation: a save or an ask that resolves after it
	// belongs to the previous design and is dropped silently.
	const designEpoch = useRef( 0 );
	const results = useRef< HTMLDivElement >( null );
	const [ viewed, setViewed ] = useState( 0 );
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
	const railCurrent = useCallback( ( index: number ) => {
		setViewed( index );
	}, [] );
	// The rail shows how far the flow has come: a calculation (even a running
	// or failed one) leaves the inputs, and reaching the report advances to it.
	// Before a calculation the rail stays at the inputs, even when the empty
	// Solution section is on screen; scrolling back does not undo a
	// calculation.
	const flowStep = status === 'empty' ? 1 : 2;
	const step = flowStep === 1 ? 1 : Math.max( flowStep, viewed + 1 );
	useEffect( () => {
		onStep?.( step as StepNumber );
	}, [ step, onStep ] );

	useEffect( () => {
		if ( config.openRoof && defaults?.plz ) {
			setRoofPlz( defaults.plz );
		}
	}, [ config.openRoof, defaults?.plz ] );

	async function calculate( next: ResidentialInput ) {
		designEpoch.current += 1;
		setInput( next );
		setStatus( 'computing' );
		setError( '' );
		setStatuses( new Map() );
		setAddOutcome( 'none' );
		setSaveState( 'idle' );
		saved.current = null;
		setAskState( 'idle' );
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

	async function save( fromAsk = false ): Promise< SavedSolution | null > {
		if ( ! input || ! result?.selected ) {
			return null;
		}
		const savingInput = input;
		const savingSelected = result.selected;
		const key = designKey( savingInput, savingSelected );
		// A click on Ask while this design's save is in flight awaits that save;
		// a save of another design is not reused.
		if ( saveInFlight.current?.key === key ) {
			return saveInFlight.current.promise;
		}
		const epoch = designEpoch.current;
		// The values this save describes, fixed now: a recalculation while the
		// POST is in flight must not change what the saved solution holds.
		const savingLines = draftLines();
		const savingReport = result.report;
		const work = ( async (): Promise< SavedSolution | null > => {
			setSaveState( 'saving' );
			try {
				// The design report exists once this input has a solution. The
				// PDF is the engine's existing report/pdf answer for that input
				// (logo stays on the download button; it is not part of the input).
				const reportPdf = savingReport
					? await engine.reportPdf( savingInput, null )
					: null;
				const record = await saveSolution(
					config.restUrl,
					config.restNonce,
					{
						kind: 'residential',
						title: `${ savingSelected.inverter.brand } ${ savingSelected.inverter.model }, ${ savingInput.plz }`,
						input: savingInput,
						lines: savingLines,
						reportPdf,
					},
					config.locale
				);
				// A recalculation while the save or its report PDF was in
				// flight makes this record stale: drop it silently, never
				// offer it as the current design's solution.
				if ( designEpoch.current === epoch ) {
					setSavedUrl( record.url );
					saved.current = { key, record };
					setSaveState( 'saved' );
				}
				return record;
			} catch {
				// One failure sentence: the Save button's own status for its
				// click, the report's Ask status when Ask started the save.
				if ( designEpoch.current === epoch ) {
					setSaveState( fromAsk ? 'idle' : 'failed' );
				}
				return null;
			}
		} )();
		saveInFlight.current = { key, promise: work };
		try {
			return await work;
		} finally {
			if ( saveInFlight.current?.promise === work ) {
				saveInFlight.current = null;
			}
		}
	}

	// "Ask Genie" (#496): the solution is saved first, through the one save
	// path above, and only then does Genie open — with the saved solution's id
	// in the page context. A save this panel already made is reused, so a
	// second click does not save a duplicate. A guest's save waits in the
	// WooCommerce session and has no post (C30): there is nothing to read yet,
	// and the report asks them to sign in, where the claim makes it theirs.
	async function ask() {
		if ( ! input || ! result?.selected ) {
			return;
		}
		const key = designKey( input, result.selected );
		if ( askingKey.current === key ) {
			return;
		}
		const epoch = designEpoch.current;
		askingKey.current = key;
		setAskState( 'saving' );
		let target: SavedSolution | null = null;
		try {
			target =
				saved.current?.key === key
					? saved.current.record
					: await save( true );
		} finally {
			if ( askingKey.current === key ) {
				askingKey.current = null;
			}
		}
		// A recalculation happened while the save ran: the record describes the
		// previous design. The new report's Ask starts its own save; do not
		// open Genie on the design the customer has already left.
		if ( designEpoch.current !== epoch ) {
			return;
		}
		if ( ! target ) {
			// The report carries the failure sentence; the Save status would
			// repeat it (or still show a save the customer did not click).
			setSaveState( 'idle' );
			setAskState( 'failed' );
			return;
		}
		if ( target.id < 1 ) {
			setAskState( 'signin' );
			return;
		}
		setAskState( 'idle' );
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-ask', {
				detail: {
					message: __(
						'What are the figures in my saved solution?',
						'linker-tools'
					),
					solution: target.id,
				},
			} )
		);
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
						onSave={ () => void save() }
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
						onAsk={ ask }
						askState={ askState }
						savedUrl={ savedUrl }
					/>
				</section>
			) : null }
			<MobileNavigation steps={ mobileSteps } onCurrent={ railCurrent } />
		</div>
	);
}
