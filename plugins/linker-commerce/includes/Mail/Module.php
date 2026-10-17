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
	 */
	public function __construct(
		private readonly Outbox $outbox,
		private readonly JobStore $jobs,
		private readonly EmailLocale $locale,
		private readonly EmailPolicy $policy,
		private readonly SmtpHealth $health = new SmtpHealth()
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( 'rest_api_init', array( $this->health, 'register_routes' ) );
		add_action( 'init', array( $this->jobs, 'register_post_type' ) );
			add_filter( 'pre_wp_mail', array( $this->outbox, 'intercept' ), 10, 2 );
			add_action( 'wp_mail_failed', array( $this->outbox, 'remember_error' ) );
		add_action( 'phpmailer_init', array( $this->outbox, 'configure_mailer' ) );
		add_action( Outbox::HOOK, array( $this->outbox, 'retry' ) );
		add_filter( 'woocommerce_allow_switching_email_locale', array( $this->locale, 'allow' ), 10, 2 );
		add_filter( 'woocommerce_allow_restoring_email_locale', array( $this->locale, 'allow' ), 10, 2 );
		add_filter( 'woocommerce_email_classes', array( $this->policy, 'switch_off_others' ), 1000 );
	}
}
