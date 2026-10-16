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
		configurator: './src/configurator/index.tsx',
	},
};
