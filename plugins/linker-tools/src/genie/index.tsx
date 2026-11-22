/**
 * WordPress dependencies
 */
import domReady from '@wordpress/dom-ready';
import { createRoot } from '@wordpress/element';

/**
 * Internal dependencies
 */
import { App } from './App';
import { readConfig } from './config';

function mount() {
	document
		.querySelectorAll< HTMLElement >( '[data-linker-app="genie"]' )
		.forEach( ( element ) =>
			createRoot( element ).render(
				<App config={ readConfig( element ) } />
			)
		);
}
if (
	document.querySelector(
		'[data-linker-app="genie"][data-surface="workspace"]'
	)
) {
	mount();
} else {
	domReady( mount );
}
