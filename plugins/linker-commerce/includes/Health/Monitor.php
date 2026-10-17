<?php
/**
 * The daily health check of the two services.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Health;

use Linker\Commerce\Settings\Options;
use WP_Error;

/**
 * Once a day, asks each service for GET /health (docs/specs/13-genie.md,
 * docs/specs/14-solution-configurator.md). A service that does not answer
 * with HTTP 200 triggers one message to the internal notification address
 * (Options::notify_to(), with its blind copies), from WooCommerce's email
 * sender like every other internal notification, through wp_mail() — the
 * Outbox takes it from there (queued, retried). Nothing is sent when every
 * service answers. WordPress has no built-in monitor for external services,
 * so the check itself is this plugin's; everything around it is WordPress's
 * own: the WP-Cron daily event, the HTTP API, and the mail queue.
 */
final class Monitor {

	/**
	 * WP-Cron hook and Action Scheduler group of the daily check.
	 */
	public const HOOK  = 'linker_commerce_health_check';
	public const GROUP = 'linker-commerce';

	/**
	 * The service addresses are instance configuration, written by `just serve`
	 * locally and by the cutover in production (docs/specs/13-genie.md,
	 * docs/specs/14-solution-configurator.md, docs/local-stack.md).
	 */
	public const GENIE_URL_OPTION  = 'linker_genie_url';
	public const ENGINE_URL_OPTION = 'linker_engine_url';

	/**
	 * Seconds to wait for one service before the check gives up. Two services
	 * answer in well under a second when they are up; ten seconds bounds the
	 * worst daily cron run at twenty.
	 */
	public const TIMEOUT_SECONDS = 10.0;

	/**
	 * The checked services and the option their address comes from.
	 *
	 * @var array<string, string>
	 */
	private const SERVICES = array(
		'genie'  => self::GENIE_URL_OPTION,
		'engine' => self::ENGINE_URL_OPTION,
	);

	/**
	 * Sets up the monitor.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings.
	 */
	public function __construct( private readonly string $plugin_file, private readonly Options $options ) {}

	/**
	 * Adds the monitor's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this, 'schedule' ) );
		add_action( self::HOOK, array( $this, 'run' ) );
		register_deactivation_hook( $this->plugin_file, array( $this, 'deactivate' ) );
	}

	/**
	 * Schedules the daily check; runs on init, so a missing event comes back
	 * without an activation hook.
	 */
	public function schedule(): void {
		if ( false === wp_next_scheduled( self::HOOK ) ) {
			wp_schedule_event( time(), 'daily', self::HOOK );
		}
	}

	/**
	 * Removes the daily event; runs on deactivation.
	 */
	public function deactivate(): void {
		wp_clear_scheduled_hook( self::HOOK );
	}

	/**
	 * The daily check; runs on the WP-Cron hook. Checks the services one after
	 * the other and sends one message per service that did not answer.
	 */
	public function run(): void {
		foreach ( self::SERVICES as $service => $option ) {
			$failure = $this->check( (string) get_option( $option, '' ), $option );
			if ( '' !== $failure ) {
				$this->alert( $service, $failure );
			}
		}
	}

	/**
	 * Asks one service whether it is up.
	 *
	 * @param string $base   The service's address, as instance configuration.
	 * @param string $option The option the address came from.
	 * @return string Why the service failed, or '' when it answered.
	 */
	private function check( string $base, string $option ): string {
		$base = trim( $base );
		if ( '' === $base ) {
			return sprintf(
				/* translators: %s: option name. */
				__( 'the address option %s is empty', 'linker-commerce' ),
				$option
			);
		}
		$response = wp_remote_get( rtrim( $base, '/' ) . '/health', array( 'timeout' => self::TIMEOUT_SECONDS ) );
		if ( $response instanceof WP_Error ) {
			return (string) $response->get_error_message();
		}
		$code = (int) wp_remote_retrieve_response_code( $response );
		if ( $code < 200 || $code >= 300 ) {
			return sprintf(
				/* translators: %d: HTTP status code. */
				__( 'the service answered HTTP %d instead of 200', 'linker-commerce' ),
				$code
			);
		}
		return '';
	}

	/**
	 * The service's name in the message: the assistant's own name, the other
	 * service by what it is.
	 *
	 * @param string $service Service key (genie or engine).
	 */
	private function label( string $service ): string {
		return 'genie' === $service ? __( 'Genie', 'linker-commerce' ) : __( 'engine', 'linker-commerce' );
	}

	/**
	 * Who feels the outage of a service.
	 *
	 * @param string $service Service key (genie or engine).
	 */
	private function consumer( string $service ): string {
		return 'genie' === $service ? $this->label( $service ) : __( 'The Solution Configurator', 'linker-commerce' );
	}

	/**
	 * Sends the team the failure of one service.
	 *
	 * @param string $service Service key (genie or engine).
	 * @param string $failure Why the check failed.
	 */
	private function alert( string $service, string $failure ): void {
		$subject = sprintf(
			/* translators: %s: service name (Genie or engine). */
			__( 'The %s service failed its health check', 'linker-commerce' ),
			$this->label( $service )
		);
		$body = sprintf(
			/* translators: 1: service name, 2: address, 3: reason, 4: UTC time, 5: what uses the service. */
			__(
				"The daily health check could not reach the %1\$s service.\n\nAddress: %2\$s\nReason: %3\$s\nChecked: %4\$s UTC\n\n%5\$s uses this service. The check runs once a day and repeats this message on every failure.",
				'linker-commerce'
			),
			$this->label( $service ),
			(string) get_option( self::SERVICES[ $service ], '' ),
			$failure,
			gmdate( 'Y-m-d H:i' ),
			$this->consumer( $service )
		);
		// The sender every other internal notification has: WooCommerce's own
		// "From" name and address (WooCommerce → Settings → Emails), read
		// through its mailer. A plain wp_mail() would otherwise go out from
		// WordPress's default wordpress@<host>.
		$mailer  = WC()->mailer();
		$headers = array( 'From: ' . $mailer->get_from_name() . ' <' . $mailer->get_from_address() . '>' );
		$bcc     = $this->options->notify_bcc();
		if ( array() !== $bcc ) {
			$headers[] = 'Bcc: ' . implode( ', ', $bcc );
		}
		wp_mail( $this->options->notify_to(), $subject, $body, $headers );
	}
}
