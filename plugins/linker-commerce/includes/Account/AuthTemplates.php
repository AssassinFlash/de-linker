<?php
/**
 * The guest pages of the account: sign-in, register and lost password.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

/**
 * Woo owns these forms — every field, nonce, hook and validation stays exactly
 * where Woo and the registration module put it. This class points the guest
 * templates at this plugin's copies, whose markup arranges the same form into
 * the account's card, and the register form's own fields (printed by
 * Registration\Fields on woocommerce_register_form_start) into the three steps
 * the account sign-up reads: company, contact and address, sign-in details.
 * The reset form is included (ticket #184): the live chain landed on Woo's
 * bare markup, the one page of the chain without a card.
 */
final class AuthTemplates {

	/**
	 * Woo template to this plugin's copy. The guest forms are the account's
	 * sign-in chain; the account-details form is WooCommerce's own signed-in
	 * form, which the redesign lays out as two panels (ticket #184).
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
	 * The templates only a guest may see; the others are the signed-in
	 * account's own forms.
	 *
	 * @var list<string>
	 */
	private const GUEST_ONLY = array(
		'myaccount/form-login.php',
		'myaccount/form-lost-password.php',
		'myaccount/lost-password-confirmation.php',
		'myaccount/form-reset-password.php',
	);

	/**
	 * Maps the account's own templates. Runs after AccountTemplates (20),
	 * which passes the account forms through, so the two adapters never
	 * compete for a request.
	 */
	public function register(): void {
		add_filter( 'wc_get_template', array( $this, 'template' ), 30, 2 );
		add_action( 'template_redirect', array( $this, 'signed_out_notice' ) );
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
	 * The account page's own templates: the guest ones for a guest, the
	 * account-details form for a signed-in account. Every other template
	 * (checkout, emails, the endpoint content Woo routes elsewhere) keeps
	 * Woo's path.
	 *
	 * @param string $path Located template.
	 * @param string $name Woo template name.
	 */
	public function template( string $path, string $name ): string {
		if ( ! isset( self::FILES[ $name ] ) || ! function_exists( 'is_account_page' ) || ! is_account_page() ) {
			return $path;
		}
		$guest_only = in_array( $name, self::GUEST_ONLY, true );
		if ( is_user_logged_in() === $guest_only ) {
			return $path;
		}
		return dirname( __DIR__, 2 ) . '/templates/myaccount/' . self::FILES[ $name ];
	}

	/**
	 * The register form's own fields in their two blocks: the company block
	 * (company, role, VAT ID) and the contact-and-address block, split where
	 * the first name field starts. Buffered from Woo's hook so the fields and
	 * their order stay Registration\Fields's own; an unknown layout returns
	 * one block, so the fields can never be lost by a cosmetic split.
	 *
	 * @return array{company: string, contact: string}
	 */
	public static function register_field_blocks(): array {
		ob_start();
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Native hook documented in Woo's form-login.php.
		do_action( 'woocommerce_register_form_start' );
		return self::split_field_blocks( (string) ob_get_clean() );
	}

	/**
	 * Splits the buffered register fields before the paragraph that holds the
	 * first-name field: everything before it is the company block, the rest is
	 * contact and address. Anything unexpected keeps all fields in one block.
	 *
	 * @param string $html Buffered woocommerce_register_form_start output.
	 * @return array{company: string, contact: string}
	 */
	public static function split_field_blocks( string $html ): array {
		$marker = strpos( $html, 'id="billing_first_name_field"' );
		if ( false === $marker ) {
			return array(
				'company' => '',
				'contact' => $html,
			);
		}
		$start = strrpos( substr( $html, 0, $marker ), '<p' );
		if ( false === $start || 0 === $start ) {
			return array(
				'company' => '',
				'contact' => $html,
			);
		}
		return array(
			'company' => substr( $html, 0, $start ),
			'contact' => substr( $html, $start ),
		);
	}
}
