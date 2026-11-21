import { useCallback, useEffect, useRef } from '@wordpress/element';
import type { TurnOwner } from '../api/turn';

interface OwnedAttempt {
	controller: AbortController;
	dispatched: boolean;
	owner: VerificationOwner;
}

interface VerificationOwner {
	owns: () => boolean;
	settle: () => Promise< boolean >;
	valid: () => boolean;
}

/** Retain the current conversation owner until the turn actually leaves the browser. */
export function useTurnOwner() {
	const active = useRef< OwnedAttempt | null >( null );
	const cancel = useCallback( () => {
		const attempt = active.current;
		if (
			! attempt ||
			attempt.dispatched ||
			attempt.controller.signal.aborted
		) {
			return;
		}
		attempt.controller.abort( new Error( 'verification_cancelled' ) );
	}, [] );
	const begin = useCallback(
		( owner: VerificationOwner ): TurnOwner => {
			cancel();
			const attempt: OwnedAttempt = {
				controller: new AbortController(),
				dispatched: false,
				owner,
			};
			active.current = attempt;
			return {
				signal: attempt.controller.signal,
				beforeDispatch: async () => {
					if ( ! ( await attempt.owner.settle() ) ) {
						throw new Error( 'verification_cancelled' );
					}
				},
				onDispatch: () => {
					if (
						active.current !== attempt ||
						attempt.controller.signal.aborted ||
						! attempt.owner.valid()
					) {
						throw new Error( 'verification_cancelled' );
					}
					attempt.dispatched = true;
				},
			};
		},
		[ cancel ]
	);
	// Deliberately runs after every render, with no dependency list: the lease
	// this attempt was bound to can be invalidated by a history/owner switch
	// that changes no state this component holds, so there is no value to
	// depend on that would be re-evaluated at the right moment. The guard is
	// the `owns()` check itself, which is cheap and reads live context state.
	useEffect( () => {
		if (
			active.current &&
			! active.current.dispatched &&
			! active.current.owner.owns()
		) {
			cancel();
		}
	} );
	return { begin, cancel };
}
