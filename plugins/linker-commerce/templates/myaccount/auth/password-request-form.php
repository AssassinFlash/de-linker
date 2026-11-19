<?php
/**
 * WooCommerce's lost-password form, shared by both recovery entry points.
 *
 * @package Linker\Commerce
 * @var string $reset_url The Woo endpoint when embedded on the sign-in page.
 */

defined( 'ABSPATH' ) || exit;
?>
<form method="post" class="woocommerce-ResetPassword lost_reset_password"
	<?php if ( '' !== $reset_url ) : ?>
		action="<?php echo esc_url( $reset_url ); ?>"
	<?php endif; ?>
>
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
		<button type="submit" class="woocommerce-Button button<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?>"><span><?php esc_html_e( 'Send reset link', 'linker-commerce' ); ?></span></button>
	</p>
	<?php wp_nonce_field( 'lost_password', 'woocommerce-lost-password-nonce' ); ?>
</form>
