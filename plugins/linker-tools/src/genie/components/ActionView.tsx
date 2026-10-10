/**
 * An allowed action from the tool results (docs/specs/13-genie.md).
 *
 * open_configurator's URL passed grounding, so a tool returned it
 * (size-hint's configurator_url). view_inquiry has no tool URL — grounding
 * refuses any — so the shell links to the account page itself.
 */

/**
 * WordPress dependencies
 */
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { ActionBlock } from '../api/turn';

export function ActionView( {
	block,
	accountUrl,
}: {
	block: ActionBlock;
	accountUrl: string;
} ) {
	const url = 'string' === typeof block.args.url ? block.args.url : '';
	if ( 'open_configurator' === block.name && url ) {
		return (
			<p>
				<a className="linker-genie-app__action" href={ url }>
					{ __( 'Open the configurator', 'linker-tools' ) }
				</a>
			</p>
		);
	}
	if ( 'view_inquiry' === block.name && accountUrl ) {
		return (
			<p>
				<a className="linker-genie-app__action" href={ accountUrl }>
					{ __( 'View your inquiry', 'linker-tools' ) }
				</a>
			</p>
		);
	}
	return null;
}
