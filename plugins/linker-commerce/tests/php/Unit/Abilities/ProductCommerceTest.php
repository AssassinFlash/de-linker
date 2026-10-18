<?php
/**
 * Tests for the commerce object of Genie's product abilities.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\ProductCommerce;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Prices follow the account (#242): the ability answers for the customer the
 * request names, by the site's one price rule.
 *
 * @covers \Linker\Commerce\Abilities\ProductCommerce
 */
final class ProductCommerceTest extends TestCase {

	/**
	 * Product 4107 (SAJ H2-10K-T3, live catalogue) with a stored price; the
	 * price line is what WooCommerce prints for it on the product page.
	 *
	 * @param string $price Stored price.
	 * @return WC_Product&\Mockery\MockInterface
	 */
	private function product( string $price = '1680' ) {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 4107 );
		$product->allows( 'get_parent_id' )->andReturn( 0 );
		$product->allows( 'get_price' )->with( 'edit' )->andReturn( $price );
		$product->allows( 'is_in_stock' )->andReturn( true );
		$product->allows( 'get_price_html' )->andReturn(
			'' === $price ? '' : '<span class="woocommerce-Price-amount amount"><bdi><span class="woocommerce-Price-currencySymbol">&euro;</span>1,680.00</bdi></span>'
		);
		return $product;
	}

	/**
	 * Signs in customer 5 in the given approval state, or nobody.
	 *
	 * @param string|null $status Approval state; null for a guest.
	 * @param string      $mode   The product's mode (CommerceState::MODE_META).
	 * @param string      $locale The turn's locale; anything but en_US switches.
	 */
	private function visitor( ?string $status, string $mode = 'orderable', string $locale = 'en_US' ): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => null !== $status ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => $mode ) );
		$this->english_products( array( 4107 => 4107 ) );
		$this->plain_text();
		// The request runs in English; a German turn's line is made inside
		// the German locale (Mail\LocaleSwitch).
		$this->reload_plugin_textdomain();
		if ( 'en_US' !== $locale ) {
			$this->allow_locale_switch( $locale );
			WP_Mock::userFunction( 'unload_textdomain', array( 'times' => '0+' ) );
		}
		$this->approval_meta( null === $status ? array() : array( Approval::STATUS_META => $status ) );
		$this->signed_in( null === $status ? 0 : 5 );
		// WordPress's own: strip_tags() after removing script and style bodies.
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn ( string $html ): string => strip_tags( $html ) ) );
	}

	/**
	 * The four account states: each reads the product page's own line — the
	 * approved account the price, the others the page's sentence — and the
	 * reason there is no price.
	 *
	 * @testWith ["approved", true, "€1,680.00", null]
	 *           ["pending", false, "Prices after approval", "pending"]
	 *           ["restricted", false, "Not available for your account", "restricted"]
	 *           [null, false, "Net price after partner sign-in", "login"]
	 *
	 * @param string|null $status  Approval state; null for a guest.
	 * @param bool        $visible Whether the price is visible.
	 * @param string|null $text    The price line.
	 * @param string|null $reason  Why there is no price.
	 */
	public function test_prices_follow_the_account( ?string $status, bool $visible, ?string $text, ?string $reason ): void {
		$this->visitor( $status );

		$commerce = ProductCommerce::of( 4107, $this->product() );

		$this->assertSame( $visible, $commerce['price_visible'] );
		$this->assertSame( $visible ? '1680' : null, $commerce['price'] ?? null );
		$this->assertSame( $text, $commerce['price_line'] ?? null );
		$this->assertSame( $reason, $commerce['price_reason'] ?? null );
		$this->assertFalse( $commerce['rfq_only'] );
	}

	/**
	 * A product quoted per project shows no price even to an approved account
	 * (live product 1957), and the card says what its product page says: the
	 * approved account reads "quoted per project", the others their own reason
	 * first, as on the page (CommerceState::reason on its PAGE surface).
	 *
	 * @testWith ["approved", "project", "Quoted per project"]
	 *           ["pending", "pending", "Prices after approval"]
	 *           ["restricted", "restricted", "Not available for your account"]
	 *           [null, "login", "Net price after partner sign-in"]
	 *
	 * @param string|null $status Approval state; null for a guest.
	 * @param string      $reason Why there is no price.
	 * @param string      $line   The page's sentence.
	 */
	public function test_a_product_quoted_per_project_shows_no_price( ?string $status, string $reason, string $line ): void {
		$this->visitor( $status, CommerceState::RFQ_ONLY );

		$commerce = ProductCommerce::of( 4107, $this->product() );

		$this->assertFalse( $commerce['price_visible'] );
		$this->assertArrayNotHasKey( 'price', $commerce );
		$this->assertSame( $line, $commerce['price_line'] ?? null );
		$this->assertSame( $reason, $commerce['price_reason'] ?? null );
		$this->assertTrue( $commerce['rfq_only'] );
	}

	/**
	 * An approved account on a product without a stored price reads the
	 * reason "unpriced"; the line is WooCommerce's empty-price text.
	 */
	public function test_an_unpriced_product_says_so(): void {
		$this->visitor( Approval::APPROVED );

		$commerce = ProductCommerce::of( 4107, $this->product( '' ) );

		$this->assertTrue( $commerce['price_visible'] );
		$this->assertSame( 'unpriced', $commerce['price_reason'] ?? null );
	}

	/**
	 * A German turn reads the line the German product page prints: the
	 * formatting and the sentences follow the language, so the line is made
	 * inside the German locale (the switch expects de_DE_formal; the money
	 * format itself is LocaleFormat's, pinned on the instance by
	 * GeniePricesTest).
	 */
	public function test_a_german_turn_reads_the_german_price_line(): void {
		$this->visitor( Approval::APPROVED, 'orderable', 'de_DE_formal' );

		$commerce = ProductCommerce::of( 4107, $this->product(), 'de' );

		$this->assertSame( '€1,680.00', $commerce['price_line'] ?? null );
	}

	/**
	 * The schema names every field the object can carry, and nothing else.
	 */
	public function test_the_schema_lists_the_price_line_and_its_reasons(): void {
		WP_Mock::passthruFunction( '__' );
		$schema = ProductCommerce::schema();

		$this->assertSame( array( 'price_visible', 'price', 'price_line', 'price_reason', 'in_stock', 'rfq_only' ), array_keys( $schema['properties'] ) );
		$this->assertSame( array( 'login', 'pending', 'restricted', 'project', 'unpriced' ), $schema['properties']['price_reason']['enum'] );
		$this->assertFalse( $schema['additionalProperties'] );
	}
}
