// @vitest-environment jsdom
/**
 * The verification slot is a live flex child above the composer. Its class
 * style must not defeat the native hidden state the proof lifecycle toggles,
 * or an empty slot keeps its padding and lifts the composer (2026-10-28).
 *
 * jsdom reports no layout, so the measurement runs in real Chromium through
 * the Playwright package this plugin already depends on, the same way
 * configurator/Steps.test.tsx measures its sticky rail. The import stays
 * inside the test: the unit suite otherwise never needs a browser.
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from 'vitest';

const css = readFileSync(
	join( dirname( fileURLToPath( import.meta.url ) ), '../genie.css' ),
	'utf8'
);

test( 'the slot class collapses to nothing while its native hidden state is set', async () => {
	const { chromium } = await import( '@playwright/test' );
	const html = `<!doctype html><html><head><meta charset="utf-8"><style>
			body { margin: 0; }
			${ css }
			</style></head><body>
			<div class="linker-genie-app">
				<div class="linker-genie-app__panel">
					<div id="hidden-slot" data-linker-resource-verification-slot
						class="linker-genie-app__status" hidden></div>
					<div id="shown-slot" data-linker-resource-verification-slot
						class="linker-genie-app__status"></div>
					<form class="linker-genie-app__composer"></form>
				</div>
			</div>
			</body></html>`;
	const browser = await chromium.launch();
	try {
		const page = await browser.newPage( {
			viewport: { width: 1440, height: 900 },
		} );
		await page.setContent( html, { waitUntil: 'load' } );
		const measured = await page.evaluate( () => {
			const hidden = document.querySelector( '#hidden-slot' );
			const shown = document.querySelector( '#shown-slot' );
			if (
				! ( hidden instanceof HTMLElement ) ||
				! ( shown instanceof HTMLElement )
			) {
				throw new Error(
					'verification slot fixture is missing a node'
				);
			}
			// What the native adapter does once a proof is in flight.
			hidden.hidden = false;
			const openHeight = hidden.getBoundingClientRect().height;
			hidden.hidden = true;
			return {
				display: getComputedStyle( hidden ).display,
				hiddenHeight: hidden.getBoundingClientRect().height,
				openHeight,
				shownHeight: shown.getBoundingClientRect().height,
			};
		} );
		expect( measured.display ).toBe( 'none' );
		expect( measured.hiddenHeight ).toBe( 0 );
		// The same class still lays out the widget while the slot is in use.
		expect( measured.openHeight ).toBeGreaterThan( 0 );
		expect( measured.shownHeight ).toBeGreaterThan( 0 );
	} finally {
		await browser.close();
	}
} );
