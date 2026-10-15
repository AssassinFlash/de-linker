<?php
/**
 * The new-password form the reset link lands on: one card, the two password
 * fields with Woo's own eye toggles, the strength meter (ticket #184,
 * owner-accepted prototype reset.html). Mirrors Woo 11.2's
 * myaccount/form-reset-password.php (version 9.2.0) — the same field names,
 * hidden key/login, nonce, filters and hooks; Woo's labels keep Woo's text
 * domain. This is the page the live chain used to land on as bare Woo markup.
 *
 * @package Linker\Commerce
 *
 * @var string        $key  Reset key (extracted from the template arguments).
 * @var string        $login Reset login (extracted from the template arguments).
 * @var array<string, string> $args Template arguments, when passed as one array.
 */

defined( 'ABSPATH' ) || exit;

$reset_key   = (string) ( $key ?? ( $args['key'] ?? '' ) );
$reset_login = (string) ( $login ?? ( $args['login'] ?? '' ) );

ob_start();
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-reset-password.php.
do_action( 'woocommerce_before_reset_password_form' );
$auth_notices = (string) ob_get_clean();
?>
<div class="linker-auth linker-auth--solo">
	<div class="linker-auth-inner linker-auth-inner--solo">
		<section class="linker-auth-card" aria-labelledby="linker-auth-new-password">
			<header class="linker-auth-card-heading">
				<h1 id="linker-auth-new-password"><?php esc_html_e( 'Choose a new password', 'linker-commerce' ); ?></h1>
				<p><?php echo apply_filters( 'woocommerce_reset_password_message', esc_html__( 'Enter a new password below.', 'woocommerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped,WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment,WordPress.WP.I18n.TextDomainMismatch -- Woo's own filtered message, its text domain and its filter, escaped by its default. ?></p>
			</header>

			<?php echo $auth_notices; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's own notice markup, kept intact and local to the form. ?>
			<form method="post" class="woocommerce-ResetPassword lost_reset_password">

				<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
					<label for="password_1"><?php esc_html_e( 'New password', 'linker-commerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
					<input type="password" class="woocommerce-Input woocommerce-Input--text input-text" name="password_1" id="password_1" autocomplete="new-password" required aria-required="true" />
					<span class="linker-auth-hint"><?php esc_html_e( 'Use at least 8 characters with a mix of letters, numbers and symbols.', 'linker-commerce' ); ?></span>
				</p>
				<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
					<label for="password_2"><?php esc_html_e( 'Re-enter new password', 'linker-commerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
					<input type="password" class="woocommerce-Input woocommerce-Input--text input-text" name="password_2" id="password_2" autocomplete="new-password" required aria-required="true" aria-describedby="linker-reset-mismatch" />
					<span class="linker-auth-error" id="linker-reset-mismatch" data-password-mismatch role="alert" hidden><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg><span><?php esc_html_e( 'The passwords do not match.', 'linker-commerce' ); ?></span></span>
				</p>

				<input type="hidden" name="reset_key" value="<?php echo esc_attr( $reset_key ); ?>" />
				<input type="hidden" name="reset_login" value="<?php echo esc_attr( $reset_login ); ?>" />

				<?php
				// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-reset-password.php.
				do_action( 'woocommerce_resetpassword_form' );
				?>

				<p class="woocommerce-form-row form-row linker-auth-submit">
					<input type="hidden" name="wc_reset_password" value="true" />
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<button type="submit" class="woocommerce-Button button<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?>" value="<?php esc_attr_e( 'Save', 'woocommerce' ); ?>"><span><?php esc_html_e( 'Save', 'woocommerce' ); ?></span></button>
				</p>

				<?php wp_nonce_field( 'reset_password', 'woocommerce-reset-password-nonce' ); ?>

			</form>
		</section>
	</div>
</div>
<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-reset-password.php.
do_action( 'woocommerce_after_reset_password_form' );
