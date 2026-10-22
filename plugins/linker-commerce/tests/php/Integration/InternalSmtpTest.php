<?php
/**
 * Native wp_mail and Outbox against a test-owned localhost SMTP server.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- native PHPMailer property names.

use Linker\Commerce\Mail\InternalSmtp;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use WP_PHPMailer;

/**
 * SMTP is real; PHP mail is captured to a local file, never sent.
 *
 * @coversNothing
 */
final class InternalSmtpTest extends IntegrationTestCase {

	/**
	 * Internal SMTP and subsequent customer mail through the same WP mailer.
	 */
	public function test_internal_smtp_and_customer_file_delivery(): void {
		$directory = $this->fixture();

		wp_mail( 'tester@example.test', 'Internal SMTP fixture', 'Internal fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ) );
		$this->assertFileExists( $directory . '/smtp.jsonl', 'An internal message actually reaches the loopback server.' );
		$smtp = (string) file_get_contents( $directory . '/smtp.jsonl' );
		$this->assertStringContainsString( 'Internal SMTP fixture', $smtp );
		$this->assertStringContainsString( 'From: Linker <sales@sunriverinverter.com>', $smtp );
		$this->assertStringNotContainsString( 'X-Linker-Internal', $smtp );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );

		wp_mail( 'tester@example.test', 'Customer file fixture', 'Customer fixture.', array( 'From: Linker <sales@de-linker.com>' ) );
		$this->assertStringContainsString( 'Customer file fixture', (string) file_get_contents( $directory . '/mail.eml' ) );
		$this->assertStringContainsString( 'From: Linker <sales@de-linker.com>', (string) file_get_contents( $directory . '/mail.eml' ) );
		$this->assertSame( $smtp, (string) file_get_contents( $directory . '/smtp.jsonl' ), 'The customer message never entered SMTP.' );
		$this->assertSame( '', $GLOBALS['phpmailer']->Password );
		$this->assertSame( '', $GLOBALS['phpmailer']->Username );
	}

