/** Copy the complete answer, even while its local reveal is still running. */
import { useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

export function CopyReply( { text }: { text: string } ) {
	const [ result, setResult ] = useState< 'copied' | 'failed' | null >(
		null
	);
	return (
		<>
			<button
				type="button"
				className="linker-genie-app__vote"
				aria-label={ __( 'Copy response', 'linker-tools' ) }
				onClick={ async () => {
					try {
						await navigator.clipboard.writeText( text );
						setResult( 'copied' );
					} catch {
						setResult( 'failed' );
					}
				} }
			>
				<svg
					viewBox="0 0 24 24"
					width="18"
					height="18"
					fill="none"
					stroke="currentColor"
					strokeWidth="1.65"
					strokeLinecap="round"
					strokeLinejoin="round"
					aria-hidden="true"
				>
					<rect x="8" y="8" width="12" height="13" rx="2" />
					<path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3" />
				</svg>
			</button>
			{ result ? (
				<span role="status" className="linker-genie-copy-status">
					{ result === 'copied'
						? __( 'Copied', 'linker-tools' )
						: __(
								'Copy failed. Select the text and copy it manually.',
								'linker-tools'
							) }
				</span>
			) : null }
		</>
	);
}
