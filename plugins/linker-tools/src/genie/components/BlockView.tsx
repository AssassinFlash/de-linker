/**
 * One block of the answer (docs/specs/13-genie.md). Cards and compare render
 * outside the block list, under the thread.
 */

/**
 * Internal dependencies
 */
import type { Block } from '../api/turn';
import type { GenieConfig } from '../config';
import { ActionView } from './ActionView';
import { Ask } from './Ask';
import { DocumentLink } from './DocumentLink';
import { Handoff } from './Handoff';
import { PartsCard, type PartsActions } from './PartsCard';

export function BlockView( {
	block,
	accountUrl,
	configuratorLinks,
	onAsk,
	parts,
}: {
	block: Block;
	accountUrl: string;
	configuratorLinks?: GenieConfig[ 'configuratorLinks' ];
	onAsk: ( text: string ) => void;
	parts: PartsActions;
} ) {
	if ( block.type === 'ask' ) {
		return <Ask block={ block } onAsk={ onAsk } />;
	}
	if ( block.type === 'text' ) {
		return <p className="linker-genie-app__text">{ block.text }</p>;
	}
	if ( block.type === 'action' ) {
		return (
			<ActionView
				block={ block }
				accountUrl={ accountUrl }
				configuratorLinks={ configuratorLinks }
			/>
		);
	}
	if ( block.type === 'handoff' ) {
		return <Handoff block={ block } />;
	}
	if ( block.type === 'document' ) {
		return <DocumentLink block={ block } />;
	}
	if ( block.type === 'parts' ) {
		return <PartsCard block={ block } { ...parts } />;
	}
	return null;
}
