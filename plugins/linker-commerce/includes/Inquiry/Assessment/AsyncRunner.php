<?php
/**
 * One-record wake-up through WooCommerce's native nonblocking HTTP runner.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Mail\NotificationHold;
use WC_Order;
use WP_Async_Request;

/** The durable queue remains authoritative when this opportunistic wake-up fails. */
final class AsyncRunner extends WP_Async_Request {
	public const ACTION = 'linker_inquiry_assessment_wake';
	public const META   = '_linker_inquiry_assessment_wake';

	/**
	 * Whether this instance handles its authenticated native HTTP callback.
	 *
	 * @var bool
	 */
	private bool $http_request = false;

	/**
	 * Native action prefix.
	 *
	 * @var string
	 */
	protected $prefix = 'linker';

	/**
	 * Native action name.
	 *
	 * @var string
	 */
	protected $action = 'inquiry_assessment_wake';

	/**
	 * Persist one capability before the native nonblocking loopback.
	 *
	 * @param int $id Existing inquiry; never a customer-supplied destination.
	 */
	public static function enqueue( int $id ): void {
		try {
			self::dispatch_record( $id );
		} catch ( \Throwable $error ) {
			// Persistence/randomness failure must leave the durable fallback alone.
			return;
		}
	}

	/**
	 * Issue and dispatch under the fail-open submit boundary.
	 *
	 * @param int $id Persisted inquiry.
	 */
	private static function dispatch_record( int $id ): void {
		$token = '';
		Lock::run(
			'wake-' . $id,
			static function () use ( $id, &$token ): void {
				$order = wc_get_order( $id );
				if ( ! $order instanceof WC_Order ) {
					return;
				}
				$order->read_meta_data( true );
				$data = Queue::data( $order );
				if ( NotificationHold::held( $order ) || array() === $data || $order->get_meta( self::META ) || 0 !== (int) ( $data['notification_job'] ?? 0 ) || microtime( true ) >= (float) $data['deadline'] ) {
					return;
				}
				$token = bin2hex( random_bytes( 32 ) );
				$wake  = array(
					'hash'      => hash( 'sha256', $token ),
					'expires'   => (float) $data['deadline'],
					'issued_at' => microtime( true ),
					'status'    => 'issued',
				);
				StructuredMeta::update( $order, self::META, $wake );
				$order->save_meta_data();
				$order->read_meta_data( true );
				if ( $order->get_meta( self::META ) !== $wake ) {
					$token = '';
				}
			}
		);
		if ( '' === $token ) {
			return;
		}
		try {
			$runner   = new self();
			$response = $runner->data(
				array(
					'inquiry' => $id,
					'token'   => $token,
				)
			)->dispatch();
			self::record(
				$id,
				array(
					'dispatched_at' => microtime( true ),
					'dispatch'      => is_wp_error( $response ) ? 'failed' : 'submitted',
				)
			);
		} catch ( \Throwable $error ) {
			// No retry or synchronous classification: the original durable work survives.
			self::record(
				$id,
				array(
					'dispatched_at' => microtime( true ),
					'dispatch'      => 'failed',
				)
			);
		}
	}

	/**
	 * No logged-in cookies or shared guest nonce authorizes model work.
	 *
	 * @return array<string, string> Fixed native AJAX action.
	 */
	protected function get_query_args(): array {
		return array( 'action' => self::ACTION );
	}

	/**
	 * Native WP_Async_Request defaults to 0.01 s; retain its bounded fire-and-forget.
	 * TLS verification stays on and redirects cannot leak the one-time capability.
	 *
	 * @return array<string, mixed> WordPress HTTP arguments.
	 */
	protected function get_post_args(): array {
		return array(
			'timeout'             => 0.01,
			'blocking'            => false,
			'redirection'         => 0,
			'sslverify'           => true,
			'cookies'             => array(),
			'body'                => $this->data,
			'limit_response_size' => 1024,
		);
	}

	/** Native callback; a record-specific single-use capability replaces its shared nonce. */
	public function maybe_handle(): void {
		if ( 'POST' !== ( $_SERVER['REQUEST_METHOD'] ?? '' ) ) { // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Fixed method equality only.
			wp_die( '', '', array( 'response' => 403 ) );
		}
		if ( PHP_SESSION_ACTIVE === session_status() ) {
			session_write_close();
		}
		$this->handle();
		wp_die();
	}

