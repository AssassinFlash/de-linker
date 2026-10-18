<?php
/**
 * Tests for prices hidden at their source and the texts shown instead.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Gating;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WC_Order_Item_Product;
use WC_Product;
use WP_Mock;

/**
 * Tests for PriceDisplay, with the real price rule.
 *
 * @covers \Linker\Commerce\Gating\PriceDisplay
 */
final class PriceDisplayTest extends TestCase {

	/**
	 * Whether a customer is logged in, in the current step of a test.
	 *
	 * @var bool
	 */
	private bool $logged_in = false;

	/**
	 * Product mode of the products, in the current step of a test.
	 *
	 * @var string
	 */
	private string $mode = 'orderable';


	/**
	 * Translation and escaping return their input; the account page is /my-account/; login state and mode follow the properties.
	 */
	public function setUp(): void {
		parent::setUp();
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products( array( 4107 => 4107 ) );
		$this->plain_text();
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => fn (): bool => $this->logged_in ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => fn (): string => $this->mode ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
	}

	/**
	 * A simple product with a stored price and mode.
	 *
	 * @param string $price Stored price.
	 * @return WC_Product&\Mockery\MockInterface
	 */
	private function product( string $price = '1680' ) {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( 4107 );
		$product->allows( 'get_parent_id' )->andReturn( 0 );
		$product->allows( 'get_price' )->with( 'edit' )->andReturn( $price );
		return $product;
	}

	/**
	 * The visitor state of a test.
	 *
	 * @param bool   $logged_in Whether a customer is logged in.
	 * @param string $mode      Product mode.
	 * @param bool   $approved  Whether the account's prices are open.
	 */
	private function visitor( bool $logged_in, string $mode = 'orderable', bool $approved = true ): PriceDisplay {
		$this->logged_in = $logged_in;
		$this->mode      = $mode;
		$this->approval_meta( $approved ? array( Approval::STATUS_META => Approval::APPROVED ) : array() );
		return new PriceDisplay( new CommerceState( new Approval() ) );
	}

	/**
	 * A guest's request has no price at all; a customer's has the stored one.
	 */
	public function test_price_at_the_source(): void {
		$this->assertSame( '', $this->visitor( false )->price( '1680', $this->product() ) );
		$this->assertSame( '1680', $this->visitor( true )->price( '1680', $this->product() ) );
		$this->assertSame( '', $this->visitor( true, 'rfq_only' )->price( '22350', $this->product( '22350' ) ) );
	}

	/**
	 * Other plugins ask the same rule through a filter (Genie's shell tells its
	 * service whether the account is approved, #242): a guest, a pending and a
	 * restricted account do not see prices, an approved one does.
	 */
	public function test_other_plugins_read_the_rule_through_the_filter(): void {
		$this->assertFalse( $this->visitor( false )->sees_prices() );
		$this->assertTrue( $this->visitor( true )->sees_prices() );
		$this->assertFalse( $this->visitor( true, 'orderable', false )->sees_prices() );
		$this->logged_in = true;
		$this->approval_meta( array( Approval::STATUS_META => Approval::RESTRICTED ) );
		$this->assertFalse( ( new PriceDisplay( new CommerceState( new Approval() ) ) )->sees_prices() );
	}

	/**
	 * The variation price cache differs between visitors with and without prices.
	 */
	public function test_variation_price_hash(): void {
		$this->assertSame(
			array(
				'x',
				'linker_prices_visible' => false,
			),
			$this->visitor( false )->variation_prices_hash( array( 'x' ) )
		);
	}

