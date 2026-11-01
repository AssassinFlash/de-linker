/** Copy the complete answer, even while its local reveal is still running. */
import { useEffect, useRef, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

export function CopyReply( {
	text,
	question = false,
	canCopy,
}: {
	text: string;
	question?: boolean;
	canCopy?: () => boolean;
} ) {
	const [ result, setResult ] = useState< 'copied' | 'failed' | null >(
		null
	);
	const version = useRef( 0 );
	useEffect( () => {
		version.current += 1;
		setResult( null );
	}, [ text ] );
	return (
		<>
			<button
				type="button"
				className={
					question
						? 'linker-genie-app__prompt'
						: 'linker-genie-app__vote'
				}
				aria-label={
					question
						? __( 'Copy question', 'linker-tools' )
						: __( 'Copy response', 'linker-tools' )
				}
				onClick={ async () => {
					if ( canCopy && ! canCopy() ) {
						return;
					}
					const captured = version.current;
					try {
						await navigator.clipboard.writeText( text );
						if ( version.current === captured ) {
							setResult( 'copied' );
						}
					} catch {
						if ( version.current === captured ) {
							setResult( 'failed' );
						}
					}
				} }
			>
				{ question ? (
					__( 'Copy question', 'linker-tools' )
				) : (
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
				) }
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
