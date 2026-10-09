/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

test( 'the shared app renders its title in Chromium', async ( { page } ) => {
	await page.goto( '/iframe.html?id=shared-app--default&viewMode=story' );

	await expect( page.getByText( 'Linker Tools' ) ).toBeVisible();
} );
