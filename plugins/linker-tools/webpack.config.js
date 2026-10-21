/**
 * Build config: the `@wordpress/scripts` default plus this plugin's entries.
 *
 * Each entry emits build/<name>.js and build/<name>.asset.php (the WordPress
 * script handles it depends on and a content hash); includes/Assets.php
 * registers every built entry from those files. React, ReactDOM, the JSX
 * runtime and `@wordpress/*` stay external, so the page uses WordPress's copies.
 */
const defaultConfig = require( '@wordpress/scripts/config/webpack.config' );

module.exports = {
	...defaultConfig,
	entry: {
		genie: './src/genie/index.tsx',
		marketing: './src/marketing/index.ts',
		configurator: './src/configurator/index.tsx',
		// Not an app: the small script of Genie's preview card (ticket #249),
		// loaded with the pages that carry the card, before any app.
		preview: './src/preview/index.ts',
		// Restore explicit quota fallback text without loading the Genie app.
		'inquiry-handoff': './src/protection/inquiryEntry.ts',
		// Not an app either: the home hero's controls (ticket #232), which
		// mount their conversation into the page's own hero.
		hero: './src/hero/index.tsx',
	},
};
