/**
 * Genie's preview card (ticket #249): starts the card's rules on the pages
 * that carry it (includes/Genie/Preview.php prints it hidden).
 */

/**
 * WordPress dependencies
 */
import domReady from '@wordpress/dom-ready';

/**
 * Internal dependencies
 */
import { startPreview } from './controller';
import './preview.css';

domReady( () => {
	const card = document.querySelector< HTMLElement >(
		'[data-linker-genie-peek]'
	);
	if ( card ) {
		startPreview( card );
	}
} );
