<?php
/**
 * Persistent global review capacity, independent of normal verified admission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Assessment\Lock;
use WC_Order;
use WP_Error;

/** Native options store only bounded HMAC references; Woo owns all content. */
final class IntakeStore {
	public const OPTION         = 'linker_public_review_capacity';
	private const MUTEX         = 'intake-capacity';
	private const ROW_LOCK_BUSY = 3572;
	/**
	 * Exact native serialized snapshot for compare-and-write within this edit.
	 *
	 * @var string|null
	 */
	private static ?string $snapshot = null;
	/**
	 * A missing option is a valid initial snapshot only inside a held edit.
	 *
	 * @var bool
	 */
	private static bool $editing = false;
	/**
	 * A nested native consumer joins the same locked snapshot, never a stale copy.
	 *
	 * @var array<string,mixed>|null
	 */
	private static ?array $active = null;
	// Initial operating allocation and separate lanes: docs/specs/542-safe-intake.md.
	public const CAPACITY = array(
		'verification' => 128,
		'campaign'     => 3,
		'individual'   => 16,
	);

	/**
	 * Serialize capacity decisions and first native save across DB connections.
	 *
	 * @param callable(array<string,mixed>&):(WC_Order|WP_Error|array<string,mixed>) $work Native work.
	 * @param int                                                                    $wait_seconds Optional bounded native business/mail wait; review stays zero.
	 * @param bool                                                                   $retry_row_lock Retry row contention inside a business first-save budget.
	 * @return WC_Order|WP_Error|array<string,mixed>
	 */
	public static function edit( callable $work, int $wait_seconds = 0, bool $retry_row_lock = false ): WC_Order|WP_Error|array {
		try {
			return \Linker\Commerce\Mail\ConnectionFence::run( static fn (): WC_Order|WP_Error|array => self::edit_native( $work, $wait_seconds, $retry_row_lock ) );
		} catch ( \Throwable $error ) {
			return new WP_Error( 'linker_intake_pending', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
		}
	}

	/**
	 * Hold the same connection policy through lock, native writes and unlock.
	 *
	 * @param callable(array<string,mixed>&):(WC_Order|WP_Error|array<string,mixed>) $work Native work.
	 * @param int                                                                    $wait_seconds Bounded native mutex wait.
	 * @param bool                                                                   $retry_row_lock Retry row contention inside a business first-save budget.
	 * @return WC_Order|WP_Error|array<string,mixed>
	 */
	private static function edit_native( callable $work, int $wait_seconds, bool $retry_row_lock ): WC_Order|WP_Error|array {
		if ( self::$editing && null !== self::$active ) {
			return $work( self::$active );
		}
		$deadline = microtime( true ) + $wait_seconds;
		do {
			$result = new WP_Error( 'linker_intake_busy', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
			$retry  = false;
			Lock::run(
				self::MUTEX,
				static function () use ( $work, &$result, &$retry ): void {
					$previous = self::$snapshot;
					$editing  = self::$editing;
					try {
						try {
							$raw = self::read();
						} catch ( \RuntimeException $error ) {
							if ( self::ROW_LOCK_BUSY === $error->getCode() ) {
								$retry = true;
								return;
							}
							throw $error;
						}
						$state = null === $raw ? array(
							'entries'        => array(),
							'campaign_count' => 0,
						) : maybe_unserialize( $raw );
						if ( ! is_array( $state ) || ! is_array( $state['entries'] ?? null ) || count( $state['entries'] ) > array_sum( self::CAPACITY ) ) {
							return;
						}
						self::$snapshot = $raw;
						self::$editing  = true;
						self::$active   =& $state;
						$result         = $work( $state );
					} catch ( \Throwable $error ) {
						// This mutex wrapper owns no transaction. Native consumers roll
						// back only their own transaction/savepoint before propagating.
						$result = self::pending();
					} finally {
						self::$snapshot = $previous;
						self::$editing  = $editing;
						self::$active   = null;
						self::clear_cache();
					}
				},
				max( 0, min( 1, (int) ceil( $deadline - microtime( true ) ) ) )
			);
			if ( ! $retry || ! $retry_row_lock ) {
				return $result;
			}
			if ( microtime( true ) >= $deadline ) {
				return self::pending();
			}
			// Release the named mutex while the transaction owner reaches its
			// final bind. Holding it here would invert the two lock owners.
			usleep( 10000 );
		} while ( true );
	}

	/**
	 * Verify the durable native option before allowing side effects.
	 *
	 * @param array<string,mixed> $state Bounded private registry.
	 * @throws \RuntimeException Storage/readback failure.
	 */
	public static function save( array $state ): void {
		global $wpdb;
		$encoded = maybe_serialize( $state );
		if ( ! self::$editing ) {
			throw new \RuntimeException( 'intake_capacity_unlocked_write' );
		}
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- The native serialized option needs a cache-free CAS under the connection-owned capacity mutex.
		if ( null === self::$snapshot ) {
			$written = $wpdb->query( $wpdb->prepare( "INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) SELECT %s, %s, 'off' WHERE IS_USED_LOCK(%s) = CONNECTION_ID()", self::OPTION, $encoded, self::lock_name() ) );
		} else {
			$written = $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value = %s, autoload = 'off' WHERE option_name = %s AND BINARY option_value = BINARY %s AND IS_USED_LOCK(%s) = CONNECTION_ID()", $encoded, self::OPTION, self::$snapshot, self::lock_name() ) );
		}
		// phpcs:enable
		if ( false === $written || ( self::$snapshot !== $encoded && 1 !== $written ) || self::read() !== $encoded ) {
			throw new \RuntimeException( 'intake_capacity_readback_failed' );
		}
		self::$snapshot = $encoded;
		self::clear_cache();
	}

	/**
	 * Read the authoritative option and connection ownership in one DB statement.
	 * Neither a stale positive cache nor WordPress's notoptions cache is consulted.
	 *
	 * @throws \RuntimeException Missing lock or database failure.
	 */
	private static function read(): ?string {
		global $wpdb;
		// NOWAIT also handles a prior owner whose outer transaction has not yet
		// committed after its connection mutex was released. CAS alone is safe
		// against excess, but would otherwise wait for the DB's long row timeout.
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Native option snapshot and mutex ownership must come from the same DB connection, without an object cache.
		$row = $wpdb->get_row( $wpdb->prepare( "SELECT (SELECT option_value FROM {$wpdb->options} WHERE option_name = %s FOR UPDATE NOWAIT) AS value, IS_USED_LOCK(%s) = CONNECTION_ID() AS owned", self::OPTION, self::lock_name() ), ARRAY_A );
		if ( ! is_array( $row ) || '1' !== (string) ( $row['owned'] ?? '' ) || '' !== $wpdb->last_error || ( null !== $row['value'] && ! is_string( $row['value'] ) ) ) {
			$handle = $wpdb->__get( 'dbh' );
			$errno  = $handle instanceof \mysqli ? (int) $handle->errno : 0;
			$error  = strtolower( $wpdb->last_error );
			if ( self::ROW_LOCK_BUSY === $errno || str_contains( $error, 'lock wait timeout' ) || str_contains( $error, 'could not be acquired immediately' ) ) {
				throw new \RuntimeException( 'intake_capacity_row_busy', self::ROW_LOCK_BUSY ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal control-flow code, never printed.
			}
			throw new \RuntimeException( 'intake_capacity_read_failed' );
		}
		return $row['value'];
	}

	/** One customer-visible generic failure; diagnostics stay in native logs. */
	private static function pending(): WP_Error {
		return new WP_Error( 'linker_intake_pending', __( 'The request status could not be confirmed. Your entries are still here. Please check before sending a new request.', 'linker-commerce' ) );
	}

	/** The existing Lock namespace is database/prefix/key scoped. */
	private static function lock_name(): string {
		global $wpdb;
		$database = isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) ? $wpdb->dbname : ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' );
		return 'linker-assessment-' . md5( $database . '/' . $wpdb->prefix . '/' . self::MUTEX );
	}

	/** Native option consumers must not retain a pre-initialization negative cache. */
	private static function clear_cache(): void {
		wp_cache_delete( self::OPTION, 'options' );
		wp_cache_delete( 'notoptions', 'options' );
		wp_cache_delete( 'alloptions', 'options' );
	}

	/**
	 * Native erasure also removes retry associations in the review registry.
	 *
	 * @throws \RuntimeException Busy storage makes erasure retryable.
	 *
	 * @param WC_Order $order Anonymized native order.
	 */
	public static function forget( WC_Order $order ): void {
		$done = Lock::run(
			'release-' . $order->get_id(),
			static function () use ( $order ): void {
				// Same order as staff release: record mutex, then capacity mutex.
				$result = self::edit(
					static function ( array &$state ) use ( $order ): array {
						$order->read_meta_data( true );
						$request = $order->get_meta( BusinessRecord::REQUEST );
						if ( \Linker\Commerce\Mail\Capacity::transaction_active() ) {
							throw new \RuntimeException( 'intake_erasure_transaction_unavailable' );
						}
						$transaction = new \Linker\Commerce\Mail\NativeTransaction();
						try {
							$order->update_meta_data( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED, 'yes' );
							$order->delete_meta_data( Intake::META );
							$order->delete_meta_data( Intake::LANE_META );
							$order->save_meta_data();
							$order->read_meta_data( true );
							if ( 'yes' !== $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) || $order->get_meta( Intake::META ) || $order->get_meta( Intake::LANE_META ) ) {
								throw new \RuntimeException( 'intake_erasure_readback_failed' );
							}
							foreach ( $state['entries'] as $id => $entry ) {
								if ( $order->get_id() === (int) ( $entry['order'] ?? 0 ) || $id === $request ) {
									unset( $state['entries'][ $id ] );
								}
							}
							self::save( $state );
							// Native erasure continues outside these locks. Its durable
							// tombstone already prevents any later notification capture.
							$transaction->commit();
							return array();
						} catch ( \Throwable $error ) {
							$transaction->rollback();
							throw $error;
						}
					}
				);
				if ( is_wp_error( $result ) ) {
					throw new \RuntimeException( 'intake_erasure_busy' );
				}
			},
			0,
			true
		);
		if ( ! $done ) {
			throw new \RuntimeException( 'intake_erasure_busy' );
		}
	}
	/**
	 * Verified-email privacy includes interrupted reservations with no native ID.
	 * Erasure strips links without refunding unresolved capacity.
	 *
	 * @param string[] $owners Trusted requester HMAC associations.
	 * @param bool     $erase Whether to strip requester associations.
	 * @return array<string,mixed>|WP_Error
	 */
	public static function privacy( array $owners, bool $erase ): array|WP_Error {
		$result = self::edit(
			static function ( array &$state ) use ( $owners, $erase ): array {
				$data = array();
				foreach ( $state['entries'] as $id => $entry ) {
					if ( array() === array_intersect( $owners, $entry['owners'] ?? array() ) ) {
						continue;
					}
					$data[] = array(
						'id'    => $id,
						'lane'  => $entry['lane'],
						'order' => $entry['order'],
						'at'    => $entry['at'],
					);
					if ( $erase ) {
						$state['entries'][ $id ]['owners']      = array();
						$state['entries'][ $id ]['fingerprint'] = '';
						$state['entries'][ $id ]['binding']     = '';
						$state['entries'][ $id ]['erased']      = true;
					}
				}
				if ( $erase && array() !== $data ) {
					self::save( $state );
				}
				return array(
					'data'    => $data,
					'removed' => $erase ? count( $data ) : 0,
				);
			}
		);
		return $result instanceof WP_Error || is_array( $result ) ? $result : new WP_Error( 'intake_privacy_unavailable' );
	}
}
