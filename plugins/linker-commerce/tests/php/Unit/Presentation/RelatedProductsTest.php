<?php
/**
 * Tests for the stable related-products order.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\RelatedProducts;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for RelatedProducts.
 *
 * @covers \Linker\Commerce\Presentation\RelatedProducts
 */
final class RelatedProductsTest extends TestCase {

	/**
	 * The native loop shuffles (`orderby => 'rand'`); the filter replaces the
	 * order, nothing else — the loop, its query and its markup stay Woo's.
	 */
	public function test_the_native_loops_random_order_becomes_title_ascending(): void {
		$filtered = ( new RelatedProducts() )->order(
			array(
				'posts_per_page' => 4,
				'orderby'        => 'rand',
				'columns'        => 4,
			)
		);

		$this->assertSame( 'title', $filtered['orderby'] );
		$this->assertSame( 'ASC', $filtered['order'] );
		$this->assertSame( 4, $filtered['posts_per_page'] );
		$this->assertSame( 4, $filtered['columns'] );
	}

	/**
	 * The module registers the filter on Woo's own extension point.
	 */
	public function test_register_hooks_woos_related_products_args(): void {
		WP_Mock::expectFilterAdded( 'woocommerce_related_products_args', array( new RelatedProducts(), 'order' ) );

		( new RelatedProducts() )->register();

		$this->assertConditionsMet();
	}
}
