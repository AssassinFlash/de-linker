/** A compact AI note and native support disclosure for the helper sheet. */
import { __ } from '@wordpress/i18n';
import { useEffect, useRef } from '@wordpress/element';

export function HelperFooter( {
	german,
	disclosure,
}: {
	german: boolean;
	disclosure: string;
} ) {
	const details = useRef< HTMLDetailsElement >( null );
	useEffect( () => {
		const element = details.current;
		const escape = ( event: KeyboardEvent ) => {
			if ( event.key === 'Escape' && element?.open ) {
				event.preventDefault();
				event.stopPropagation();
				element.open = false;
				element.querySelector( 'summary' )?.focus();
			}
		};
		element?.addEventListener( 'keydown', escape );
		return () => element?.removeEventListener( 'keydown', escape );
	}, [] );
	return (
		<footer className="linker-genie-footnote">
			<span>{ __( 'Genie is an AI assistant.', 'linker-tools' ) }</span>
			<details className="linker-genie-help" ref={ details }>
				<summary>
					{ __( 'Help & privacy', 'linker-tools' ) }
					<svg
						width="12"
						height="12"
						viewBox="0 0 12 12"
						fill="none"
						aria-hidden="true"
					>
						<path
							d="m3 4.5 3 3 3-3"
							stroke="currentColor"
							strokeWidth="1.25"
							strokeLinecap="round"
							strokeLinejoin="round"
						/>
					</svg>
				</summary>
				<div className="linker-genie-help-menu">
					<p className="linker-genie-app__disclosure">
						{ disclosure }
					</p>
					<nav className="linker-genie-app__links">
						<a
							href={
								german ? '/de/faq-download/' : '/faq-download/'
							}
						>
							{ __( 'FAQ & Downloads', 'linker-tools' ) }
						</a>
						<a href={ german ? '/de/kontakt/' : '/contact/' }>
							{ __( 'Contact Linker', 'linker-tools' ) }
						</a>
						<a
							href={
								german ? '/de/datenschutz/' : '/privacy-policy/'
							}
						>
							{ __( 'Privacy Policy', 'linker-tools' ) }
						</a>
					</nav>
				</div>
			</details>
		</footer>
	);
}
