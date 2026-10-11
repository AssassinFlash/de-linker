<?php
/**
 * Tests for the product page's structured data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\ProductSchema;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Tests for ProductSchema: the Product node carries the product's own facts,
 * never a price, and an unknown fact is left out rather than guessed.
 *
 * @covers \Linker\Commerce\Storefront\ProductSchema
 */
final class ProductSchemaTest extends TestCase {

	private const PRODUCT = 6521;

	/**
	 * JSON encoding is the real one; everything else the class touches is mocked per test.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction(
			'wp_json_encode',
			array( 'return' => static fn( $value, $flags = 0 ) => json_encode( $value, $flags ) )
		);
		WP_Mock::userFunction(
			'wp_strip_all_tags',
			array( 'return' => static fn( $value ) => strip_tags( (string) $value ) )
		);
	}

	/**
	 * The hook the block is printed on.
	 */
	public function test_register_adds_the_block_to_the_head(): void {
		$schema = new ProductSchema();
		WP_Mock::expectActionAdded( 'wp_head', array( $schema, 'print_block' ) );

		$schema->register();

		$this->assertConditionsMet();
	}

	/**
	 * Every fact the page shows about the product, under the name schema.org
	 * gives it. The values are the ones the live page carries today.
	 */
	public function test_the_block_carries_the_products_own_facts(): void {
		$schema = new ProductSchema();
		$data   = $schema->data( $this->product() );

		$this->assertSame( 'https://schema.org', $data['@context'] );
		$this->assertSame( 'Product', $data['@type'] );
		$this->assertSame( 'GoodWe GW5.1-BAT-D-G21 (ESA battery module, 5.12 kWh)', $data['name'] );
		$this->assertSame( 'https://de-linker.com/product/gw51/', $data['url'] );
		$this->assertSame( 'DLK-GOODWE-GW51BATDG21', $data['sku'] );
		$this->assertSame(
			array(
				'@type' => 'Brand',
				'name'  => 'GoodWe',
			),
			$data['brand']
		);
		$this->assertSame(
			array(
				'@type' => 'Organization',
				'name'  => 'GoodWe',
			),
			$data['manufacturer']
		);
		$this->assertSame( 'GW5.1-BAT-D-G21', $data['model'] );
		$this->assertSame( 'Home Storage', $data['category'] );
		$this->assertStringContainsString( '5.12 kWh rated ESA battery module', $data['description'] );
		$this->assertSame( 'https://de-linker.com/full.png', $data['image'] );
		$this->assertConditionsMet();
	}

	/**
	 * The gate #11 owns: this block lands in pages LiteSpeed serves to
	 * anonymous visitors, so a price in it would leak what the gate hides.
	 */
	public function test_the_block_never_carries_a_price(): void {
		$schema = new ProductSchema();
		$json   = $schema->encoded( $this->product() );

		foreach ( array( '"price"', 'priceCurrency', 'listPrice', 'lowPrice', 'Net price', '€' ) as $forbidden ) {
			$this->assertStringNotContainsString( $forbidden, $json, "the block must not carry $forbidden" );
		}
		// The block still carries the two public facts of an offer.
		$this->assertStringContainsString( '"@type":"Offer"', $json );
		$this->assertStringContainsString( '"availability":"https://schema.org/InStock"', $json );
		$this->assertConditionsMet();
	}

	/**
	 * Availability is WooCommerce's own stock state — the authority once the
	 * previous tree's mirror is gone (its states map one to one).
	 *
	 * @param string $status   WooCommerce's stock status.
	 * @param string $expected The schema.org term, or '' for "claim nothing".
	 * @dataProvider stock_states
	 */
	public function test_availability_follows_the_stock_state( string $status, string $expected ): void {
		$schema = new ProductSchema();
		$offers = $schema->data( $this->product( stock_status: $status ) )['offers'];

		if ( '' === $expected ) {
			$this->assertArrayNotHasKey( 'availability', $offers );
			$this->assertSame( 'https://de-linker.com/product/gw51/', $offers['url'] );
			return;
		}
		$this->assertSame( $expected, $offers['availability'] );
		$this->assertConditionsMet();
	}

