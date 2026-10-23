<?php
/**
 * Tests for linker/get-product.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\GetProduct;
use Linker\Commerce\Tests\Support\MocksLiveProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for GetProduct.
 *
 * @covers \Linker\Commerce\Abilities\GetProduct
 */
final class GetProductTest extends TestCase {

	use MocksLiveProducts;

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
	}

	/**
	 * A published product carries facts, commerce and REST schemas.
	 */
	public function test_published_product(): void {
		$this->mock_live_products( array( 4107 ) );
		$result = ( new GetProduct( $this->publication_data() ) )->execute(
			array(
				'product_id' => 4107,
				'lang'       => 'en',
			)
		);

		$this->assertSame( 4107, $result['product_id'] );
		$this->assertNotSame( '', $result['title'] );
		// Title and URL are the marker Genie reads as a real product
		// (facts._real_product); the commerce object's price line is not it.
		$this->assertNotSame( '', $result['url'] );
		$this->assertSame( 'home', $result['facts']['application'] );
		$this->assertSame( 3, $result['facts']['phase'] );
		$this->assertFalse( $result['commerce']['price_visible'] );
		$this->assertTrue( $result['commerce']['in_stock'] );
		$this->assertTrue( ( new GetProduct( $this->publication_data() ) )->can_execute() );
		$schema = ( new GetProduct( $this->publication_data() ) )->args()['output_schema'];
		$this->assertContains( 'facts', $schema['required'] );
		$this->assertContains( 'documents', $schema['required'] );
		$this->assertContains( 'faq', $schema['required'] );
	}

	/**
	 * An unpublished or missing ID still fits the schema. Its title, URL and
	 * SKU are empty: the three fields Genie reads as the marker of a real
	 * product (facts._real_product).
	 */
	public function test_missing_product_fits_the_schema(): void {
		$this->mock_live_products( array() );
		$result = ( new GetProduct( $this->publication_data() ) )->execute( array( 'product_id' => 1 ) );

		$this->assertSame( '', $result['title'] );
		$this->assertSame( '', $result['url'] );
		$this->assertSame( '', $result['sku'] );
		$this->assertSame( array(), (array) $result['facts'] );
	}
}
