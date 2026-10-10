/**
 * Out of scope: the sentence already names the team mailbox
 * (docs/specs/13-genie.md).
 */

/**
 * Internal dependencies
 */
import type { HandoffBlock } from '../api/turn';

export function Handoff( { block }: { block: HandoffBlock } ) {
	return <p className="linker-genie-app__handoff">{ block.summary }</p>;
}
