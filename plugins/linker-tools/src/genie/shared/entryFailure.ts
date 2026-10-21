/** Scope validation for the shared failed-turn readers and transport consumers. */
import type { GenieConfig } from '../config';
import { entryScope } from './entryDraft';
import { FAILURE_KEY, readFailure, type FailureStore } from './failure';

export class EntryScopeError extends Error {
	constructor( public readonly changed: boolean ) {
		super( 'entry-scope' );
	}
}
/**
 * Validate immediately before transport, after any queued history/metadata read.
 * @param config   Current native REST identity.
 * @param expected Scope of the entry-derived text/files, absent for legacy turns.
 */
export async function assertEntryScope(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
	expected?: string
): Promise< void > {
	if ( ! expected ) {
		return;
	}
	let scope: string;
	try {
		scope = await entryScope( config, true );
	} catch {
		throw new EntryScopeError( false );
	}
	if ( scope !== expected ) {
		throw new EntryScopeError( true );
	}
}
/**
 * No cached private text is returned before verification. Compare exact stored bytes
 * after the await so a late reader cannot remove/reconcile a newer failed turn.
 * @param config Current native REST identity.
 * @param store  Shared failure record, never a conversation/history store.
 */
export async function verifiedEntryFailure(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
	store: FailureStore
) {
	const raw = store.getItem( FAILURE_KEY );
	const record = readFailure( store );
	if ( record?.entryId ) {
		try {
			await assertEntryScope(
				config,
				record.entryScope || 'missing-scope'
			);
		} catch ( error ) {
			if (
				error instanceof EntryScopeError &&
				error.changed &&
				store.getItem( FAILURE_KEY ) === raw
			) {
				store.removeItem( FAILURE_KEY );
			}
			return null;
		}
	}
	return store.getItem( FAILURE_KEY ) === raw
		? { record, unchanged: () => store.getItem( FAILURE_KEY ) === raw }
		: null;
}
