/**
 * The `@wordpress/scripts` default flat config (recommended rules of
 * `@wordpress/eslint-plugin` with Prettier and TypeScript, and its Vitest rules
 * for unit tests), plus the plugin's Playwright rules for the end-to-end specs.
 */
const wpScriptsConfig = require( '@wordpress/scripts/config/eslint.config.cjs' );
const wpPlugin = require( '@wordpress/eslint-plugin' );

module.exports = [
	{ ignores: [ 'artifacts/**', 'storybook-static/**' ] },
	...wpScriptsConfig,
	...wpPlugin.configs[ 'test-playwright' ].map( ( config ) => ( {
		...config,
		files: [ 'tests/e2e/**/*.ts' ],
	} ) ),
];
