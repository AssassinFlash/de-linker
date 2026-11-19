<?php
/**
 * Lost password, as one centred card (ticket #184, owner-accepted prototype).
 *
 * Every field, nonce, filter and hook is Woo 11.2's own (mirrors
 * myaccount/form-lost-password.php, version 9.2.0). Woo's own labels keep
 * Woo's text domain, so Woo's translations keep applying. The confirmation of
 * a sent link is its own Woo template (lost-password-confirmation.php) and
 * lands in the same card.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

?>
<div class="linker-auth linker-auth--solo">
	<div class="linker-auth-inner linker-auth-inner--solo">
		<section class="linker-auth-card" aria-labelledby="linker-auth-reset">
			<header class="linker-auth-card-heading">
				<h1 id="linker-auth-reset"><?php esc_html_e( 'Reset your password', 'linker-commerce' ); ?></h1>
				<p><?php echo esc_html( apply_filters( 'woocommerce_lost_password_message', __( 'We’ll email you a link to set a new password.', 'linker-commerce' ) ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native filter documented in Woo's form-lost-password.php. ?></p>
			</header>

			<?php
			// The before hook may open a buffer to restore a retry's input; the
			// matching after hook closes it after the form has rendered.
			// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-lost-password.php.
			do_action( 'woocommerce_before_lost_password_form' );
			$reset_url = '';
			require __DIR__ . '/password-request-form.php';
			?>

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
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-lost-password.php.
do_action( 'woocommerce_after_lost_password_form' );
