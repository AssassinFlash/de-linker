<?php
/**
 * The native Message-ID of a successful inquiry transport.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- native PHPMailer property names.

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Assessment\AuthorizationStore;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\SendAuthorization;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Mail\InternalSmtp;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;
use PHPMailer\PHPMailer\PHPMailer;
use WC_Order;

/**
 * One real inquiry, the loopback SMTP sink, and PHP mail captured to a file.
 *
 * @coversNothing
 */
final class MessageIdWitnessTest extends IntegrationTestCase {

	/**
	 * Classifier fixture for this test.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;

	/**
	 * Install the local classifier and hold the send quota until a test releases it.
	 */
	protected function setUp(): void {
		parent::setUp();
		foreach ( array( Queue::ENABLED, Queue::HEARTBEAT, 'linker_genie_url', Options::NOTIFY_FROM, Options::NOTIFY_TO ) as $name ) {
			$value = get_option( $name );
			$this->later(
				static function () use ( $name, $value ): void {
					false === $value ? delete_option( $name ) : update_option( $name, $value, false );
				}
			);
		}
		update_option( Options::NOTIFY_FROM, 'sales@sunriverinverter.com', false );
		update_option( Options::NOTIFY_TO, 'sales@sunriverinverter.com', false );
		delete_option( OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
	}

	/**
	 * SMTP success stores the sink's Message-ID; a reused ID still marks the other purpose delivered.
	 */
	public function test_smtp_success_binds_the_sent_id_without_duplicating_it(): void {
		$order  = $this->inquiry();
		$state  = $this->authorization->process( $order );
		$team   = (int) $state['jobs']['team']['id'];
		$stored = ( new JobStore() )->load( $team );
		$this->assertNotNull( $stored );
		$this->assertSame( 0, $stored['attempts'] );
		$hash    = SendAuthorization::message_hash( $stored['message'] );
		$receipt = ( new JobStore() )->load( (int) $state['jobs']['receipt']['id'] );
		$this->assertNotNull( $receipt );

		$directory = $this->transport();
		delete_option( Throttle::OPTION );
		delete_option( OptionBudgetLedger::OPTION );
		$logs = $this->capture_logs();
		$this->send( $team );

		$raw = $this->mime( (string) file_get_contents( $directory . '/smtp.jsonl' ) );
		$id  = $this->message_id( $raw );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$witness = $this->witness( $order->get_id(), 'team' );
		$this->assertSame( $order->get_id(), $witness['inquiry_id'] );
		$this->assertSame( 'team', $witness['purpose'] );
		$this->assertSame( $hash, $witness['message_sha256'] );
		$this->assertSame( 64, strlen( $witness['message_sha256'] ) );
		$this->assertSame( $id, $witness['message_id'] );
		$this->assertEqualsWithDelta( time(), $witness['at'], 5 );
		$this->assertArrayNotHasKey( 'witness', $this->job_state( $order->get_id(), 'receipt' ) );
		$this->assertStringNotContainsString( $id, implode( "\n", $logs->getArrayCopy() ) );
		$this->assertStringNotContainsString( 'Please contact us about project equipment.', (string) wp_json_encode( $witness ) );
		$this->assertSame( 1, preg_match_all( '/^Message-ID:/mi', $raw ) );
		$this->assertDoesNotMatchRegularExpression( '/^X-Linker-Message/mi', $raw );
		$this->assertStringNotContainsString( $id, (string) wp_json_encode( $order->get_meta_data() ) );

		$before = $witness;
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $team ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- The registered Outbox retry.
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $team ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- A repeated retry must not send again.
		$this->assertSame( $before, $this->witness( $order->get_id(), 'team' ) );
		$lines = file( $directory . '/smtp.jsonl', FILE_IGNORE_NEW_LINES );
		$this->assertIsArray( $lines );
		$this->assertCount( 1, $lines );

		SendAuthorization::delivered( $receipt['message'], (int) $state['jobs']['receipt']['id'], $id );
		$after = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $after );
		$this->assertArrayNotHasKey( 'witness', $after['jobs']['receipt'] );
		$this->assertArrayHasKey( 'delivered_at', $after['jobs']['receipt'] );
		$this->assertIsInt( $after['jobs']['receipt']['delivered_at'] );
		$this->assertSame( $before, $after['jobs']['team']['witness'] );

		$altered = new Message(
			$receipt['message']->to,
			$receipt['message']->subject,
			$receipt['message']->body . ' altered',
			$receipt['message']->headers,
			$receipt['message']->attachments,
			false,
			Message::STANDARD,
			$receipt['message']->origin
		);
		SendAuthorization::delivered( $altered, (int) $state['jobs']['receipt']['id'], '<other-purpose@example.test>' );
		$this->assertSame( $after['jobs']['receipt'], $this->job_state( $order->get_id(), 'receipt' ) );

		SendAuthorization::erase( $order );
		$erased = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $erased );
		$this->assertStringNotContainsString( $id, (string) wp_json_encode( $erased ) );
	}

	/**
	 * Erasure wins over a transport result that arrives afterwards.
	 */
	public function test_late_delivery_does_not_restore_an_erased_authorization(): void {
		$order  = $this->inquiry();
		$state  = $this->authorization->process( $order );
		$team   = (int) $state['jobs']['team']['id'];
		$stored = ( new JobStore() )->load( $team );
		$this->assertNotNull( $stored );
		$this->assertSame( 'normal', $state['status'] );
		$this->assertSame( SendAuthorization::message_hash( $stored['message'] ), $state['jobs']['team']['hash'] );
		$this->assertSame( $order->get_id(), \Linker\Commerce\Mail\NotificationHold::inquiry( $team ) );
		$this->assertArrayNotHasKey( 'delivered_at', $state['jobs']['team'] );
		$message = $stored['message'];
		$id      = '<late-transport@example.test>';

		SendAuthorization::erase( $order );
		$erased = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $erased );
		$this->assertSame( 'erased', $erased['status'] );

		SendAuthorization::delivered( $message, $team, $id );

		$after = AuthorizationStore::read( $order->get_id() );
		$this->assertIsArray( $after );
		$this->assertSame( 'erased', $after['status'] );
		$this->assertArrayNotHasKey( 'delivered_at', $after['jobs']['team'] );
		$this->assertArrayNotHasKey( 'witness', $after['jobs']['team'] );
		$this->assertStringNotContainsString( $id, (string) wp_json_encode( $after ) );
	}

	/**
	 * A failed SMTP attempt writes nothing; the PHP fallback stores only its own sent ID.
	 */
	public function test_php_fallback_stores_only_the_successful_message_id(): void {
		$order  = $this->inquiry();
		$state  = $this->authorization->process( $order );
		$team   = (int) $state['jobs']['team']['id'];
		$stored = ( new JobStore() )->load( $team );
		$this->assertNotNull( $stored );
		$hash = SendAuthorization::message_hash( $stored['message'] );

		$directory = $this->transport();
		file_put_contents( $directory . '/smtp.env', str_replace( 'fake-password', 'wrong-test-password', (string) file_get_contents( $directory . '/smtp.env' ) ) );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() - 120 ), false );
		$failed = array();
		$watch  = static function () use ( &$failed ): void {
			$mailer = $GLOBALS['phpmailer'] ?? null;
			if ( $mailer instanceof PHPMailer && '' !== $mailer->getLastMessageID() ) {
				$failed[] = $mailer->getLastMessageID();
			}
		};
		add_action( 'wp_mail_failed', $watch );
		$this->later(
			static function () use ( $watch ): void {
				remove_action( 'wp_mail_failed', $watch );
			}
		);
		$this->send( $team );
		$this->assertArrayNotHasKey( 'witness', $this->job_state( $order->get_id(), 'team' ) );
		$this->assertArrayNotHasKey( 'delivered_at', $this->job_state( $order->get_id(), 'team' ) );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertFileDoesNotExist( $directory . '/mail.eml' );
		$this->assertNotNull( ( new JobStore() )->load( $team ) );

		delete_option( Throttle::OPTION );
		delete_option( OptionBudgetLedger::OPTION );
		$this->send( $team );
		$raw     = (string) file_get_contents( $directory . '/mail.eml' );
		$id      = $this->message_id( $raw );
		$witness = $this->witness( $order->get_id(), 'team' );
		$this->assertSame( $id, $witness['message_id'] );
		$this->assertSame( $hash, $witness['message_sha256'] );
		$this->assertSame( 'team', $witness['purpose'] );
		$this->assertSame( $order->get_id(), $witness['inquiry_id'] );
		$this->assertFileDoesNotExist( $directory . '/smtp.jsonl' );
		$this->assertDoesNotMatchRegularExpression( '/^X-Linker-Message/mi', $raw );
		foreach ( $failed as $earlier ) {
			if ( $earlier !== $id ) {
				$this->assertNotSame( $earlier, $witness['message_id'] );
			}
		}
		$this->assertSame( $id, $this->message_id( $raw ), 'The witness is the fallback file, not an earlier SMTP header.' );
	}

	/**
	 * A received inquiry whose notifications stay queued.
	 */
	private function inquiry(): WC_Order {
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic Alex',
				'email'   => self::TESTER,
				'company' => 'Example Solar',
				'message' => 'Please contact us about project equipment.',
				'consent' => '1',
				'lang'    => 'en',
			)
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->message( $details );
		$this->assertInstanceOf( WC_Order::class, $order );
		$id = $order->get_id();
		$this->later(
			static function () use ( $id ): void {
				as_unschedule_all_actions( Queue::PROCESS, array( $id ), Outbox::GROUP );
				as_unschedule_all_actions( Queue::EXPIRE, array( $id ), Outbox::GROUP );
				$record = wc_get_order( $id );
				if ( $record instanceof WC_Order ) {
					$record->delete( true );
				}
			}
		);
		return $order;
	}

	/**
	 * Replace the site outbox with a loopback SMTP sink and a file mailer.
	 */
	private function transport(): string {
		$directory = sys_get_temp_dir() . '/linker-message-id-' . self::tag();
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
		$pipes   = array();
		$process = proc_open( // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Test-owned loopback, never production.
			array( 'python3', dirname( __DIR__, 2 ) . '/fixtures/smtp_sink.py', $directory . '/smtp.jsonl', 'fake-password' ),
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
		stream_set_timeout( $pipes[1], 5 );
		$port = (int) fgets( $pipes[1] );
		$this->assertGreaterThan( 0, $port );
		file_put_contents( $directory . '/smtp.env', "LINKER_SMTP_HOST=127.0.0.1\nLINKER_SMTP_PORT={$port}\nLINKER_SMTP_USER=sales@sunriverinverter.com\nLINKER_SMTP_PASS=fake-password\nLINKER_SMTP_SECURE=\n" );

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
		$GLOBALS['phpmailer'] = new class( $directory ) extends \WP_PHPMailer {
			/**
			 * Exceptions match WordPress's mailer.
			 *
			 * @param string $directory Capture directory.
			 */
			public function __construct( private readonly string $directory ) {
				parent::__construct( true );
			}

			/**
			 * SMTP stays on the loopback sink; PHP mail is the captured file.
			 *
			 * @throws \RuntimeException When SMTP leaves the loopback.
			 */
			public function postSend(): bool {
				if ( 'smtp' === $this->Mailer ) {
					if ( '127.0.0.1' !== $this->Host ) {
						throw new \RuntimeException( 'SMTP fixture refuses non-loopback hosts.' );
					}
					return parent::postSend();
				}
				file_put_contents( $this->directory . '/mail.eml', $this->getSentMIMEMessage() );
				return true;
			}
		};
		$outbox               = new Outbox( new JobStore(), new Throttle(), new TestMode(), new InternalSmtp( $directory . '/smtp.env' ) );
		add_filter( 'pre_wp_mail', array( $outbox, 'intercept' ), 10, 2 );
		add_action( 'wp_mail_failed', array( $outbox, 'remember_error' ) );
		add_action( 'wp_mail_succeeded', array( $outbox, 'remember_message_id' ) );
		add_action( 'phpmailer_init', array( $outbox, 'configure_mailer' ) );
		add_action( Outbox::HOOK, array( $outbox, 'retry' ) );
		$this->later(
			static function () use ( $outbox ): void {
				remove_action( 'wp_mail_succeeded', array( $outbox, 'remember_message_id' ) );
			}
		);
		return $directory;
	}

	/**
	 * Run the registered retry once and drop its queue row's pending action.
	 *
	 * @param int $job Original job.
	 */
	private function send( int $job ): void {
		as_unschedule_all_actions( Outbox::HOOK, array( $job ), Outbox::GROUP );
		/** This action is documented in Mail\Module::register(). */
		do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- The registered Outbox retry.
		as_unschedule_all_actions( Outbox::HOOK, array( $job ), Outbox::GROUP );
	}

	/**
	 * Keep mail-log lines so the Message-ID can be shown to be absent.
	 *
	 * @return \ArrayObject<int,string>
	 */
	private function capture_logs(): \ArrayObject {
		$logs   = new \ArrayObject();
		$filter = static function ( $message, $level, $context ) use ( $logs ) {
			unset( $level );
			if ( is_array( $context ) && Outbox::LOG_SOURCE === ( $context['source'] ?? '' ) ) {
				$logs->append( (string) $message );
			}
			return $message;
		};
		add_filter( 'woocommerce_logger_log_message', $filter, 10, 3 );
		$this->later(
			static function () use ( $filter ): void {
				remove_filter( 'woocommerce_logger_log_message', $filter, 10 );
			}
		);
		return $logs;
	}

	/**
	 * The persisted witness for one purpose.
	 *
	 * @param int    $inquiry Inquiry ID.
	 * @param string $purpose Team or receipt.
	 * @return array<string,mixed>
	 */
	private function witness( int $inquiry, string $purpose ): array {
		$entry = $this->job_state( $inquiry, $purpose );
		$this->assertIsArray( $entry['witness'] ?? null );
		return $entry['witness'];
	}

	/**
	 * One purpose row from the private authorization option.
	 *
	 * @param int    $inquiry Inquiry ID.
	 * @param string $purpose Team or receipt.
	 * @return array<string,mixed>
	 */
	private function job_state( int $inquiry, string $purpose ): array {
		$state = AuthorizationStore::read( $inquiry );
		$this->assertIsArray( $state );
		$this->assertIsArray( $state['jobs'][ $purpose ] ?? null );
		return $state['jobs'][ $purpose ];
	}

	/**
	 * MIME body from a file capture or one SMTP sink JSON record.
	 *
	 * @param string $raw File contents.
	 */
	private function mime( string $raw ): string {
		if ( ! str_starts_with( ltrim( $raw ), '{' ) ) {
			return $raw;
		}
		$decoded = json_decode( $raw, true );
		$this->assertIsArray( $decoded );
		$this->assertIsString( $decoded['message'] ?? null );
		return $decoded['message'];
	}

	/**
	 * The Message-ID header of a captured message.
	 *
	 * @param string $raw MIME body.
	 */
	private function message_id( string $raw ): string {
		if ( 1 !== preg_match( '/^Message-ID:\s*(<[^<>\s]+@[^<>\s]+>)/mi', $raw, $match ) ) {
			$this->fail( 'Captured transport has no Message-ID header.' );
		}
		return $match[1];
	}
}
