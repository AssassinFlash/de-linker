<?php
/**
 * Guest sign-in and register: the design of the account redesign (ticket #184,
 * owner-accepted prototype docs/design/2026-10-15-account-redesign).
 *
 * Every field, nonce and hook is Woo 11.2's own (mirrors
 * myaccount/form-login.php, version 9.9.0); the register form's own fields
 * arrive buffered from woocommerce_register_form_start and keep the three
 * sign-up steps the account reads — company, contact and address, sign-in
 * details. Woo's own labels keep Woo's text domain, so Woo's translations
 * keep applying. The desktop layout adds the brand panel; below 1080px the
 * two cards stand alone, the register card below the sign-in card.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

use Linker\Commerce\Account\AuthTemplates;

ob_start();
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
do_action( 'woocommerce_before_customer_login_form' );
$auth_notices = (string) ob_get_clean();
// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Presentation only; Woo owns verification and processing.
$register_notice = isset( $_POST['register'] );
$registration    = 'yes' === get_option( 'woocommerce_enable_myaccount_registration' );
$brand_logo      = plugins_url( 'assets/linker-logo-wordmark.png', dirname( __DIR__, 3 ) . '/linker-commerce.php' );
$brand_check     = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';
$brand_documents = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>';
$brand_workspace = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>';
?>
<div class="linker-auth" id="customer_login">
	<div class="linker-auth-inner">

		<aside class="linker-auth-brand">
			<img class="linker-auth-brand-logo" src="<?php echo esc_url( $brand_logo ); ?>" alt="" width="124" height="47" aria-hidden="true">
			<div>
				<p class="linker-auth-brand-title"><?php esc_html_e( 'Your partner account', 'linker-commerce' ); ?></p>
				<p class="linker-auth-brand-sub"><?php esc_html_e( 'The workspace for installers, EPCs and distributors.', 'linker-commerce' ); ?></p>
			</div>
			<ul class="linker-auth-brand-points">
				<li><?php echo $brand_check; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php esc_html_e( 'Net prices and Proforma requests once approved', 'linker-commerce' ); ?></span></li>
				<li><?php echo $brand_documents; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php esc_html_e( 'Every inquiry and document in one place', 'linker-commerce' ); ?></span></li>
				<li><?php echo $brand_workspace; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php esc_html_e( 'We answer inquiries within one working day', 'linker-commerce' ); ?></span></li>
			</ul>
		</aside>

		<section class="linker-auth-card" id="linker-signin" aria-labelledby="linker-auth-signin">
			<header class="linker-auth-card-heading">
				<h1 id="linker-auth-signin"><?php esc_html_e( 'Sign in', 'linker-commerce' ); ?></h1>
				<p><?php esc_html_e( 'Your inquiries, documents and prices in one place.', 'linker-commerce' ); ?></p>
			</header>

			<?php
			if ( ! $register_notice ) {
				// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's notice markup, kept intact beside the form it belongs to.
				echo $auth_notices;
			}
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
				<?php if ( $registration ) : ?>
					<a href="#linker-register"><?php esc_html_e( 'No partner account yet?', 'linker-commerce' ); ?> <strong><?php esc_html_e( 'Create your business account', 'linker-commerce' ); ?></strong></a>
				<?php endif; ?>
			</p>
		</section>

		<?php if ( $registration ) : ?>
		<section class="linker-auth-card linker-auth-register" id="linker-register" aria-labelledby="linker-auth-register-heading">
			<header class="linker-auth-card-heading">
				<h2 id="linker-auth-register-heading"><?php esc_html_e( 'Create your business account', 'linker-commerce' ); ?></h2>
				<p><?php esc_html_e( 'We review every new account before activation.', 'linker-commerce' ); ?></p>
			</header>

			<?php
			if ( $register_notice ) {
				// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's notice markup, kept intact beside the form it belongs to.
				echo $auth_notices;
			}
			?>
			<form method="post" action="#linker-register" class="woocommerce-form woocommerce-form-register register" <?php do_action( 'woocommerce_register_form_tag' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php. ?> >

				<?php $register_blocks = AuthTemplates::register_field_blocks(); ?>

				<ol class="linker-auth-steps">
					<li class="linker-auth-step">
						<h3 class="linker-auth-step-title"><span class="linker-auth-step-index" aria-hidden="true">1</span><?php esc_html_e( 'Company', 'linker-commerce' ); ?></h3>
						<div class="linker-auth-step-fields">
							<?php echo $register_blocks['company']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's own register field markup, buffered from woocommerce_register_form_start; kses would strip the inputs. ?>
						</div>
					</li>
					<li class="linker-auth-step">
						<h3 class="linker-auth-step-title"><span class="linker-auth-step-index" aria-hidden="true">2</span><?php esc_html_e( 'Contact and address', 'linker-commerce' ); ?></h3>
						<div class="linker-auth-step-fields">
							<?php echo $register_blocks['contact']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's own register field markup, buffered from woocommerce_register_form_start; kses would strip the inputs. ?>
						</div>
					</li>
					<li class="linker-auth-step">
						<h3 class="linker-auth-step-title"><span class="linker-auth-step-index" aria-hidden="true">3</span><?php esc_html_e( 'Sign-in details', 'linker-commerce' ); ?></h3>
						<div class="linker-auth-step-fields">
							<?php if ( 'no' === get_option( 'woocommerce_registration_generate_username' ) ) : ?>
								<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
									<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
									<label for="reg_username"><?php esc_html_e( 'Username', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
									<input type="text" class="woocommerce-Input woocommerce-Input--text input-text" name="username" id="reg_username" autocomplete="username" value="<?php echo ( ! empty( $_POST['username'] ) ) ? esc_attr( wp_unslash( $_POST['username'] ) ) : ''; ?>" required aria-required="true" /><?php // phpcs:ignore WordPress.Security.NonceVerification.Missing,WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Woo's own repopulation of its register field, escaped on print. ?>
								</p>
							<?php endif; ?>

							<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
								<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
								<label for="reg_email"><?php esc_html_e( 'Email address', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
								<input type="email" class="woocommerce-Input woocommerce-Input--text input-text" name="email" id="reg_email" autocomplete="email" value="<?php echo ( ! empty( $_POST['email'] ) ) ? esc_attr( wp_unslash( $_POST['email'] ) ) : ''; ?>" required aria-required="true" /><?php // phpcs:ignore WordPress.Security.NonceVerification.Missing,WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Woo's own repopulation of its register field, escaped on print. ?>
							</p>

							<?php if ( 'no' === get_option( 'woocommerce_registration_generate_password' ) ) : ?>
								<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
									<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
									<label for="reg_password"><?php esc_html_e( 'Password', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span><span class="screen-reader-text"><?php esc_html_e( 'Required', 'woocommerce' ); ?></span></label>
									<input type="password" class="woocommerce-Input woocommerce-Input--text input-text" name="password" id="reg_password" autocomplete="new-password" required aria-required="true" />
									<span class="linker-auth-hint"><?php esc_html_e( 'Use at least 8 characters with a mix of letters, numbers and symbols.', 'linker-commerce' ); ?></span>
								</p>
							<?php else : ?>
								<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
								<p><?php esc_html_e( 'A link to set a new password will be sent to your email address.', 'woocommerce' ); ?></p>
							<?php endif; ?>
						</div>
					</li>
				</ol>

				<?php
				// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
				do_action( 'woocommerce_register_form' );
				?>

				<p class="linker-auth-links linker-auth-legal">
					<?php if ( wc_get_page_id( 'terms' ) > 0 ) : ?>
						<a href="<?php echo esc_url( wc_get_page_permalink( 'terms' ) ); ?>"><?php esc_html_e( 'Terms of Sale', 'linker-commerce' ); ?></a>
					<?php endif; ?>
					<?php if ( get_privacy_policy_url() ) : ?>
						<a href="<?php echo esc_url( get_privacy_policy_url() ); ?>"><?php esc_html_e( 'Privacy', 'linker-commerce' ); ?></a>
					<?php endif; ?>
				</p>
				<p class="woocommerce-form-row form-row linker-auth-submit">
					<?php wp_nonce_field( 'woocommerce-register', 'woocommerce-register-nonce' ); ?>
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<button type="submit" class="woocommerce-Button woocommerce-button button<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?> woocommerce-form-register__submit" name="register" value="<?php esc_attr_e( 'Register', 'woocommerce' ); ?>"><span><?php esc_html_e( 'Register', 'woocommerce' ); ?></span></button>
				</p>
				<p class="linker-auth-links">
					<a href="#linker-signin"><?php esc_html_e( 'Already have a partner account?', 'linker-commerce' ); ?> <strong><?php esc_html_e( 'Sign in', 'linker-commerce' ); ?></strong></a>
				</p>

				<?php
				// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
				do_action( 'woocommerce_register_form_end' );
				?>

			</form>
		</section>
		<?php endif; ?>

	</div>
</div>
<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
do_action( 'woocommerce_after_customer_login_form' );
