<?php
/**
 * Tests for the account menu.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\Menu;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for Menu.
 *
 * @covers \Linker\Commerce\Account\Menu
 */
final class MenuTest extends TestCase {

	/**
	 * Translations return their source string.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
	}

	/**
	 * The menu of docs/specs/11-commerce.md step 6; items of other plugins stay before "Log out"; downloads and payment methods are gone.
	 */
	public function test_items(): void {
		$items = ( new Menu( '/plugin/templates/' ) )->items(
			array(
				'dashboard'       => 'Dashboard',
				'orders'          => 'Orders',
				'downloads'       => 'Downloads',
				'edit-address'    => 'Address',
				'payment-methods' => 'Payment methods',
				'edit-account'    => 'Account details',
				'genie'           => 'Genie',
				'customer-logout' => 'Log out',
			)
		);

		$this->assertSame(
			array(
				'dashboard'       => 'Overview',
				'orders'          => 'Inquiries',
				'saved-solutions' => 'Saved solutions',
				'documents'       => 'Documents',
				'edit-address'    => 'Company',
				'edit-account'    => 'Account details',
				'genie'           => 'Genie',
				'customer-logout' => 'Log out',
			),
			$items
		);
	}

	/**
	 * The two endpoints of this plugin join WooCommerce's.
	 */
	public function test_query_vars(): void {
		$this->assertSame(
			array(
				'orders'          => 'inquiries',
				'saved-solutions' => 'saved-solutions',
				'documents'       => 'documents',
			),
			( new Menu( '/plugin/templates/' ) )->query_vars( array( 'orders' => 'inquiries' ) )
		);
	}

	/**
	 * Page titles of the endpoints, with the inquiry number on an inquiry.
	 */
	public function test_titles(): void {
		global $wp;
		$wp             = new \stdClass();
		$wp->query_vars = array( 'view-order' => '20' );
		WP_Mock::userFunction( 'absint', array( 'return' => static fn ( $value ): int => (int) $value ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		WP_Mock::userFunction( 'wc_get_order', array( 'return' => $order ) );
		$menu = new Menu( '/plugin/templates/' );

		$this->assertSame( 'Inquiries', $menu->title( 'Orders', 'orders' ) );
		$this->assertSame( 'Inquiry #20', $menu->title( 'Order #20', 'view-order' ) );
		$this->assertSame( 'Saved solutions', $menu->title( '', 'saved-solutions' ) );
		$this->assertSame( 'Company', $menu->title( 'Addresses', 'edit-address' ) );
		$this->assertSame( 'Lost password', $menu->title( 'Lost password', 'lost-password' ) );
		unset( $GLOBALS['wp'] );
	}

	/**
	 * The navigation is ours; every other template keeps the path WooCommerce located.
	 */
	public function test_navigation_template(): void {
		$menu = new Menu( '/plugin/templates/' );

		$this->assertSame(
			'/plugin/templates/myaccount/navigation.php',
			$menu->navigation_template( '/theme/woocommerce/myaccount/navigation.php', 'myaccount/navigation.php' )
		);
		$this->assertSame(
			'/theme/woocommerce/myaccount/orders.php',
			$menu->navigation_template( '/theme/woocommerce/myaccount/orders.php', 'myaccount/orders.php' )
		);
	}
}
