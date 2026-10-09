/**
 * End-to-end tests in Chromium.
 *
 * The specs drive the components through Storybook, which needs no WordPress.
 */
/**
 * External dependencies
 */
import { defineConfig, devices } from '@playwright/test';

// Storybook's default dev-server port (`storybook dev --help`).
const port = 6006;

export default defineConfig( {
	testDir: './tests/e2e',
	outputDir: './artifacts/test-results',
	forbidOnly: !! process.env.CI,
	reporter: process.env.CI ? [ [ 'list' ], [ 'github' ] ] : 'list',
	use: {
		baseURL: `http://localhost:${ port }`,
	},
	webServer: {
		command: `npx storybook dev --ci --exact-port --port ${ port }`,
		url: `http://localhost:${ port }/iframe.html`,
		// Start this checkout's Storybook every time; reusing whatever already
		// listens on the port (another worktree's Storybook) would test that.
		reuseExistingServer: false,
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices[ 'Desktop Chrome' ] },
		},
	],
} );
