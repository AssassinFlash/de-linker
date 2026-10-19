<?php
/**
 * Tests for linker/inquiry-status.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\InquiryStatus;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WC_Order_Item_Product;
use WP_Mock;

/**
 * Tests for InquiryStatus.
 *
 * @covers \Linker\Commerce\Abilities\InquiryStatus
 */
final class InquiryStatusTest extends TestCase {

	/**
	 * Decimal amounts, grouped amounts and currency marks.
	 */
	private const MONEY = '/(?:€|\bEUR\b|\d+[.,]\d{2}|\d{1,3}(?:[.,]\d{3})+)/';

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * Guests cannot run the ability; a logged-in customer can.
	 */
	public function test_guests_cannot_run_the_ability(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->assertFalse( ( new InquiryStatus() )->can_execute() );
	}

	/**
	 * A logged-in customer may run the ability.
	 */
	public function test_customers_can_run_the_ability(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$this->assertTrue( ( new InquiryStatus() )->can_execute() );
	}

	/**
	 * The current customer's inquiries, with the four status names.
	 */
	public function test_lists_this_account_inquiries(): void {
		WP_Mock::userFunction(
			'is_user_logged_in',
			array(
				'times'  => '0+',
				'return' => true,
			)
		);
		$this->approval_meta( array( Approval::STATUS_META => Approval::APPROVED ) );
		$created = new \DateTimeImmutable( '2026-10-01T12:00:00+00:00' );
		$line    = Mockery::mock( WC_Order_Item_Product::class );
		$line->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( '' );
		$line->allows( 'get_total' )->andReturn( '1200.00' );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 59 );
		$order->allows( 'get_order_number' )->andReturn( '59' );
		$order->allows( 'get_status' )->andReturn( Statuses::PROFORMA );
		$order->allows( 'get_date_created' )->andReturn( $created );
		$order->allows( 'get_total' )->andReturn( '1200.00' );
		$order->allows( 'get_item_count' )->andReturn( 1 );
		$order->allows( 'get_items' )->andReturn( array( $line ) );
		$order->allows( 'get_meta' )->andReturnUsing(
			static fn ( string $key ): string => Issuer::NUMBER_META === $key ? 'PI-2026-0007' : ''
		);
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'args'   => array(
					array(
						'customer_id' => 5,
						'limit'       => -1,
						'orderby'     => 'date',
						'order'       => 'DESC',
					),
				),
				'return' => array( $order ),
			)
		);

		$result = ( new InquiryStatus() )->execute( array() );

		$this->assertSame( 59, $result['inquiries'][0]['id'] );
		$this->assertSame( Statuses::PROFORMA, $result['inquiries'][0]['status'] );
		$this->assertSame( 'Proforma invoice issued', $result['inquiries'][0]['status_label'] );
		$this->assertSame( 'PI-2026-0007', $result['inquiries'][0]['proforma_number'] );
		$this->assertSame( '1200.00', $result['inquiries'][0]['total'] );
		$schema = ( new InquiryStatus() )->args()['output_schema'];
		$this->assertSame( array( 'inquiries' ), $schema['required'] );
		$this->assertNotContains( 'total', $schema['properties']['inquiries']['items']['required'] );
	}

	/**
	 * A guest is refused before any inquiry is read. The REST layer turns that
	 * refusal into HTTP 401 (InquiryStatusRestTest).
	 */
	public function test_a_guest_reads_no_inquiries(): void {
		WP_Mock::userFunction(
			'is_user_logged_in',
			array(
				'times'  => '0+',
				'return' => false,
			)
		);

		$this->assertFalse( ( new InquiryStatus() )->can_execute() );
		$this->assertSame( array( 'inquiries' => array() ), ( new InquiryStatus() )->execute( array() ) );
	}

	/**
	 * Pending and restricted accounts keep their own inquiry and lose the amount.
	 * The field is absent, not a translated dash, so English and German are the
	 * same payload. The raw JSON must not contain an amount shape.
	 *
	 * @testWith ["pending"]
	 *           ["restricted"]
	 *
	 * @param string $status Approval state.
	 */
	public function test_an_account_without_prices_gets_no_inquiry_amount( string $status ): void {
		$result  = $this->list_priced_inquiry( $status );
		$inquiry = $result['inquiries'][0];

		$this->assertCount( 1, $result['inquiries'] );
		$this->assertSame( 59, $inquiry['id'] );
		$this->assert_no_amount( $inquiry, (string) json_encode( $result ) );
	}

	/**
	 * An approved account still reads the amount stored on a priced inquiry.
	 */
	public function test_an_approved_account_reads_the_stored_amount(): void {
		$result = $this->list_priced_inquiry( Approval::APPROVED );

		$this->assertSame( '1680.00', $result['inquiries'][0]['total'] );
		$this->assertStringContainsString( '1680.00', (string) json_encode( $result ) );
	}

	/**
	 * The same monetary-total rule as the account page: an approved account
	 * does not read a total for a contact message or an inquiry that still
	 * has a line without a price.
	 *
	 * @testWith ["contact", ""]
	 *           ["", "approval"]
	 *
	 * @param string $source Line source meta, "contact" for a contact message.
	 * @param string $reason Price-reason meta on the line; non-empty and a zero line total hides the amount.
	 */
	public function test_an_approved_account_reads_no_amount_when_the_inquiry_has_none( string $source, string $reason ): void {
		$result = $this->list_priced_inquiry( Approval::APPROVED, $source, $reason );

		$this->assert_no_amount( $result['inquiries'][0], (string) json_encode( $result ) );
	}

	/**
	 * No amount field and no amount-shaped value in the inquiry or its JSON.
	 *
	 * @param array<string, mixed> $inquiry One inquiry.
	 * @param string               $raw     Encoded payload.
	 */
	private function assert_no_amount( array $inquiry, string $raw ): void {
		$this->assertArrayNotHasKey( 'total', $inquiry );
		foreach ( $inquiry as $key => $value ) {
			if ( 'id' === $key ) {
				continue;
			}
			$this->assertIsString( $value, $key );
			$this->assertDoesNotMatchRegularExpression( self::MONEY, $value, $key );
		}
		$this->assertDoesNotMatchRegularExpression( self::MONEY, $raw );
	}

	/**
	 * One priced inquiry listed for the signed-in account.
	 *
	 * @param string $status Approval state.
	 * @param string $source Inquiry source meta.
	 * @param string $reason Line price-reason meta.
	 * @param string $total  Stored amount.
	 * @return array{inquiries: list<array<string, mixed>>}
	 */
	private function list_priced_inquiry( string $status, string $source = '', string $reason = '', string $total = '1680.00' ): array {
		WP_Mock::userFunction(
			'is_user_logged_in',
			array(
				'times'  => '0+',
				'return' => true,
			)
		);
		$this->approval_meta( array( Approval::STATUS_META => $status ) );
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'args'   => array(
					array(
						'customer_id' => 5,
						'limit'       => -1,
						'orderby'     => 'date',
						'order'       => 'DESC',
					),
				),
				'return' => array( $this->priced_inquiry( $total, $source, $reason ) ),
			)
		);

		return ( new InquiryStatus() )->execute( array() );
	}

	/**
	 * An inquiry whose stored amount is the leak the gate must withhold.
	 *
	 * @param string $total  Stored amount.
	 * @param string $source Inquiry source meta.
	 * @param string $reason Line price-reason meta.
	 */
	private function priced_inquiry( string $total, string $source, string $reason ): WC_Order {
		$line = Mockery::mock( WC_Order_Item_Product::class );
		$line->allows( 'get_meta' )->with( PriceDisplay::ITEM_REASON_META )->andReturn( $reason );
		$line->allows( 'get_total' )->andReturn( 'approval' === $reason ? '0' : $total );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 59 );
		$order->allows( 'get_order_number' )->andReturn( '59' );
		$order->allows( 'get_status' )->andReturn( Statuses::RECEIVED );
		$order->allows( 'get_date_created' )->andReturn( new \DateTimeImmutable( '2026-10-01T12:00:00+00:00' ) );
		$order->allows( 'get_total' )->andReturn( $total );
		$order->allows( 'get_item_count' )->andReturn( 1 );
		$order->allows( 'get_items' )->andReturn( array( $line ) );
		$order->allows( 'get_meta' )->andReturnUsing(
			static function ( string $key ) use ( $source ): string {
				if ( '_linker_inquiry_source' === $key ) {
					return $source;
				}
				return '';
			}
		);

		return $order;
	}
}
