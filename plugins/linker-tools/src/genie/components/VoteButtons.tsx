/**
 * The customer's thumbs under an assistant message (docs/specs/13-genie.md §B
 * logging: 用户点赞/点踩). Both buttons always render, so the message height
 * never jumps; one vote wins and both then stay pressed-off except the chosen
 * one.
 */

/**
 * WordPress dependencies
 */
import { useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { sendVote } from '../api/turn';

export function VoteButtons( {
	voteUrl,
	nonce,
	turnId,
}: {
	voteUrl: string;
	nonce: string;
	turnId?: number;
} ) {
	const [ voted, setVoted ] = useState< 1 | -1 | null >( null );

	if ( ! turnId ) {
		return null;
	}
	const vote = ( value: 1 | -1 ) => {
		if ( voted !== null ) {
			return;
		}
		setVoted( value );
		void sendVote( voteUrl, nonce, turnId, value );
	};
	return (
		<div className="linker-genie-app__votes">
			<button
				type="button"
				className="linker-genie-app__vote"
				aria-label={ __( 'Helpful', 'linker-tools' ) }
				aria-pressed={ voted === 1 }
				disabled={ voted !== null && voted !== 1 }
				onClick={ () => vote( 1 ) }
			>
				👍
			</button>
			<button
				type="button"
				className="linker-genie-app__vote"
				aria-label={ __( 'Not helpful', 'linker-tools' ) }
				aria-pressed={ voted === -1 }
				disabled={ voted !== null && voted !== -1 }
				onClick={ () => vote( -1 ) }
			>
				👎
			</button>
		</div>
	);
}
