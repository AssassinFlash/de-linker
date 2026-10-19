/**
 * Playwright config for the campaign #331 in-browser battery
 * (docs/research/2026-10-20-campaign-331/harness/browser.spec.ts).
 *
 * It borrows the e2e suite's installed Playwright (tests/e2e/node_modules)
 * and its instance registry; the instance name comes from the environment
 * (`LINKER_E2E_INSTANCE=c331`). One worker, headless: every case drives real
 * model turns and shares the service.
 */
import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: __dirname,
	testMatch: /browser\.spec\.ts/,
	timeout: 900_000,
	fullyParallel: false,
	workers: 1,
	retries: 0,
	reporter: [['list']],
	use: {
		baseURL: 'http://127.0.0.1:9165',
		headless: true,
		locale: 'en-US',
		timezoneId: 'Europe/Berlin',
	},
	projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
