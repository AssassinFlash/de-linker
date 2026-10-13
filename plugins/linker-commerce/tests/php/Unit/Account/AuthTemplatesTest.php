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
 * plugin's cards; every other request keeps Woo's path. The register field
 * split never loses a field: an unknown layout falls back to one block.
 *
 * @covers \Linker\Commerce\Account\AuthTemplates
 */
final class AuthTemplatesTest extends TestCase {

	/** The template filter is registered after AccountTemplates' (20). */
	public function test_register_hooks_the_template_filter(): void {
		$auth = new AuthTemplates();
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $auth, 'template' ), 30, 2 );
		$auth->register();
		$this->assertConditionsMet();
	}

	/** A guest on the account page gets the plugin's sign-in and lost-password cards. */
	public function test_guest_account_page_uses_the_plugin_templates(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$auth = new AuthTemplates();
		$this->assertStringEndsWith( '/templates/myaccount/auth/form-login.php', $auth->template( '/woo/form-login.php', 'myaccount/form-login.php' ) );
		$this->assertStringEndsWith( '/templates/myaccount/auth/form-lost-password.php', $auth->template( '/woo/form-lost-password.php', 'myaccount/form-lost-password.php' ) );
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
