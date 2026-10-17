/**
 * A hosted document as a link (#233): the service filled the label (title and
 * page) and the URL from this turn's tool results, so no address ever stands
 * in the answer text.
 */

/**
 * Internal dependencies
 */
import type { DocumentBlock } from '../api/turn';

export function DocumentLink( { block }: { block: DocumentBlock } ) {
	if ( ! block.url || ! block.label ) {
		return null;
	}
	return (
		<p>
			<a
				className="linker-genie-app__document"
				href={ block.url }
				target="_blank"
				rel="noopener noreferrer"
			>
				{ block.label }
			</a>
		</p>
	);
}
