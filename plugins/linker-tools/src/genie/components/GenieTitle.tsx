import { __ } from '@wordpress/i18n';
import './genie-title.css';

export function GenieTitle() {
	return (
		<>
			<span aria-hidden="true" className="linker-genie-mark">
				G
			</span>
			<span className="linker-genie-full-title">
				{ __( "Genie – Linker's AI assistant", 'linker-tools' ) }
			</span>
			<span className="linker-genie-short-title" aria-hidden="true">
				{ __( 'Genie', 'linker-tools' ) }
				<span>{ __( 'AI assistant', 'linker-tools' ) }</span>
			</span>
		</>
	);
}
