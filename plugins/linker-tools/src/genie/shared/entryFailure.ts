/** The single verified failed-draft selector used by both surfaces and their controller. */
import type { GenieConfig } from '../config';
import type { DraftContext } from './draftContext';
import { nativeScope } from './nativeScope';
import { FAILURE_KEY, type FailureStore } from './failure';
import { FailureJournal } from './ownedFailure';

export class EntryScopeError extends Error {
	constructor( public readonly changed: boolean ) {
		super( 'entry-scope' );
	}
}
/**
 * Fresh verification after queued thread/metadata reads; required for ordinary and entry bytes.
 * @param config   The currently mounted native routes and REST nonce.
 * @param expected The immutable owner expected by this operation.
 */
export async function assertEntryScope(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
	expected?: string
): Promise< void > {
	if ( ! expected ) {
		throw new EntryScopeError( true );
	}
	let scope: string;
	try {
		scope = ( await nativeScope( config, true ) ).scope;
	} catch {
		throw new EntryScopeError( false );
	}
	if ( scope !== expected ) {
		throw new EntryScopeError( true );
	}
}
/**
 * Never return private bytes before authority; unknown v1 and foreign scopes stay untouched.
 * @param config  The currently mounted native routes and REST nonce.
 * @param store   The underlying tab storage adapter.
 * @param context The mounted surface identity and epoch.
 */
export async function verifiedEntryFailure(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
	store: FailureStore,
	context?: DraftContext
) {
	let legacyRaw: string | null = null;
	let legacyReadable = false;
	try {
		legacyRaw = store.getItem( FAILURE_KEY );
		legacyReadable = true;
	} catch {
		/* Memory-only candidates still require native verification. */
	}
	const previousScope = context?.identity?.scope;
	try {
		const identity = context
			? await context.verify( true )
			: await nativeScope( config, true );
		if ( legacyReadable && store.getItem( FAILURE_KEY ) !== legacyRaw ) {
			return null;
		}
		const journal = new FailureJournal( store, identity );
		// An old reader can invalidate its surface, but cannot migrate/select the next owner's record.
		const candidate =
			previousScope && previousScope !== identity.scope
				? null
				: journal.candidate( context?.editor?.attempt );
		return {
			identity,
			journal,
			candidate,
			record: candidate?.record ?? null,
			unchanged: () => ! candidate || journal.matches( candidate.cursor ),
		};
	} catch {
		return null;
	}
}