	/**
	 * WooCommerce's statuses and what each means in schema.org.
	 *
	 * @return array<string, array{string, string}>
	 */
	public static function stock_states(): array {
		return array(
			'in stock'      => array( 'instock', 'https://schema.org/InStock' ),
			'out of stock'  => array( 'outofstock', 'https://schema.org/OutOfStock' ),
			'on backorder'  => array( 'onbackorder', 'https://schema.org/BackOrder' ),
			'unknown state' => array( 'reserved-for-review', '' ),
		);
	}

	/**
	 * A fact the product does not have is left out. An empty string is a
	 * claim that the value is nothing; an absent key is no claim at all.
	 */
	public function test_a_missing_fact_is_left_out_rather_than_emptied(): void {
		$schema = new ProductSchema();
		$data   = $schema->data( $this->product( sku: '', model: array(), image: 0, category: array() ) );

		$this->assertArrayNotHasKey( 'sku', $data );
		$this->assertArrayNotHasKey( 'model', $data );
		$this->assertArrayNotHasKey( 'image', $data );
		$this->assertArrayNotHasKey( 'category', $data );
		$this->assertArrayHasKey( 'name', $data );
		$this->assertConditionsMet();
	}

	/**
	 * A product without a brand term gets no brand and no manufacturer: the
	 * one thing the block must never do is name this company as the maker of
	 * somebody else's inverter.
	 */
	public function test_a_product_without_a_brand_says_nothing_about_a_brand(): void {
		$schema = new ProductSchema();
		$data   = $schema->data( $this->product( brand: array() ) );

		$this->assertArrayNotHasKey( 'brand', $data );
		$this->assertArrayNotHasKey( 'manufacturer', $data );
		$this->assertConditionsMet();
	}

	/**
	 * The German page's block must carry the German address, the way every
	 * link on that page does.
	 */
	public function test_the_url_is_the_permalink_of_the_page_that_prints_the_block(): void {
		$schema = new ProductSchema();
		$data   = $schema->data( $this->product( permalink: 'https://de-linker.com/de/produkt/gw51/' ) );

		$this->assertSame( 'https://de-linker.com/de/produkt/gw51/', $data['url'] );
		$this->assertSame( 'https://de-linker.com/de/produkt/gw51/', $data['offers']['url'] );
		$this->assertConditionsMet();
	}

	/**
	 * A product named with a `<` would otherwise close the script element and
	 * spill the block onto the page as text.
	 */
	public function test_a_less_than_sign_cannot_end_the_script_element(): void {
		$schema = new ProductSchema();
		$json   = $schema->encoded( $this->product( name: 'Inverter &lt;/script&gt;&lt;b&gt;x' ) );

		// The name reaches the block HTML-decoded and tag-stripped, as the
		// page's own heading does; what is left is the character, not an entity.
		$this->assertStringNotContainsString( '<', $json );
		$this->assertStringContainsString( '\u003C/script>', $json );
		$this->assertStringContainsString( 'Inverter', $json );
		$this->assertConditionsMet();
	}

	/**
	 * The name the page prints is HTML-decoded first ('C&I'), because the
	 * encoder escapes for itself and the heading above the block is decoded.
	 */
	public function test_the_name_is_the_decoded_one_the_page_prints(): void {
		$schema = new ProductSchema();
		$data   = $schema->data( $this->product( name: 'C&amp;I inverter &lt;GW&gt;' ) );

		$this->assertSame( 'C&I inverter <GW>', $data['name'] );
		$this->assertConditionsMet();
	}

	/**
	 * Nothing is printed for a request that is not a product page.
	 */
	public function test_nothing_is_printed_off_a_product_page(): void {
		WP_Mock::userFunction(
			'is_singular',
			array(
				'args'   => array( 'product' ),
				'return' => false,
			)
		);
		$schema = new ProductSchema();

		ob_start();
		$schema->print_block();
		$printed = (string) ob_get_clean();

		$this->assertSame( '', $printed );
		$this->assertConditionsMet();
	}

