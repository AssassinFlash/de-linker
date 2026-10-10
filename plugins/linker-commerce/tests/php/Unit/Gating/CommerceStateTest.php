<?php
/**
 * Tests for the price rule.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Gating;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Tests for CommerceState.
 *
 * @covers \Linker\Commerce\Gating\CommerceState
 */
final class CommerceStateTest extends TestCase {

	/**
	 * A product with the given id, parent and stored price.
	 *
	 * @param int    $id        Product id.
	 * @param int    $parent_id Parent id (variations).
	 * @param string $price     Stored price.
	 * @return WC_Product&\Mockery\MockInterface
	 */
	private function product( int $id, int $parent_id = 0, string $price = '100' ) {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( $id );
		$product->allows( 'get_parent_id' )->andReturn( $parent_id );
		$product->allows( 'get_price' )->with( 'edit' )->andReturn( $price );
		return $product;
	}

	/**
	 * Product 1957 is quoted per project (live catalogue data); a variation follows its parent.
	 */
	public function test_rfq_only_reads_the_product_mode(): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): string => CommerceState::MODE_META === $key && 1957 === $id ? 'rfq_only' : 'orderable',
			)
		);
		$state = new CommerceState();

		$this->assertTrue( $state->is_rfq_only( $this->product( 1957 ) ) );
		$this->assertTrue( $state->is_rfq_only( $this->product( 9000, 1957 ) ) );
		$this->assertFalse( $state->is_rfq_only( $this->product( 4107 ) ) );
	}

	/**
	 * Guests see no prices; customers see them except for products quoted per project.
	 *
	 * @testWith [false, "orderable", "100", "login"]
	 *           [true, "orderable", "", "unpriced"]
	 *           [true, "rfq_only", "22350", "project"]
	 *           [false, "rfq_only", "22350", "project"]
	 *
	 * @param bool        $logged_in Whether a customer is logged in.
	 * @param string      $mode      Product mode.
	 * @param string      $price     Stored price.
	 * @param string|null $reason    Expected reason.
	 */
	public function test_reason( bool $logged_in, string $mode, string $price, ?string $reason ): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $logged_in ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => $mode ) );
		$state   = new CommerceState();
		$product = $this->product( 4107, 0, $price );

		$this->assertSame( $reason, $state->reason( $product ) );
	}
}
