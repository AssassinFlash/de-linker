<?php
/**
 * Account details: the profile and the password change as the account
 * redesign's two panels (ticket #184, owner-accepted prototype account.html).
 * Woo 11.2's own form (mirrors myaccount/form-edit-account.php, version
 * 11.0.0): the same field names, ids, nonce, action, hooks and labels — the
 * password labels are shortened to the page's note line, and the strength
 * meter is WooCommerce's own (wc-password-strength-meter, which binds to
 * form.edit-account #password_1); the styles live in the WindPress layer.
 *
 * @package Linker\Commerce
 *
 * @var WP_User $user The account being edited (Woo template argument).
 */

defined( 'ABSPATH' ) || exit;

// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-edit-account.php.
do_action( 'woocommerce_before_edit_account_form' );
?>

<form class="woocommerce-EditAccountForm edit-account linker-account-forms" action="" method="post" <?php do_action( 'woocommerce_edit_account_form_tag' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-edit-account.php. ?> >

	<?php
	// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-edit-account.php.
	do_action( 'woocommerce_edit_account_form_start' );
	?>

	<section class="linker-account-panel" aria-label="<?php esc_attr_e( 'Your details', 'linker-commerce' ); ?>">
		<div class="linker-account-panel-body">
			<div class="linker-account-field-pair">
				<p class="woocommerce-form-row woocommerce-form-row--first form-row form-row-first">
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<label for="account_first_name"><?php esc_html_e( 'First name', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span></label>
					<input type="text" class="woocommerce-Input woocommerce-Input--text input-text" name="account_first_name" id="account_first_name" autocomplete="given-name" value="<?php echo esc_attr( \Linker\Commerce\Registration\PendingProfileCapacity::account_value( 'account_first_name', $user->first_name ) ); ?>" aria-required="true" />
				</p>
				<p class="woocommerce-form-row woocommerce-form-row--last form-row form-row-last">
					<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
					<label for="account_last_name"><?php esc_html_e( 'Last name', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span></label>
					<input type="text" class="woocommerce-Input woocommerce-Input--text input-text" name="account_last_name" id="account_last_name" autocomplete="family-name" value="<?php echo esc_attr( \Linker\Commerce\Registration\PendingProfileCapacity::account_value( 'account_last_name', $user->last_name ) ); ?>" aria-required="true" />
				</p>
			</div>

			<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
				<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
				<label for="account_display_name"><?php esc_html_e( 'Display name', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span></label>
				<input type="text" class="woocommerce-Input woocommerce-Input--text input-text" name="account_display_name" id="account_display_name" aria-describedby="account_display_name_description" value="<?php echo esc_attr( \Linker\Commerce\Registration\PendingProfileCapacity::account_value( 'account_display_name', $user->display_name ) ); ?>" aria-required="true" />
				<span class="linker-account-hint" id="account_display_name_description"><?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native hint. */ ?><?php echo wc_reviews_enabled() ? esc_html__( 'This will be how your name will be displayed in the account section and in reviews', 'woocommerce' ) : esc_html__( 'This will be how your name will be displayed in the account section', 'woocommerce' ); ?></span>
			</p>

			<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
				<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
				<label for="account_email"><?php esc_html_e( 'Email address', 'woocommerce' ); ?>&nbsp;<span class="required" aria-hidden="true">*</span></label>
				<input type="email" class="woocommerce-Input woocommerce-Input--email input-text" name="account_email" id="account_email" autocomplete="email" value="<?php echo esc_attr( \Linker\Commerce\Registration\PendingProfileCapacity::account_value( 'account_email', $user->user_email ) ); ?>" aria-required="true" />
			</p>
		</div>
	</section>

	<?php
	/**
	 * Hook where additional fields should be rendered.
	 *
	 * @since 8.7.0
	 */
	// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-edit-account.php.
	do_action( 'woocommerce_edit_account_form_fields' );
	?>

	<section class="linker-account-panel" aria-labelledby="linker-account-password">
		<header class="linker-account-panel-heading">
			<h2 id="linker-account-password"><?php esc_html_e( 'Password change', 'linker-commerce' ); ?></h2>
		</header>
		<div class="linker-account-panel-body">
			<p class="linker-account-note"><?php esc_html_e( 'Leave the password fields blank to keep your current password.', 'linker-commerce' ); ?></p>

			<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
				<label for="password_current"><?php esc_html_e( 'Current password', 'linker-commerce' ); ?></label>
				<input type="password" class="woocommerce-Input woocommerce-Input--password input-text" name="password_current" id="password_current" autocomplete="current-password" />
			</p>
			<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
				<label for="password_1"><?php esc_html_e( 'New password', 'linker-commerce' ); ?></label>
				<input type="password" class="woocommerce-Input woocommerce-Input--password input-text" name="password_1" id="password_1" autocomplete="new-password" />
				<span class="linker-account-hint"><?php esc_html_e( 'Use at least 8 characters with a mix of letters, numbers and symbols.', 'linker-commerce' ); ?></span>
			</p>
			<p class="woocommerce-form-row woocommerce-form-row--wide form-row form-row-wide">
				<label for="password_2"><?php esc_html_e( 'Confirm new password', 'linker-commerce' ); ?></label>
				<input type="password" class="woocommerce-Input woocommerce-Input--password input-text" name="password_2" id="password_2" autocomplete="new-password" />
				<span class="linker-account-error" id="linker-account-mismatch" data-password-mismatch role="alert" hidden><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg><span><?php esc_html_e( 'The passwords do not match.', 'linker-commerce' ); ?></span></span>
			</p>

			<?php
			/**
			 * My Account edit account form.
			 *
			 * @since 2.6.0
			 */
			// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-edit-account.php.
			do_action( 'woocommerce_edit_account_form' );
			?>

			<div class="linker-account-actions">
				<?php wp_nonce_field( 'save_account_details', 'save-account-details-nonce' ); ?>
				<?php /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */ ?>
				<button type="submit" class="woocommerce-Button button<?php echo esc_attr( wc_wp_theme_get_element_class_name( 'button' ) ? ' ' . wc_wp_theme_get_element_class_name( 'button' ) : '' ); ?>" name="save_account_details" value="<?php esc_attr_e( 'Save changes', 'woocommerce' ); ?>"><span><?php esc_html_e( 'Save changes', 'woocommerce' ); ?></span></button>
				<input type="hidden" name="action" value="save_account_details" />
			</div>
		</div>
	</section>

	<?php
	// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-edit-account.php.
	do_action( 'woocommerce_edit_account_form_end' );
	?>
</form>

<?php
// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native hook documented in Woo's form-edit-account.php.
do_action( 'woocommerce_after_edit_account_form' );
