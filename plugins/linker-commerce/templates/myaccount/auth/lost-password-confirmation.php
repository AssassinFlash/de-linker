<?php
/**
 * The confirmation after a reset link was sent: the same card the request form
 * stands in (ticket #184, owner-accepted prototype), with the form gone and
 * Woo's own confirmation marked as done. Mirrors Woo 11.2's
 * myaccount/lost-password-confirmation.php (version 3.9.0): the same notice,
 * the same two hooks and the same filtered message — the message now sits in
 * the card's heading, above the notice, the way the prototype reads.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's lost-password-confirmation.php.
do_action( 'woocommerce_before_lost_password_confirmation_message' );
?>
<div class="linker-auth linker-auth--solo">
	<div class="linker-auth-inner linker-auth-inner--solo">
		<section class="linker-auth-card" aria-labelledby="linker-auth-sent">
			<header class="linker-auth-card-heading">
				<h1 id="linker-auth-sent"><?php esc_html_e( 'Reset your password', 'linker-commerce' ); ?></h1>
				<p><?php echo esc_html( apply_filters( 'woocommerce_lost_password_confirmation_message', esc_html__( 'A password reset email has been sent to the email address on file for your account, but may take several minutes to show up in your inbox. Please wait at least 10 minutes before attempting another reset.', 'woocommerce' ) ) ); // phpcs:ignore WordPress.WP.I18n.TextDomainMismatch,WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Woo's own filtered message, its text domain, its filter and its hook comment. ?></p>
			</header>

			<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native message. */ ?>
			<?php wc_print_notice( esc_html__( 'Password reset email has been sent.', 'woocommerce' ) ); ?>

			<p class="linker-auth-links"><a href="<?php echo esc_url( wc_get_page_permalink( 'myaccount' ) ); ?>"><?php esc_html_e( 'Back to sign in', 'linker-commerce' ); ?></a><?php echo \Linker\Commerce\Presentation\AccountLinks::create(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped data in the LC registration fragment. ?></p>
		</section>
	</div>
</div>
<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's lost-password-confirmation.php.
do_action( 'woocommerce_after_lost_password_confirmation_message' );
