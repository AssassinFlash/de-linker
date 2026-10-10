<?php
/**
 * Tests for the German shop on the English products.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Woo;

use Linker\I18n\Languages;
use Linker\I18n\Tests\Unit\PolylangDouble;
use Linker\I18n\Woo\Storefront;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Storefront.
 *
 * @covers \Linker\I18n\Woo\Storefront
 */
final class StorefrontTest extends TestCase {

	/**
	 * Whether the request runs in the admin.
	 *
	 * @var bool
	 */
	private static bool $admin = false;

	/**
	 * The storefront of the current test.
	 */
	private function storefront(): Storefront {
		WP_Mock::userFunction( 'is_admin', array( 'return' => static fn(): bool => self::$admin ) );
		return new Storefront( new Languages() );
	}

	/**
	 * The mocks the quoted name needs: the wrapper string, tag stripping and
	 * the German title.
	 *
	 * @param array<int, string> $titles Post ID => title.
	 */
	private function names( array $titles ): void {
		WP_Mock::userFunction(
			'_x',
			array(
				'args'   => array( '&ldquo;%s&rdquo;', 'Item name in quotes', 'woocommerce' ),
				'return' => static fn( string $format ): string => $format,
			)
		);
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn( string $text ): string => trim( preg_replace( '/<[^>]*>/', '', $text ) ?? $text ) ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => static fn( $id ) => $titles[ (int) $id ] ?? '' ) );
	}

	/**
	 * A German request names the German product in the add-to-cart notice's
	 * quotes: the notice takes its name from get_the_title(), which the
	 * get_name() filter does not reach.
	 */
	public function test_german_notice_names_the_german_product(): void {
		self::$admin = false;
		PolylangDouble::mock(
			array(
				24  => 'en',
				249 => 'de',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'de'
		);
		$this->names(
			array(
				24  => 'SAJ CB2 (battery cabinet)',
				249 => 'SAJ CB2 (Batteriespeicherschrank)',
			)
		);

		$quoted = $this->storefront()->quoted_item_name( '&ldquo;SAJ CB2 (battery cabinet)&rdquo;', 24 );

		$this->assertSame( '&ldquo;SAJ CB2 (Batteriespeicherschrank)&rdquo;', $quoted );
	}

	/**
	 * An English request, and a product with no German version, keep
	 * WooCommerce's own name in the quotes.
	 */
	public function test_other_requests_and_untranslated_products_keep_the_name(): void {
		$english = '&ldquo;SAJ CB2 (battery cabinet)&rdquo;';

		self::$admin = false;
		PolylangDouble::mock(
			array(
				24 => 'en',
				25 => 'en',
			),
			array( 24 => 249 ),
			array(),
			array(),
			'en'
		);
		$this->names( array( 249 => 'SAJ CB2 (Batteriespeicherschrank)' ) );
		$this->assertSame( $english, $this->storefront()->quoted_item_name( $english, 24 ), 'English request' );

		self::$admin = false;
		PolylangDouble::mock( array( 25 => 'en' ), array(), array(), array(), 'de' );
		$this->names( array() );
		$this->assertSame( $english, $this->storefront()->quoted_item_name( $english, 25 ), 'No German version' );

		self::$admin = true;
		PolylangDouble::mock( array( 24 => 'en' ), array( 24 => 249 ), array(), array(), 'de' );
		$this->names( array() );
		$this->assertSame( $english, $this->storefront()->quoted_item_name( $english, 24 ), 'Admin request' );
	}
}
