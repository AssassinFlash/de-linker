import { useCallback, useEffect, useRef, useState } from '@wordpress/element';
import type { TurnVerification } from '../api/turn';

interface OwnedAttempt {
	controller: AbortController;
	dispatched: boolean;
	owner: VerificationOwner;
	slot: () => HTMLDivElement | null;
}

interface VerificationOwner {
	owns: () => boolean;
	settle: () => Promise< boolean >;
	valid: () => boolean;
}

/**
 * Bind one pre-dispatch verification to its actual editor and mounted slot.
 *
 * This runs only in the browser: it hands the native widget a live node and
 * cancels through `window.linkerPublicProtection`, neither of which exists
 * during a static render.
 *
 * @param waiting Whether the current surface is waiting for a turn.
 */
export function useVerificationStage( waiting: boolean ) {
	const target = useRef< HTMLDivElement | null >( null );
	const active = useRef< OwnedAttempt | null >( null );
	const [ pending, setPending ] = useState( false );
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
		const owner = attempt.slot();
		if ( owner ) {
			owner.hidden = true;
		}
		const widget = owner?.querySelector< HTMLElement >(
			'[data-linker-resource-verification="genie"]'
		);
		if ( widget ) {
			window.linkerPublicProtection?.cancel?.( 'genie', widget );
		}
	}, [] );
	const slot = useCallback(
		( node: HTMLDivElement | null ) => {
			if ( target.current && ! node ) {
				cancel();
			}
			target.current = node;
		},
		[ cancel ]
	);
	const begin = useCallback(
		( owner: VerificationOwner ): TurnVerification => {
			cancel();
			let ownedSlot: HTMLDivElement | null = null;
			const attempt: OwnedAttempt = {
				controller: new AbortController(),
				dispatched: false,
				owner,
				slot: () => {
					ownedSlot ??= target.current;
					return ownedSlot;
				},
			};
			active.current = attempt;
			// The same condition the shared client uses to run a challenge at
			// all (resourceFetch skips proof in `off` and `observe`), so the
			// turn's preparation bound matches what will really happen.
			const challenge =
				window.linkerPublicProtectionConfig?.mode === 'enforce';
			setPending( challenge );
			return {
				slot: attempt.slot,
				signal: attempt.controller.signal,
				challenge,
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
					setPending( false );
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
	return { slot, begin, cancel, pending: waiting && pending };
}
