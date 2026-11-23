import { __ } from '@wordpress/i18n';

import type { TurnStage } from '../api/turn';

function stageLabel( stage?: TurnStage ) {
	switch ( stage ) {
		case 'reading_attachments':
			return __( 'Reading your file…', 'linker-tools' );
		case 'understanding':
			return __( 'Understanding your question…', 'linker-tools' );
		case 'checking_catalog':
			return __( 'Checking products and compatibility…', 'linker-tools' );
		case 'searching_documents':
			return __( 'Searching manufacturer manuals…', 'linker-tools' );
		case 'writing_answer':
			return __( 'Preparing your answer…', 'linker-tools' );
		case 'verifying_answer':
			return __( 'Verifying figures and sources…', 'linker-tools' );
		default:
			return __( 'Genie is thinking…', 'linker-tools' );
	}
}

export function TurnProgress( {
	skeleton = false,
	stage,
}: {
	skeleton?: boolean;
	stage?: TurnStage;
} ) {
	return (
		<li className="linker-genie-app__message linker-genie-app__message--assistant linker-genie-wait">
			<div role="status" className="linker-genie-wait__status">
				<span className="linker-genie-wait__dot" aria-hidden="true" />
				{ stageLabel( stage ) }
			</div>
			{ skeleton && (
				<div className="linker-genie-wait__lines" aria-hidden="true">
					<span />
					<span />
					<span />
				</div>
			) }
		</li>
	);
}
