<?php
/**
 * Guest sign-in: the design of the account redesign (ticket #184,
 * owner-accepted prototype docs/design/2026-10-15-account-redesign), one page
 * per card since the owner's 2026-10-16 ruling — this page carries the sign-in
 * card, its register endpoint carries the sign-up card
 * (templates/myaccount/auth/form-register.php), and each links to the other.
 *
 * Every field, nonce and hook is Woo 11.2's own (mirrors
 * myaccount/form-login.php, version 9.9.0); signing in is this template's own
 * form, so an error stays on this page. On the desktop the card carries its own
 * brand panel — the sign-in words (ticket #184, the owner-accepted prototype's
 * login page). Below 1080px the panel is hidden and the card stands alone.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

use Linker\Commerce\Account\AuthTemplates;

ob_start();
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
do_action( 'woocommerce_before_customer_login_form' );
$auth_notices    = (string) ob_get_clean();
$registration    = 'yes' === get_option( 'woocommerce_enable_myaccount_registration' );
$register_url    = AuthTemplates::register_url();
$brand_logo      = plugins_url( 'assets/linker-logo-wordmark.webp', dirname( __DIR__, 3 ) . '/linker-commerce.php' );
$brand_check     = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';
$brand_documents = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>';
$brand_workspace = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>';

// The card's brand panel: its own title, its own subtitle and its three points.
$brand_panel = static function ( string $title, string $subtitle, array $points ) use ( $brand_logo, $brand_check, $brand_documents, $brand_workspace ): void {
	?>
	<aside class="linker-auth-brand" aria-hidden="true">
		<img class="linker-auth-brand-logo" src="<?php echo esc_url( $brand_logo ); ?>" alt="" width="124" height="47" decoding="async">
		<div>
			<p class="linker-auth-brand-title"><?php echo esc_html( $title ); ?></p>
			<p class="linker-auth-brand-sub"><?php echo esc_html( $subtitle ); ?></p>
		</div>
		<ul class="linker-auth-brand-points">
			<li><?php echo $brand_check; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php echo esc_html( (string) $points[0] ); ?></span></li>
			<li><?php echo $brand_documents; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php echo esc_html( (string) $points[1] ); ?></span></li>
			<li><?php echo $brand_workspace; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php echo esc_html( (string) $points[2] ); ?></span></li>
		</ul>
	</aside>
	<?php
};
?>
<div class="linker-auth" id="customer_login">
	<div class="linker-auth-inner">

		<div class="linker-auth-unit">
			<?php
			$brand_panel(
				__( 'Your partner account', 'linker-commerce' ),
				__( 'The workspace for installers, EPCs and distributors.', 'linker-commerce' ),
				array(
					__( 'Net prices and Proforma requests once approved', 'linker-commerce' ),
					__( 'Every inquiry and document in one place', 'linker-commerce' ),
					__( 'We answer inquiries within one working day', 'linker-commerce' ),
				)
			);
			?>

			<section class="linker-auth-card" id="linker-signin" aria-labelledby="linker-auth-signin">
				<header class="linker-auth-card-heading">
					<h1 id="linker-auth-signin"><?php esc_html_e( 'Sign in', 'linker-commerce' ); ?></h1>
					<p><?php esc_html_e( 'Your inquiries, documents and prices in one place.', 'linker-commerce' ); ?></p>
				</header>

				<?php
				// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's notice markup, kept intact beside the form it belongs to.
				echo $auth_notices;
				?>
				<form class="woocommerce-form woocommerce-form-login login" method="post" novalidate>

					<?php
					// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
					do_action( 'woocommerce_login_form_start' );
					?>

					<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
						<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
						<label for="username"><?php esc_html_e( 'Username or email address', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
						<input type="text" class="woocommerce-Input woocommerce-Input--text input-text" name="username" id="username" autocomplete="username" value="<?php echo ( ! empty( $_POST['username'] ) && is_string( $_POST['username'] ) ) ? esc_attr( wp_unslash( $_POST['username'] ) ) : ''; ?>" required aria-required="true" /><?php // phpcs:ignore WordPress.Security.NonceVerification.Missing,WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Woo's own repopulation of its login field, escaped on print. ?>
					</p>
					<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
						<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
						<label for="password"><?php esc_html_e( 'Password', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
						<input class="woocommerce-Input woocommerce-Input--text input-text" type="password" name="password" id="password" autocomplete="current-password" required aria-required="true" />
					</p>

					<?php
					// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
					do_action( 'woocommerce_login_form' );
					?>

					<p class="form-row linker-auth-remember">
						<label class="woocommerce-form__label woocommerce-form__label-for-checkbox woocommerce-form-login__rememberme">
							<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
							<input class="woocommerce-form__input woocommerce-form__input-checkbox" name="rememberme" type="checkbox" id="rememberme" value="forever" /> <span><?php esc_html_e( 'Remember me', 'woocommerce' ); ?></span>
						</label>
					</p>
					<p class="form-row linker-auth-submit">
						<?php wp_nonce_field( 'woocommerce-login', 'woocommerce-login-nonce' ); ?>
						<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
						<button type="submit" class="woocommerce-button button woocommerce-form-login__submit<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?>" name="login" value="<?php esc_attr_e( 'Log in', 'woocommerce' ); ?>"><span><?php esc_html_e( 'Log in', 'woocommerce' ); ?></span></button>
					</p>

					<?php
					// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
					do_action( 'woocommerce_login_form_end' );
					?>

				</form>
				<p class="linker-auth-links">
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<a href="<?php echo esc_url( wp_lostpassword_url() ); ?>"><?php esc_html_e( 'Lost your password?', 'woocommerce' ); ?></a>
					<?php if ( $registration && '' !== $register_url ) : ?>
						<a href="<?php echo esc_url( $register_url ); ?>"><?php esc_html_e( 'No partner account yet?', 'linker-commerce' ); ?> <strong><?php esc_html_e( 'Create your business account', 'linker-commerce' ); ?></strong></a>
					<?php endif; ?>
				</p>
			</section>

		</div>

	</div>
</div>
<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
do_action( 'woocommerce_after_customer_login_form' );
