<?php
/**
 * Hooks of the mail module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * The outbox for every wp_mail() call, its queue, the email language and the
 * WooCommerce emails that stay on.
 */
final class Module {


	/**
	 * Sets up the module.
	 *
	 * @param Outbox      $outbox The outbox.
	 * @param JobStore    $jobs   The queue.
	 * @param EmailLocale $locale The email language rule.
	 * @param EmailPolicy $policy The WooCommerce emails that stay on.
	 * @param SmtpHealth  $health Staff web-context readback of SMTP status.
	 * @param Producer    $producer Native mail priority contexts.
	 */
	public function __construct(
		private readonly Outbox $outbox,
		private readonly JobStore $jobs,
		private readonly EmailLocale $locale,
		private readonly EmailPolicy $policy,
		private readonly SmtpHealth $health = new SmtpHealth(),
		private readonly Producer $producer = new Producer()
	) {
	}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( 'rest_api_init', array( $this->health, 'register_routes' ) );
		add_action( 'init', array( $this->jobs, 'register_post_type' ) );
		add_action( 'deleted_post', array( Capacity::class, 'deleted' ), 10, 2 );
		add_action( \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::HOOK, array( new \Linker\Commerce\Health\ReviewReminder(), 'tick' ), 20 );
				add_filter( 'woocommerce_mail_callback', array( $this->producer, 'woocommerce' ), 10, 2 );
		add_filter( 'retrieve_password_notification_email', array( $this->producer, 'password_reset' ), PHP_INT_MAX, 4 );
		add_filter( 'email_change_email', array( $this->producer, 'account_change' ), PHP_INT_MAX, 3 );
		add_filter( 'password_change_email', array( $this->producer, 'account_change' ), PHP_INT_MAX, 3 );
		add_filter( 'wp_password_change_notification_email', array( $this->producer, 'password_changed_admin' ), PHP_INT_MAX, 3 );
		add_action( 'retrieve_password_key', array( ResetNotice::class, 'begin' ), PHP_INT_MAX, 2 );
		add_action( 'woocommerce_email_sent', array( ResetNotice::class, 'woocommerce_result' ), PHP_INT_MAX, 3 );
		add_action( 'woocommerce_before_lost_password_form', array( ResetNotice::class, 'render_begin' ), PHP_INT_MAX );
		add_action( 'woocommerce_after_lost_password_form', array( ResetNotice::class, 'render_end' ), PHP_INT_MIN );
		add_action( 'woocommerce_email_disabled', array( ResetNotice::class, 'disabled' ), 10, 2 );
		add_filter( 'send_retrieve_password_email', array( ResetNotice::class, 'allowed' ), PHP_INT_MAX, 3 );
		add_filter( 'pre_wp_mail', array( $this->outbox, 'intercept' ), 10, 2 );
		add_action( 'wp_mail_failed', array( $this->outbox, 'remember_error' ) );
		add_action( 'phpmailer_init', array( $this->outbox, 'configure_mailer' ) );
		add_action( Outbox::HOOK, array( $this->outbox, 'retry' ) );
		add_filter( 'woocommerce_allow_switching_email_locale', array( $this->locale, 'allow' ), 10, 2 );
		add_filter( 'woocommerce_allow_restoring_email_locale', array( $this->locale, 'allow' ), 10, 2 );
		add_filter( 'woocommerce_email_recipient_customer_reset_password', array( $this->locale, 'password_recipient' ), 10, 3 );
		add_filter( 'woocommerce_email_classes', array( $this->policy, 'switch_off_others' ), 1000 );
	}
}
