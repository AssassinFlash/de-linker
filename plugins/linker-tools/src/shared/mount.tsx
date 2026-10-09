/**
 * WordPress dependencies
 */
import { createRoot } from '@wordpress/element';

/**
 * External dependencies
 */
import type { ComponentType } from 'react';

/**
 * Renders `App` into every element marked `data-linker-app="<name>"`.
 *
 * PHP prints the mount points; each entry calls this once the DOM is ready.
 *
 * @param name Value of the `data-linker-app` attribute to mount on.
 * @param App  Root component of the app.
 */
export function mountApp( name: string, App: ComponentType ): void {
	document
		.querySelectorAll( `[data-linker-app="${ name }"]` )
		.forEach( ( element ) => createRoot( element ).render( <App /> ) );
}
