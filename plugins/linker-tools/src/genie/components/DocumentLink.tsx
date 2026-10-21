/**
 * A hosted document as a link (#233): the service supplies the source URL;
 * live and restored turns share current-locale metadata labels. The original
 * document title stays in the link title, never guessed from translated prose.
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
		<p className="linker-genie-document-row">
			<a
				className="linker-genie-app__document"
				href={ block.url }
				title={ block.sourceTitle }
				target="_blank"
				rel="noopener noreferrer"
			>
				<svg
					viewBox="0 0 24 24"
					width="20"
					height="20"
					fill="none"
					stroke="currentColor"
					strokeWidth="1.65"
					strokeLinecap="round"
					strokeLinejoin="round"
					aria-hidden="true"
				>
					<path d="M14 3H5v18h14V8Z M14 3v5h5 M8 12h8 M8 16h5" />
				</svg>
				<span>{ block.label }</span>
				<span aria-hidden="true">↗</span>
			</a>
		</p>
	);
}
