import { __ } from '@wordpress/i18n';

export function TurnProgress( { skeleton = false }: { skeleton?: boolean } ) {
	return (
		<li className="linker-genie-app__message linker-genie-app__message--assistant linker-genie-wait">
			<div role="status" className="linker-genie-wait__status">
				<span className="linker-genie-wait__dot" aria-hidden="true" />
				{ __( 'Genie is thinking…', 'linker-tools' ) }
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
