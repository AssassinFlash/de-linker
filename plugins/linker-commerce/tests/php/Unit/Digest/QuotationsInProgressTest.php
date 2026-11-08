<?php
/**
 * Tests for the digest's quotation block.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\Format;
use Linker\Commerce\Digest\QuotationsInProgress;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for QuotationsInProgress: the window is "last touched more than
 * 3 days ago", the entries carry number, company, admin link and the moment.
 *
 * @covers \Linker\Commerce\Digest\QuotationsInProgress
 * @covers \Linker\Commerce\Digest\Format
 */
final class QuotationsInProgressTest extends TestCase {

	/**
	 * Unix time the digest runs at.
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
	 * The query reads the quotations in preparation; the window is applied on
	 * the record's last change.
	 */
	public function test_queries_quotations_and_applies_the_window(): void {
		$captured = null;
		WP_Mock::userFunction(
			'wc_get_orders',
			array(
				'times'  => 1,
				'return' => static function ( array $args ) use ( &$captured ): array {
					$captured = $args;
					return array( self::order( self::NOW - 3 * 86400 - 3600 ), self::order( self::NOW - 86400 ) );
				},
			)
		);

		$entries = ( new QuotationsInProgress( self::NOW ) )->entries();

		$this->assertCount( 1, $entries );
		$this->assertSame( 'Inquiry #20 – Solarbau GmbH', $entries[0]['label'] );
		$this->assertSame( array( Statuses::QUOTATION ), $captured['status'] ?? null );
		$this->assertSame( -1, $captured['limit'] );
		$this->assertSame( 3 * 86400, QuotationsInProgress::WINDOW );
	}

	/**
	 * A quotation comes back as number, company, admin link and the moment the
	 * record was last touched.
	 */
	public function test_entry_carries_number_company_link_and_moment(): void {
		WP_Mock::userFunction( 'wc_get_orders', array( 'return' => array( self::order( self::NOW - 4 * 86400 ) ) ) );

		$entries = ( new QuotationsInProgress( self::NOW ) )->entries();

		$this->assertCount( 1, $entries );
		$this->assertSame( 'Inquiry #20 – Solarbau GmbH', $entries[0]['label'] );
		$this->assertSame( '/wp-admin/admin.php?page=wc-orders&id=20&action=edit', $entries[0]['url'] );
		$this->assertSame( 'Open the inquiry', $entries[0]['link_text'] );
	}

	/**
	 * A mock quotation order.
	 *
	 * @param int $modified Unix time of the last change.
	 */
	private static function order( int $modified ): \WC_Order {
		$date = \Mockery::mock( 'WC_DateTime' );
		$date->shouldReceive( 'getTimestamp' )->andReturn( $modified );
		$order = \Mockery::mock( 'WC_Order' );
		$order->shouldReceive( 'get_date_modified' )->andReturn( $date );
		$order->shouldReceive( 'get_order_number' )->andReturn( '20' );
		$order->shouldReceive( 'get_billing_company' )->andReturn( 'Solarbau GmbH' );
		$order->shouldReceive( 'get_edit_order_url' )->andReturn( '/wp-admin/admin.php?page=wc-orders&id=20&action=edit' );
		return $order;
	}
}
