<?php
/**
 * Tests for inquiries in the admin.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\OrderAdmin;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for OrderAdmin.
 *
 * @covers \Linker\Commerce\Inquiry\OrderAdmin
 */
final class OrderAdminTest extends TestCase {

	/**
	 * The order type reads "Inquiry" ("Inquiry #123 details"); other labels and arguments stay.
	 */
	public function test_labels(): void {
		WP_Mock::passthruFunction( '__' );

		$args = ( new OrderAdmin() )->labels(
			array(
				'labels' => array(
					'singular_name' => 'Order',
					'parent'        => 'Parent orders',
				),
				'public' => false,
			)
		);

		$this->assertSame( 'Inquiry', $args['labels']['singular_name'] );
		$this->assertSame( 'Inquiries', $args['labels']['name'] );
		$this->assertSame( 'Inquiries', $args['labels']['menu_name'] );
		$this->assertSame( 'Parent orders', $args['labels']['parent'] );
		$this->assertFalse( $args['public'] );
	}
}