	/**
	 * Env values are literal, including INI comment and assignment characters.
	 */
	public function test_password_punctuation_reaches_the_local_authenticator(): void {
		$directory = $this->fixture( 'fake;#=password' );
		wp_mail( 'tester@example.test', 'Literal env fixture', 'Fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ) );
		$this->assertFileExists( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
	}

	/**
	 * An auth failure must deliver immediately and make the failure visible.
	 */
	public function test_auth_failure_falls_back_and_reports_the_last_outcome(): void {
		$directory = $this->fixture();
		$file      = $directory . '/smtp.env';
		file_put_contents( $file, str_replace( 'fake-password', 'wrong-test-password', (string) file_get_contents( $file ) ) );
		$marker = self::newest_mail_job();
		$before = time();
		wp_mail( 'tester@example.test', 'Auth fallback fixture', 'Fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ) );
		$this->assertFileExists( $directory . '/mail.eml' );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$outcome = ( new \Linker\Commerce\Mail\SmtpOutcome() )->last();
		$this->assertNotNull( $outcome );
		$this->assertSame( 'failure', $outcome['status'] );
		$this->assertSame( 'smtp_failure', $outcome['reason'] );
		$this->assertGreaterThanOrEqual( $before, $outcome['at'] );
		$block = new \Linker\Commerce\Health\InternalMail( new InternalSmtp( $file ) );
		$this->assertSame( 'The last SMTP attempt failed.', $block->entries()[0]['label'] );
		$locale_switch = new LocaleSwitch();
		$locale_switch->to( 'de_DE_formal' );
		try {
			$this->assertSame( 'Der letzte SMTP-Versuch ist fehlgeschlagen.', $block->entries()[0]['label'] );
		} finally {
			$locale_switch->back();
		}
		$this->assertStringNotContainsString( 'wrong-test-password', (string) wp_json_encode( $outcome ) );
		$this->assertCount( 2, json_decode( (string) get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true )['entries'] );
	}

	/**
	 * TLS mode is configuration, and the shared mailer returns to native defaults.
	 */
	public function test_configured_encryption_and_reset_defaults(): void {
		$directory = $this->fixture();
		$file      = $directory . '/smtp.env';
		file_put_contents( $file, (string) file_get_contents( $file ) . "LINKER_SMTP_SECURE=ssl\n" );
		$mailer       = $GLOBALS['phpmailer'];
		$mailer->From = 'sales@sunriverinverter.com';
		$smtp         = new InternalSmtp( $file );
		$smtp->configure( $mailer, true );
		$this->assertSame( 'ssl', $mailer->SMTPSecure, 'Loopback does not select an encryption exception.' );
		$smtp->reset( $mailer );
		$this->assertSame( 25, $mailer->Port, 'PHPMailer native default.' );
		$this->assertTrue( $mailer->SMTPAutoTLS );
	}

	/**
	 * A mismatched From falls back without changing the original sender.
	 */
	public function test_mismatched_sender_falls_back_with_a_fixed_reason(): void {
		$directory = $this->fixture();
		$marker    = self::newest_mail_job();
		wp_mail( 'tester@example.test', 'Mismatched sender fixture', 'Fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@de-linker.com>' ) );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertStringContainsString( 'From: Linker <sales@de-linker.com>', (string) file_get_contents( $directory . '/mail.eml' ) );
		$last = ( new \Linker\Commerce\Mail\SmtpOutcome() )->last();
		$this->assertNotNull( $last );
		$this->assertSame( 'identity_mismatch', $last['reason'] );
	}

	/**
	 * A failed authenticated attempt keeps its marker and retries through SMTP.
	 */
	public function test_retry_redirection_throttle_and_secret_free_diagnostics(): void {
		$directory = $this->fixture( 'fake-password', 1 );
		$file      = $directory . '/smtp.env';
		file_put_contents( $file, str_replace( 'fake-password', 'wrong-test-password', (string) file_get_contents( $file ) ) );
		$lines = array();
		$log   = static function ( string $line ) use ( &$lines ): string {
			$lines[] = $line;
			return $line;
		};
		add_filter( 'woocommerce_logger_log_message', $log );
		$this->later(
			static function () use ( $log ): void {
				remove_filter( 'woocommerce_logger_log_message', $log );
			}
		);
		$test_mode = get_option( TestMode::OPTION );
		update_option( TestMode::OPTION, 'tester@example.test' );
		$this->later(
			static function () use ( $test_mode ): void {
				if ( false === $test_mode ) {
					delete_option( TestMode::OPTION );
				} else {
					update_option( TestMode::OPTION, $test_mode );
				}
			}
		);
		$option_writes = array();
		$record_option = static function ( $value, string $name ) use ( &$option_writes ) {
			$option_writes[ $name ] = $value;
			return $value;
		};
		add_filter( 'pre_update_option', $record_option, 10, 2 );
		$this->later(
			static function () use ( $record_option ): void {
				remove_filter( 'pre_update_option', $record_option, 10 );
			}
		);
		$marker = self::newest_mail_job();
		wp_mail( 'internal@example.test', 'Retry fixture', 'Retry fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>', 'Bcc: copy@example.test' ) );
		$ids = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $ids );
		// A successful retry deletes its post, so the base cleanup can no longer
		// discover it. Keep this test's ID to remove its manually fired actions.
		$this->later(
			static function () use ( $ids ): void {
				as_unschedule_all_actions( Outbox::HOOK, array( $ids[0] ), Outbox::GROUP );
			}
		);
		$job = ( new JobStore() )->load( $ids[0] );
		$this->assertNotNull( $job );
		$this->assertTrue( $job['message']->is_internal() );
		$this->assertSame( array( 'internal@example.test' ), $job['message']->to );
		$this->assertContains( 'Bcc: copy@example.test', $job['message']->headers );
		$this->assertSame( 'Internal notification delivery failed.', get_post_meta( $ids[0], '_linker_mail_error', true ) );
		$this->assertStringNotContainsString( 'wrong-test-password', implode( "\n", $lines ) );
		$this->assertStringNotContainsString( 'wrong-test-password', (string) wp_json_encode( get_post_meta( $ids[0] ) ) );
		$this->assertSame( '', $GLOBALS['phpmailer']->Password, 'Failure clears authentication too.' );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		file_put_contents( $file, str_replace( 'wrong-test-password', 'fake-password', (string) file_get_contents( $file ) ) );
		// #297 keeps the existing site quota even for SMTP: a full window queues the retry.
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		/**
		 * The existing Outbox retry hook, invoked as Action Scheduler invokes it.
		 *
		 * @since 0.2.0
		 */
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $ids[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- this plugin's hook constant.
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		/**
		 * The existing Outbox retry hook, invoked as Action Scheduler invokes it.
		 *
		 * @since 0.2.0
		 */
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $ids[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- this plugin's hook constant.
		$this->assertNull( ( new JobStore() )->load( $ids[0] ) );
		$this->assertCount( 1, (array) file( $directory . '/smtp.jsonl', FILE_IGNORE_NEW_LINES ) );
		$message = json_decode( (string) file_get_contents( $directory . '/smtp.jsonl' ), true );
		$this->assertSame( array( 'RCPT TO:<tester@example.test>' ), $message['recipients'] );
		$this->assertStringNotContainsString( 'Bcc:', $message['message'] );
		$this->assertStringNotContainsString( 'fake-password', implode( "\n", $lines ) );
		$this->assertCount( 1, json_decode( (string) get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true )['entries'] );
		$this->assertNotEmpty( $option_writes, 'Observe actual quota writes through WordPress.' );
		$this->assertStringNotContainsString( 'fake-password', (string) wp_json_encode( $option_writes ) );
		$this->assertStringNotContainsString( 'LINKER_SMTP_', (string) wp_json_encode( $option_writes ) );
		$last = ( new \Linker\Commerce\Mail\SmtpOutcome() )->last();
		$this->assertNotNull( $last );
		$this->assertSame( 'success', $last['status'] );
		$this->assertSame( array(), ( new \Linker\Commerce\Health\InternalMail( new InternalSmtp( $file ) ) )->entries() );
	}

	/**
	 * Missing configuration falls back to a file and is visible in EN and DE.
	 */
	public function test_missing_configuration_falls_back_and_reports_once_per_digest(): void {
		$directory = $this->fixture();
		unlink( $directory . '/smtp.env' );
		foreach ( array(
			'en_US'        => 'Internal mail not authenticated.',
			'de_DE_formal' => 'Interne E-Mails sind nicht authentifiziert.',
		) as $locale => $warning ) {
			$locale_switch = new LocaleSwitch();
			$locale_switch->to( $locale );
			try {
				$block = new \Linker\Commerce\Health\InternalMail( new InternalSmtp( $directory . '/smtp.env' ) );
				$this->assertCount( 1, $block->entries() );
				$this->assertSame( $warning, $block->entries()[0]['label'] );
				WC()->mailer();
				$plugin = WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php';
				$body   = wc_get_template_html(
					'emails/linker-digest.php',
					array(
						'email_heading'      => 'Digest fixture',
						'additional_content' => '',
						'sent_to_admin'      => true,
						'plain_text'         => false,
						'email'              => new \Linker\Commerce\Digest\DigestEmail( $plugin, new \Linker\Commerce\Settings\Options() ),
						'blocks'             => array( $block ),
					),
					'',
					dirname( $plugin ) . '/templates/'
				);
				$this->assertSame( 1, substr_count( $body, $warning ), 'The real digest template renders the warning once.' );
				wp_mail( 'tester@example.test', 'Fallback fixture', $block->entries()[0]['label'], array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ) );
			} finally {
				$locale_switch->back();
			}
		}
		$this->assertFileExists( $directory . '/mail.eml' );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$blocks = ( new \Linker\Commerce\Digest\Blocks( new JobStore() ) )->all();
		$this->assertCount( 1, array_filter( $blocks, static fn ( \Linker\Commerce\Digest\Block $block ): bool => 'internal_mail' === $block->id() ) );
	}

	/**
	 * The actual daily digest survives an SMTP authentication outage.
	 */
	public function test_digest_is_delivered_by_fallback_after_auth_failure(): void {
		$directory = $this->fixture();
		$file      = $directory . '/smtp.env';
		file_put_contents( $file, str_replace( 'fake-password', 'wrong-test-password', (string) file_get_contents( $file ) ) );
		WC()->mailer();
		$email = new \Linker\Commerce\Digest\DigestEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new \Linker\Commerce\Settings\Options() );
		$email->send_report( array( new \Linker\Commerce\Health\InternalMail( new InternalSmtp( $file ) ) ) );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertStringContainsString( 'Daily digest', (string) file_get_contents( $directory . '/mail.eml' ) );
		$this->assertStringContainsString( 'To: tester@example.test', (string) file_get_contents( $directory . '/mail.eml' ) );
		$last = ( new \Linker\Commerce\Mail\SmtpOutcome() )->last();
		$this->assertNotNull( $last );
		$this->assertSame( 'failure', $last['status'] );
	}

