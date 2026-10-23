<?php
/**
 * One persistent, bounded native Outbox envelope (#568).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use Linker\Commerce\Protection\IntakeStore;
use WP_Error;

/** Held, failed and unknown reservations do not expire into free queue capacity. */
final class Capacity {
	// Adjustable operator allocations approved in #568; not physical DB sizes.
	public const LIMITS = array(
		'ordinary' => array(
			'count' => 192,
			'bytes' => 50331648,
		),
		'critical' => array(
			'count' => 64,
			'bytes' => 16777216,
		),
	);
	/** Current trusted producer scope; restored on every nested exit.
	 *
	 * @var string
	 */
	private static string $scope = '';
	// Completed operation receipts retain the native admission retry horizon.
	// Pending slots never expire. The registry cannot grow beyond this envelope.
	private const MAX_RESERVATIONS = 256;

	/**
	 * Server-only preflight before a native account/approval/reset side effect.
	 * Each producer must prove its maximum complete encoded Message size.
	 *
	 * @param string $native_operation Stable, server-owned native operation key.
	 * @param int    $count Maximum messages this operation may create.
	 * @param int    $max_bytes_per_message Proven complete encoded-message bound.
	 * @return array<string,mixed>|WP_Error Opaque scope; never a browser field.
	 */
	public static function reserve_critical( string $native_operation, int $count, int $max_bytes_per_message ): array|WP_Error {
		if ( '' === $native_operation || $count < 1 || $max_bytes_per_message < 1 || $count > self::LIMITS['critical']['count'] || $max_bytes_per_message > self::LIMITS['critical']['bytes'] ) {
			return self::problem();
		}
		$key    = hash_hmac( 'sha256', 'critical-mail|' . $native_operation, wp_salt( 'nonce' ) );
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $key, $count, $max_bytes_per_message ): array|WP_Error {
				self::initialize( $state );
				foreach ( $state['mail_capacity']['reservations'] as $token => $receipt ) {
					if ( 0 === $receipt['remaining'] && $receipt['closed'] < time() - DAY_IN_SECONDS ) {
						unset( $state['mail_capacity']['reservations'][ $token ] );
					}
				}
				$existing = $state['mail_capacity']['reservations'][ $key ] ?? null;
				if ( is_array( $existing ) ) {
					return (int) $existing['count'] === $count && (int) $existing['max_bytes'] === $max_bytes_per_message
						? array(
							'key'       => $key,
							'remaining' => $existing['remaining'],
						) : self::problem();
				}
				if ( count( $state['mail_capacity']['reservations'] ) >= self::MAX_RESERVATIONS || ! self::room( $state, 'critical', $count, $count * $max_bytes_per_message ) ) {
					return self::problem();
				}
				$state['mail_capacity']['reservations'][ $key ] = array(
					'count'     => $count,
					'remaining' => $count,
					'max_bytes' => $max_bytes_per_message,
					'closed'    => 0,
				);
				IntakeStore::save( $state );
				return array(
					'key'       => $key,
					'remaining' => $count,
				);
			},
			1
		);
		return is_array( $result ) || $result instanceof WP_Error ? $result : self::problem();
	}

	/**
	 * Bind only a trusted synchronous producer; restore a nested native caller.
	 *
	 * @param array<string,mixed>|string $reservation Server pre-reservation.
	 * @param callable                   $send Native producer, not a public callback.
	 * @return mixed Native outcome.
	 */
	public static function within( array|string $reservation, callable $send ): mixed {
		$previous    = self::$scope;
		self::$scope = is_string( $reservation ) ? $reservation : (string) ( $reservation['key'] ?? '' );
		try {
			return $send();
		} finally {
			self::$scope = $previous;
		}
	}

	/** Opaque current server producer; not a public authorization proof. */
	public static function current(): string {
		return self::$scope;
	}

	/**
	 * Only a native caller that proved no business side effect may cancel.
	 * A partially consumed, completed or unknown operation is never refunded.
	 *
	 * @param array<string,mixed>|string $reservation Server-owned reservation.
	 */
	public static function cancel_before_side_effect( array|string $reservation ): bool {
		$key    = is_string( $reservation ) ? $reservation : (string) ( $reservation['key'] ?? '' );
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $key ): array|WP_Error {
				$entry = $state['mail_capacity']['reservations'][ $key ] ?? null;
				if ( ! is_array( $entry ) || $entry['count'] !== $entry['remaining'] ) {
					return self::problem();
				}
				unset( $state['mail_capacity']['reservations'][ $key ] );
				IntakeStore::save( $state );
				return array();
			},
			1
		);
		return is_array( $result );
	}

	/**
	 * Return only a verified native job id, under the same count/byte decision.
	 *
	 * @param Message        $message Immutable message.
	 * @param callable():int $write Native JobStore first write and readback.
	 */
	public static function create( Message $message, callable $write ): int {
		$json = wp_json_encode( $message->to_array() );
		if ( ! is_string( $json ) ) {
			return 0;
		}
		$bytes  = strlen( $json );
		$pool   = $message->critical ? 'critical' : 'ordinary';
		$scope  = self::$scope;
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $write, $pool, $bytes, $scope ): array|WP_Error {
				self::initialize( $state );
				$reserved = '' !== $scope ? ( $state['mail_capacity']['reservations'][ $scope ] ?? null ) : null;
				if ( '' !== $scope && ( ! is_array( $reserved ) || 'critical' !== $pool || (int) $reserved['remaining'] < 1 || $bytes > (int) $reserved['max_bytes'] ) ) {
					return self::problem();
				}
				if ( null === $reserved && ! self::room( $state, $pool, 1, $bytes ) ) {
					return self::problem();
				}
				return self::transaction(
					static function () use ( &$state, $write, $pool, $bytes, $reserved, $scope ): array {
						$id = $write();
						if ( $id < 1 ) {
							throw new \RuntimeException( 'mail_capacity_native_write_failed' );
						}
						$state['mail_capacity']['entries'][ $id ] = array(
							'pool'  => $pool,
							'bytes' => $bytes,
						);
						if ( is_array( $reserved ) ) {
							--$state['mail_capacity']['reservations'][ $scope ]['remaining'];
							if ( 0 === $state['mail_capacity']['reservations'][ $scope ]['remaining'] ) {
								$state['mail_capacity']['reservations'][ $scope ]['closed'] = time();
							}
						}
						IntakeStore::save( $state );
						return array( 'job' => $id );
					}
				);
			},
			1
		);
		return is_array( $result ) ? (int) ( $result['job'] ?? 0 ) : 0;
	}

	/**
	 * Atomically move an existing held job, never release ordinary space first.
	 *
	 * @param int             $id Existing native job.
	 * @param callable():void $promote Verified native priority write/readback.
	 * @throws \RuntimeException The hold/release transaction must remain unchanged.
	 */
	public static function promote( int $id, callable $promote ): void {
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $id, $promote ): array|WP_Error {
				self::initialize( $state );
				$entry = $state['mail_capacity']['entries'][ $id ] ?? null;
				if ( ! is_array( $entry ) || ( 'critical' !== $entry['pool'] && ! self::room( $state, 'critical', 1, (int) $entry['bytes'] ) ) ) {
					return self::problem();
				}
				return self::transaction(
					static function () use ( &$state, $id, $promote ): array {
						$promote();
						$state['mail_capacity']['entries'][ $id ]['pool'] = 'critical';
						IntakeStore::save( $state );
						return array();
					}
				);
			},
			1
		);
		if ( $result instanceof WP_Error ) {
			throw new \RuntimeException( 'mail_critical_capacity_unavailable' );
		}
	}

	/**
	 * Release only after actual native deletion, not a failed/held/timed-out job.
	 *
	 * @param int           $id Native deleted job.
	 * @param \WP_Post|null $post Optional native deleted row, before cache cleanup.
	 */
	public static function deleted( int $id, ?\WP_Post $post = null ): void {
		if ( null !== $post && JobStore::POST_TYPE !== $post->post_type ) {
			return;
		}
		// WordPress fires deleted_post before its own cache cleanup.
		clean_post_cache( $id );
		if ( get_post( $id ) ) {
			return;
		}
		IntakeStore::edit(
			static function ( array &$state ) use ( $id ): array {
				if ( isset( $state['mail_capacity']['entries'][ $id ] ) ) {
					unset( $state['mail_capacity']['entries'][ $id ] );
					IntakeStore::save( $state );
				}
				return array();
			},
			1
		);
	}

	/**
	 * Existing private/failed/held jobs are debt; no old content is modified.
	 *
	 * @param array<string,mixed> $state Locked native registry.
	 * @throws \RuntimeException An existing job cannot be accounted for safely.
	 */
	private static function initialize( array &$state ): void {
		if ( isset( $state['mail_capacity'] ) ) {
			$capacity = $state['mail_capacity'];
			if ( ! is_array( $capacity ) || ! is_array( $capacity['entries'] ?? null ) || ! is_array( $capacity['reservations'] ?? null ) || count( $capacity['reservations'] ) > self::MAX_RESERVATIONS ) {
				throw new \RuntimeException( 'mail_capacity_invalid_state' );
			}
			foreach ( $capacity['entries'] as $id => $entry ) {
				if ( ! is_int( $id ) || $id < 1 || ! is_array( $entry ) || ! isset( self::LIMITS[ $entry['pool'] ?? '' ] ) || ! is_int( $entry['bytes'] ?? null ) || $entry['bytes'] < 1 ) {
					throw new \RuntimeException( 'mail_capacity_invalid_job' );
				}
			}
			foreach ( $capacity['reservations'] as $key => $entry ) {
				if ( ! is_string( $key ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $key ) || ! is_array( $entry ) || ! is_int( $entry['count'] ?? null ) || $entry['count'] < 1 || $entry['count'] > self::LIMITS['critical']['count'] || ! is_int( $entry['remaining'] ?? null ) || $entry['remaining'] < 0 || $entry['remaining'] > $entry['count'] || ! is_int( $entry['max_bytes'] ?? null ) || $entry['max_bytes'] < 1 || $entry['max_bytes'] > self::LIMITS['critical']['bytes'] || ! is_int( $entry['closed'] ?? null ) || $entry['closed'] < 0 ) {
					throw new \RuntimeException( 'mail_capacity_invalid_reservation' );
				}
			}
			return;
		}
		$state['mail_capacity'] = array(
			'entries'      => array(),
			'reservations' => array(),
		);
		$page                   = 1;
		do {
			$ids = get_posts(
				array(
					'post_type'      => JobStore::POST_TYPE,
					'post_status'    => array( 'private', 'draft', 'trash' ),
					'posts_per_page' => 100,
					'paged'          => $page,
					'orderby'        => 'ID',
					'order'          => 'ASC',
					'fields'         => 'ids',
				)
			);
			foreach ( $ids as $id ) {
				$raw     = get_post_meta( (int) $id, '_linker_mail_message', true );
				$decoded = is_string( $raw ) ? json_decode( $raw, true ) : null;
				$pool    = ( is_array( $decoded ) && true === ( $decoded['critical'] ?? false ) ) || ( new JobStore() )->critical( (int) $id ) ? 'critical' : 'ordinary';
				// An unreadable native job is never silently treated as zero space.
				if ( ! is_string( $raw ) || '' === $raw ) {
					throw new \RuntimeException( 'mail_capacity_unreadable_history' );
				}
				$state['mail_capacity']['entries'][ (int) $id ] = array(
					'pool'  => $pool,
					'bytes' => strlen( $raw ),
				);
			}
			++$page;
			$more = count( $ids ) === 100;
		} while ( $more );
		IntakeStore::save( $state );
	}

	/**
	 * Include unknown pre-reservations and the actual complete message bytes.
	 *
	 * @param array<string,mixed> $state Locked registry.
	 * @param string              $pool Native producer pool.
	 * @param int                 $count Additional slots.
	 * @param int                 $bytes Additional complete encoded bytes.
	 */
	private static function room( array $state, string $pool, int $count, int $bytes ): bool {
		$entries = array_filter( $state['mail_capacity']['entries'], static fn ( array $entry ): bool => $pool === $entry['pool'] );
		$used    = array_sum( array_column( $entries, 'bytes' ) );
		$total   = count( $entries );
		if ( 'critical' === $pool ) {
			foreach ( $state['mail_capacity']['reservations'] as $reservation ) {
				$total += (int) $reservation['remaining'];
				$used  += (int) $reservation['remaining'] * (int) $reservation['max_bytes'];
			}
		}
		return $total + $count <= self::LIMITS[ $pool ]['count'] && $used + $bytes <= self::LIMITS[ $pool ]['bytes'];
	}

	/**
	 * Join a native outer transaction; never commit an unrelated Woo transaction.
	 *
	 * @param callable $work Native queue write plus capacity CAS.
	 * @phpstan-param callable():array<string,mixed> $work
	 * @return array<string,mixed>
	 * @throws \Throwable Native failure propagates to the locked-store boundary.
	 * @throws \RuntimeException A native savepoint cannot be established.
	 */
	private static function transaction( callable $work ): array {
		return ConnectionFence::run( static fn (): array => self::transaction_native( $work ) );
	}

	/**
	 * Keep the exact native transaction and original savepoint until commit.
	 *
	 * @param callable $work Short native writes.
	 * @phpstan-param callable():array<string,mixed> $work
	 * @return array<string,mixed>
	 * @throws \RuntimeException The original transaction/savepoint cannot be confirmed.
	 */
	private static function transaction_native( callable $work ): array {
		global $wpdb;
		$own  = ! self::transaction_active();
		$name = 'linker_mail_' . bin2hex( random_bytes( 8 ) );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.InterpolatedNotPrepared -- Server-generated hexadecimal savepoint identifier, never public input.
		if ( $own ) {
			wc_transaction_query( 'start' );
			if ( self::database_error() || ! self::transaction_active() ) {
				wc_transaction_query( 'rollback' );
				throw new \RuntimeException( 'mail_capacity_transaction_start_failed' );
			}
		}
		if ( false === $wpdb->query( "SAVEPOINT $name" ) ) {
			if ( $own ) {
				wc_transaction_query( 'rollback' );
			}
			throw new \RuntimeException( 'mail_capacity_transaction_unavailable' );
		}
		try {
			$result = $work();
			// Releasing the ORIGINAL point proves the transaction survived all writes.
			if ( false === $wpdb->query( "RELEASE SAVEPOINT $name" ) ) {
				throw new \RuntimeException( 'mail_capacity_savepoint_unconfirmed' );
			}
			if ( $own ) {
				wc_transaction_query( 'commit' );
				if ( self::database_error() || self::transaction_active() ) {
					throw new \RuntimeException( 'mail_capacity_commit_unconfirmed' );
				}
			}
			return $result;
		} catch ( \Throwable $error ) {
			try {
				if ( $own ) {
					wc_transaction_query( 'rollback' );
				} else {
					$wpdb->query( "ROLLBACK TO SAVEPOINT $name" );
				}
			} catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- A dead connection must not trigger any new-connection compensation or erase the original failure.
				// Strict original-handle policy forbids reconnect/compensation.
				// A lost commit remains unknown, never reported as rolled back.
			}
			throw $error;
		}
		// phpcs:enable
	}

	/**
	 * A joined Outbox must defer transport until an independent committed reader.
	 *
	 * @phpstan-impure
	 * @throws \RuntimeException The DB connection cannot prove transaction state.
	 * @throws \mysqli_sql_exception Unexpected native errors propagate without replay.
	 */
	public static function transaction_active(): bool {
		return ConnectionFence::run( self::transaction_active_native( ... ) );
	}

	/** Inspect only the original connection; 1305 on a live handle means no transaction.
	 *
	 * @phpstan-impure
	 * @throws \RuntimeException The original transaction state cannot be read.
	 * @throws \mysqli_sql_exception Unexpected native errors must not become a false no-transaction result.
	 */
	private static function transaction_active_native(): bool {
		global $wpdb;
		// MySQL 8 has no @@in_transaction (the local native DB proves this).
		// SAVEPOINT is ignored outside a transaction; RELEASE then detects that
		// without committing an existing Woo transaction or probing customer data.
		$name     = 'linker_mail_' . bin2hex( random_bytes( 8 ) );
		$previous = $wpdb->suppress_errors( true );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.InterpolatedNotPrepared -- Server-generated hexadecimal savepoint identifier, never public input.
		try {
			$wpdb->query( "SAVEPOINT $name" );
			try {
				$active = false !== $wpdb->query( "RELEASE SAVEPOINT $name" );
			} catch ( \mysqli_sql_exception $error ) {
				if ( 1305 !== $error->getCode() ) {
					throw $error;
				}
				// Expected native result: RELEASE outside a transaction has no point.
				$active = false;
			}
			if ( '1' !== (string) $wpdb->get_var( 'SELECT 1' ) || self::database_error() ) {
				throw new \RuntimeException( 'mail_capacity_transaction_unavailable' );
			}
		} finally {
			$wpdb->suppress_errors( $previous );
		}
		return $active;
		// phpcs:enable
	}

	/**
	 * The driver error changes across native transaction/commit calls.
	 *
	 * @phpstan-impure
	 */
	private static function database_error(): bool {
		global $wpdb;
		return '' !== $wpdb->last_error;
	}

	/** Fixed internal diagnostic; customer/account consumers retain native notices. */
	private static function problem(): WP_Error {
		return new WP_Error( 'linker_mail_capacity', 'The bounded notification queue is full or unavailable.', array( 'status' => 503 ) );
	}
}
