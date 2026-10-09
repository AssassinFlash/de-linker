/**
 * Unit tests: Vitest in jsdom, set up as in the `@wordpress/scripts` 36 Vitest
 * guide (node_modules/@wordpress/scripts/docs/vitest-migration.md, "Opt into
 * jsdom"). Vite 8 compiles TSX itself and honours `jsx: react-jsx` from
 * tsconfig.json, so no React plugin is needed. End-to-end specs under
 * tests/e2e belong to Playwright.
 */
import { defineConfig } from 'vitest/config';

export default defineConfig( {
	test: {
		environment: 'jsdom',
		globals: false,
		restoreMocks: true,
		include: [ 'src/**/*.test.{ts,tsx}' ],
		setupFiles: [ './vitest.setup.ts' ],
	},
} );
