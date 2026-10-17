<?php
/**
 * Tests for the email language switch.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Tests\Fixtures\WooCommerce;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for LocaleSwitch.
 *
 * @covers \Linker\Commerce\Mail\LocaleSwitch
 */
final class LocaleSwitchTest extends TestCase {

	/**
	 * Switching sets WordPress's and WooCommerce's language, plugin translations and a fresh country list;
	 * switching back undoes only the locale stack entry this scope owns.
	 *
	 * @dataProvider switch_results
	 * @param bool $changed Whether WordPress pushed a new locale.
	 */
	public function test_switches_and_back( bool $changed ): void {
		$woocommerce = new WooCommerce();
		$countries   = $woocommerce->countries;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
		WP_Mock::userFunction(
			'switch_to_locale',
			array(
				'times'  => 1,
				'args'   => array( 'de_DE_formal' ),
				'return' => $changed,
			)
		);
		WP_Mock::userFunction( 'restore_previous_locale', array( 'times' => $changed ? 1 : 0 ) );
		$switch = new LocaleSwitch();
		WP_Mock::expectFilterAdded( 'plugin_locale', array( $switch, 'plugin_locale' ) );
		// The switch loads this plugin's German .mo itself, by file (review 2026-10-10, S2).
		WP_Mock::userFunction(
			'load_textdomain',
			array(
				'times' => 1,
				'args'  => array(
					'linker-commerce',
					dirname( __DIR__, 4 ) . '/languages/linker-commerce-de_DE_formal.mo',
				),
			)
		);
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		WP_Mock::userFunction(
			'remove_filter',
			array(
				'times' => 1,
				'args'  => array( 'plugin_locale', array( $switch, 'plugin_locale' ) ),
			)
		);

		$switch->to( 'de_DE_formal' );
		$this->assertSame( 'de_DE_formal', $switch->plugin_locale( 'en_US' ) );
		$this->assertNotSame( $countries, $woocommerce->countries, 'Country names in the new language.' );
		$switch->back();
		$this->assertSame( 'en_US', $switch->plugin_locale( 'en_US' ) );
		$this->assertSame( $countries, $woocommerce->countries );
		$this->assertSame( 2, $woocommerce->textdomain_loads );

		$this->assertConditionsMet();
	}

	/**
	 * Native switch_to_locale returns false when the requested locale is already active.
	 *
	 * @return array<string, array{bool}>
	 */
	public function switch_results(): array {
		return array(
			'new locale'  => array( true ),
			'same locale' => array( false ),
		);
	}

	/**
	 * The team's language is the site's default language; without one, English.
	 */
	public function test_site_default(): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'            => array( 'WPLANG' ),
				'return_in_order' => array( '', 'de_DE_formal' ),
			)
		);

		$this->assertSame( 'en_US', LocaleSwitch::site_default() );
		$this->assertSame( 'de_DE_formal', LocaleSwitch::site_default() );
	}
}
