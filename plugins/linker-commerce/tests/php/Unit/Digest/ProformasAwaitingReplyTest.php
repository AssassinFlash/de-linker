<?php
/**
 * Tests for the digest's proforma block.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\ProformasAwaitingReply;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for ProformasAwaitingReply: the window starts at the Issuer's meta,
 * runs 3 × 24 hours, and is strict.
 *
 * @covers \Linker\Commerce\Digest\ProformasAwaitingReply
 */
final class ProformasAwaitingReplyTest extends TestCase {

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
				'return' => static fn ( string $format ): string => 'H:i' === $format ? '09:30' : 'October 6, 2026',
			)
		);
	}

	/**
	 * The query reads the issued status; the window filters on the issue meta.
	 */
	public function test_window_is_three_days_from_the_issue_meta(): void {
		$captured = null;
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'times'  => 1,
				'return' => static function ( array $args ) use ( &$captured ): array {
					$captured = $args;
					return array();
				},
			)
		);

		$this->assertSame( array(), ( new ProformasAwaitingReply( self::NOW ) )->entries() );
		$this->assertSame( array( Statuses::PROFORMA ), $captured['status'] ?? null );
		$this->assertSame( 3 * 24 * 3600, ProformasAwaitingReply::WINDOW );
	}

	/**
	 * In, out and the boundaries: 73 hours in, 71 and exactly 72 out, a
	 * proforma-issued inquiry without the issue meta out.
	 */
	public function test_boundaries_are_strict(): void {
		$in       = $this->order( self::NOW - 73 * 3600, 'PI-2026-0001' );
		$out      = $this->order( self::NOW - 71 * 3600, 'PI-2026-0002' );
		$boundary = $this->order( self::NOW - ProformasAwaitingReply::WINDOW, 'PI-2026-0003' );
		$no_meta  = $this->order( 0, '' );
		WP_Mock::userFunction( 'wc_get_orders', array( 'return' => array( $in, $out, $boundary, $no_meta ) ) );

		$entries = ( new ProformasAwaitingReply( self::NOW ) )->entries();

		$this->assertCount( 1, $entries );
		$this->assertSame( 'Inquiry #20 – Solarbau GmbH', $entries[0]['label'] );
		$this->assertSame( 'Proforma invoice PI-2026-0001 issued on October 6, 2026 at 09:30 (3 days ago)', $entries[0]['detail'] );
		$this->assertSame( '/wp-admin/admin.php?page=wc-orders&id=20&action=edit', $entries[0]['url'] );
	}

	/**
	 * The empty sentence mirrors the window.
	 */
	public function test_empty_text(): void {
		$this->assertSame( 'No Proforma invoice has waited more than 3 days for a reply.', ( new ProformasAwaitingReply() )->empty_text() );
	}

	/**
	 * An issued inquiry.
	 *
	 * @param int    $issued Unix time of issue, 0 for none.
	 * @param string $number Proforma number.
	 */
	private function order( int $issued, string $number ): WC_Order {
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_billing_company' )->andReturn( 'Solarbau GmbH' );
		$order->allows( 'get_edit_order_url' )->andReturn( '/wp-admin/admin.php?page=wc-orders&id=20&action=edit' );
		$order->allows( 'get_meta' )->andReturnUsing(
			static function ( string $key ) use ( $issued, $number ): string {
				return Issuer::ISSUED_META === $key ? (string) $issued : $number;
			}
		);
		return $order;
	}
}