	/**
	 * Only authorized staff can read configuration status, never config values.
	 */
	public function test_staff_rest_readback_has_no_credentials(): void {
		$before = get_option( \Linker\Commerce\Mail\CapacityHealth::OPTION );
		$this->later(
			static function () use ( $before ): void {
				false === $before ? delete_option( \Linker\Commerce\Mail\CapacityHealth::OPTION ) : update_option( \Linker\Commerce\Mail\CapacityHealth::OPTION, $before, false );
			}
		);
		\Linker\Commerce\Mail\CapacityHealth::failed();
		$directory = $this->fixture();
		$server    = rest_get_server();
		$health    = new \Linker\Commerce\Mail\SmtpHealth( new InternalSmtp( $directory . '/smtp.env' ) );
		$health->register_routes();
		$this->later(
			static function (): void {
				( new \Linker\Commerce\Mail\SmtpHealth() )->register_routes();
			}
		);
		wp_set_current_user( 0 );
		$this->assertSame( 401, $server->dispatch( new \WP_REST_Request( 'GET', '/linker/v1/mail-health' ) )->get_status() );
		wp_set_current_user( 1 );
		$response = $server->dispatch( new \WP_REST_Request( 'GET', '/linker/v1/mail-health' ) );
		$this->assertSame( 200, $response->get_status() );
		$data = $response->get_data();
		$this->assertTrue( $data['smtp_configured'] );
		$this->assertSame( 'SMTP configured', $data['label'] );
		$this->assertSame( array( 'smtp_configured', 'label', 'last_outcome', 'capacity_failure' ), array_keys( $data ) );
		$this->assertSame( array( 'at', 'reason' ), array_keys( $data['capacity_failure'] ) );
		$this->assertIsInt( $data['capacity_failure']['at'] );
		$this->assertSame( 'notification_not_accepted', $data['capacity_failure']['reason'] );
		$this->assertStringNotContainsString( 'fake-password', (string) wp_json_encode( $data ) );
	}

