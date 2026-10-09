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
import configuratorGerman from '../languages/linker-tools-de_DE_formal-linker-tools-configurator.json';

const withLocale: Decorator = ( Story, context ) => {
	const locale = context.globals.locale === 'de' ? 'de' : 'en';
	resetLocaleData( {}, 'linker-tools' );
	if ( locale === 'de' ) {
		setLocaleData(
			configuratorGerman.locale_data.messages,
			'linker-tools'
		);
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
