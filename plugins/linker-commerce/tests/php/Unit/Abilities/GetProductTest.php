<?php
/**
 * Tests for linker/get-product.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\GetProduct;
use Linker\Commerce\Tests\Support\MocksCatalogue;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for GetProduct.
 *
 * @covers \Linker\Commerce\Abilities\GetProduct
 */
final class GetProductTest extends TestCase {

	use MocksCatalogue;

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
		$this->mock_catalogue( array( 4107 ) );
		$result = ( new GetProduct() )->execute(
			array(
				'product_id' => 4107,
				'lang'       => 'en',
			)
		);

		$this->assertSame( 4107, $result['product_id'] );
		$this->assertNotSame( '', $result['title'] );
		$this->assertSame( 'home', $result['facts']['application'] );
		$this->assertSame( 3, $result['facts']['phase'] );
		$this->assertFalse( $result['commerce']['price_visible'] );
		$this->assertTrue( $result['commerce']['in_stock'] );
		$this->assertTrue( ( new GetProduct() )->can_execute() );
		$schema = ( new GetProduct() )->args()['output_schema'];
		$this->assertContains( 'facts', $schema['required'] );
		$this->assertContains( 'documents', $schema['required'] );
		$this->assertContains( 'faq', $schema['required'] );
	}

	/**
	 * An unpublished or missing ID still fits the schema.
	 */
	public function test_missing_product_fits_the_schema(): void {
		$this->mock_catalogue( array() );
		$result = ( new GetProduct() )->execute( array( 'product_id' => 1 ) );

		$this->assertSame( '', $result['title'] );
		$this->assertSame( array(), (array) $result['facts'] );
	}
}
