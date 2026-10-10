<?php
/**
 * Tests for linker/inquiry-status.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\InquiryStatus;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Issuer;
use Mockery;
use WC_Order;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for InquiryStatus.
 *
 * @covers \Linker\Commerce\Abilities\InquiryStatus
 */
final class InquiryStatusTest extends TestCase {

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( '_x' );
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
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
		$created = new \DateTimeImmutable( '2026-10-01T12:00:00+00:00' );
		$order   = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 59 );
		$order->allows( 'get_order_number' )->andReturn( '59' );
		$order->allows( 'get_status' )->andReturn( Statuses::PROFORMA );
		$order->allows( 'get_date_created' )->andReturn( $created );
		$order->allows( 'get_total' )->andReturn( '1200.00' );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( 'PI-2026-0007' );
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'args'   => array(
					array(
						'customer_id' => 7,
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
		$schema = ( new InquiryStatus() )->args()['output_schema'];
		$this->assertSame( array( 'inquiries' ), $schema['required'] );
	}
}
