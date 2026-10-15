<?php
/**
 * Tests for the guest account templates.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\AuthTemplates;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Only the guest account page routes sign-in and lost-password to the
 * plugin's cards, and the account page's register endpoint routes the sign-up
 * to its own card; every other request keeps Woo's path. The register field
 * split never loses a field: an unknown layout falls back to one block.
 *
 * @covers \Linker\Commerce\Account\AuthTemplates
 */
final class AuthTemplatesTest extends TestCase {

	/**
	 * The query-var filter that adds the register page, the template filter
	 * (after AccountTemplates' 20) and the two redirect-time handlers.
	 */
	public function test_register_hooks_the_query_vars_the_template_filter_and_the_notices(): void {
		$auth = new AuthTemplates();
		WP_Mock::expectFilterAdded( 'woocommerce_get_query_vars', array( $auth, 'query_vars' ) );
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $auth, 'template' ), 30, 2 );
		WP_Mock::expectActionAdded( 'template_redirect', array( $auth, 'signed_out_notice' ) );
		WP_Mock::expectActionAdded( 'template_redirect', array( $auth, 'register_redirect' ) );
		$auth->register();
		$this->assertConditionsMet();
	}

	/**
	 * The register page is WooCommerce's own account endpoint: the query var
	 * registers it (the saved-solutions and documents mechanism), and its URL
	 * is WooCommerce's own — one slug in both languages, as the site's other
	 * endpoints are.
	 */
	public function test_the_register_endpoint_registers_its_query_var_and_url(): void {
		$auth = new AuthTemplates();
		$this->assertSame( array( 'register' => 'register' ), $auth->query_vars( array() ) );
		$this->assertSame(
			array(
				'documents' => 'documents',
				'register'  => 'register',
			),
			$auth->query_vars( array( 'documents' => 'documents' ) )
		);

		WP_Mock::userFunction(
			'wc_get_account_endpoint_url',
			array(
				'args'   => array( 'register' ),
				'return' => 'https://example.test/my-account/register/',
			)
		);
		$this->assertSame( 'https://example.test/my-account/register/', AuthTemplates::register_url() );
	}

	/**
	 * A guest on the account page gets the plugin's own cards: sign-in,
	 * the lost-password request, its confirmation and the new-password form
	 * the reset link lands on (ticket #184). The register endpoint asks for
	 * the same template name and gets the sign-up card instead.
	 */
	public function test_guest_account_page_uses_the_plugin_templates(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		$auth   = new AuthTemplates();
		$mapped = array(
			'myaccount/form-login.php'                 => '/templates/myaccount/auth/form-login.php',
			'myaccount/form-lost-password.php'         => '/templates/myaccount/auth/form-lost-password.php',
			'myaccount/lost-password-confirmation.php' => '/templates/myaccount/auth/lost-password-confirmation.php',
			'myaccount/form-reset-password.php'        => '/templates/myaccount/auth/form-reset-password.php',
		);
		foreach ( $mapped as $name => $path ) {
			$this->assertStringEndsWith( $path, $auth->template( '/woo/native.php', $name ) );
		}
	}

	/**
	 * The register endpoint splits the guest page (owner ruling 2026-10-16):
	 * WooCommerce asks for form-login.php on either page, and the endpoint
	 * request gets the sign-up card — the sign-in card stays on the account
	 * page — while every other guest template keeps its own.
	 */
	public function test_the_register_endpoint_gets_the_sign_up_card(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		$auth = new AuthTemplates();
		$this->assertStringEndsWith(
			'/templates/myaccount/auth/form-register.php',
			$auth->template( '/woo/native.php', 'myaccount/form-login.php' )
		);
		$this->assertStringEndsWith(
			'/templates/myaccount/auth/form-lost-password.php',
			$auth->template( '/woo/native.php', 'myaccount/form-lost-password.php' )
		);
	}

	/**
	 * The register page is the guests' sign-up: a signed-in account is sent to
	 * the account page, which shows its own state. WooCommerce answers the
	 * endpoint check only on the account page (a `?register=1` query var is
	 * mapped on any page), so the redirect waits for both.
	 */
	public function test_a_signed_in_account_is_sent_off_the_register_page(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'args'   => array( 'myaccount' ),
				'return' => 'https://example.test/my-account/',
			)
		);
		WP_Mock::userFunction(
			'wp_safe_redirect',
			array(
				'args'   => array( 'https://example.test/my-account/' ),
				'times'  => 1,
				'return' => static function (): void {
					throw new \RuntimeException( 'redirect' );
				},
			)
		);

		try {
			( new AuthTemplates() )->register_redirect();
			$this->fail( 'The redirect must exit, the same as the plugin\'s other redirects.' );
		} catch ( \RuntimeException $stopped ) {
			$this->assertSame( 'redirect', $stopped->getMessage(), 'exit stops the request after the redirect.' );
		}
		$this->assertConditionsMet();
	}

	/**
	 * A guest stays on the register page — that is the page's visitor.
	 */
	public function test_the_register_page_keeps_its_guest(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_safe_redirect', array( 'times' => 0 ) );
		( new AuthTemplates() )->register_redirect();
		$this->assertConditionsMet();
	}

	/**
	 * The endpoint check alone is not enough: WooCommerce maps a `?register=1`
	 * query var on any page, and that page is not the register page.
	 */
	public function test_the_query_var_outside_the_account_page_is_not_the_register_page(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		$this->assertFalse( AuthTemplates::is_register_request() );

		// And without the query var there is nothing to see, whichever page.
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		$this->assertFalse( AuthTemplates::is_register_request() );
		$this->assertConditionsMet();
	}

	/** The signed-in account-details form is the plugin's own two-panel layout. */
	public function test_signed_in_account_details_uses_the_plugin_template(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$auth = new AuthTemplates();
		$this->assertStringEndsWith(
			'/templates/myaccount/account/form-edit-account.php',
			$auth->template( '/woo/native.php', 'myaccount/form-edit-account.php' )
		);
		// The guest cards are not for a signed-in request.
		$this->assertSame( '/woo/native.php', $auth->template( '/woo/native.php', 'myaccount/form-login.php' ) );
	}

	/** Signed-in requests, other pages and other templates keep Woo's path. */
	public function test_nothing_else_is_remapped(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$auth = new AuthTemplates();
		$this->assertSame( '/woo/form-login.php', $auth->template( '/woo/form-login.php', 'myaccount/form-login.php' ) );
		$this->assertSame( '/woo/dashboard.php', $auth->template( '/woo/dashboard.php', 'myaccount/dashboard.php' ) );
	}

	/** A guest request outside the account page (checkout, emails) keeps Woo's path. */
	public function test_off_the_account_page_keeps_native(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$auth = new AuthTemplates();
		$this->assertSame( '/woo/form-login.php', $auth->template( '/woo/form-login.php', 'myaccount/form-login.php' ) );
	}

	/**
	 * The one-click sign-out lands with `signed-out`: the account page adds
	 * WooCommerce's own notice, once, and only for a guest.
	 */
	public function test_the_sign_out_notice_lands_on_the_guest_account_page(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );

		$_GET['signed-out'] = 'true';
		try {
			WP_Mock::userFunction(
				'wc_add_notice',
				array(
					'args'  => array( 'You have been signed out.', 'notice' ),
					'times' => 1,
				)
			);
			( new AuthTemplates() )->signed_out_notice();
		} finally {
			unset( $_GET['signed-out'] );
		}

		// Without the state, nothing is added.
		WP_Mock::userFunction( 'wc_add_notice', array( 'times' => 0 ) );
		( new AuthTemplates() )->signed_out_notice();
		$this->assertConditionsMet();
	}

	/**
	 * A signed-in request never reads the sign-out notice: the card it belongs
	 * to is not on that page.
	 */
	public function test_a_signed_in_request_gets_no_sign_out_notice(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$_GET['signed-out'] = 'true';
		try {
			WP_Mock::userFunction( 'wc_add_notice', array( 'times' => 0 ) );
			( new AuthTemplates() )->signed_out_notice();
		} finally {
			unset( $_GET['signed-out'] );
		}
		$this->assertConditionsMet();
	}

	/** The split puts the company fields before the first-name row and the rest after. */
	public function test_register_field_split_at_the_first_name_row(): void {
		$company = '<p class="form-row" id="billing_company_field">company</p>' . "\n"
			. '<p class="form-row" id="linker_customer_role_field">role</p>' . "\n"
			. '<p class="form-row" id="billing_vat_id_field">vat</p>' . "\n";
		$contact = '<p class="form-row" id="billing_first_name_field">first</p>' . "\n"
			. '<p class="form-row" id="billing_last_name_field">last</p>' . "\n"
			. '<p class="form-row" id="billing_city_field">city</p>';
		$blocks  = AuthTemplates::split_field_blocks( $company . $contact );
		$this->assertSame( $company, $blocks['company'] );
		$this->assertSame( $contact, $blocks['contact'] );
	}

	/** A layout without the first-name row keeps every field in one block. */
	public function test_register_field_split_never_loses_a_field(): void {
		$html   = '<div class="something-unexpected">fields</div>';
		$blocks = AuthTemplates::split_field_blocks( $html );
		$this->assertSame( '', $blocks['company'] );
		$this->assertSame( $html, $blocks['contact'] );

		$direct = '<p id="billing_first_name_field">first</p>';
		$this->assertSame(
			array(
				'company' => '',
				'contact' => $direct,
			),
			AuthTemplates::split_field_blocks( $direct )
		);
	}
}
