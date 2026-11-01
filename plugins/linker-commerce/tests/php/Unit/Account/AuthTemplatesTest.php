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
 * The account page routes recovery to the same cards for either visitor state,
 * keeps sign-in for guests and account details for signed-in accounts, and
 * routes the register endpoint to its own card. The register field
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
		WP_Mock::expectFilterAdded( 'seopress_titles_title', array( $auth, 'document_title' ), 40 );
		WP_Mock::expectFilterAdded( 'pre_get_document_title', array( $auth, 'document_title' ), 40 );
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
		$this->assertSame( '/woo/native.php', $auth->template( '/woo/native.php', 'myaccount/form-edit-account.php' ) );
	}

	/** Signed-in recovery uses the same cards without changing the login guard. */
	public function test_signed_in_account_page_uses_all_recovery_templates(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$auth = new AuthTemplates();
		foreach ( array( 'form-lost-password.php', 'lost-password-confirmation.php', 'form-reset-password.php' ) as $file ) {
			$this->assertStringEndsWith( '/templates/myaccount/auth/' . $file, $auth->template( '/woo/native.php', 'myaccount/' . $file ) );
		}
		$this->assertSame( '/woo/native.php', $auth->template( '/woo/native.php', 'myaccount/form-login.php' ) );
	}

	/**
	 * Both recovery pages point back to the native account URL. Guests retain
	 * sign-in and registration links, while signed-in visitors get their account.
	 *
	 * @dataProvider recovery_link_cases
	 * @param string $file        Woo template filename.
	 * @param bool   $signed_in   Whether the visitor is signed in.
	 * @param string $account_url The request language's account URL.
	 */
	public function test_recovery_links_follow_the_visitor( string $file, bool $signed_in, string $account_url ): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $signed_in ) );
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'args'   => array( 'myaccount' ),
				'return' => $account_url,
			)
		);
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => $account_url . 'register/' ) );

		if ( 'form-lost-password.php' === $file ) {
			WP_Mock::expectAction( 'woocommerce_before_lost_password_form' );
			WP_Mock::expectAction( 'woocommerce_lostpassword_form' );
			WP_Mock::expectAction( 'woocommerce_after_lost_password_form' );
			$this->filter_returns( 'woocommerce_lost_password_message', 'Reset instructions' );
			WP_Mock::userFunction( 'wc_wp_theme_get_element_class_name', array( 'return' => '' ) );
			WP_Mock::userFunction( 'wp_nonce_field' );
		} else {
			WP_Mock::expectAction( 'woocommerce_before_lost_password_confirmation_message' );
			WP_Mock::expectAction( 'woocommerce_after_lost_password_confirmation_message' );
			$this->filter_returns( 'woocommerce_lost_password_confirmation_message', 'Confirmation' );
			WP_Mock::userFunction( 'wc_print_notice' );
		}

		$path = ( new AuthTemplates() )->template( '/woo/native.php', 'myaccount/' . $file );
		ob_start();
		require $path;
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'class="linker-auth-card"', $html );
		$this->assertStringContainsString( 'href="' . $account_url . '"', $html );
		$this->assertStringContainsString( $signed_in ? 'My account' : 'Back to sign in', $html );
		$this->assertStringNotContainsString( $signed_in ? 'Back to sign in' : 'My account', $html );
		if ( $signed_in ) {
			$this->assertStringNotContainsString( 'linker-create-account', $html );
		} else {
			$this->assertStringContainsString( 'href="' . $account_url . 'register/"', $html );
		}
		$this->assertConditionsMet();
	}

	/**
	 * Recovery request and confirmation in both visitor states and languages.
	 *
	 * @return list<array{string, bool, string}>
	 */
	public static function recovery_link_cases(): array {
		$cases = array();
		foreach ( array( 'form-lost-password.php', 'lost-password-confirmation.php' ) as $file ) {
			foreach ( array( false, true ) as $signed_in ) {
				foreach ( array( 'https://example.test/my-account/', 'https://example.test/de/mein-konto/' ) as $account_url ) {
					$cases[] = array( $file, $signed_in, $account_url );
				}
			}
		}
		return $cases;
	}

	/**
	 * A retry hook can buffer the form without pulling notices out of the card.
	 *
	 * @throws \LogicException If WP_Mock does not return an action responder.
	 */
	public function test_recovery_retry_keeps_notice_and_input_inside_the_card(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		WP_Mock::userFunction( 'wc_wp_theme_get_element_class_name', array( 'return' => '' ) );
		WP_Mock::userFunction( 'wp_nonce_field' );
		$this->filter_returns( 'woocommerce_lost_password_message', 'Reset instructions' );
		WP_Mock::expectAction( 'woocommerce_lostpassword_form' );
		$before = WP_Mock::onAction( 'woocommerce_before_lost_password_form' )->with( null );
		$after  = WP_Mock::onAction( 'woocommerce_after_lost_password_form' )->with( null );
		if ( ! $before instanceof \WP_Mock\Action_Responder || ! $after instanceof \WP_Mock\Action_Responder ) {
			throw new \LogicException( 'The native form hooks must use action responders.' );
		}
		$before->perform(
			static function (): void {
				echo '<div class="woocommerce-error">Try again</div>';
				ob_start(); // Mirrors the retained-input hook's own form buffer.
			}
		);
		$after->perform(
			static function (): void {
				$html = (string) ob_get_clean();
				echo str_replace( 'id="user_login"', 'id="user_login" value="installer@example.test"', $html ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Synthetic hook fixture.
			}
		);

		$path  = ( new AuthTemplates() )->template( '/woo/native.php', 'myaccount/form-lost-password.php' );
		$level = ob_get_level();
		ob_start();
		require $path;
		$html = (string) ob_get_clean();

		$this->assertSame( $level, ob_get_level(), 'Every hook buffer closes at the matching after hook.' );
		$this->assertMatchesRegularExpression( '/<section class="linker-auth-card"[^>]*>.*class="woocommerce-error".*id="user_login" value="installer@example\.test"/s', $html );
		$this->assertConditionsMet();
	}

	/**
	 * The shared reset card receives Woo's arguments in either visitor state.
	 *
	 * @dataProvider visitor_states
	 * @param bool $signed_in Whether the visitor is signed in.
	 */
	public function test_reset_card_keeps_the_native_form_arguments( bool $signed_in ): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $signed_in ) );
		WP_Mock::userFunction( 'wc_wp_theme_get_element_class_name', array( 'return' => '' ) );
		WP_Mock::userFunction(
			'wp_nonce_field',
			array(
				'args'  => array( 'reset_password', 'woocommerce-reset-password-nonce' ),
				'times' => 1,
			)
		);
		WP_Mock::expectAction( 'woocommerce_before_reset_password_form' );
		WP_Mock::expectAction( 'woocommerce_resetpassword_form' );
		WP_Mock::expectAction( 'woocommerce_after_reset_password_form' );
		$this->filter_returns( 'woocommerce_reset_password_message', 'Reset instructions' );
		$args = array(
			'key'   => 'synthetic-key',
			'login' => 'synthetic-login',
		);
		$path = ( new AuthTemplates() )->template( '/woo/native.php', 'myaccount/form-reset-password.php' );
		ob_start();
		require $path;
		$html = (string) ob_get_clean();

		$this->assertStringContainsString( 'class="linker-auth-card"', $html );
		$this->assertStringContainsString( 'name="password_1"', $html );
		$this->assertStringContainsString( 'name="password_2"', $html );
		$this->assertStringContainsString( 'name="reset_key" value="synthetic-key"', $html );
		$this->assertStringContainsString( 'name="reset_login" value="synthetic-login"', $html );
		$this->assertConditionsMet();
	}

	/**
	 * Guest and signed-in requests.
	 *
	 * @return list<array{bool}>
	 */
	public static function visitor_states(): array {
		return array( array( false ), array( true ) );
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
		foreach ( array( 'form-login.php', 'form-lost-password.php', 'lost-password-confirmation.php', 'form-reset-password.php', 'form-edit-account.php' ) as $file ) {
			$this->assertSame( '/woo/native.php', $auth->template( '/woo/native.php', 'myaccount/' . $file ) );
		}
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

	/** The split puts the company fields before the website row, the verification pair next, and the name after. */
	public function test_register_field_split_at_the_website_and_first_name_rows(): void {
		$company = '<p class="form-row" id="billing_company_field">company</p>' . "\n"
			. '<p class="form-row" id="linker_customer_role_field">role</p>' . "\n"
			. '<p class="form-row" id="billing_country_field">country</p>' . "\n";
		$verify  = '<p class="form-row" id="linker_company_website_field">website</p>' . "\n"
			. '<p class="form-row" id="billing_vat_id_field">vat</p>' . "\n";
		$you     = '<p class="form-row" id="billing_first_name_field">first</p>' . "\n"
			. '<p class="form-row" id="billing_last_name_field">last</p>';
		$blocks  = AuthTemplates::split_field_blocks( $company . $verify . $you );
		$this->assertSame( $company, $blocks['company'] );
		$this->assertSame( $verify, $blocks['verify'] );
		$this->assertSame( $you, $blocks['you'] );
	}

	/** A layout without one of the markers keeps every field in the earlier block. */
	public function test_register_field_split_never_loses_a_field(): void {
		$html   = '<div class="something-unexpected">fields</div>';
		$blocks = AuthTemplates::split_field_blocks( $html );
		$this->assertSame( $html, $blocks['company'] );
		$this->assertSame( '', $blocks['verify'] );
		$this->assertSame( '', $blocks['you'] );

		// Without the first-name row the company part still splits at the website.
		$no_name = '<p id="billing_company_field">company</p><p id="linker_company_website_field">website</p>';
		$this->assertSame(
			array(
				'company' => '<p id="billing_company_field">company</p>',
				'verify'  => '<p id="linker_company_website_field">website</p>',
				'you'     => '',
			),
			AuthTemplates::split_field_blocks( $no_name )
		);
	}
	/** Native registration and recovery headings replace the parent SEO title. */
	public function test_english_authentication_endpoints_use_their_existing_headings(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_404', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'get_bloginfo',
			array(
				'args'   => array( 'name' ),
				'return' => 'Linker',
			)
		);
		$auth              = new AuthTemplates();
		$selected_endpoint = '';
		WP_Mock::userFunction(
			'is_wc_endpoint_url',
			array(
				'return' => static function ( string $key ) use ( &$selected_endpoint ): bool {
					return $key === $selected_endpoint;
				},
			)
		);
		foreach ( array(
			'register'      => 'Create your business account',
			'lost-password' => 'Reset your password',
		) as $endpoint => $heading ) {
			$selected_endpoint = $endpoint;
			$this->assertSame( $heading . ' | Linker', $auth->document_title( 'Partner Account: Sign In or Register | Linker' ) );
			$this->assertSame( $heading . ' | Linker', $auth->document_title( '' ), 'WordPress and SEOPress receive the same native title even when the original title is empty.' );
		}
	}

	/** Login marketing copy and unrelated account endpoints keep their own titles. */
	public function test_other_english_account_titles_remain_unchanged(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_404', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		$existing = 'Partner Account: Sign In or Register | Linker';
		$this->assertSame( $existing, ( new AuthTemplates() )->document_title( $existing ) );
	}

	/** German and any other page language preserve their independent title owner. */
	public function test_non_english_titles_are_not_rewritten(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_404', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		$current_language = '';
		WP_Mock::userFunction(
			'pll_current_language',
			array(
				'return' => static function () use ( &$current_language ): string {
					return $current_language;
				},
			)
		);
		foreach ( array(
			'de' => 'Passwort zurücksetzen | Linker',
			'fr' => 'Titre indépendant',
			''   => 'Unresolved language',
		) as $language => $existing ) {
			$current_language = $language;
			$this->assertSame( $existing, ( new AuthTemplates() )->document_title( $existing ) );
		}
	}

	/** Account query vars cannot rewrite unrelated or not-found page metadata. */
	public function test_authentication_titles_require_the_real_account_page(): void {
		WP_Mock::userFunction( 'is_account_page', array( 'return' => false ) );
		$this->assertSame( 'Other page | Linker', ( new AuthTemplates() )->document_title( 'Other page | Linker' ) );
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_404', array( 'return' => true ) );
		$this->assertSame( 'Not found | Linker', ( new AuthTemplates() )->document_title( 'Not found | Linker' ) );
	}
	/**
	 * Portal titles reuse Woo's menu-aware endpoint headings after sign-in.
	 *
	 * @testWith ["", "Overview"]
	 *           ["orders", "Inquiries"]
	 *           ["saved-solutions", "Saved solutions"]
	 *           ["documents", "Documents"]
	 *           ["edit-address", "Company"]
	 *           ["edit-account", "Account details"]
	 * @param string $endpoint Native Woo endpoint key.
	 * @param string $heading Existing native page heading.
	 */
	public function test_signed_in_portal_titles_use_existing_native_headings( string $endpoint, string $heading ): void {
		$this->english_portal_request();
		$query = \Mockery::mock( \WC_Query::class );
		$query->shouldReceive( 'get_current_endpoint' )->once()->andReturn( $endpoint );
		if ( '' === $endpoint ) {
			$query->shouldNotReceive( 'get_endpoint_title' );
		} else {
			$query->shouldReceive( 'get_endpoint_title' )->with( $endpoint )->once()->andReturn( $heading );
		}
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'query' => $query ) ) );
		$this->assertSame( $heading . ' | Linker', ( new AuthTemplates() )->document_title( 'Partner Account: Sign In or Register | Linker' ) );
	}

	/**
	 * Unknown and other-owner details never resolve a private inquiry number.
	 *
	 * @testWith [0]
	 *           [42]
	 * @param int $id Synthetic detail endpoint value, never a real order lookup.
	 */
	public function test_unavailable_inquiry_titles_do_not_read_private_numbers( int $id ): void {
		$this->english_portal_request();
		$query = \Mockery::mock( \WC_Query::class );
		$query->shouldReceive( 'get_current_endpoint' )->once()->andReturn( 'view-order' );
		$query->shouldNotReceive( 'get_endpoint_title' );
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'query' => $query ) ) );
		WP_Mock::userFunction(
			'get_query_var',
			array(
				'args'   => array( 'view-order' ),
				'return' => $id,
			)
		);
		WP_Mock::userFunction(
			'absint',
			array(
				'args'   => array( $id ),
				'return' => $id,
			)
		);
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'view_order', $id ),
				'return' => false,
			)
		);
		WP_Mock::userFunction( 'wc_get_order', array( 'times' => 0 ) );
		$this->assertSame( 'Inquiry | Linker', ( new AuthTemplates() )->document_title( 'Parent account title | Linker' ) );
	}

	/** Only native Woo permission permits the endpoint's private display number. */
	public function test_owned_inquiry_title_requires_native_view_order_permission(): void {
		$this->english_portal_request();
		$query = \Mockery::mock( \WC_Query::class );
		$query->shouldReceive( 'get_current_endpoint' )->once()->andReturn( 'view-order' );
		$query->shouldReceive( 'get_endpoint_title' )->with( 'view-order' )->once()->andReturn( 'Inquiry #SYNTHETIC-42' );
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'query' => $query ) ) );
		WP_Mock::userFunction(
			'get_query_var',
			array(
				'args'   => array( 'view-order' ),
				'return' => 42,
			)
		);
		WP_Mock::userFunction(
			'absint',
			array(
				'args'   => array( 42 ),
				'return' => 42,
			)
		);
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'view_order', 42 ),
				'return' => true,
			)
		);
		$this->assertSame( 'Inquiry #SYNTHETIC-42 | Linker', ( new AuthTemplates() )->document_title( 'Parent account title | Linker' ) );
	}

	/** Unregistered extension endpoints retain their existing title owner. */
	public function test_unknown_account_endpoints_keep_existing_metadata(): void {
		$this->english_portal_request();
		$query = \Mockery::mock( \WC_Query::class );
		$query->shouldReceive( 'get_current_endpoint' )->once()->andReturn( 'other-extension' );
		$query->shouldNotReceive( 'get_endpoint_title' );
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'query' => $query ) ) );
		$this->assertSame( 'Extension title | Linker', ( new AuthTemplates() )->document_title( 'Extension title | Linker' ) );
	}

	/** A synthetic authenticated request on the actual English account page. */
	private function english_portal_request(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'is_account_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_404', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_bloginfo',
			array(
				'args'   => array( 'name' ),
				'return' => 'Linker',
			)
		);
	}
}
