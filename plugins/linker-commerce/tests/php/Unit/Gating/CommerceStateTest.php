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
	 * The products of these tests are English: each answers for itself.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->english_products(
			array(
				1957 => 1957,
				4107 => 4107,
			)
		);
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
	 * The card surface (WooCommerce's own price HTML, the solution draft's and
	 * the inquiry's lines, the Store API) names the product before the account:
	 * live 2026-10-18, a guest's Store API answer for 1957 has the price_html
	 * "Quoted per project". Guests see no prices; approved customers see them
	 * except for products quoted per project.
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

		$this->assertSame( $reason, $state->reason( $product, CommerceState::CARD ) );
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

		$this->assertSame( CommerceState::APPROVAL, $state->reason( $this->product( 4107 ), CommerceState::CARD ) );
		$this->assertSame( CommerceState::APPROVAL, $state->reason( $this->product( 4107 ), CommerceState::PAGE ) );
		$this->assertSame( CommerceState::APPROVAL, $state->visitor_reason() );
		$this->assertFalse( $state->visitor_sees_prices() );
		$this->assertSame( Approval::PENDING, $state->current_approval_status() );
	}

	/**
	 * The page surface (the product page, the comparison page, Genie's card)
	 * names the account before the product: live 2026-10-18, the guest's
	 * product page of 1957 reads "Net price after partner sign-in", not
	 * "Quoted per project". An approved account reads "quoted per project" or
	 * "on request" where there is no price.
	 *
	 * @testWith [false, null, "orderable", "1680", "login"]
	 *           [false, null, "rfq_only", "33250", "login"]
	 *           [true, "pending", "rfq_only", "33250", "approval"]
	 *           [true, "restricted", "orderable", "1680", "unavailable"]
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
	public function test_the_page_names_the_account_first( bool $logged_in, ?string $status, string $mode, string $price, ?string $reason ): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $logged_in ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => $mode ) );
		$this->approval_meta( null === $status ? array() : array( Approval::STATUS_META => $status ) );
		$this->signed_in( $logged_in ? 5 : 0 );
		$state = new CommerceState( new Approval() );

		$this->assertSame( $reason, $state->reason( $this->product( 4107, 0, $price ), CommerceState::PAGE ) );
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
		$this->english_products( array( 6800 => 1957 ) );
		$state = new CommerceState( new Approval() );

		$this->assertTrue( $state->is_rfq_only( $this->product( 6800 ) ) );
		$this->assertFalse( $state->is_rfq_only( $this->product( 4107 ) ) );
	}

	/**
	 * A surface the rule does not know is refused, not guessed.
	 */
	public function test_an_unknown_surface_is_refused(): void {
		$this->expectException( \InvalidArgumentException::class );
		( new CommerceState( new Approval() ) )->reason( $this->product( 4107 ), 'shelf' );
	}

	/** A recorded approval reason becomes an unset line price after approval. */
	public function test_approved_historical_approval_reason_is_unpriced(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::APPROVED ) );
		$this->signed_in( 5 );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$this->assertSame( CommerceState::UNPRICED, ( new CommerceState() )->reason( CommerceState::APPROVAL, CommerceState::CARD ) );
	}
}
