<?php
/**
 * Account sign-in, registration, password recovery and account details.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

/**
 * Woo owns these forms — every field, nonce, hook and validation stays exactly
 * where Woo and the registration module put it. This class points the account
 * templates at this plugin's copies, whose markup arranges the same form into
 * the account's card, and the register form's own fields (printed by
 * Registration\Fields on woocommerce_register_form_start) into the two steps
 * the account sign-up reads: the company with its verification values, and the
 * person with the sign-in details (owner ruling 2026-10-17, ticket #225).
 * The reset form is included (ticket #184): the live chain landed on Woo's
 * bare markup, the one page of the chain without a card.
 *
 * Sign-in and sign-up are two pages (owner ruling 2026-10-16): the account page
 * carries the sign-in card, its register endpoint REGISTER_ENDPOINT carries the
 * sign-up card, each linking to the other. The endpoint is WooCommerce's own
 * mechanism — a query var like saved-solutions and documents, whose rewrite
 * WooOptions rebuilds once the set changes — so Woo still dispatches the page,
 * validates the nonce and processes both forms.
 */
final class AuthTemplates {

	/**
	 * The account page's register endpoint: the guests' sign-up page.
	 */
	public const REGISTER_ENDPOINT = 'register';

	/**
	 * Woo template to this plugin's copy. Recovery can be opened while signed
	 * in or out; sign-in and account details remain limited to their respective
	 * visitor states.
	 *
	 * @var array<string, string>
	 */
	private const FILES = array(
		'myaccount/form-login.php'                 => 'auth/form-login.php',
		'myaccount/form-lost-password.php'         => 'auth/form-lost-password.php',
		'myaccount/lost-password-confirmation.php' => 'auth/lost-password-confirmation.php',
		'myaccount/form-reset-password.php'        => 'auth/form-reset-password.php',
		'myaccount/form-edit-account.php'          => 'account/form-edit-account.php',
	);

	/**
	 * The plugin's copy of Woo's form-login.php for the register endpoint: Woo
	 * asks for the same template name for either guest page, so the request
	 * decides which of the two cards that template renders.
	 */
	private const REGISTER_FILE = 'auth/form-register.php';

	/**
	 * The sign-in template is only for guests. Recovery templates are available
	 * to either visitor state; WooCommerce continues to own their validation.
	 *
	 * @var list<string>
	 */
	private const GUEST_ONLY = array(
		'myaccount/form-login.php',
	);

	/**
	 * The account-details form is only for a signed-in account.
	 *
	 * @var list<string>
	 */
	private const SIGNED_IN_ONLY = array(
		'myaccount/form-edit-account.php',
	);

	/**
	 * Maps the account's own templates and registers the register page. Runs
	 * after AccountTemplates (20), which passes the account forms through, so
	 * the two adapters never compete for a request.
	 */
	public function register(): void {
		add_filter( 'woocommerce_get_query_vars', array( $this, 'query_vars' ) );
		add_filter( 'wc_get_template', array( $this, 'template' ), 30, 2 );
		add_action( 'template_redirect', array( $this, 'signed_out_notice' ) );
		add_action( 'template_redirect', array( $this, 'register_redirect' ) );
	}

	/**
	 * Adds the register page to WooCommerce's query vars: the same mechanism
	 * the saved-solutions and documents endpoints use, so WooCommerce's own
	 * rewrite rules, endpoint checks and endpoint URLs know the page. The
	 * rewrite cache is rebuilt when the set changes (Settings\WooOptions).
	 *
	 * @param array<string, string> $vars Query var → slug.
	 * @return array<string, string>
	 */
	public function query_vars( array $vars ): array {
		$vars[ self::REGISTER_ENDPOINT ] = self::REGISTER_ENDPOINT;
		return $vars;
	}

	/**
	 * The register page's address in the request's own language: WooCommerce's
	 * own endpoint URL of the account page, so the German request reads
	 * /de/mein-konto/register/ next to the English /my-account/register/ (the
	 * endpoint slugs are shared across the languages, as the site's other
	 * endpoints are). '' when WooCommerce is not there to answer it.
	 */
	public static function register_url(): string {
		if ( ! function_exists( 'wc_get_account_endpoint_url' ) ) {
			return '';
		}
		return (string) wc_get_account_endpoint_url( self::REGISTER_ENDPOINT );
	}