	/** Parse only the fixed record ID and capability; never accept classification input. */
	protected function handle(): void {
		// phpcs:disable WordPress.Security.NonceVerification -- Unpredictable one-use record capability is verified and consumed atomically below; guest WP nonces are not authorization.
		$value = isset( $_POST['inquiry'] ) && is_string( $_POST['inquiry'] ) ? sanitize_text_field( wp_unslash( $_POST['inquiry'] ) ) : '';
		$id    = strlen( $value ) <= 19 && ctype_digit( $value ) ? absint( $value ) : 0;
		$token = isset( $_POST['token'] ) && is_string( $_POST['token'] ) ? sanitize_text_field( wp_unslash( $_POST['token'] ) ) : '';
		// phpcs:enable
		$this->http_request = true;
		if ( ! $this->run( $id, $token ) ) {
			wp_die( '', '', array( 'response' => 403 ) );
		}
	}

	/**
	 * Atomically claim a single record, then call the existing sole consumer.
	 *
	 * @param int    $id Existing inquiry.
	 * @param string $token One-use server-generated capability.
	 */
	public function run( int $id, string $token ): bool {
		if ( $id <= 0 || 1 !== preg_match( '/\A[a-f0-9]{64}\z/D', $token ) ) {
			return false;
		}
		$claimed = false;
		Lock::run(
			'wake-' . $id,
			static function () use ( $id, $token, &$claimed ): void {
				$order = wc_get_order( $id );
				if ( ! $order instanceof WC_Order ) {
					return;
				}
				$order->read_meta_data( true );
				$wake = $order->get_meta( self::META );
				$data = Queue::data( $order );
				if ( ! is_array( $wake ) || 'issued' !== ( $wake['status'] ?? '' ) || ! is_string( $wake['hash'] ?? null ) || ! hash_equals( $wake['hash'], hash( 'sha256', $token ) ) || microtime( true ) >= (float) ( $wake['expires'] ?? 0 ) || (float) ( $wake['expires'] ?? 0 ) !== (float) ( $data['deadline'] ?? 0 ) || NotificationHold::held( $order ) || 0 !== (int) ( $data['notification_job'] ?? 0 ) ) {
					return;
				}
				$wake['status']     = 'claimed';
				$wake['claimed_at'] = microtime( true );
				unset( $wake['hash'] );
				StructuredMeta::update( $order, self::META, $wake );
				$order->save_meta_data();
				$order->read_meta_data( true );
				$claimed = $wake === $order->get_meta( self::META );
			}
		);
		if ( ! $claimed ) {
			return false;
		}
		// An abandoned caller must not kill this authenticated background worker.
		ignore_user_abort( true );
		if ( $this->http_request ) {
			$this->acknowledge();
		}
		// One additional dedicated worker, with zero wait; AS concurrency is unchanged.
		$ran = Lock::run( 'async-worker', static fn () => ( new Queue() )->process( $id ) );
		self::record(
			$id,
			array(
				'status'      => $ran ? 'consumer_returned' : 'busy',
				'finished_at' => microtime( true ),
			)
		);
		return true;
	}

	/** Acknowledge only an already-consumed capability before any model work. */
	private function acknowledge(): void {
		status_header( 202 );
		header( 'Content-Length: 0' );
		header( 'Connection: close' );
		wp_ob_end_flush_all();
		if ( function_exists( 'fastcgi_finish_request' ) ) {
			fastcgi_finish_request();
		} elseif ( function_exists( 'litespeed_finish_request' ) ) {
			litespeed_finish_request();
		} else {
			// Content-Length allows the native HTTP transport to finish on local PHP.
			flush();
		}
	}

	/**
	 * Add non-sensitive transport diagnostics without overwriting a concurrent claim.
	 *
	 * @param int                  $id Inquiry.
	 * @param array<string, mixed> $change Fixed diagnostic fields.
	 */
	private static function record( int $id, array $change ): void {
		Lock::run(
			'wake-' . $id,
			static function () use ( $id, $change ): void {
				$order = wc_get_order( $id );
				if ( $order instanceof WC_Order ) {
					$order->read_meta_data( true );
					$wake = $order->get_meta( self::META );
					if ( is_array( $wake ) ) {
						StructuredMeta::update( $order, self::META, array_merge( $wake, $change ) );
						$order->save_meta_data();
					}
				}
			}
		);
	}
}
