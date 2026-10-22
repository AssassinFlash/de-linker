/** Preserve accepted ordinary editor bytes before a verified surface is quarantined or left. */
import type { DraftContext } from './draftContext';
import type { Upload } from '../attachments/prepare';
import { buildQuestion } from './conversation';
import { pageFailureStore } from './failure';
import { FailureJournal, type FailureWrite } from './ownedFailure';
export interface EditingSnapshot {
	text: string;
	uploads: Upload[];
	missing: string[];
}
/**
 * Never assigns the freshly returned B principal to A's already accepted bytes.
 * @param context  The mounted surface identity and epoch.
 * @param snapshot Accepted text, prepared files, and explicit reselection names.
 */
export function preserveEditing(
	context: DraftContext,
	snapshot: EditingSnapshot
): FailureWrite | null {
	const owner = context.editor;
	const identity = context.identity;
	if (
		! owner ||
		! identity ||
		context.phase !== 'ready' ||
		identity.scope !== owner.scope
	) {
		return null;
	}
	const journal = new FailureJournal( pageFailureStore(), identity );
	if ( ! (
		snapshot.text ||
		snapshot.uploads.length ||
		snapshot.missing.length
	) ) {
		const candidate = journal.editing( owner );
		if ( candidate === undefined ) {
			return {
				state: { phase: 'clear', draft: null, kind: null },
				cursor: { owner, revision: 0, raw: null },
				durable: false,
				conflict: true,
			};
		}
		if (
			candidate?.record.editing &&
			candidate.cursor.owner.attempt === owner.attempt
		) {
			const removed = journal.consume( candidate.cursor );
			if ( removed ) {
				context.releaseEditor();
			}
			return {
				state: { phase: 'clear', draft: null, kind: null },
				cursor: candidate.cursor,
				durable: removed && ! candidate.cursor.memory,
				conflict: ! removed,
			};
		}
		// No accepted bytes remain; a later keystroke must get a new attempt.
		if ( ! candidate ) {
			context.releaseEditor();
		}
		return null;
	}

	return new FailureJournal( pageFailureStore(), identity ).begin(
		{
			phase: 'editing',
			kind: null,
			draft: {
				owner,
				editing: true,
				text: snapshot.text,
				question:
					buildQuestion( snapshot.text, snapshot.uploads ) ||
					snapshot.missing.join( '\n' ),
				uploads: snapshot.uploads,
				omitted: snapshot.missing,
			},
		},
		owner
	);
}
