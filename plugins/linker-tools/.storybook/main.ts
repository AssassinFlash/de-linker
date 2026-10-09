/**
 * External dependencies
 */
import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
	stories: [ '../src/**/*.stories.tsx' ],
	framework: '@storybook/react-vite',
	core: {
		disableTelemetry: true,
	},
	viteFinal: ( viteConfig ) => ( {
		...viteConfig,
		optimizeDeps: {
			...viteConfig.optimizeDeps,
			// Our components use the automatic JSX runtime and never import
			// `react`, so Vite meets it only in Storybook's preview entries,
			// which its dependency scan skips: Storybook 10.6 escapes the `@`
			// in their node_modules paths and Vite 8's glob then matches
			// nothing. Unbundled, CommonJS React fails in the browser with "does
			// not provide an export named 'default'".
			include: [ ...( viteConfig.optimizeDeps?.include ?? [] ), 'react' ],
		},
	} ),
};

export default config;
