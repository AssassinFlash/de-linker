<?php
/**
 * Guest sign-in and register, as one centred column of cards. Every field,
 * nonce and hook is Woo 11.2's own (mirrors myaccount/form-login.php,
 * version 9.9.0); the register form's own fields arrive buffered from
 * woocommerce_register_form_start and are laid out in the three sign-up
 * steps — company, contact and address, sign-in details. Woo's own labels
 * keep Woo's text domain, so Woo's translations keep applying.
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
?>
<div class="linker-auth" id="customer_login">
	<section class="linker-auth-card" aria-labelledby="linker-auth-signin">
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

			<p class="form-row">
				<label class="woocommerce-form__label woocommerce-form__label-for-checkbox woocommerce-form-login__rememberme">
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<input class="woocommerce-form__input woocommerce-form__input-checkbox" name="rememberme" type="checkbox" id="rememberme" value="forever" /> <span><?php esc_html_e( 'Remember me', 'woocommerce' ); ?></span>
				</label>
			</p>
			<p class="form-row linker-auth-submit">
				<?php wp_nonce_field( 'woocommerce-login', 'woocommerce-login-nonce' ); ?>
				<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
				<button type="submit" class="woocommerce-button button woocommerce-form-login__submit<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?>" name="login" value="<?php esc_attr_e( 'Log in', 'woocommerce' ); ?>"><?php esc_html_e( 'Log in', 'woocommerce' ); ?></button>
			</p>
			<p class="woocommerce-LostPassword lost_password">
				<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
				<a href="<?php echo esc_url( wp_lostpassword_url() ); ?>"><?php esc_html_e( 'Lost your password?', 'woocommerce' ); ?></a>
			</p>

			<?php
			// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
			do_action( 'woocommerce_login_form_end' );
			?>

		</form>
		<?php if ( $registration ) : ?>
			<p class="linker-auth-links linker-auth-mobile-links"><a href="#linker-register"><?php esc_html_e( 'Create your business account', 'linker-commerce' ); ?></a></p>
		<?php endif; ?>
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
				<button type="submit" class="woocommerce-Button woocommerce-button button<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?> woocommerce-form-register__submit" name="register" value="<?php esc_attr_e( 'Register', 'woocommerce' ); ?>"><?php esc_html_e( 'Register', 'woocommerce' ); ?></button>
			</p>

			<?php
			// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
			do_action( 'woocommerce_register_form_end' );
			?>

		</form>
	</section>
	<?php endif; ?>
</div>
<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
do_action( 'woocommerce_after_customer_login_form' );
