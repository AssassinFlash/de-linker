<?php
/**
 * Tests for the digest's inquiry block.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\Format;
use Linker\Commerce\Digest\InquiriesAwaitingProforma;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_DateTime;
use WC_Order;
use WP_Mock;

/**
 * Tests for InquiriesAwaitingProforma: the window is "created more than 24
 * hours ago", the entries carry number, company, admin link and the moment.
 *
 * @covers \Linker\Commerce\Digest\InquiriesAwaitingProforma
 * @covers \Linker\Commerce\Digest\Format
 */
final class InquiriesAwaitingProformaTest extends TestCase {

	/**
	 * Unix time the digest runs at: 2026-10-11 09:00 Berlin (CEST).
	 */
	private const NOW = 1_791_702_000;

	/**
	 * Translation returns its argument; the email renders in English.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::passthruFunction( '_n' );
		WP_Mock::userFunction(
			'wp_date',
			array(
				'return' => static fn ( string $format ): string => 'H:i' === $format ? '07:12' : 'October 10, 2026',
			)
		);
	}

	/**
	 * The query reads the received inquiries; the window is applied on the
	 * creation moment (WooCommerce's date filter only reaches calendar-day
	 * precision, the spec's window is strict to the second).
	 */
	public function test_queries_received_inquiries_and_applies_the_window(): void {
		$captured = null;
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'times'  => 1,
				'return' => static function ( array $args ) use ( &$captured ): array {
					$captured = $args;
					return array( self::order( self::NOW - 25 * 3600 ), self::order( self::NOW - 24 * 3600 ), self::order( self::NOW - 23 * 3600 ) );
				},
			)
		);

		$entries = ( new InquiriesAwaitingProforma( self::NOW ) )->entries();

		$this->assertCount( 1, $entries );
		$this->assertSame( 'Inquiry #20 – Solarbau GmbH', $entries[0]['label'] );
		$this->assertSame( array( Statuses::RECEIVED ), $captured['status'] ?? null );
		$this->assertSame( -1, $captured['limit'] );
		$this->assertSame( 24 * 3600, InquiriesAwaitingProforma::WINDOW );
	}

	/**
	 * An inquiry comes back as number, company, admin link and received moment.
	 */
	public function test_entry_carries_number_company_link_and_moment(): void {
		WP_Mock::userFunction( 'wc_get_orders', array( 'return' => array( $this->order( self::NOW - 26 * 3600 ) ) ) );

		$entries = ( new InquiriesAwaitingProforma( self::NOW ) )->entries();

		$this->assertCount( 1, $entries );
		$this->assertSame( 'Inquiry #20 – Solarbau GmbH', $entries[0]['label'] );
		$this->assertSame( '/wp-admin/admin.php?page=wc-orders&id=20&action=edit', $entries[0]['url'] );
		$this->assertSame( 'Open the inquiry', $entries[0]['link_text'] );
		$this->assertSame( 'Received on October 10, 2026 at 07:12 (26 hours ago)', $entries[0]['detail'] );
	}

	/**
	 * The empty sentence mirrors the window.
	 */
	public function test_empty_text(): void {
		$this->assertSame( 'No inquiry is waiting for more than 24 hours.', ( new InquiriesAwaitingProforma() )->empty_text() );
	}

	/**
	 * Hours below two days, whole days from then on (Format::age).
	 */
	public function test_ages_in_hours_then_days(): void {
		$this->assertSame( '1 hour ago', Format::age( self::NOW - 3600, self::NOW ) );
		$this->assertSame( '26 hours ago', Format::age( self::NOW - 26 * 3600, self::NOW ) );
		$this->assertSame( '47 hours ago', Format::age( self::NOW - 47 * 3600 - 3599, self::NOW ) );
		$this->assertSame( '2 days ago', Format::age( self::NOW - 48 * 3600, self::NOW ) );
		$this->assertSame( '3 days ago', Format::age( self::NOW - 3 * 24 * 3600 - 59, self::NOW ) );
		$this->assertSame( '1 hour ago', Format::age( self::NOW - 59, self::NOW ), 'Below one hour reads as one.' );
	}

	/**
	 * A received inquiry.
	 *
	 * @param int $created Unix time of creation.
	 */
	private static function order( int $created ): WC_Order {
		$moment = Mockery::mock( WC_DateTime::class );
		$moment->allows( 'getTimestamp' )->andReturn( $created );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_billing_company' )->andReturn( 'Solarbau GmbH' );
		$order->allows( 'get_edit_order_url' )->andReturn( '/wp-admin/admin.php?page=wc-orders&id=20&action=edit' );
		$order->allows( 'get_date_created' )->andReturn( $moment );
		return $order;
	}
}