	/**
	 * Start a test-owned loopback sink and configure a fake server file.
	 *
	 * @param string $password      Fake password accepted by the local sink.
	 * @param int    $mail_failures Number of initial file deliveries to reject.
	 */
	private function fixture( string $password = 'fake-password', int $mail_failures = 0 ): string {
		$previous_to     = get_option( TestMode::OPTION );
		$previous_digest = get_option( 'linker_commerce_team_locale' );
		update_option( 'linker_commerce_team_locale', 'en_US', false );
		$this->later(
			static function () use ( $previous_digest ): void {
				if ( false !== $previous_digest ) {
					update_option( 'linker_commerce_team_locale', $previous_digest, false );
				}
			}
		);
		update_option( TestMode::OPTION, 'tester@example.test' );
		$this->later(
			static function () use ( $previous_to ): void {
				if ( false === $previous_to ) {
					delete_option( TestMode::OPTION ); } else {
								update_option( TestMode::OPTION, $previous_to, false ); }
			}
		);
		$previous_outcome = get_option( 'linker_commerce_internal_smtp_outcome' );
		delete_option( 'linker_commerce_internal_smtp_outcome' );
		$this->later(
			static function () use ( $previous_outcome ): void {
				if ( false === $previous_outcome ) {
					delete_option( 'linker_commerce_internal_smtp_outcome' ); } else {
								update_option( 'linker_commerce_internal_smtp_outcome', $previous_outcome, false ); }
			}
		);
		$directory = sys_get_temp_dir() . '/linker-smtp-' . self::tag();
		mkdir( $directory );
		$this->later(
			static function () use ( $directory ): void {
				$files = glob( $directory . '/*' );
				foreach ( false === $files ? array() : $files as $file ) {
					unlink( $file );
				}
				rmdir( $directory );
			}
		);
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- test-owned loopback fixture, never production.
		$process = proc_open(
			array( 'python3', dirname( __DIR__, 2 ) . '/fixtures/smtp_sink.py', $directory . '/smtp.jsonl', $password ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'pipe', 'w' ),
				2 => array( 'file', $directory . '/sink.log', 'a' ),
			),
			$pipes
		);
		$this->assertIsResource( $process );
		$this->later(
			static function () use ( $process, $pipes ): void {
				proc_terminate( $process );
				foreach ( $pipes as $pipe ) {
					fclose( $pipe );
				}
				proc_close( $process );
			}
		);
		// Fixture startup is bounded by the health monitor's local test timeout.
		stream_set_timeout( $pipes[1], (int) \Linker\Commerce\Health\Monitor::TIMEOUT_SECONDS );
		$port = (int) fgets( $pipes[1] );
		$this->assertGreaterThan( 0, $port );
		file_put_contents( $directory . '/smtp.env', "LINKER_SMTP_HOST=127.0.0.1\nLINKER_SMTP_PORT={$port}\nLINKER_SMTP_USER=sales@sunriverinverter.com\nLINKER_SMTP_PASS={$password}\nLINKER_SMTP_SECURE=\n" );

