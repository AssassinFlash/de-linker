import {
	readJobDraft,
	keepPickedFile,
	removeFiles,
	releasePickedFiles,
} from '../attachments/turnFiles';
import { useCallback, useEffect, useRef } from '@wordpress/element';
import {
	assistantMessage,
	resumeTurn,
	type PendingJob,
	type TurnMessage,
	type TurnStage,
	type readThread,
	type Turn,
} from '../api/turn';
import type { GenieConfig } from '../config';
import type { DraftEditor } from './draftContext';
import { pageFailureStore, type FailureDraft } from './failure';
import { verifiedEntryFailure } from './entryFailure';
import type { useFailure } from './useFailure';

type Stored = Awaited< ReturnType< typeof readThread > >;
type Failure = ReturnType< typeof useFailure >;
interface View {
	verified?: () => void;
	wait: ( messages: TurnMessage[], job: PendingJob ) => void;
	stage: ( stage: TurnStage ) => void;
	complete: ( messages: TurnMessage[], answer: Turn ) => void;
	failed: ( draft: FailureDraft, error: unknown ) => void;
}

/**
 * A newly mounted surface follows the server-owned pending turn without resending its question.
 * @param config
 * @param editor
 * @param failure
 * @param view
 */
export function usePendingTurn(
	config: GenieConfig,
	editor: DraftEditor,
	failure: Pick< Failure, 'adoptFailure' | 'commitFailure' | 'placeChips' >,
	view: View
) {
	const current = useRef( { failure, view } );
	current.current = { failure, view };
	const active = useRef< { id: string; controller: AbortController } | null >(
		null
	);
	useEffect( () => () => active.current?.controller.abort(), [] );
	return useCallback(
		( stored: Pick< Stored, 'messages' | 'pendingJob' > ): boolean => {
			const job = stored.pendingJob;
			const lease = editor.capture();
			if ( ! job || ! lease ) {
				return false;
			}
			if (
				active.current?.id === job.job_id &&
				! active.current.controller.signal.aborted
			) {
				return true;
			}
			active.current?.controller.abort();
			const controller = new AbortController();
			active.current = { id: job.job_id, controller };
			const owns = () =>
				! controller.signal.aborted && editor.context.owns( lease );
			const messages: TurnMessage[] = [
				...stored.messages,
				{ role: 'user', content: job.user_message },
			];
			current.current.view.wait( messages, job );
			void ( async () => {
				const journal = await verifiedEntryFailure(
					config,
					pageFailureStore(),
					editor
				);
				if ( ! owns() ) {
					return;
				}
				if ( journal?.unchanged() ) {
					current.current.view.verified?.();
				}
				const matched =
					journal?.unchanged() &&
					journal.record &&
					job.operation_id &&
					journal.record.operationId === job.operation_id
						? journal.record
						: null;
				const carried = await readJobDraft( job.job_id );
				const uploads = carried?.uploads ?? [];
				if ( ! owns() ) {
					return;
				}
				const draft: FailureDraft = matched
					? {
							...matched,
							...( uploads.length
								? { uploads, omitted: [] }
								: {} ),
						}
					: {
							text: carried?.text ?? job.user_message,
							question: job.user_message,
							conversationId: job.conversation_id,
							operationId: job.operation_id,
							uploads,
							omitted: [],
						};
				if ( matched && journal?.candidate ) {
					current.current.failure.adoptFailure( journal.candidate, {
						phase: 'pending',
						kind: null,
						draft,
					} );
				}
				if ( draft.uploads.length ) {
					current.current.failure.placeChips( draft.uploads );
				}
				try {
					const answer = await resumeTurn(
						{
							turnUrl: config.turnUrl,
							nonce: config.restNonce,
							onStage: ( stage ) => {
								if ( owns() ) {
									current.current.view.stage( stage );
								}
							},
						},
						job,
						controller.signal
					);
					if (
						! owns() ||
						! ( await editor.context.settle( lease ) )
					) {
						return;
					}
					if ( matched ) {
						current.current.failure.commitFailure( {
							type: 'answered',
						} );
					}
					if ( draft.uploads.length ) {
						void removeFiles( job.job_id ).catch( () => undefined );
						releasePickedFiles( draft.uploads );
					}
					current.current.view.complete(
						[ ...messages, assistantMessage( answer ) ],
						answer
					);
				} catch ( error ) {
					if (
						! owns() ||
						! ( await editor.context.settle( lease ) )
					) {
						return;
					}
					if ( ! matched ) {
						await Promise.all(
							draft.uploads.map( ( upload ) =>
								keepPickedFile( lease.scope, upload )
							)
						);
						if ( ! owns() ) {
							return;
						}
						current.current.failure.commitFailure( {
							type: 'send',
							draft,
						} );
					}
					current.current.failure.commitFailure( {
						type: 'upstream',
					} );
					current.current.view.failed( draft, error );
				} finally {
					if ( active.current?.controller === controller ) {
						active.current = null;
					}
				}
			} )();
			return true;
		},
		[ config, editor ]
	);
}
