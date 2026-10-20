/**
 * The failed-turn record for both Genie surfaces (ticket #411).
 *
 * The dock and the home hero keep the same record, the same chips, and the
 * same decision to send a retry. Each surface still sends on its own route.
 */

/**
 * WordPress dependencies
 */
import { useCallback, useEffect, useRef, useState } from '@wordpress/element';

/**
 * Internal dependencies
 */
import type { Upload } from '../attachments/prepare';
import {
	failureReducer,
	failureWithUploads,
	pageFailureStore,
	retryPayload,
	writeFailure,
	type FailureDraft,
	type FailureEvent,
	type FailureKind,
	type FailureMessage,
	type FailureState,
} from './failure';

/** The composer files this record reads and puts back. */
export interface FailureFiles {
	uploads: readonly Upload[];
	restore: ( uploads: Upload[] ) => void;
	clear: () => void;
}

/** A retry that is allowed to send. The machine is already `pending`. */
export interface OpenRetry {
	draft: FailureDraft;
	kind: FailureKind;
}

/**
 * The shared failure record.
 *
 * @param files The composer's files.
 */
export function useFailure( files: FailureFiles ) {
	const failureState = useRef< FailureState >( {
		phase: 'clear',
		draft: null,
		kind: null,
	} );
	const [ omitted, setOmitted ] = useState< string[] >( [] );
	// True while this component is putting chips back, so that paint is not
	// read as the customer removing them.
	const placingChips = useRef( false );
	const filesRef = useRef( files );
	filesRef.current = files;

	const commitFailure = useCallback( ( event: FailureEvent ) => {
		const reduced = failureReducer( failureState.current, event );
		const stored = writeFailure( pageFailureStore(), reduced );
		failureState.current = stored;
		setOmitted(
			'failed' === stored.phase ? ( stored.draft?.omitted ?? [] ) : []
		);
		return stored;
	}, [] );

	const placeChips = useCallback( ( chips: readonly Upload[] ) => {
		placingChips.current = true;
		if ( chips.length > 0 ) {
			filesRef.current.restore( [ ...chips ] );
		} else {
			filesRef.current.clear();
		}
	}, [] );

	// A chip removed, or a file attached again, while the failure is up.
	useEffect( () => {
		if ( placingChips.current ) {
			placingChips.current = false;
			return;
		}
		const next = failureWithUploads( failureState.current, files.uploads );
		if ( next === failureState.current ) {
			return;
		}
		failureState.current = writeFailure( pageFailureStore(), next );
		setOmitted( failureState.current.draft?.omitted ?? [] );
	}, [ files.uploads ] );

	/**
	 * Leaves `failed` only when a retry would send. A second call finds
	 * `pending` and does not send.
	 *
	 * @param thread The thread the retry would post on top of.
	 */
	const openRetry = useCallback(
		( thread: readonly FailureMessage[] ): OpenRetry | null => {
			const current = failureState.current;
			if (
				'failed' !== current.phase ||
				! current.draft ||
				! current.kind ||
				! retryPayload( current, thread, filesRef.current.uploads )
			) {
				return null;
			}
			const opened = { draft: current.draft, kind: current.kind };
			commitFailure( { type: 'retry' } );
			return opened;
		},
		[ commitFailure ]
	);

	/**
	 * The payload a retry would send, without changing the record. The
	 * catch of a send that never left still has this.
	 *
	 * @param draft  The failed question, as it was when the retry opened.
	 * @param kind   Which failure.
	 * @param thread The thread to send on top of.
	 */
	const previewRetry = useCallback(
		< T extends FailureMessage >(
			draft: FailureDraft,
			kind: FailureKind,
			thread: readonly T[]
		) =>
			retryPayload(
				{ phase: 'failed', draft, kind },
				thread,
				filesRef.current.uploads
			),
		[]
	);

	/**
	 * The payload against the thread now, or null after the failure is put
	 * back. An empty upstream question does not send.
	 *
	 * @param draft  The failed question, as it was when the retry opened.
	 * @param kind   Which failure.
	 * @param thread The thread to send on top of.
	 */
	const payloadOrRestore = useCallback(
		< T extends FailureMessage >(
			draft: FailureDraft,
			kind: FailureKind,
			thread: readonly T[]
		) => {
			const payload = retryPayload(
				{ phase: 'failed', draft, kind },
				thread,
				filesRef.current.uploads
			);
			if ( ! payload ) {
				commitFailure( { type: kind } );
				return null;
			}
			return payload;
		},
		[ commitFailure ]
	);

	return {
		failureState,
		omitted,
		setOmitted,
		commitFailure,
		placeChips,
		openRetry,
		previewRetry,
		payloadOrRestore,
	};
}
