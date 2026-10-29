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
				<p><?php echo apply_filters( 'woocommerce_lost_password_message', esc_html__( 'Lost your password? Please enter your username or email address. You will receive a link to create a new password via email.', 'woocommerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped,WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment,WordPress.WP.I18n.TextDomainMismatch -- Woo's own filtered message, its text domain and its filter, escaped by its default. ?></p>
			</header>

			<?php
			// The before hook may open a buffer to restore a retry's input; the
			// matching after hook closes it after the form has rendered.
			// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-lost-password.php.
			do_action( 'woocommerce_before_lost_password_form' );
			?>
			<form method="post" class="woocommerce-ResetPassword lost_reset_password">

				<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<label for="user_login"><?php esc_html_e( 'Username or email', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
					<input class="woocommerce-Input woocommerce-Input--text input-text" type="text" name="user_login" id="user_login" autocomplete="username" required aria-required="true" />
				</p>

				<?php
				// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-lost-password.php.
				do_action( 'woocommerce_lostpassword_form' );
				?>

				<p class="woocommerce-form-row form-row linker-auth-submit">
					<input type="hidden" name="wc_reset_password" value="true" />
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<button type="submit" class="woocommerce-Button button<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?>" value="<?php esc_attr_e( 'Reset password', 'woocommerce' ); ?>"><span><?php esc_html_e( 'Reset password', 'woocommerce' ); ?></span></button>
				</p>

				<?php wp_nonce_field( 'lost_password', 'woocommerce-lost-password-nonce' ); ?>

			</form>

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
