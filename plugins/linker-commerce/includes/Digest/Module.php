<?php
/**
 * Hooks of the digest module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Settings\Options;

/**
 * The daily digest: its cron schedule, its email in WooCommerce's list, and
 * the task that composes the blocks and sends.
 */
final class Module {

	/**
	 * Native daily admission boundary.
	 *
	 * @var Delivery
	 */
	private readonly Delivery $delivery;

	/**
	 * Sets up the module.
	 *
	 * @param string   $plugin_file Absolute path of the main plugin file.
	 * @param JobStore $jobs        The mail queue, for the failed-emails block.
	 * @param Delivery $delivery    Native daily admission boundary.
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly JobStore $jobs,
		Delivery $delivery = new NativeDailyDelivery()
	) {
		$this->delivery = $delivery;
	}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( Scheduler::HOOK, array( $this, 'run' ) );
		add_action( 'init', array( new Scheduler(), 'ensure' ) );
		add_filter( 'woocommerce_email_classes', array( $this, 'add_email' ) );
		add_filter( 'woocommerce_email_styles', array( $this, 'email_styles' ), 10, 2 );
	}

	/**
	 * Inlines the digest presentation when this email is the one being sent.
	 *
	 * @param string $css   The email stylesheet so far.
	 * @param mixed  $email The email being rendered.
	 */
	public function email_styles( $css, $email = null ): string {
		return DigestEmail::append_styles( (string) $css, $email );
	}

	/**
	 * Adds the digest to the emails WooCommerce shows under Settings → Emails.
	 *
	 * @param array<string, object> $emails Email objects by class.
	 * @return array<string, object>
	 */
	public function add_email( array $emails ): array {
		$emails[ DigestEmail::class ] = new DigestEmail( $this->plugin_file, new Options() );
		return $emails;
	}

	/**
	 * The scheduled task: one digest — empty or not — then the next 09:00
	 * Berlin (docs/specs/74-daily-digest.md).
	 */
	public function run(): void {
		$this->delivery->send( new DigestEmail( $this->plugin_file, new Options() ), ( new Blocks( $this->jobs ) )->all() );
		( new Scheduler() )->reschedule();
	}
}
