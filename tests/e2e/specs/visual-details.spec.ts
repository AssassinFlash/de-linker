/** Owner's 2026-10-21 review: affordances, spacing and keyboard destinations. */
import { expect, test } from '@playwright/test';
import { instance } from '../lib/instance';
import type { Page } from '@playwright/test';

test.setTimeout( 45_000 );

async function dismissConsent( page: Page ) {
	const reject = page.getByRole( 'button', {
		name: /^(Reject all|Alle ablehnen)$/,
	} );
	if ( await reject.isVisible() ) {
		await reject.click();
	}
}

for ( const locale of [ 'en', 'de' ] as const ) {
	for ( const width of [ 390, 1440 ] ) {
		test( `${ locale } ${ width }: choice labels breathe and cards remain native radios`, async ( {
			page,
		} ) => {
			await page.setViewportSize( { width, height: 900 } );
			await page.goto(
				`${ instance().url }${ locale === 'en' ? '/solution-configurator/' : '/de/loesungskonfigurator/' }`
			);
			await dismissConsent( page );
			const group = page.getByRole( 'group', {
				name: locale === 'en' ? 'Grid connection' : 'Netzanschluss',
				exact: true,
			} );
			await expect( group ).toBeVisible();
			const gap = await group.evaluate(
				( node ) =>
					node.querySelector( 'label' )!.getBoundingClientRect().top -
					node.querySelector( 'legend' )!.getBoundingClientRect()
						.bottom
			);
			// Existing --proto-space-2 = 8px; the native legend is outside grid gap.
			expect( gap ).toBeGreaterThanOrEqual( 8 );
			await group.locator( 'label' ).last().click();
			await expect( group.getByRole( 'radio' ).last() ).toBeChecked();
		} );

		test( `${ locale } ${ width }: footer links, current language and keyboard panel agree`, async ( {
			page,
		} ) => {
			await page.setViewportSize( { width, height: 900 } );
			const home = locale === 'en' ? '/' : '/de/';
			const paths =
				locale === 'en'
					? [
							'/products/',
							'/about/capability/',
							'/services-support/',
						]
					: [
							'/de/produkte/',
							'/de/ueber-uns/leistungsfaehigkeit/',
							'/de/kundendienst/',
						];
			await page.goto( `${ instance().url }${ home }` );
			await dismissConsent( page );
			const current = page.locator(
				'.tv-footer-lang-seg [aria-current="true"]'
			);
			await expect( current ).toHaveCount( 1 );
			await expect( current ).toHaveAttribute( 'lang', locale );
			for ( const [ i, path ] of paths.entries() ) {
				const link = page.locator( '.footer-identity-node' ).nth( i );
				await expect( link ).toHaveAttribute( 'href', path );
				expect(
					( await link.boundingBox() )!.height
				).toBeGreaterThanOrEqual( 44 );
				await link.click();
				await expect( page ).toHaveURL(
					`${ instance().url }${ path }`
				);
			}
			const tab = page.locator( '#footer-tab-services' );
			await tab.click();
			await tab.press( 'Tab' );
			await expect(
				page.locator( '#footer-panel-services' )
			).toBeFocused();
			await page.keyboard.press( 'Tab' );
			await expect(
				page.locator( '#footer-panel-services a' ).first()
			).toBeFocused();
		} );

		test( `${ locale } ${ width }: service status bar and inline behaviours survive WordPress`, async ( {
			page,
		} ) => {
			const errors: string[] = [];
			page.on( 'pageerror', ( error ) => errors.push( error.message ) );
			await page.setViewportSize( { width, height: 900 } );
			await page.goto(
				`${ instance().url }${ locale === 'en' ? '/services-support/' : '/de/kundendienst/' }`
			);
			await dismissConsent( page );
			await expect( page.locator( '.lk-topbar br' ) ).toHaveCount( 0 );
			await expect( page.locator( '.lk-topbar a' ) ).toHaveCount( 2 );
			for ( let stage = 2; stage <= 5; stage++ ) {
				await page.locator( `#service-stage-tab-${ stage }` ).click();
				await expect(
					page.locator( `#service-stage-${ stage }` )
				).toBeVisible();
				await expect(
					page.locator( `#service-stage-tab-${ stage }` )
				).toHaveAttribute( 'aria-selected', 'true' );
			}
			await page.locator( '#service-role-tab-2' ).click();
			await expect( page.locator( '#service-role-2' ) ).toBeVisible();
			expect( errors ).toEqual( [] );
		} );

		test( `${ locale } ${ width }: privacy processing records retain readable measure`, async ( {
			page,
		} ) => {
			await page.setViewportSize( { width, height: 900 } );
			await page.goto(
				`${ instance().url }${ locale === 'en' ? '/privacy-policy/' : '/de/datenschutz/' }`
			);
			await dismissConsent( page );
			const records = page.locator(
				'[data-doc="privacy"] #section-2 tbody tr'
			);
			await expect( records ).toHaveCount( 7 );
			const measurements = await records.evaluateAll( ( rows ) =>
				rows.map( ( row ) => {
					const title = row
						.querySelector( 'th' )!
						.getBoundingClientRect();
					const prose = row
						.querySelector( 'td' )!
						.getBoundingClientRect();
					return {
						separated: prose.top > title.bottom,
						width: prose.width,
						available: row.getBoundingClientRect().width - 42,
					};
				} )
			);
			for ( const record of measurements ) {
				expect( record.separated ).toBe( true );
				expect( record.width ).toBeGreaterThanOrEqual(
					record.available - 1
				);
			}
			await page.emulateMedia( { media: 'print' } );
			await expect( page.locator( '#section-2 table' ) ).toHaveCSS(
				'display',
				'table'
			);
			await expect( records.first().locator( 'th' ) ).toHaveCSS(
				'display',
				'table-cell'
			);
		} );

		test( `${ locale } ${ width }: generated legal navigation retains language and chapter`, async ( {
			page,
		} ) => {
			await page.setViewportSize( { width, height: 900 } );
			const path =
				locale === 'en' ? '/privacy-policy/' : '/de/datenschutz/';
			await page.goto( `${ instance().url }${ path }#section-4` );
			await dismissConsent( page );
			const expected =
				locale === 'en'
					? [
							'/imprint/',
							'/privacy-policy/',
							'/terms-of-sale/',
							'/refund-returns/',
						]
					: [
							'/de/impressum/',
							'/de/datenschutz/',
							'/de/verkaufsbedingungen/',
							'/de/rueckgabe-erstattung/',
						];
			const routes = await page
				.locator( '.lga-docs-link' )
				.evaluateAll( ( links ) =>
					links.map(
						( link ) =>
							new URL( ( link as HTMLAnchorElement ).href )
								.pathname
					)
				);
			expect( routes ).toEqual( [ ...expected, ...expected ] );
			const other = locale === 'en' ? 'de' : 'en';
			await page
				.locator( `.lnk-lang-half[lang="${ other }"]:visible` )
				.click();
			await expect( page ).toHaveURL(
				`${ instance().url }${ locale === 'en' ? '/de/datenschutz/' : '/privacy-policy/' }#section-4`
			);
			await expect( page.locator( '#section-4 h2' ) ).toBeVisible();
		} );

		test( `${ locale } ${ width }: utility platform titles fit and details open`, async ( {
			page,
		} ) => {
			const errors: string[] = [];
			page.on( 'pageerror', ( error ) => errors.push( error.message ) );
			await page.setViewportSize( { width, height: 900 } );
			await page.goto(
				`${ instance().url }${ locale === 'en' ? '/solution/utility-storage/' : '/de/loesung/grossspeicher/' }`
			);
			await dismissConsent( page );
			const fit = await page.evaluate(
				() =>
					document.documentElement.scrollWidth <=
					document.documentElement.clientWidth
			);
			expect( fit ).toBe( true );
			if ( width === 390 ) {
				const card = page
					.locator( '.us-platform-mobile .us-platform' )
					.nth( 1 );
				const title = card.locator( 'summary > h3' );
				expect( ( await title.boundingBox() )!.width ).toBeGreaterThan(
					150
				);
				await card.locator( 'summary' ).click();
				await expect( card ).toHaveAttribute( 'open', '' );
				await expect(
					card.locator( '.lk-runway-detail' )
				).toBeVisible();
			}
			for ( let stage = 2; stage <= 4; stage++ ) {
				await page.locator( `#us-stage-tab-${ stage }` ).click();
				await expect(
					page.locator( `#us-stage-tab-${ stage }` )
				).toHaveAttribute( 'aria-selected', 'true' );
			}
			expect( errors ).toEqual( [] );
		} );
	}
}
