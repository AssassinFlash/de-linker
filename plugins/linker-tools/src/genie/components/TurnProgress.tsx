import { __ } from '@wordpress/i18n';

// Verification has no assistant response; model progress begins at dispatch.
export function TurnProgress( {
	verificationPending,
	onCancel,
	skeleton = false,
}: {
	verificationPending: boolean;
	onCancel: () => void;
	skeleton?: boolean;
} ) {
	if ( verificationPending ) {
		return (
			<li className="linker-genie-app__verification">
				<p role="status">
					{ __( 'Checking verification…', 'linker-tools' ) }
				</p>
				<button
					type="button"
					className="linker-genie-app__prompt"
					onClick={ onCancel }
				>
					{ __( 'Cancel verification', 'linker-tools' ) }
				</button>
			</li>
		);
	}
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
