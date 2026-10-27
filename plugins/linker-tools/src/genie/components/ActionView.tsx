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
import type { GenieConfig } from '../config';

/**
 * Localize navigation only; preserve saved project/run parameters and history.
 *
 * @param url   Saved, grounded action address.
 * @param links Native page addresses in both languages.
 */
function configuratorLink(
	url: string,
	links: GenieConfig[ 'configuratorLinks' ]
): string {
	if ( ! links?.current ) {
		return url;
	}
	try {
		const original = new URL( url );
		const current = new URL( links.current );
		const known = [ links.en, links.de ]
			.filter( Boolean )
			.map( ( value ) => new URL( value ).href );
		if (
			original.origin !== current.origin ||
			! known.includes( original.origin + original.pathname )
		) {
			return url;
		}
		current.search = original.search;
		current.hash = original.hash;
		return current.href;
	} catch {
		return url;
	}
}

export function ActionView( {
	block,
	accountUrl,
	configuratorLinks,
}: {
	block: ActionBlock;
	accountUrl: string;
	configuratorLinks?: GenieConfig[ 'configuratorLinks' ];
} ) {
	const url = 'string' === typeof block.args.url ? block.args.url : '';
	if ( 'open_configurator' === block.name && url ) {
		return (
			<p>
				<a
					className="linker-genie-app__action"
					href={ configuratorLink( url, configuratorLinks ) }
				>
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
