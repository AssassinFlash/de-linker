/** Preserve accepted ordinary editor bytes before a verified surface is quarantined or left. */
import type { DraftContext } from './draftContext';
import type { NativeScope } from './nativeScope';
import type { FailureOwner } from './failure';
import type { Upload } from '../attachments/prepare';
import { buildQuestion } from './conversation';
import { pageFailureStore } from './failure';
import {
	FailureJournal,
	type FailureCursor,
	type FailureWrite,
} from './ownedFailure';
export interface EditingSnapshot {
	text: string;
	uploads: Upload[];
	missing: string[];
}
/** Captured at the explicit operation's acceptance, never inferred from a later principal. */
export interface EditingAuthority {
	owner: FailureOwner;
	identity: NativeScope;
	/** Exact checkpoint acknowledged by the mounted editor or accepted operation. */
	cursor?: FailureCursor;
}
/**
 * Never assigns the freshly returned B principal to A's already accepted bytes.
 * @param context  The mounted surface identity and epoch.
 * @param snapshot Accepted text, prepared files, and explicit reselection names.
 * @param accepted Original authority for bytes already accepted by an ongoing operation.
 */
export function preserveEditing(
	context: DraftContext,
	snapshot: EditingSnapshot,
	accepted?: EditingAuthority
): FailureWrite | null {
	const owner = accepted?.owner ?? context.editor;
	const identity = accepted?.identity ?? context.identity;
	if (
		! owner ||
		! identity ||
		( ! accepted && context.phase !== 'ready' ) ||
		identity.scope !== owner.scope
	) {
		return null;
	}
	const journal = new FailureJournal( pageFailureStore(), identity );
	let cursor = accepted?.cursor;
	const empty = ! (
		snapshot.text ||
		snapshot.uploads.length ||
		snapshot.missing.length
	);
	if ( cursor && empty ) {
		const current = journal.rebase( cursor );
		if (
			cursor.owner.scope !== owner.scope ||
			cursor.owner.attempt !== owner.attempt ||
			! current?.record.editing ||
			! journal.sameCheckpoint( cursor, current.cursor )
		) {
			return {
				state: { phase: 'clear', draft: null, kind: null },
				cursor,
				durable: false,
				conflict: true,
			};
		}
		// Another attempt may change the bucket; this target's revision and
		// entire entry must remain exact before advancing only its raw cursor.
		cursor = current.cursor;
	}
	if ( empty ) {
		const candidate = cursor
			? { cursor, record: { editing: true } }
			: journal.editing( owner );
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
			const removed = journal.consume( candidate.cursor, true );
			if ( removed && context.editor === owner ) {
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
		if ( ! candidate && context.editor === owner ) {
			context.releaseEditor();
		}
		return null;
	}

	const state = {
		phase: 'editing' as const,
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
	};
	return cursor
		? journal.checkpoint( state, cursor )
		: journal.begin( state, owner );
}
