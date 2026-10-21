/** The marketing page's editor uses the current lazy dock, without changing its resting layout. */
import domReady from '@wordpress/dom-ready';
import { readConfig } from '../genie/config';
import { bindMarketingEntries } from './entries';

domReady( () => {
	const mount = document.querySelector< HTMLElement >(
		'[data-linker-app="genie"]'
	);
	if ( mount ) {
		bindMarketingEntries( document, readConfig( mount ) );
	}
} );
