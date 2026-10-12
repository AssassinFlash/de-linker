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
	 * @param EmailPolicy $policy    The WooCommerce emails that stay on.
	 * @param TestMode    $test_mode The test-mode switch of outgoing mail.
	 */
	public function __construct(
		private readonly Outbox $outbox,
		private readonly JobStore $jobs,
		private readonly EmailLocale $locale,
		private readonly EmailPolicy $policy,
		private readonly TestMode $test_mode = new TestMode()
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this->jobs, 'register_post_type' ) );
		add_filter( 'pre_wp_mail', array( $this->outbox, 'intercept' ), 10, 2 );
		// After every other wp_mail filter, including the legacy plugin's copy
		// queue at priority 100: what leaves this filter is what wp_mail() sends.
		add_filter( 'wp_mail', array( $this->test_mode, 'rewrite' ), PHP_INT_MAX );
		add_action( 'plugins_loaded', array( $this->test_mode, 'silence_copy_queues' ), PHP_INT_MAX );
		add_action( 'init', array( $this->test_mode, 'silence_copy_queues' ), PHP_INT_MAX );
		add_action( 'wp_mail_failed', array( $this->outbox, 'remember_error' ) );
		add_action( Outbox::HOOK, array( $this->outbox, 'retry' ) );
		add_filter( 'woocommerce_allow_switching_email_locale', array( $this->locale, 'allow' ), 10, 2 );
		add_filter( 'woocommerce_allow_restoring_email_locale', array( $this->locale, 'allow' ), 10, 2 );
		add_filter( 'woocommerce_email_classes', array( $this->policy, 'switch_off_others' ), 1000 );
	}
}
