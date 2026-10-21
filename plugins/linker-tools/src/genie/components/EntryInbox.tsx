/** Explicit draft ownership decisions, using the approved existing button primitives. */
import { __, sprintf } from '@wordpress/i18n';
import type { useEntryInbox } from '../shared/useEntryInbox';
export function EntryInbox( {
	inbox,
	busy,
	composerOccupied,
}: {
	inbox: ReturnType< typeof useEntryInbox >;
	busy: boolean;
	composerOccupied: boolean;
} ) {
	return (
		<>
			{ inbox.identityError ? (
				<p role="alert" className="linker-genie-app__error">
					{ __( 'Genie could not load.', 'linker-tools' ) }
					{ inbox.recoveryBlocked ? (
						<button
							type="button"
							className="linker-genie-app__prompt"
							disabled={ busy }
							onClick={ inbox.retryRecovery }
						>
							{ __( 'Try again', 'linker-tools' ) }
						</button>
					) : null }
				</p>
			) : null }
			{ inbox.inbox.map( ( { draft } ) => (
				<section
					className="linker-genie-app__photo-prompt"
					data-genie-entry-review={ draft.id }
					key={ draft.id }
					aria-label={ __(
						'Question from this page',
						'linker-tools'
					) }
				>
					<p>
						<strong>
							{ __( 'Question from this page', 'linker-tools' ) }
						</strong>
					</p>
					<p>{ draft.text }</p>
					<div className="flex flex-wrap gap-3">
						{ composerOccupied ? (
							<button
								type="button"
								className="linker-genie-app__prompt"
								onClick={ () => inbox.defer( draft ) }
							>
								{ __( 'Keep current draft', 'linker-tools' ) }
							</button>
						) : null }
						<button
							type="button"
							className="linker-genie-app__prompt"
							disabled={ busy }
							onClick={ () => inbox.append( draft ) }
						>
							{ __( 'Add to current draft', 'linker-tools' ) }
						</button>
						<button
							type="button"
							className="linker-genie-app__prompt"
							disabled={ busy || !! inbox.parked }
							onClick={ () =>
								void inbox.accept( draft, composerOccupied )
							}
						>
							{ draft.mode === 'compose'
								? __(
										'Send question separately',
										'linker-tools'
									)
								: __( 'Open as draft', 'linker-tools' ) }
						</button>
					</div>
				</section>
			) ) }
			{ inbox.parked ? (
				<section
					className="linker-genie-app__photo-prompt"
					data-genie-parked-draft
				>
					<p>
						<strong>
							{ __( 'Current unsent draft', 'linker-tools' ) }
						</strong>
					</p>
					<p>{ inbox.parked.text }</p>
					{ inbox.parked.uploads.map( ( file ) => (
						<p key={ file.name }>{ file.name }</p>
					) ) }
					{ inbox.parked.missing.map( ( name ) => (
						<p key={ name }>
							{ sprintf(
								// translators: %s is the name of a file that must be selected again.
								__(
									'Select %s again before sending.',
									'linker-tools'
								),
								name
							) }
						</p>
					) ) }
					<button
						type="button"
						className="linker-genie-app__prompt"
						disabled={ busy }
						onClick={ inbox.restoreParked }
					>
						{ __( 'Restore unsent draft', 'linker-tools' ) }
					</button>
				</section>
			) : null }
			{ inbox.missing.map( ( name ) => (
				<p
					role="status"
					className="linker-genie-app__refused"
					key={ name }
				>
					{ sprintf(
						// translators: %s is the name of a file that must be selected again.
						__( 'Select %s again before sending.', 'linker-tools' ),
						name
					) }{ ' ' }
					<button
						type="button"
						className="linker-genie-app__prompt"
						onClick={ () =>
							inbox.setMissing( ( files ) =>
								files.filter( ( file ) => file !== name )
							)
						}
					>
						{ __( 'Remove', 'linker-tools' ) }
					</button>
				</p>
			) ) }
		</>
	);
}
