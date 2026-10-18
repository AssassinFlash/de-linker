/**
 * The parts of a Genie turn that both surfaces word the same way (ticket
 * #232 review round 1, item 4): the question with its files, the proxy's
 * attachment-refusal code, and the manual-model opening words. One
 * implementation, used by the dock (App.tsx) and the home hero (Hero.tsx).
 */

/**
 * WordPress dependencies
 */
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { TurnError } from '../api/turn';
import type { Upload } from '../attachments/prepare';

/**
 * The message a turn carries: the typed question and one line per file. A
 * file with no text is still a question (the file is what Genie reads).
 *
 * @param text    What the customer typed.
 * @param uploads The files of this turn.
 */
export function buildQuestion( text: string, uploads: Upload[] ): string {
	return [
		text.trim(),
		...uploads.map( ( upload ) =>
			// translators: %s is the name of a file the visitor attached.
			__( 'Attached: %s', 'linker-tools' ).replace( '%s', upload.name )
		),
	]
		.filter( ( part ) => part !== '' )
		.join( '\n' );
}

/**
 * The proxy's refusal code of a turn (`linker_genie_attachment_<reason>`),
 * or '' when the failure is not an attachment refusal.
 *
 * @param error The turn's error.
 */
export function attachmentRefusalReason( error: unknown ): string {
	return error instanceof TurnError &&
		error.code.startsWith( 'linker_genie_attachment_' )
		? error.code.slice( 'linker_genie_attachment_'.length )
		: '';
}

/**
 * "My device is the " — the manual-model exit's opening words, with the
 * model left for the customer to type.
 */
export function typeModelPrompt(): string {
	return sprintf(
		// translators: %s stays empty: the customer types the model after the words.
		__( 'My device is the %s', 'linker-tools' ),
		''
	);
}
