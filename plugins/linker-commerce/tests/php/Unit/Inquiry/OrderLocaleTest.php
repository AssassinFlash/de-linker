<?php
/**
 * Tests for the language of an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for OrderLocale.
 *
 * @covers \Linker\Commerce\Inquiry\OrderLocale
 */
final class OrderLocaleTest extends TestCase {

	/**
	 * A new inquiry keeps the language the customer used; an inquiry without one uses the site's.
	 */
	public function test_remember_and_read(): void {
		WP_Mock::userFunction(
			'pll_current_language',
			array(
				'args'   => array( 'locale' ),
				'return' => false,
			)
		);
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'de_DE_formal' ) );
		$new = Mockery::mock( WC_Order::class );
		$new->expects( 'update_meta_data' )->with( OrderLocale::META, 'de_DE_formal' );
		( new OrderLocale() )->remember( $new );

		$german = Mockery::mock( WC_Order::class );
		$german->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'de_DE_formal' );
		$old = Mockery::mock( WC_Order::class );
		$old->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( '' );
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'WPLANG' ),
				'return' => '',
			)
		);

		$this->assertSame( 'de_DE_formal', OrderLocale::of( $german ) );
		$this->assertSame( 'en_US', OrderLocale::of( $old ) );
	}

	/**
	 * With Polylang running, the inquiry takes its current language's locale:
	 * the checkout AJAX address carries no language prefix (Checkout::language_field()).
	 */
	public function test_remember_prefers_polylangs_language(): void {
		WP_Mock::userFunction(
			'pll_current_language',
			array(
				'args'   => array( 'locale' ),
				'return' => 'de_DE_formal',
			)
		);

		$new = Mockery::mock( WC_Order::class );
		$new->expects( 'update_meta_data' )->with( OrderLocale::META, 'de_DE_formal' );

		( new OrderLocale() )->remember( $new );

		$this->assertConditionsMet();
	}

	/**
	 * The checkout AJAX request: Polylang cannot name a language there, so the
	 * form's own "lang" field does; its locale comes from Polylang's language table.
	 */
	public function test_remember_reads_the_posted_language_of_the_checkout(): void {
		WP_Mock::userFunction(
			'pll_current_language',
			array(
				'args'   => array( 'locale' ),
				'return' => false,
			)
		);
		$_POST['lang'] = 'de';

		$language = Mockery::mock( 'PLL_Language' );
		$language->allows( 'get_prop' )->with( 'locale' )->andReturn( 'de_DE_formal' );
		$model = Mockery::mock( 'PLL_Model' );
		$model->allows( 'get_language' )->with( 'de' )->andReturn( $language );
		$polylang = Mockery::mock( 'Polylang' );
		// Polylang's public $model; the stubs do not declare it.
		$polylang->model = $model; // @phpstan-ignore-line phpcs:ignore
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Polylang's own global.
		$GLOBALS['polylang'] = $polylang;
		WP_Mock::userFunction( 'PLL', array( 'return' => $polylang ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => 'de' ) );
		WP_Mock::userFunction(
			'wp_unslash',
			array(
				'return' => 'de',
			)
		);

		$new = Mockery::mock( WC_Order::class );
		$new->expects( 'update_meta_data' )->with( OrderLocale::META, 'de_DE_formal' );

		( new OrderLocale() )->remember( $new );

		unset( $GLOBALS['polylang'], $_POST['lang'] );
		$this->assertConditionsMet();
	}
}
