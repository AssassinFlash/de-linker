<?php
/**
 * Tests for the price rule.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Gating;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Registration\Approval;
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
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$state = new CommerceState( new Approval() );

		$this->assertTrue( $state->is_rfq_only( $this->product( 1957 ) ) );
		$this->assertTrue( $state->is_rfq_only( $this->product( 9000, 1957 ) ) );
		$this->assertFalse( $state->is_rfq_only( $this->product( 4107 ) ) );
	}

	/**
	 * Guests see no prices; approved customers see them except for products
	 * quoted per project.
	 *
	 * @testWith [false, true, "orderable", "100", "login"]
	 *           [true, true, "orderable", "", "unpriced"]
	 *           [true, true, "rfq_only", "22350", "project"]
	 *           [true, false, "rfq_only", "22350", "project"]
	 *
	 * @param bool        $logged_in Whether a visitor is signed in.
	 * @param bool        $approved  Whether the account's prices are open.
	 * @param string      $mode      Product mode.
	 * @param string      $price     Stored price.
	 * @param string|null $reason    Expected reason.
	 */
	public function test_reason( bool $logged_in, bool $approved, string $mode, string $price, ?string $reason ): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $logged_in ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => $mode ) );
		if ( $logged_in ) {
			WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		}
		$this->approval_meta( $approved ? array( Approval::STATUS_META => Approval::APPROVED ) : array() );
		$state   = new CommerceState( new Approval() );
		$product = $this->product( 4107, 0, $price );

		$this->assertSame( $reason, $state->reason( $product ) );
	}

	/**
	 * A signed-in account whose prices are not open reads its own state: the
	 * reason is the approval, not "log in".
	 */
	public function test_an_account_without_approval_reads_its_own_reason(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => 'orderable' ) );
		$this->approval_meta( array() );
		$state = new CommerceState( new Approval() );

		$this->assertSame( CommerceState::APPROVAL, $state->reason( $this->product( 4107 ) ) );
		$this->assertSame( CommerceState::APPROVAL, $state->visitor_reason() );
		$this->assertFalse( $state->visitor_sees_prices() );
		$this->assertSame( Approval::PENDING, $state->current_approval_status() );
	}
}