	/**
	 * A published simple product stays addable without a visible price; drafts, grouped products and WooCommerce's yes stay as they are.
	 */
	public function test_purchasable(): void {
		$display = $this->visitor( false );
		$product = $this->product();
		$product->allows( 'exists' )->andReturn( true );
		$product->allows( 'is_type' )->with( array( 'simple', 'variation' ) )->andReturn( true );
		WP_Mock::userFunction( 'get_post_status', array( 'return_in_order' => array( 'publish', 'draft' ) ) );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => false ) );

		$this->assertTrue( $display->purchasable( false, $product ) );
		$this->assertFalse( $display->purchasable( false, $product ) );
		$this->assertTrue( $display->purchasable( true, $product ) );

		$grouped = $this->product();
		$grouped->allows( 'exists' )->andReturn( true );
		$grouped->allows( 'is_type' )->andReturn( false );
		$this->assertFalse( $display->purchasable( false, $grouped ) );
	}

	/**
	 * The texts: log in (guest), the account's approval (signed in without
	 * approval), quoted per project, price on request (no stored price).
	 */
	public function test_texts_instead_of_prices(): void {
		$this->assertSame( '<a class="linker-price-login" href="https://example.test/my-account/">Log in for prices</a>', $this->visitor( false )->empty_price_html( '', $this->product() ) );
		$this->assertSame( '<span class="linker-price-note">Account under review. Prices after approval.</span>', $this->visitor( true, 'orderable', false )->empty_price_html( '', $this->product() ) );
		$this->assertSame( '<span class="linker-price-note">Quoted per project</span>', $this->visitor( true, 'rfq_only' )->empty_price_html( '', $this->product( '22350' ) ) );
		$this->assertSame( '<span class="linker-price-note">Price on request</span>', $this->visitor( true )->empty_price_html( '', $this->product( '' ) ) );
		$this->assertSame( 'WooCommerce', $this->visitor( true )->empty_price_html( 'WooCommerce', $this->product() ) );
	}

	/** Approval removes pending wording even from an inquiry's recorded missing price. */
	public function test_approved_account_reads_a_neutral_note_on_its_pending_inquiry(): void {
		$display = $this->visitor( true );
		$item    = \Mockery::mock( \WC_Order_Item_Product::class );
		$item->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( CommerceState::APPROVAL );
		$item->allows( 'get_total' )->andReturn( '0' );
		$this->assertSame( '<span class="linker-price-note">Price on request</span>', $display->order_line_subtotal( '€0.00', $item ) );
	}

	/**
	 * Solution draft lines show the text in their price and subtotal cells.
	 */
	public function test_draft_lines(): void {
		$display = $this->visitor( true );

		$this->assertSame( '<span class="linker-price-note">Price on request</span>', $display->cart_item_price( '€0.00', array( 'data' => $this->product( '' ) ) ) );
		$this->assertSame( '€1,680.00', $display->cart_item_price( '€1,680.00', array( 'data' => $this->product() ) ) );
		$this->assertSame( '€1.00', $display->cart_item_price( '€1.00', array() ) );
	}

	/**
	 * A visitor's draft subtotal names what opens the prices: "log in" for a
	 * guest, the account's approval for a signed-in one; an approved
	 * customer's subtotal stays. The guest's text is plain: the theme prints
	 * the subtotal inside its own link to the draft, so a link here would nest
	 * one link in another.
	 */
	public function test_draft_subtotal(): void {
		$guest = $this->visitor( false )->cart_subtotal( '€0.00' );
		$this->assertSame( '<span class="linker-price-note">Log in for prices</span>', $guest );
		$this->assertStringNotContainsString( '<a ', $guest, 'No link inside the theme\'s own link to the draft.' );
		$this->assertSame( '<span class="linker-price-note">Account under review. Prices after approval.</span>', $this->visitor( true, 'orderable', false )->cart_subtotal( '€0.00' ) );
		$this->assertSame( '€3,360.00', $this->visitor( true )->cart_subtotal( '€3,360.00' ) );
	}

	/**
	 * Inquiry lines remember why they had no price; staff see the missing price as the line's 0, not the bookkeeping key.
	 */
	public function test_inquiry_lines(): void {
		$display = $this->visitor( true );
		$item    = Mockery::mock( WC_Order_Item_Product::class );
		$item->expects( 'add_meta_data' )->with( PriceDisplay::ITEM_REASON_META, 'unpriced', true );
		$display->remember_line_reason( $item, 'key', array( 'data' => $this->product( '' ) ) );

		$unpriced = Mockery::mock( WC_Order_Item_Product::class );
		$unpriced->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( 'unpriced' );
		$unpriced->allows( 'get_total' )->andReturn( '0' );
		$priced = Mockery::mock( WC_Order_Item_Product::class );
		$priced->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( 'unpriced' );
		$priced->allows( 'get_total' )->andReturn( '680' );

		$this->assertSame( '<span class="linker-price-note">Price on request</span>', $display->order_line_subtotal( '€0.00', $unpriced ) );
		$this->assertSame( '€680.00', $display->order_line_subtotal( '€680.00', $priced ) );

		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_items' )->andReturn( array( $priced, $unpriced ) );
		$this->assertTrue( $display->has_unpriced_lines( $order ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_items' )->andReturn( array( $priced ) );
		$this->assertFalse( $display->has_unpriced_lines( $order ) );

		$this->assertSame( array( '_reduced_stock', PriceDisplay::ITEM_REASON_META ), $display->hidden_item_meta( array( '_reduced_stock' ) ) );
	}

	/**
	 * Removing account price access also hides previously priced inquiry lines.
	 *
	 * @testWith ["pending", "Account under review. Prices after approval."]
	 *           ["restricted", "Not available for your account"]
	 *           ["guest", "Log in for prices"]
	 * @param string $status Account state.
	 * @param string $note Expected price note.
	 */
	public function test_priced_inquiry_line_respects_current_access( string $status, string $note ): void {
		$this->logged_in = 'guest' !== $status;
		$this->approval_meta( array( Approval::STATUS_META => $status ) );
		$item = Mockery::mock( WC_Order_Item_Product::class );
		$item->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( '' );
		$item->allows( 'get_total' )->andReturn( '100' );
		$html = ( new PriceDisplay( new CommerceState() ) )->order_line_subtotal( '€100.00', $item );
		$this->assertStringContainsString( $note, $html );
		$this->assertStringNotContainsString( '€', $html );
	}

	/**
	 * All inquiry surfaces share visibility and missing-line checks.
	 *
	 * @testWith [true, true, false, true]
	 *           [true, true, true, false]
	 *           [true, false, false, false]
	 *           [false, false, false, false]
	 * @param bool $signed_in Signed-in visitor.
	 * @param bool $approved Approved customer.
	 * @param bool $unpriced A line awaits a price.
	 * @param bool $visible Monetary totals are visible.
	 */
	public function test_inquiry_totals_follow_account_and_lines( bool $signed_in, bool $approved, bool $unpriced, bool $visible ): void {
		$display = $this->visitor( $signed_in, 'orderable', $approved );
		$item    = Mockery::mock( WC_Order_Item_Product::class );
		$item->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( $unpriced ? CommerceState::APPROVAL : '' );
		$item->allows( 'get_total' )->andReturn( $unpriced ? '0' : '100' );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_items' )->andReturn( array( $item ) );
		$order->allows( 'get_item_count' )->andReturn( 1 );
		$order->allows( 'get_meta' )->with( '_linker_inquiry_source' )->andReturn( '' );
		$totals = array(
			'order_total' => array(
				'label' => 'Total',
				'value' => '€100.00',
			),
		);
		$this->assertSame( $visible, $display->shows_order_total( $order ) );
		$this->assertSame( $visible ? $totals : array(), $display->order_totals( $totals, $order ) );
	}
}
