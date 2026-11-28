/**
 * The home hero's Genie entry (ticket #232): binds the LiveCanvas hero's own
 * controls to the conversation in place. Loaded only on the front page
 * (includes/Genie/Hero.php); without it the hero's links keep their live
 * no-JavaScript destination.
 */

/**
 * WordPress dependencies
 */
import domReady from '@wordpress/dom-ready';

/**
 * Internal dependencies
 */
import { readConfig } from '../genie/config';
import { startHero } from './controller';
import { pageDraftContext } from '../genie/shared/draftContext';
import './hero.css';

domReady( async () => {
	const hero = document.querySelector< HTMLElement >( '.hero-cinematic' );
	// The dock's mount carries the routes, nonce, language and page context;
	// the hero is one more entry on the same conversation (config.ts).
	const mount = document.querySelector< HTMLElement >(
		'[data-linker-app="genie"]'
	);
	if ( hero && mount ) {
		const config = readConfig( mount );
		// Keep the native textarea editable while the first owner lookup is in flight.
		const context = pageDraftContext( config );
		await context.initialized().catch( () => undefined );
		startHero( hero, { config } );
		window.dispatchEvent( new CustomEvent( 'linker-genie-hero-ready' ) );
	}
} );
