/** Completion needs the live sender's identity and exact posted messages (#563). */

/**
 * Internal dependencies
 */
import { assistantMessage, type Turn, type TurnMessage } from '../api/turn';
import type { Upload } from '../attachments/prepare';

/** In-memory evidence from an actual send; never inferred from a saved question. */
export interface RequestWitness {
	conversationId: number;
	messages: TurnMessage[];
	uploads: Upload[];
}

interface StoredThread {
	conversationId?: number;
	messages: TurnMessage[];
	turn: Turn | null;
}

/**
 * Whether the freshly read complete answer belongs to this pending request.
 * Unknown identity, another prefix, edited files and partial results do not.
 *
 * @param witness  The live send, absent after a reload.
 * @param stored   The native Thread reader's fresh result.
 * @param question The question this retry would send.
 * @param uploads  The files this retry would send.
 */
export function completedRequest(
	witness: RequestWitness | null,
	stored: StoredThread,
	question: string,
	uploads: Upload[]
): boolean {
	if (
		! witness ||
		! stored.turn ||
		witness.conversationId !== stored.conversationId
	) {
		return false;
	}
	const tail = witness.messages[ witness.messages.length - 1 ];
	const assistant = stored.messages[ witness.messages.length ];
	return !! (
		tail?.role === 'user' &&
		tail.content === question &&
		stored.messages.length === witness.messages.length + 1 &&
		witness.messages.every(
			( message, index ) =>
				message.role === stored.messages[ index ].role &&
				message.content === stored.messages[ index ].content
		) &&
		assistant?.role === 'assistant' &&
		assistant.content === assistantMessage( stored.turn ).content &&
		JSON.stringify( witness.uploads ) === JSON.stringify( uploads )
	);
}
