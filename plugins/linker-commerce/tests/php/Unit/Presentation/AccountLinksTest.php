<?php
/**
 * Public registration links beside guest sign-in entries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\AccountLinks;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Public guest account destinations.
 *
 * @covers \Linker\Commerce\Presentation\AccountLinks
 */
final class AccountLinksTest extends TestCase {

	/** A guest can go straight to the native register endpoint. */
	public function test_guest_gets_a_direct_create_account_link(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction(
			'wc_get_account_endpoint_url',
			array(
				'args'   => array( 'register' ),
				'return' => 'https://example.test/my-account/register/',
			)
		);

		$html = AccountLinks::create();

		$this->assertStringContainsString( 'href="https://example.test/my-account/register/"', $html );
		$this->assertStringContainsString( '>Create account</a>', $html );
		$this->assertStringNotContainsString( 'style=', $html );
	}

	/** Native URLs and translated labels are safe in the LC output context. */
	public function test_output_escapes_native_url_and_translated_label(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/my-account/register/?a=1&b=2' ) );
		WP_Mock::userFunction(
			'esc_url',
			array(
				'args'   => array( 'https://example.test/my-account/register/?a=1&b=2' ),
				'return' => 'https://example.test/my-account/register/?a=1&#038;b=2',
			)
		);
		WP_Mock::userFunction(
			'esc_html__',
			array(
				'args'   => array( 'Create account', 'linker-commerce' ),
				'return' => 'Create &lt;account&gt;',
			)
		);
		$html = AccountLinks::create();
		$this->assertStringContainsString( 'href="https://example.test/my-account/register/?a=1&#038;b=2"', $html );
		$this->assertStringContainsString( '>Create &lt;account&gt;</a>', $html );
		$this->assertStringNotContainsString( '<account>', $html );
	}

	/** Both guest entries use the request language's native addresses. */
	public function test_guest_entry_group_uses_german_account_addresses(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/de/mein-konto/register/' ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'args'   => array( 'myaccount' ),
				'return' => 'https://example.test/de/mein-konto/',
			)
		);

		$html = AccountLinks::guest_links();

		$this->assertStringContainsString( 'href="https://example.test/de/mein-konto/"', $html );
		$this->assertStringContainsString( 'href="https://example.test/de/mein-konto/register/"', $html );
	}

	/** The narrow price cell offers both actions without repeating its row label. */
	public function test_comparison_has_concise_links_and_retains_the_price_explanation(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/my-account/register/' ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wp_kses_post', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );

		$html = AccountLinks::comparison_price( 'Net price after partner sign-in' );

		$this->assertStringContainsString( '>Sign in</a>', $html );
		$this->assertStringContainsString( '>Create account</a>', $html );
		$this->assertStringContainsString( 'Net price after partner sign-in', $html );
	}

	/** Registration is not offered to signed-in visitors or when Woo disables it. */
	public function test_registration_respects_the_visitor_and_woo_setting(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'no' ) );
		$this->assertSame( '', AccountLinks::create() );
	}

	/** The signed-in menu never offers a second account. */
	public function test_signed_in_visitor_has_no_guest_entries(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$this->assertSame( '', AccountLinks::create() );
		$this->assertSame( '', AccountLinks::guest_links() );
	}

	/** The footer keeps both destinations in the existing account tile. */
	public function test_footer_exposes_two_independent_account_destinations(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/my-account/register/' ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );

		$html = AccountLinks::footer();

		$this->assertSame( 2, substr_count( $html, '<a ' ) );
		$this->assertStringContainsString( '>Sign in</a>', $html );
		$this->assertStringContainsString( '>Create account</a>', $html );
		$this->assertSame( '04', AccountLinks::footer_count() );
	}
}
