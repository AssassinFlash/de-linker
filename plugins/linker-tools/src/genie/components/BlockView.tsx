/**
 * One block of the answer (docs/specs/13-genie.md). Cards and compare render
 * outside the block list, under the thread.
 */

/**
 * Internal dependencies
 */
import type { Block } from '../api/turn';
import { ActionView } from './ActionView';
import { Ask } from './Ask';
import { DocumentLink } from './DocumentLink';
import { Handoff } from './Handoff';

export function BlockView( {
	block,
	accountUrl,
	onAsk,
}: {
	block: Block;
	accountUrl: string;
	onAsk: ( text: string ) => void;
} ) {
	if ( block.type === 'ask' ) {
		return <Ask block={ block } onAsk={ onAsk } />;
	}
	if ( block.type === 'text' ) {
		return <p className="linker-genie-app__text">{ block.text }</p>;
	}
	if ( block.type === 'action' ) {
		return <ActionView block={ block } accountUrl={ accountUrl } />;
	}
	if ( block.type === 'handoff' ) {
		return <Handoff block={ block } />;
	}
	if ( block.type === 'document' ) {
		return <DocumentLink block={ block } />;
	}
	return null;
}
