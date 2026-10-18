<?php
/**
 * Guest sign-up: the register page's card, the design of the account redesign
 * (ticket #184, owner-accepted prototype docs/design/2026-10-15-account-redesign
 * register.html), one page per card since the owner's 2026-10-16 ruling — the
 * account page carries the sign-in card
 * (templates/myaccount/auth/form-login.php), this page the sign-up card, each
 * linking to the other.
 *
 * The form is the owner's two-step variant (2026-10-17, ticket #225): step 1
 * asks the company and its verification values, step 2 the person and the
 * sign-in details. Both steps are one WooCommerce form and one submission;
 * without JavaScript both are visible and the form works, with JavaScript the
 * account-ui.js file opens and closes the panes and the progress bar reports
 * the step. Every field, nonce and hook is Woo 11.2's own (mirrors
 * myaccount/form-login.php, version 9.9.0): the form posts to this page, so a
 * refused registration reads its WooCommerce error right here, next to the
 * fields it belongs to, and a successful one signs the account in and lands on
 * the account page (WooCommerce's own redirect). The register form's own fields
 * arrive buffered from woocommerce_register_form_start and keep the two
 * sign-up steps the account reads. Woo's own labels keep Woo's text domain, so
 * Woo's translations keep applying. On the desktop the card carries its own
 * brand panel — the register words (prototype register.html). Below 1080px the
 * panel is hidden and the card stands alone.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

use Linker\Commerce\Account\AuthTemplates;
use Linker\Commerce\Registration\Fields;

ob_start();
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
do_action( 'woocommerce_before_customer_login_form' );
$auth_notices    = (string) ob_get_clean();
$signin_url      = (string) wc_get_page_permalink( 'myaccount' );
$brand_logo      = plugins_url( 'assets/linker-logo-wordmark.webp', dirname( __DIR__, 3 ) . '/linker-commerce.php' );
$brand_check     = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';
$brand_documents = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>';
$brand_workspace = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>';
$active_step     = Fields::active_step();
?>
<div class="linker-auth" id="customer_login">
	<div class="linker-auth-inner">
		<div class="linker-auth-unit">

			<aside class="linker-auth-brand" aria-hidden="true">
				<img class="linker-auth-brand-logo" src="<?php echo esc_url( $brand_logo ); ?>" alt="" width="124" height="47" decoding="async">
				<div>
					<p class="linker-auth-brand-title"><?php esc_html_e( 'Create your partner account', 'linker-commerce' ); ?></p>
					<p class="linker-auth-brand-sub"><?php esc_html_e( 'For installers, EPCs and distributors: net prices, documents and inquiries in one workspace.', 'linker-commerce' ); ?></p>
				</div>
				<ul class="linker-auth-brand-points">
					<li><?php echo $brand_check; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php esc_html_e( 'You see net prices on every product after approval', 'linker-commerce' ); ?></span></li>
					<li><?php echo $brand_documents; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php esc_html_e( 'We answer inquiries within one working day', 'linker-commerce' ); ?></span></li>
					<li><?php echo $brand_workspace; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup. ?><span><?php esc_html_e( 'We run the VAT ID check in VIES for you', 'linker-commerce' ); ?></span></li>
				</ul>
			</aside>

			<section class="linker-auth-card linker-auth-register" aria-labelledby="linker-auth-register-heading">
				<header class="linker-auth-card-heading">
					<h1 id="linker-auth-register-heading"><?php esc_html_e( 'Create your business account', 'linker-commerce' ); ?></h1>
					<p><?php esc_html_e( 'We review every new account before activation.', 'linker-commerce' ); ?></p>
				</header>

				<?php
				// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's notice markup, kept intact beside the form it belongs to.
				echo $auth_notices;
				?>
				<form method="post" class="woocommerce-form woocommerce-form-register register linker-auth-register-form" data-linker-register data-active-step="<?php echo esc_attr( (string) $active_step ); ?>" <?php do_action( 'woocommerce_register_form_tag' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php. ?> >

					<?php $register_blocks = AuthTemplates::register_field_blocks(); ?>

					<div class="linker-auth-progress" data-progress hidden aria-hidden="true">
						<span class="linker-auth-progress-segment is-on" data-progress-segment="1"></span>
						<span class="linker-auth-progress-segment" data-progress-segment="2"></span>
					</div>
					<div aria-live="polite">
						<p class="linker-auth-stepnote" data-stepnote="1" hidden><?php esc_html_e( 'Step 1 of 2 · Your company', 'linker-commerce' ); ?></p>
						<p class="linker-auth-stepnote" data-stepnote="2" hidden><?php esc_html_e( 'Step 2 of 2 · You and your sign-in', 'linker-commerce' ); ?></p>
					</div>

					<div class="linker-auth-pane" data-pane="1">
						<h2 class="linker-auth-pane-title"><?php esc_html_e( 'Your company', 'linker-commerce' ); ?></h2>
						<div class="linker-auth-fields">
							<?php echo $register_blocks['company']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's own register field markup, buffered from woocommerce_register_form_start; kses would strip the inputs. ?>
						</div>

						<p class="linker-auth-note"><?php esc_html_e( 'We use one of these to verify your company. Enter at least one.', 'linker-commerce' ); ?></p>
						<div class="linker-auth-verify">
							<div class="linker-auth-fields">
								<?php echo $register_blocks['verify']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's own register field markup, buffered from woocommerce_register_form_start; kses would strip the inputs. ?>
							</div>
						</div>
						<p class="linker-auth-error" data-oneof-error role="alert" hidden><?php esc_html_e( 'Enter your company website or VAT ID, so we can verify your company.', 'linker-commerce' ); ?></p>
						<p class="linker-auth-error" data-client-error role="alert" hidden><?php esc_html_e( 'Please complete the required fields.', 'linker-commerce' ); ?></p>

						<button type="button" class="linker-auth-btn" data-next hidden><span><?php esc_html_e( 'Continue', 'linker-commerce' ); ?></span></button>
						<p class="linker-auth-links">
							<a href="<?php echo esc_url( $signin_url ); ?>"><?php esc_html_e( 'Already have a partner account?', 'linker-commerce' ); ?> <strong><?php esc_html_e( 'Sign in', 'linker-commerce' ); ?></strong></a>
						</p>
					</div>

					<div class="linker-auth-pane" data-pane="2">
						<h2 class="linker-auth-pane-title"><?php esc_html_e( 'You and your sign-in', 'linker-commerce' ); ?></h2>
						<div class="linker-auth-fields">
							<?php echo $register_blocks['you']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Woo's own register field markup, buffered from woocommerce_register_form_start; kses would strip the inputs. ?>

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
								<input type="email" class="woocommerce-Input woocommerce-Input--text input-text" name="email" id="reg_email" autocomplete="email" value="<?php echo ( ! empty( $_POST['email'] ) ) ? esc_attr( wp_unslash( $_POST['email'] ) ) : esc_attr( \Linker\Commerce\Inquiry\AccountLink::email() ); ?>" required aria-required="true" /><?php // phpcs:ignore WordPress.Security.NonceVerification.Missing,WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Woo's own repopulation of its register field, escaped on print. ?>
								<span class="linker-auth-hint"><?php esc_html_e( 'You sign in with it. We send the approval to this address.', 'linker-commerce' ); ?></span>
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
						<button type="button" class="linker-auth-btn is-ghost" data-back hidden><span><?php esc_html_e( 'Back', 'linker-commerce' ); ?></span></button>
					</div>

					<?php
					// The public form's bot traps sit outside the panes: the step
					// script disables the hidden pane's controls, and these fields
					// must reach WooCommerce on every attempt.
					// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
					do_action( 'woocommerce_register_form' );
					?>

					<?php
					// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
					do_action( 'woocommerce_register_form_end' );
					?>

				</form>
			</section>

		</div>
	</div>
</div>
<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-login.php.
do_action( 'woocommerce_after_customer_login_form' );
