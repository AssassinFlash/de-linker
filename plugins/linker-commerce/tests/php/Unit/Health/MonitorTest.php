<?php
/**
 * Tests for the daily health check and its team alert.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Health;

use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;

/**
 * Tests for Monitor, with an in-memory WordPress for options and mocked HTTP.
 *
 * @covers \Linker\Commerce\Health\Monitor
 */
final class MonitorTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-commerce/linker-commerce.php';

	/**
	 * Options by name.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array(
		Monitor::GENIE_URL_OPTION  => 'http://127.0.0.1:8901',
		Monitor::ENGINE_URL_OPTION => 'http://127.0.0.1:8902',
		Options::CONTACT_EMAIL     => 'ops@example.test',
		Options::NOTIFY_BCC        => 'watch@example.test, mirror@example.test',
		Options::TEAM_TO           => 'sales@de-linker.com',
	);

	/**
	 * The URLs the checks asked, in order.
	 *
	 * @var list<string>
	 */
	private array $requests = array();

	/**
	 * The answers of the next wp_remote_get() calls, by URL.
	 *
	 * @var array<string, WP_Error|array<string, mixed>>
	 */
	private array $answers = array();

	/**
	 * The wp_mail() calls: [to, subject, body, headers].
	 *
	 * @var list<array<int|string, mixed>>
	 */
	private array $mails = array();

	/**
	 * An in-memory WordPress for options, the scheduler and the mail.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $name, $default_value = false ) => $this->options[ $name ] ?? $default_value ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::passthruFunction( '__' );
		// The Options readers, as WordPress's own functions behave for these addresses.
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => filter_var( $email, FILTER_VALIDATE_EMAIL ) ? $email : '' ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool|string => filter_var( $email, FILTER_VALIDATE_EMAIL ) ? $email : false ) );
		WP_Mock::userFunction(
			'wp_remote_get',
			array(
				'return' => function ( string $url, array $args = array() ) {
					$this->requests[] = $url;
					$this->assertSame( Monitor::TIMEOUT_SECONDS, $args['timeout'] );
					return $this->answers[ $url ] ?? new WP_Error( 'http_request_failed', 'cURL error 28: Operation timed out.' );
				},
			)
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code', array( 'return' => static fn ( $response ): int => is_array( $response ) ? (int) ( $response['response']['code'] ?? 0 ) : 0 ) );
		// WooCommerce's mailer, for the sender of the alert (its own getters read
		// woocommerce_email_from_name / _address).
		$mailer = \Mockery::mock();
		$mailer->allows( 'get_from_name' )->andReturn( 'Linker' );
		$mailer->allows( 'get_from_address' )->andReturn( 'sales@de-linker.com' );
		$woocommerce = \Mockery::mock();
		$woocommerce->allows( 'mailer' )->andReturn( $mailer );
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
		WP_Mock::userFunction(
			'wp_mail',
			array(
				'return' => function ( ...$args ): bool {
					$this->mails[] = $args;
					return true;
				},
			)
		);
	}

	/**
	 * Without a daily event, one is scheduled.
	 */
	public function test_schedules_the_daily_check_once(): void {
		WP_Mock::userFunction(
			'wp_schedule_event',
			array(
				'times'  => 1,
				'args'   => array( WP_Mock\Functions::type( 'int' ), 'daily', Monitor::HOOK ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => false ) );

		( new Monitor( self::FILE, new Options() ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * An event already being scheduled is left alone.
	 */
	public function test_leaves_the_scheduled_event_alone(): void {
		WP_Mock::userFunction( 'wp_schedule_event', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => 12345 ) );

		( new Monitor( self::FILE, new Options() ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * Deactivation removes the daily event.
	 */
	public function test_deactivate_clears_the_event(): void {
		WP_Mock::userFunction(
			'wp_clear_scheduled_hook',
			array(
				'times' => 1,
				'args'  => array( Monitor::HOOK ),
			)
		);

		( new Monitor( self::FILE, new Options() ) )->deactivate();
		$this->assertConditionsMet();
	}

	/**
	 * The check asks both services, one after the other, and sends one message
	 * per service that did not answer: to the contact person, with the blind
	 * copies of the settings, naming the service, the address and the reason.
	 */
	public function test_sends_one_alert_per_failed_service(): void {
		$this->answers = array(
			'http://127.0.0.1:8901/health' => new WP_Error( 'http_request_failed', 'cURL error 7: Failed to connect.' ),
			'http://127.0.0.1:8902/health' => array( 'response' => array( 'code' => 200 ) ),
		);

		( new Monitor( self::FILE, new Options() ) )->run();

		$this->assertSame( array( 'http://127.0.0.1:8901/health', 'http://127.0.0.1:8902/health' ), $this->requests, 'Both services are asked, in the declared order.' );
		$this->assertCount( 1, $this->mails, 'Only the failed service sends a message.' );
		[ $to, $subject, $body, $headers ] = $this->mails[0];
		$this->assertSame( 'sales@sunriverinverter.com', $to, 'The internal notification address receives the message, not the contact person customers see.' );
		$this->assertSame( 'The Genie service failed its health check', $subject );
		$this->assertStringContainsString( 'Address: http://127.0.0.1:8901', $body );
		$this->assertStringContainsString( 'Reason: cURL error 7: Failed to connect.', $body );
		$this->assertStringContainsString( 'Genie uses this service.', $body );
		$this->assertSame( array( 'From: Linker <sales@de-linker.com>', 'Bcc: watch@example.test, mirror@example.test' ), $headers, 'Sent from WooCommerce\'s email sender, with the blind copies.' );
	}

	/**
	 * Every service answering HTTP 200 sends nothing.
	 */
	public function test_sends_nothing_when_both_services_answer(): void {
		$this->answers = array(
			'http://127.0.0.1:8901/health' => array( 'response' => array( 'code' => 200 ) ),
			'http://127.0.0.1:8902/health' => array( 'response' => array( 'code' => 200 ) ),
		);

		( new Monitor( self::FILE, new Options() ) )->run();

		$this->assertSame( array(), $this->mails );
	}

	/**
	 * A service that answers with anything but HTTP 200 fails the check, with
	 * the status in the message.
	 */
	public function test_alerts_on_an_http_error_status(): void {
		$this->answers = array(
			'http://127.0.0.1:8901/health' => array( 'response' => array( 'code' => 200 ) ),
			'http://127.0.0.1:8902/health' => array( 'response' => array( 'code' => 502 ) ),
		);

		( new Monitor( self::FILE, new Options() ) )->run();

		$this->assertCount( 1, $this->mails );
		$this->assertSame( 'The engine service failed its health check', $this->mails[0][1] );
		$this->assertStringContainsString( 'Reason: the service answered HTTP 502 instead of 200', $this->mails[0][2] );
		$this->assertStringContainsString( 'The Solution Configurator uses this service.', $this->mails[0][2] );
	}

	/**
	 * An empty address option is a failure of its own: the check cannot pass
	 * while the instance configuration is incomplete.
	 */
	public function test_alerts_when_an_address_is_not_configured(): void {
		unset( $this->options[ Monitor::GENIE_URL_OPTION ] );
		$this->answers = array(
			'http://127.0.0.1:8902/health' => array( 'response' => array( 'code' => 200 ) ),
		);

		( new Monitor( self::FILE, new Options() ) )->run();

		$this->assertCount( 1, $this->mails );
		$this->assertSame( 'The Genie service failed its health check', $this->mails[0][1] );
		$this->assertStringContainsString( 'Reason: the address option linker_genie_url is empty', $this->mails[0][2] );
		$this->assertSame( array( 'http://127.0.0.1:8902/health' ), $this->requests, 'Without an address its check is skipped; the other service is still asked.' );
	}
}
