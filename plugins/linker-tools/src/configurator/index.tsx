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

domReady( () => {
	document
		.querySelectorAll< HTMLElement >( '[data-linker-app="configurator"]' )
		.forEach( ( element ) =>
			createRoot( element ).render(
				<App config={ readConfig( element ) } />
			)
		);
} );
