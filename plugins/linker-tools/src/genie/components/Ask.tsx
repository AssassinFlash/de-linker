/**
 * The one deciding question, as clickable chips (docs/specs/13-genie.md).
 */

/**
 * Internal dependencies
 */
import { __ } from '@wordpress/i18n';
import type { AskBlock } from '../api/turn';

export function Ask( {
	block,
	onAsk,
}: {
	block: AskBlock;
	onAsk: ( text: string ) => void;
} ) {
	const label =
		block.field === 'phase'
			? __( 'Grid connection', 'linker-tools' )
			: __( 'Continue with your project', 'linker-tools' );
	return (
		<div
			className="linker-genie-app__ask"
			role="group"
			aria-label={ label }
		>
			<p className="linker-genie-ask-label">{ label }</p>
			{ block.options.map( ( option ) => (
				<button
					key={ option }
					type="button"
					className="linker-genie-app__chip"
					onClick={ () => onAsk( option ) }
				>
					{ option }
					<span aria-hidden="true">↗</span>
				</button>
			) ) }
		</div>
	);
}
