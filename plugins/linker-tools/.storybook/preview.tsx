/**
 * Stories render as on the site: the site's typeface, and a language toggle
 * that loads the German translations the page would receive from WordPress.
 */

/**
 * External dependencies
 */
import type { Decorator, Preview } from '@storybook/react-vite';

/**
 * WordPress dependencies
 */
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import configuratorGerman from '../languages/linker-tools-de_DE_formal-ff47dbd6ce1b77b210b406f2367c7ea7.json';
import genieGerman from '../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';
import heroGerman from '../languages/linker-tools-de_DE_formal-6796211aef57736d0923df38ef696ad2.json';

const withLocale: Decorator = ( Story, context ) => {
	const locale = context.globals.locale === 'de' ? 'de' : 'en';
	resetLocaleData( {}, 'linker-tools' );
	if ( locale === 'de' ) {
		setLocaleData(
			configuratorGerman.locale_data.messages,
			'linker-tools'
		);
		// Each built script has its own catalog. Genie and the hero need
		// theirs; setLocaleData merges into the one domain.
		if (
			context.title.startsWith( 'Genie/' ) ||
			context.title.startsWith( 'Hero/' )
		) {
			setLocaleData( genieGerman.locale_data.messages, 'linker-tools' );
			setLocaleData( heroGerman.locale_data.messages, 'linker-tools' );
		}
	}
	document.documentElement.lang = locale === 'de' ? 'de-DE' : 'en-GB';
	return <Story key={ locale } />;
};

const preview: Preview = {
	globalTypes: {
		locale: {
			description: 'Page language',
			toolbar: {
				title: 'Language',
				icon: 'globe',
				items: [
					{ value: 'en', title: 'English' },
					{ value: 'de', title: 'Deutsch' },
				],
				dynamicTitle: true,
			},
		},
	},
	initialGlobals: { locale: 'en' },
	decorators: [ withLocale ],
	parameters: { layout: 'fullscreen' },
};

export default preview;
