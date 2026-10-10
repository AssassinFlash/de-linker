<?php
/**
 * Tests for the inquiry statuses.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for Statuses.
 *
 * @covers \Linker\Commerce\Inquiry\Statuses
 */
final class StatusesTest extends TestCase {

	/**
	 * Translations return their source string.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * The two inquiry statuses are post statuses with counts for the admin list.
	 */
	public function test_register(): void {
		WP_Mock::userFunction( '_n_noop', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'register_post_status',
			array(
				'times' => 1,
				'args'  => array( 'wc-inquiry-received', Mockery::on( static fn ( array $args ): bool => 'Inquiry received' === $args['label'] && $args['show_in_admin_status_list'] ) ),
			)
		);
		WP_Mock::userFunction(
			'register_post_status',
			array(
				'times' => 1,
				'args'  => array( 'wc-proforma-issued', Mockery::on( static fn ( array $args ): bool => 'Proforma invoice issued' === $args['label'] ) ),
			)
		);

		( new Statuses() )->register();

		$this->assertConditionsMet();
	}

	/**
	 * The four states of AGENTS.md §3 with their names, the inquiry statuses right after "pending".
	 */
	public function test_names(): void {
		$names = ( new Statuses() )->names(
			array(
				'wc-pending'    => 'Pending payment',
				'wc-processing' => 'Processing',
				'wc-completed'  => 'Completed',
				'wc-cancelled'  => 'Cancelled',
			)
		);

		$this->assertSame( array( 'wc-pending', 'wc-inquiry-received', 'wc-proforma-issued', 'wc-processing', 'wc-completed', 'wc-cancelled' ), array_keys( $names ) );
		$this->assertSame( 'Inquiry received', $names['wc-inquiry-received'] );
		$this->assertSame( 'Proforma invoice issued', $names['wc-proforma-issued'] );
		$this->assertSame( 'Not sent', $names['wc-pending'] );
		$this->assertSame( 'Completed', $names['wc-completed'] );
		$this->assertSame( 'Cancelled', $names['wc-cancelled'] );
	}

	/**
	 * Staff may change a received inquiry; one with a Proforma stays as issued.
	 */
	public function test_editable(): void {
		$received = Mockery::mock( WC_Order::class );
		$received->allows( 'get_status' )->andReturn( 'inquiry-received' );
		$issued = Mockery::mock( WC_Order::class );
		$issued->allows( 'get_status' )->andReturn( 'proforma-issued' );
		$statuses = new Statuses();

		$this->assertTrue( $statuses->editable( false, $received ) );
		$this->assertFalse( $statuses->editable( false, $issued ) );
		$this->assertTrue( $statuses->editable( true, $issued ) );
	}

	/**
	 * Every inquiry can be requested again; open inquiries are not revenue.
	 */
	public function test_request_again_and_analytics(): void {
		$statuses = new Statuses();

		$this->assertSame( array( 'completed', 'inquiry-received', 'proforma-issued', 'cancelled' ), $statuses->request_again( array( 'completed' ) ) );
		$this->assertSame( array( 'pending', 'failed', 'cancelled', 'inquiry-received', 'proforma-issued' ), $statuses->analytics_excluded( array( 'pending', 'failed', 'cancelled' ) ) );
	}

	/**
	 * The admin list colours are WooCommerce's on-hold and processing badge colours.
	 */
	public function test_admin_colours(): void {
		ob_start();
		( new Statuses() )->admin_colours();

		$this->assertSame( '<style id="linker-inquiry-statuses">.order-status.status-inquiry-received{background:#f8dda7;color:#573b00}.order-status.status-proforma-issued{background:#c6e1c6;color:#2c4700}</style>', ob_get_clean() );
	}
}
