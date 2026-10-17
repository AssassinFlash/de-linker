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
	 * Whether linker-i18n's language layer listens in the current test.
	 *
	 * @var bool
	 */
	private bool $language_layer = false;

	/**
	 * Without the language layer a product's mode is its own.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'has_filter', array( 'return' => fn (): bool => $this->language_layer ) );
	}

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

	/**
	 * The product page decides in its own order: an account without prices
	 * reads its account's reason before the product's, and an approved one
	 * reads "quoted per project" or "on request" where there is no price.
	 *
	 * @testWith [false, null, "orderable", "1680", "login"]
	 *           [false, null, "rfq_only", "33250", "login"]
	 *           [true, "pending", "rfq_only", "33250", "approval"]
	 *           [true, "restricted", "orderable", "1680", "approval"]
	 *           [true, "approved", "rfq_only", "33250", "project"]
	 *           [true, "approved", "orderable", "", "unpriced"]
	 *           [true, "approved", "orderable", "1680", null]
	 *
	 * @param bool        $logged_in Whether a visitor is signed in.
	 * @param string|null $status    The account's approval state.
	 * @param string      $mode      Product mode.
	 * @param string      $price     Stored price.
	 * @param string|null $reason    Expected reason.
	 */
	public function test_page_reason( bool $logged_in, ?string $status, string $mode, string $price, ?string $reason ): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $logged_in ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => $mode ) );
		$this->approval_meta( null === $status ? array() : array( Approval::STATUS_META => $status ) );
		$this->signed_in( $logged_in ? 5 : 0 );
		$state = new CommerceState( new Approval() );

		$this->assertSame( $reason, $state->page_reason( $this->product( 4107, 0, $price ) ) );
	}

	/**
	 * The German twin of 1957 (6800 in the live snapshot of 2026-10-17)
	 * carries no mode of its own: it is asked through its English product,
	 * the one the solution draft holds.
	 */
	public function test_a_german_product_reads_the_mode_of_its_english_one(): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): string => CommerceState::MODE_META === $key && 1957 === $id ? 'rfq_only' : '',
			)
		);
		// linker-i18n swaps a German product for its English one.
		$this->language_layer = true;
		$this->filter_returns( 'linker_commerce_facts_product_id', 1957, array( 6800 ) );
		$this->filter_returns( 'linker_commerce_facts_product_id', 4107, array( 4107 ) );
		$state = new CommerceState( new Approval() );

		$this->assertTrue( $state->is_rfq_only( $this->product( 6800 ) ) );
		$this->assertFalse( $state->is_rfq_only( $this->product( 4107 ) ) );
	}
}
