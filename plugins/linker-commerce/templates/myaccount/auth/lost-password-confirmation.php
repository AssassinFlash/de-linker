<?php
/**
 * The confirmation after a reset link was sent: the same card the request form
 * stands in (ticket #184, owner-accepted prototype), with the form gone and
 * Confirmation means the request was accepted. The outbox may still be
 * waiting for a delivery slot.
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
				<h1 id="linker-auth-sent"><?php esc_html_e( 'Check your email', 'linker-commerce' ); ?></h1>
				<p><?php echo esc_html( apply_filters( 'woocommerce_lost_password_confirmation_message', __( 'Open the link in the email to choose a new password.', 'linker-commerce' ) ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native filter documented in Woo's lost-password-confirmation.php. ?></p>
			</header>

			<?php wc_print_notice( esc_html__( 'Password reset requested.', 'linker-commerce' ) ); ?>

			<p class="linker-auth-links">
				<a href="<?php echo esc_url( wc_get_page_permalink( 'myaccount' ) ); ?>">
					<?php if ( is_user_logged_in() ) : ?>
						<?php esc_html_e( 'My account', 'linker-commerce' ); ?>
					<?php else : ?>
						<?php esc_html_e( 'Back to sign in', 'linker-commerce' ); ?>
					<?php endif; ?>
				</a>
				<?php echo \Linker\Commerce\Presentation\AccountLinks::create(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped data in the LC registration fragment. ?>
			</p>
		</section>
	</div>
</div>
<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's lost-password-confirmation.php.
do_action( 'woocommerce_after_lost_password_confirmation_message' );