		$this->install_outbox( new InternalSmtp( $directory . '/smtp.env' ), $directory, $mail_failures );
		return $directory;
	}

	/** Existing unlabelled attempts do not throttle the verified SMTP plan as PHP. */
	public function test_smtp_succeeds_after_legacy_php_budget_is_full(): void {
		$directory = $this->fixture();
		$legacy    = array_fill( 0, Throttle::PER_DAY, time() - 120 );
		update_option( Throttle::OPTION, $legacy, false );
		wp_mail( 'original@example.test', 'Real internal capacity fixture', 'Fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ) );
		$this->assertFileExists( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
		$entries = json_decode( get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true )['entries'];
		$this->assertCount( 81, array_filter( $entries, static fn ( array $entry ): bool => Throttle::SMTP === $entry['transport'] ) );
		$this->assertCount( 80, array_filter( $entries, static fn ( array $entry ): bool => Throttle::PHP === $entry['transport'] ) );
		$this->assertStringContainsString( 'RCPT TO:<tester@example.test>', (string) file_get_contents( $directory . '/smtp.jsonl' ) );
	}

	/** Failed SMTP cannot use a full PHP pool; recovery retries only the original job. */
	public function test_smtp_failure_php_full_then_recovered_smtp(): void {
		$directory = $this->fixture();
		$file      = $directory . '/smtp.env';
		file_put_contents( $file, str_replace( 'fake-password', 'wrong-test-password', (string) file_get_contents( $file ) ) );
		$legacy = array_fill( 0, Throttle::PER_DAY, time() - 120 );
		update_option( Throttle::OPTION, $legacy, false );
		$marker = self::newest_mail_job();
		$before = time();
		wp_mail( 'original@example.test', 'Failed channel fixture', 'Original fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ) );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$ids = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $ids );
		$jobs = new JobStore();
		$job  = $jobs->load( $ids[0] );
		$this->assertNotNull( $job );
		$this->assertSame( 1, $job['attempts'] );
		$this->assertSame( array( 'original@example.test' ), $job['message']->to );
		$scheduled = as_next_scheduled_action( Outbox::HOOK, array( $ids[0] ), Outbox::GROUP );
		$this->assertIsInt( $scheduled );
		$this->assertEqualsWithDelta( $before + Outbox::RETRY_DELAYS[0], $scheduled, 3, 'PHP exhaustion must not delay the recovered SMTP channel for a day.' );
		file_put_contents( $file, str_replace( 'wrong-test-password', 'fake-password', (string) file_get_contents( $file ) ) );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $ids[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Fixed native Outbox retry.
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $ids[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Duplicate delivery owner must be idempotent.
		$this->assertNull( $jobs->load( $ids[0] ) );
		$lines = file( $directory . '/smtp.jsonl', FILE_IGNORE_NEW_LINES );
		$this->assertIsArray( $lines );
		$this->assertCount( 1, $lines );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
		$entries = json_decode( get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true )['entries'];
		$this->assertCount( 82, array_filter( $entries, static fn ( array $entry ): bool => Throttle::SMTP === $entry['transport'] ) );
		$this->assertCount( 80, array_filter( $entries, static fn ( array $entry ): bool => Throttle::PHP === $entry['transport'] ) );
		as_unschedule_all_actions( Outbox::HOOK, array( $ids[0] ), Outbox::GROUP );
	}

	/** No configured SMTP and a full PHP pool remains queued without claiming delivery. */
	public function test_unavailable_smtp_and_full_php_does_not_claim_a_send(): void {
		$directory = $this->fixture();
		unlink( $directory . '/smtp.env' );
		$legacy = array_fill( 0, Throttle::PER_DAY, time() - 120 );
		update_option( Throttle::OPTION, $legacy, false );
		$marker = self::newest_mail_job();
		wp_mail( 'original@example.test', 'No channel fixture', 'Fixture.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ) );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$ids = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $ids );
		$job = ( new JobStore() )->load( $ids[0] );
		$this->assertNotNull( $job );
		$this->assertSame( 0, $job['attempts'], 'A capacity wait is not a failed transport attempt.' );
		$this->assertNull( ( new \Linker\Commerce\Mail\SmtpOutcome() )->last() );
		$this->assertSame( $legacy, get_option( Throttle::OPTION ) );
	}

	/** A trusted staff-restored original job can use the reserved SMTP capacity. */
	public function test_staff_release_can_use_reserved_smtp_slots_without_rewriting_message(): void {
		$directory = $this->fixture();
		$now       = time();
		$entries   = array_fill(
			0,
			Throttle::SMTP_PER_DAY - Throttle::SMTP_RESERVE,
			array(
				'time'      => $now - 120,
				'transport' => Throttle::SMTP,
			)
		);
		update_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION, wp_json_encode( array( 'entries' => $entries ) ), false );
		$jobs    = new JobStore();
		$message = new Message( array( 'original@example.test' ), 'Staff-restored fixture', 'Original body.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ), array() );
		$id      = $jobs->create( $message );
		$jobs->promote( $id );
		$readback = $jobs->load( $id );
		$this->assertNotNull( $readback );
		$this->assertSame( $message->to_array(), $readback['message']->to_array() );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Fixed native Outbox retry.
		$this->assertNull( $jobs->load( $id ) );
		$this->assertFileExists( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$entries = json_decode( get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true )['entries'];
		$this->assertCount( 361, $entries );
	}

	/** A bounded pending-review health notice can use reserve when ordinary SMTP is saturated. */
	public function test_pending_review_aggregate_uses_critical_reserve(): void {
		$directory = $this->fixture();
		$now       = time();
		$entries   = array_fill(
			0,
			Throttle::SMTP_PER_DAY - Throttle::SMTP_RESERVE,
			array(
				'time'      => $now - 120,
				'transport' => Throttle::SMTP,
			)
		);
		update_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION, wp_json_encode( array( 'entries' => $entries ) ), false );
		$previous = get_option( \Linker\Commerce\Health\ReviewReminder::OPTION );
		delete_option( \Linker\Commerce\Health\ReviewReminder::OPTION );
		$this->later(
			static function () use ( $previous ): void {
				false === $previous ? delete_option( \Linker\Commerce\Health\ReviewReminder::OPTION ) : update_option( \Linker\Commerce\Health\ReviewReminder::OPTION, $previous, false );
			}
		);
		$summary = new \Linker\Commerce\Health\ReviewSummary(
			static fn () => array(
				'count'  => 2,
				'oldest' => $now - 600,
				'url'    => admin_url( 'edit.php?post_type=shop_order' ),
			)
		);
		$marker  = self::newest_mail_job();
		( new \Linker\Commerce\Health\ReviewReminder( $summary ) )->tick();
		$ids = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $ids );
		$job = ( new JobStore() )->load( $ids[0] );
		$this->assertNotNull( $job );
		$this->assertTrue( $job['message']->critical );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $ids[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Fixed native Outbox retry.
		$this->assertFileExists( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$this->assertNull( ( new JobStore() )->load( $ids[0] ) );
		as_unschedule_all_actions( Outbox::HOOK, array( $ids[0] ), Outbox::GROUP );
	}

	/** Every real reminder attempt is bounded, including failed SMTP, failed PHP and retries. */
	public function test_reminder_transport_attempt_caps_preserve_other_critical_capacity(): void {
		$directory = $this->fixture( 'fake-password', 1 );
		$file      = $directory . '/smtp.env';
		file_put_contents( $file, str_replace( 'fake-password', 'wrong-test-password', (string) file_get_contents( $file ) ) );
		$now     = time();
		$entries = array();
		foreach ( array(
			Throttle::SMTP => 360,
			Throttle::PHP  => 64,
		) as $transport => $count ) {
			for ( $i = 0; $i < $count; ++$i ) {
				$entries[] = array(
					'time'      => $now - 300,
					'transport' => $transport,
					'origin'    => 'legacy',
				);
			}
		}
		$id = 1;
		foreach ( array(
			Throttle::SMTP => 21,
			Throttle::PHP  => 7,
		) as $transport => $count ) {
			for ( $i = 0; $i < $count; ++$i ) {
				$entries[] = array(
					'time'      => $now - 120,
					'transport' => $transport,
					'origin'    => 'attempt',
					'category'  => Message::REVIEW_REMINDER,
					'id'        => $id++,
				);
			}
		}
		update_option(
			\Linker\Commerce\Mail\OptionBudgetLedger::OPTION,
			wp_json_encode(
				array(
					'entries' => $entries,
					'next_id' => $id,
				)
			),
			false
		);
		$previous = get_option( \Linker\Commerce\Health\ReviewReminder::OPTION );
		update_option(
			\Linker\Commerce\Health\ReviewReminder::OPTION,
			wp_json_encode(
				array(
					'events' => array_fill( 0, 23, $now - 120 ),
					'active' => false,
					'job'    => 0,
				)
			),
			false
		);
		$this->later(
			static function () use ( $previous ): void {
				false === $previous ? delete_option( \Linker\Commerce\Health\ReviewReminder::OPTION ) : update_option( \Linker\Commerce\Health\ReviewReminder::OPTION, $previous, false );
			}
		);
		$summary = new \Linker\Commerce\Health\ReviewSummary(
			static fn () => array(
				'count'  => 1,
				'oldest' => $now - 300,
				'url'    => admin_url( 'edit.php?post_type=shop_order' ),
			)
		);
		$marker  = self::newest_mail_job();
		( new \Linker\Commerce\Health\ReviewReminder( $summary ) )->tick();
		$ids = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $ids );
		$jobs = new JobStore();
		$job  = $jobs->load( $ids[0] );
		$this->assertNotNull( $job );
		$this->assertSame( Message::REVIEW_REMINDER, $job['message']->category );
		$this->assertSame( Message::REVIEW_REMINDER, ( new TestMode() )->redirect( $job['message'] )->category );
		for ( $attempt = 1; $attempt <= 3; ++$attempt ) {
			/** This action is documented in Mail\Module::register(). */
			do_action( Outbox::HOOK, $ids[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Fixed native Outbox retry.
			$retry = $jobs->load( $ids[0] );
			$this->assertNotNull( $retry );
			$this->assertSame( $attempt, $retry['attempts'] );
			$this->assertSame( $job['message']->to_array(), $retry['message']->to_array() );
		}
		$state     = json_decode( get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true );
		$reminders = array_filter( $state['entries'], static fn ( array $entry ): bool => Message::REVIEW_REMINDER === ( $entry['category'] ?? '' ) );
		$this->assertCount( 24, array_filter( $reminders, static fn ( array $entry ): bool => Throttle::SMTP === $entry['transport'] ) );
		$this->assertCount( 8, array_filter( $reminders, static fn ( array $entry ): bool => Throttle::PHP === $entry['transport'] ) );
		$this->assertCount( 384, array_filter( $state['entries'], static fn ( array $entry ): bool => Throttle::SMTP === $entry['transport'] ) );
		$this->assertCount( 72, array_filter( $state['entries'], static fn ( array $entry ): bool => Throttle::PHP === $entry['transport'] ) );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $ids[0] ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Full category budget must retain the original job.
		$waiting = $jobs->load( $ids[0] );
		$this->assertNotNull( $waiting );
		$this->assertSame( 3, $waiting['attempts'], 'A category-cap wait does not consume a failure retry.' );
		$this->assertEquals( $state, json_decode( get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true ), 'Denied retries create no additional transport charge.' );
		$t = new Throttle( new \Linker\Commerce\Mail\OptionBudgetLedger(), new InternalSmtp( $file ) );
		$this->assertSame( $now - 120 + DAY_IN_SECONDS, $t->next_message_slot( $now, $job['message'] ) );
		$this->assertSame( $now, $t->next_slot( $now, Throttle::SMTP, true ) );
		$this->assertSame( $now, $t->next_slot( $now, Throttle::PHP, true ) );
		$t->next_message_slot( $now + DAY_IN_SECONDS, $job['message'] );
		$this->assertEquals( $state, json_decode( get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ), true ), 'Future category scheduling cannot refund old attempts.' );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		// An authenticated single-record staff release can still use the remaining capacity.
		$manual    = new Message( array( 'original@example.test' ), 'Manual critical recovery', 'Original message.', array( Message::INTERNAL_HEADER, 'From: Linker <sales@sunriverinverter.com>' ), array() );
		$manual_id = $jobs->create( $manual );
		$jobs->promote( $manual_id );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $manual_id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Trusted staff-restored critical original job.
		$this->assertNull( $jobs->load( $manual_id ) );
		$this->assertFileExists( $directory . '/mail.eml' );
		$this->assertStringContainsString( 'Manual critical recovery', (string) file_get_contents( $directory . '/mail.eml' ) );
		as_unschedule_all_actions( Outbox::HOOK, array( $manual_id ), Outbox::GROUP );
	}

	/**
	 * Replace only this process's Outbox hooks and mail capture, restoring both.
	 *
	 * @param InternalSmtp $smtp      Transport configured with fake values.
	 * @param string       $directory Local capture directory.
	 * @param int          $mail_failures Initial file deliveries to reject.
	 */
	private function install_outbox( InternalSmtp $smtp, string $directory, int $mail_failures = 0 ): void {
		$hooks = array();
		foreach ( array( 'pre_wp_mail', 'wp_mail_failed', 'phpmailer_init', Outbox::HOOK ) as $name ) {
			$hooks[ $name ] = isset( $GLOBALS['wp_filter'][ $name ] ) ? clone $GLOBALS['wp_filter'][ $name ] : null;
			remove_all_filters( $name );
		}
		$previous = $GLOBALS['phpmailer'] ?? null;
		$this->later(
			static function () use ( $hooks, $previous ): void {
				foreach ( $hooks as $name => $hook ) {
					if ( null === $hook ) {
						unset( $GLOBALS['wp_filter'][ $name ] );
					} else {
						$GLOBALS['wp_filter'][ $name ] = $hook;
					}
				}
				$GLOBALS['phpmailer'] = $previous;
			}
		);
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/PHPMailer/PHPMailer.php';
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/PHPMailer/SMTP.php';
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/PHPMailer/Exception.php';
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/class-wp-phpmailer.php';
		$GLOBALS['phpmailer'] = new class( $directory, $mail_failures ) extends WP_PHPMailer {
			/**
			 * Exceptions match WordPress's normal mailer.
			 *
			 * @param string $directory Local capture directory.
			 * @param int    $mail_failures Initial file deliveries to reject.
			 */
			public function __construct( private readonly string $directory, private int $mail_failures ) {
				parent::__construct( true );
			}

			/**
			 * Only the test-owned loopback connection may leave PHP; mail() is a file.
			 *
			 * @throws \RuntimeException When the test attempts a non-loopback connection.
			 * @throws \PHPMailer\PHPMailer\Exception On an injected local mail failure.
			 */
			public function postSend(): bool {
				if ( 'smtp' === $this->Mailer ) {
					if ( '127.0.0.1' !== $this->Host ) {
						throw new \RuntimeException( 'SMTP fixture refuses non-loopback hosts.' );
					}
					return parent::postSend();
				}
				if ( $this->mail_failures > 0 ) {
					--$this->mail_failures;
					throw new \PHPMailer\PHPMailer\Exception( 'Fake mail failure: wrong-test-password' );
				}
				file_put_contents( $this->directory . '/mail.eml', $this->getSentMIMEMessage(), FILE_APPEND );
				return true;
			}
		};
		$outbox               = new Outbox( new JobStore(), new Throttle( new \Linker\Commerce\Mail\OptionBudgetLedger(), $smtp ), new TestMode(), $smtp );
		add_filter( 'pre_wp_mail', array( $outbox, 'intercept' ), 10, 2 );
		add_action( 'wp_mail_failed', array( $outbox, 'remember_error' ) );
		add_action( 'phpmailer_init', array( $outbox, 'configure_mailer' ) );
		add_action( Outbox::HOOK, array( $outbox, 'retry' ) );
	}
}
