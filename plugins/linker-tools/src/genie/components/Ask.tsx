/**
 * The one deciding question, as clickable chips (docs/specs/13-genie.md).
 */

/**
 * Internal dependencies
 */
import type { AskBlock } from '../api/turn';

export function Ask( {
	block,
	onAsk,
}: {
	block: AskBlock;
	onAsk: ( text: string ) => void;
} ) {
	return (
		<div className="linker-genie-app__ask" role="group">
			{ block.options.map( ( option ) => (
				<button
					key={ option }
					type="button"
					className="linker-genie-app__chip"
					onClick={ () => onAsk( option ) }
				>
					{ option }
				</button>
			) ) }
		</div>
	);
}