	/**
	 * Whether the request is the register page. WooCommerce's own endpoint
	 * check; the account page is required besides, because a query-var request
	 * (?register=1) is mapped on any page.
	 */
	public static function is_register_request(): bool {
		return function_exists( 'is_wc_endpoint_url' )
			&& is_wc_endpoint_url( self::REGISTER_ENDPOINT )
			&& function_exists( 'is_account_page' )
			&& is_account_page();
	}

	/**
	 * The register page is the guests' sign-up: a signed-in account is sent to
	 * the account workspace, which shows the current review status alongside
	 * its normal content.
	 */
	public function register_redirect(): void {
		if ( ! self::is_register_request() || ! is_user_logged_in() ) {
			return;
		}
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own account permalink.
		\wp_safe_redirect( \wc_get_page_permalink( 'myaccount' ) );
		exit;
	}

	/**
	 * The one-click sign-out lands back on the account page with `signed-out`
	 * and reads one notice there (ticket #184, owner ruling 2026-10-15). The
	 * notice is Woo's own, so it is printed and cleared the way every other
	 * account notice is.
	 */
	public function signed_out_notice(): void {
		if ( ! function_exists( 'is_account_page' ) || ! is_account_page() || is_user_logged_in() ) {
			return;
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only UI state, set by the sign-out redirect.
		if ( ! isset( $_GET['signed-out'] ) ) {
			return;
		}
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- WooCommerce's own notice API.
		wc_add_notice( __( 'You have been signed out.', 'linker-commerce' ), 'notice' );
	}

	/**
	 * The account page's own templates: sign-in for a guest, recovery for both
	 * visitor states and account details for a signed-in account. Every other
	 * template (checkout, emails, the endpoint content Woo routes elsewhere) keeps
	 * Woo's path. The register endpoint splits the guest page: Woo asks for
	 * form-login.php on either, and this plugin's copy of that name is the
	 * sign-in page or — on the endpoint — the sign-up page.
	 *
	 * @param string $path Located template.
	 * @param string $name Woo template name.
	 */
	public function template( string $path, string $name ): string {
		if ( ! isset( self::FILES[ $name ] ) || ! function_exists( 'is_account_page' ) || ! is_account_page() ) {
			return $path;
		}
		$signed_in = is_user_logged_in();
		if ( ( $signed_in && in_array( $name, self::GUEST_ONLY, true ) )
			|| ( ! $signed_in && in_array( $name, self::SIGNED_IN_ONLY, true ) ) ) {
			return $path;
		}
		$file = 'myaccount/form-login.php' === $name && self::is_register_request()
			? self::REGISTER_FILE
			: self::FILES[ $name ];
		return dirname( __DIR__, 2 ) . '/templates/myaccount/' . $file;
	}

	/**
	 * The register form's own fields in the two steps the account sign-up
	 * reads (owner ruling 2026-10-17, ticket #225): step 1's company fields,
	 * its verification pair (website or VAT ID), and step 2's names. Buffered
	 * from Woo's hook so the fields and their order stay Registration\Fields's
	 * own; an unknown layout keeps every field in the earlier block, so the
	 * fields can never be lost by a cosmetic split.
	 *
	 * @return array{company: string, verify: string, you: string}
	 */
	public static function register_field_blocks(): array {
		ob_start();
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Native hook documented in Woo's form-login.php.
		do_action( 'woocommerce_register_form_start' );
		return self::split_field_blocks( (string) ob_get_clean() );
	}

	/**
	 * Splits the buffered register fields before the first-name paragraph and
	 * the company block before the website paragraph. Anything unexpected
	 * keeps the remaining fields together.
	 *
	 * @param string $html Buffered woocommerce_register_form_start output.
	 * @return array{company: string, verify: string, you: string}
	 */
	public static function split_field_blocks( string $html ): array {
		list( $company_and_verify, $you ) = self::split_before( $html, 'id="billing_first_name_field"' );
		list( $company, $verify )         = self::split_before( $company_and_verify, 'id="linker_company_website_field"' );
		return array(
			'company' => $company,
			'verify'  => $verify,
			'you'     => $you,
		);
	}

	/**
	 * Everything before the paragraph that holds a field id, and the rest.
	 *
	 * @param string $html   Markup.
	 * @param string $marker The id attribute of the first field of the second block.
	 * @return array{0: string, 1: string}
	 */
	private static function split_before( string $html, string $marker ): array {
		$position = strpos( $html, $marker );
		if ( false === $position ) {
			return array( $html, '' );
		}
		$start = strrpos( substr( $html, 0, $position ), '<p' );
		if ( false === $start || 0 === $start ) {
			return array( $html, '' );
		}
		return array( substr( $html, 0, $start ), substr( $html, $start ) );
	}
}