	/**
	 * A product page prints exactly one block, wrapped in the element a
	 * structured-data reader looks for.
	 */
	public function test_a_product_page_prints_one_block(): void {
		WP_Mock::userFunction(
			'is_singular',
			array(
				'args'   => array( 'product' ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => self::PRODUCT ) );
		$product = $this->product();
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'args'   => array( self::PRODUCT ),
				'return' => $product,
			)
		);

		ob_start();
		( new ProductSchema() )->print_block();
		$printed = (string) ob_get_clean();

		$this->assertSame( 1, substr_count( $printed, 'type="application/ld+json"' ) );
		$this->assertStringStartsWith( '<script type="application/ld+json">', $printed );
		$this->assertStringContainsString( '"@type":"Product"', $printed );
		$this->assertConditionsMet();
	}

	/**
	 * A product page of a product that is not a product (a deleted one, a
	 * variation whose parent is gone) prints nothing.
	 */
	public function test_a_page_without_a_product_prints_nothing(): void {
		WP_Mock::userFunction(
			'is_singular',
			array(
				'args'   => array( 'product' ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'get_the_ID', array( 'return' => self::PRODUCT ) );
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'args'   => array( self::PRODUCT ),
				'return' => false,
			)
		);

		ob_start();
		( new ProductSchema() )->print_block();
		$printed = (string) ob_get_clean();

		$this->assertSame( '', $printed );
		$this->assertConditionsMet();
	}

	/**
	 * A product double with the values product 6521 holds on the live site.
	 *
	 * @param array<int, string>|null $brand       pa_brand terms (null: GoodWe).
	 * @param array<int, string>|null $model       pa_model terms (null: the model code).
	 * @param array<int, string>|null $category    product_cat terms (null: Home Storage).
	 * @param string                  $name        Product name.
	 * @param string                  $sku         SKU.
	 * @param string                  $stock_status WooCommerce stock status.
	 * @param int                     $image       Featured attachment ID.
	 * @param string                  $permalink   The page's own address.
	 */
	private function product(
		?array $brand = null,
		?array $model = null,
		?array $category = null,
		string $name = 'GoodWe GW5.1-BAT-D-G21 (ESA battery module, 5.12 kWh)',
		string $sku = 'DLK-GOODWE-GW51BATDG21',
		string $stock_status = 'instock',
		int $image = 900,
		string $permalink = 'https://de-linker.com/product/gw51/'
	): WC_Product {
		$terms = array(
			'pa_brand'    => null === $brand ? array( 'GoodWe' ) : $brand,
			'pa_model'    => null === $model ? array( 'GW5.1-BAT-D-G21' ) : $model,
			'product_cat' => null === $category ? array( 'Home Storage' ) : $category,
		);
		foreach ( $terms as $taxonomy => $names ) {
			WP_Mock::userFunction(
				'get_the_terms',
				array(
					'args'   => array( self::PRODUCT, $taxonomy ),
					'return' => array() === $names ? false : array_map(
						static fn( string $term ) => (object) array( 'name' => $term ),
						array_values( $names )
					),
				)
			);
		}
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( self::PRODUCT ),
				'return' => $permalink,
			)
		);
		WP_Mock::userFunction(
			'wp_get_attachment_image_url',
			array(
				'args'   => array( $image, 'full' ),
				'return' => 0 === $image ? false : 'https://de-linker.com/full.png',
			)
		);

		$product = Mockery::mock( WC_Product::class );
		$product->shouldReceive( 'get_id' )->andReturn( self::PRODUCT );
		$product->shouldReceive( 'get_name' )->andReturn( $name );
		$product->shouldReceive( 'get_sku' )->andReturn( $sku );
		$product->shouldReceive( 'get_stock_status' )->andReturn( $stock_status );
		$product->shouldReceive( 'get_image_id' )->andReturn( $image );
		$product->shouldReceive( 'get_short_description' )->andReturn( '<p>GW5.1-BAT-D-G21 is the 5.12 kWh rated ESA battery module.</p>' );
		$product->shouldReceive( 'get_description' )->andReturn( '' );
		if ( 0 === $image ) {
			$product->shouldNotReceive( 'get_image_id' );
		}
		return $product;
	}
}
