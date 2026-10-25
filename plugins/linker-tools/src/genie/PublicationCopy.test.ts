/**
 * Standalone Genie and the home assistant load their own translation bundles.
 */

/**
 * External dependencies
 */
import { afterEach, expect, test } from 'vitest';

/**
 * WordPress dependencies
 */
import { __, resetLocaleData, setLocaleData } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import germanGenie from '../../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';
import germanHero from '../../languages/linker-tools-de_DE_formal-6796211aef57736d0923df38ef696ad2.json';
import {
	additionStatusText,
	additionUnconfirmedText,
} from '../configurator/publication';

afterEach( () => resetLocaleData( {}, 'linker-tools' ) );

for ( const [ name, catalog ] of [
	[ 'standalone Genie', germanGenie ],
	[ 'home assistant', germanHero ],
] as const ) {
	test( `${ name } translates publication states without loading the configurator`, () => {
		resetLocaleData( {}, 'linker-tools' );
		setLocaleData( catalog.locale_data.messages, 'linker-tools' );
		expect( additionStatusText() ).toBe( 'Hinzufügen nicht bestätigt.' );
		expect( additionUnconfirmedText() ).toBe(
			'Das Hinzufügen konnte nicht bestätigt werden. Die Produkte können bereits im Lösungsentwurf stehen.'
		);
		expect(
			__(
				'The request status could not be confirmed. Please check before sending it again.',
				'linker-tools'
			)
		).toBe(
			'Der Status Ihrer Anfrage konnte nicht bestätigt werden. Bitte prüfen Sie ihn vor einem erneuten Versand.'
		);
		expect( __( 'Saved in this browser for now.', 'linker-tools' ) ).toBe(
			'Vorerst in diesem Browser gespeichert.'
		);
		expect(
			__(
				'The product information changed while Genie was answering. Your message is still here.',
				'linker-tools'
			)
		).toBe(
			'Während der Antwort haben sich die Produktinformationen geändert. Ihre Nachricht bleibt erhalten.'
		);
	} );
}
