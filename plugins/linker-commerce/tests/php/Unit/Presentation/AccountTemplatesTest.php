<?php
/**
 * Tests for Woo account data feeding LiveCanvas fragments.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\AccountTemplates;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The adapter stays behind Woo's account/login guards, and its filter preserves
 * Woo's customer/paging values. It must not disclose guest rows or accept PHP
 * hook names from a shortcode attribute.
 *
 * @covers \Linker\Commerce\Presentation\AccountTemplates
 */
final class AccountTemplatesTest extends TestCase {

	/** Logged-out requests retain Woo's forms and templates. */
	public function test_guest_keeps_native_template_and_cannot_read_rows(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		$adapter = new AccountTemplates();
		$this->assertSame( '/woo/orders.php', $adapter->template( '/woo/orders.php', 'myaccount/orders.php' ) );
		$this->assertSame( '', $adapter->rows( array( 'type' => 'groups' ) ) );
	}

	/** Forms, email templates and checkout never route to account LC fragments. */
	public function test_only_signed_in_account_content_is_adapted(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction(
			'shortcode_exists',
			array(
				'args'   => array( 'lc_if' ),
				'return' => true,
			)
		);
		$adapter = new AccountTemplates();
		foreach ( array( 'myaccount/orders.php', 'myaccount/view-order.php', 'myaccount/dashboard.php' ) as $name ) {
			$this->assertStringEndsWith( '/templates/myaccount/livecanvas.php', $adapter->template( '/woo/native.php', $name ) );
		}
		foreach ( array( 'myaccount/form-login.php', 'myaccount/form-edit-account.php', 'myaccount/form-edit-address.php', 'checkout/thankyou.php', 'emails/customer-completed-order.php' ) as $name ) {
			$this->assertSame( '/woo/native.php', $adapter->template( '/woo/native.php', $name ) );
		}
	}

	/** An absent LC keeps the mature native Woo fallback. */
	public function test_without_lc_native_template_stays(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'shortcode_exists', array( 'return' => false ) );
		$this->assertSame( '/woo/orders.php', ( new AccountTemplates() )->template( '/woo/orders.php', 'myaccount/orders.php' ) );
	}

	/** The tab only narrows statuses, without replacing Woo's ownership/paging. */
	public function test_open_tab_keeps_customer_and_pagination(): void {
		$adapter = new AccountTemplates();
		$query   = array(
			'customer_id' => 3,
			'page'        => 2,
			'limit'       => 10,
			'paginate'    => true,
		);
		unset( $_GET['inquiries'] );
		$this->assertSame( $query, $adapter->orders_query( $query ) );
		$_GET['inquiries'] = 'open';
		try {
			$this->assertSame( $query + array( 'status' => array( 'inquiry-received', 'proforma-issued' ) ), $adapter->orders_query( $query ) );
		} finally {
			unset( $_GET['inquiries'] );
		}
	}

	/** Shortcode attributes cannot choose an arbitrary PHP action. */
	public function test_arbitrary_hook_is_not_invoked(): void {
		$this->assertSame( '', ( new AccountTemplates() )->hook( array( 'name' => 'delete_user' ) ) );
	}
}
