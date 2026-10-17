/**
 * The regression suite of the review site (docs/specs/16-review-acceptance.md).
 *
 * It drives a real local instance (`just up <name>` + a live snapshot + the
 * two services), so there is no webServer here: `just e2e <name>` sets
 * LINKER_E2E_INSTANCE and the specs resolve the instance's ports from
 * ~/de-linker-local/instances.toml.
 *
 * One worker: the instance is a single WordPress, its object cache and its
 * mail spool are shared state, and the Genie turns go to one real model.
 */

/**
 * External dependencies
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './specs',
	outputDir: './artifacts/test-results',
	globalSetup: './lib/health.ts',
	fullyParallel: false,
	workers: 1,
	forbidOnly: !!process.env.CI,
	// Genie's real-model turns run for up to a minute; a broken turn must not
	// hide behind a default 30 s timeout. Specs narrow this where they can.
	timeout: 300_000,
	expect: { timeout: 15_000 },
	reporter: [['list'], ['json', { outputFile: 'artifacts/report.json' }]],
	use: {
		baseURL: undefined,
		trace: 'off',
		screenshot: 'off',
		video: 'off',
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
		},
		// #229's font/fit boundary is an engine contract. Keep the extra engines
		// scoped to the header fixture; model/account suites remain Chromium.
		{
			name: 'webkit',
			testMatch: 'header-parity.spec.ts',
			use: { ...devices['Desktop Safari'] },
		},
		{
			name: 'firefox',
			testMatch: 'header-parity.spec.ts',
			use: { ...devices['Desktop Firefox'] },
		},
	],
});
