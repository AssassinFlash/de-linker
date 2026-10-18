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
			aria-label={ __( 'Reply with an option', 'linker-tools' ) }
		>
			<div className="linker-genie-ask-heading">
				<p className="linker-genie-ask-title">
					{ __( 'Reply with an option', 'linker-tools' ) }
				</p>
				<p className="linker-genie-ask-hint">
					{ __( 'Your selection is sent to Genie.', 'linker-tools' ) }
				</p>
			</div>
			<p className="linker-genie-ask-label">{ label }</p>
			{ block.options.map( ( option ) => (
				<button
					key={ option }
					type="button"
					className="linker-genie-app__chip"
					aria-label={ option }
					onClick={ () => onAsk( option ) }
				>
					<span className="linker-genie-ask-option">{ option }</span>
					<span className="linker-genie-ask-send" aria-hidden="true">
						{ __( 'Send', 'linker-tools' ) }
						<svg
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
						>
							<path
								d="M5 12h14m-6-6 6 6-6 6"
								stroke="currentColor"
								strokeWidth="1.7"
								strokeLinecap="round"
								strokeLinejoin="round"
							/>
						</svg>
					</span>
				</button>
			) ) }
		</div>
	);
}
