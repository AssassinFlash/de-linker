/** The existing explicit draft recovery action; content is supplied only after native verification. */
import { __ } from '@wordpress/i18n';
import type { FailureCandidate } from '../shared/ownedFailure';
export function OwnedRecovery( {
	candidate,
	restore,
	busy,
}: {
	candidate: FailureCandidate | null;
	restore: () => void;
	busy: boolean;
} ) {
	return candidate ? (
		<section
			className="linker-genie-app__photo-prompt"
			data-genie-owned-recovery
		>
			<p>
				<strong>
					{ __( 'Current unsent draft', 'linker-tools' ) }
				</strong>
			</p>
			<p>{ candidate.record.text }</p>
			{ [
				...candidate.record.omitted,
				...candidate.record.uploads.map( ( file ) => file.name ),
			].map( ( name ) => (
				<p key={ name }>{ name }</p>
			) ) }
			<button
				type="button"
				className="linker-genie-app__prompt"
				disabled={ busy }
				onClick={ restore }
			>
				{ __( 'Restore unsent draft', 'linker-tools' ) }
			</button>
		</section>
	) : null;
}
