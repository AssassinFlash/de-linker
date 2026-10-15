<?php
/**
 * Tests for the account menu.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\AuthTemplates;
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
		$items = ( new Menu() )->items(
			array(
				'dashboard'       => 'Dashboard',
				'orders'          => 'Orders',
				'downloads'       => 'Downloads',
				'edit-address'    => 'Address',
				'payment-methods' => 'Payment methods',
				'edit-account'    => 'Account details',
				'genie'           => 'Genie',
				// The register page is the guests' sign-up (owner ruling
				// 2026-10-16): a row offered for it never reaches the menu.
				'register'        => 'Create your business account',
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
		$this->assertArrayNotHasKey( AuthTemplates::REGISTER_ENDPOINT, $items, 'the register page is not a menu row' );
	}

	/**
	 * The two endpoints of this plugin join WooCommerce's. The register page
	 * registers its own query var (AuthTemplates), not this menu.
	 */
	public function test_query_vars(): void {
		$this->assertSame(
			array(
				'orders'          => 'inquiries',
				'saved-solutions' => 'saved-solutions',
				'documents'       => 'documents',
			),
			( new Menu() )->query_vars( array( 'orders' => 'inquiries' ) )
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
		$menu = new Menu();

		$this->assertSame( 'Inquiries', $menu->title( 'Orders', 'orders' ) );
		$this->assertSame( 'Inquiry #20', $menu->title( 'Order #20', 'view-order' ) );
		$this->assertSame( 'Saved solutions', $menu->title( '', 'saved-solutions' ) );
		$this->assertSame( 'Company', $menu->title( 'Addresses', 'edit-address' ) );
		$this->assertSame( 'Lost password', $menu->title( 'Lost password', 'lost-password' ) );
		unset( $GLOBALS['wp'] );
	}
}
