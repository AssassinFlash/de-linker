<?php
/**
 * Persistent public-account slots across native user creation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Registration\Approval;
use WP_Error;

/** Native users own account data; interrupted creation keeps its reserved slot. */
final class RegistrationSlots {

	public const OPTION = 'linker_public_registration_slots';
	public const META   = '_linker_public_registration_operation';
	// Operating allocation, not a customer-traffic measurement: specification 569.
	public const MAX_PENDING = 128;
	public const MAX_BYTES   = 8388608;
	private const MUTEX      = 'registration-capacity';

	/**
	 * Reserve before native account creation, with no password or business payload.
	 *
	 * @param string $operation Server-admitted registration UUID.
	 * @param int    $bytes Proven native business-profile envelope, excluding credentials.
	 * @return array<string,mixed>|WP_Error Durable slot.
	 */
	public static function reserve( string $operation, int $bytes ): array|WP_Error {
		if ( 1 > $bytes || self::MAX_BYTES < $bytes ) {
			return self::unavailable();
		}
		$key = hash_hmac( 'sha256', 'registration|' . $operation, wp_salt( 'auth' ) );
		return self::edit(
			static function ( array &$state ) use ( $key, $bytes ): array|WP_Error {
				if ( isset( $state[ $key ] ) ) {
					return new WP_Error( 'linker_registration_pending', __( 'This request has already been processed. Please check the result before sending it again.', 'linker-commerce' ) );
				}
				$pending = self::pending_users();
				if ( count( $pending ) + count( $state ) >= self::MAX_PENDING || array_sum( $pending ) + array_sum( array_column( $state, 'bytes' ) ) + $bytes > self::MAX_BYTES ) {
					return self::unavailable();
				}
				$state[ $key ] = array(
					'at'    => time(),
					'bytes' => $bytes,
				);
				return array( 'key' => $key );
			}
		);
	}

	/**
	 * Exchange a placeholder only after the native user and association exist.
	 * The native pending account then occupies capacity until staff disposition.
	 *
	 * @param string $key Server reservation key.
	 * @param int    $user_id Created native user.
	 * @return array<string,mixed>|WP_Error Confirmed association.
	 */
	public static function bind( string $key, int $user_id ): array|WP_Error {
		return self::edit(
			static function ( array &$state ) use ( $key, $user_id ): array|WP_Error {
				if ( ! isset( $state[ $key ] ) || 0 >= $user_id || ! get_userdata( $user_id ) || get_user_meta( $user_id, self::META, true ) !== $key ) {
					return self::unavailable();
				}
				unset( $state[ $key ] );
				return array( 'user' => $user_id );
			}
		);
	}

	/**
	 * Read current native unresolved accounts without loading private fields.
	 * Existing customers are counted without importing or changing their data.
	 *
	 * @return array<int,int> Native ID to business-profile bytes, capped one above the operating limit.
	 * @throws \RuntimeException A failed query cannot mean zero pending accounts.
	 */
	private static function pending_users(): array {
		global $wpdb;
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Admission needs an authoritative bounded native account count, including pre-existing customers and public core registrations.
		$rows = $wpdb->get_results(
			$wpdb->prepare(
				"SELECT u.ID, OCTET_LENGTH(u.user_login) + OCTET_LENGTH(u.user_nicename) + OCTET_LENGTH(u.user_email) + OCTET_LENGTH(u.user_url) + OCTET_LENGTH(u.display_name)
				 + COALESCE((SELECT SUM(OCTET_LENGTH(m.meta_key) + OCTET_LENGTH(m.meta_value)) FROM {$wpdb->usermeta} m WHERE m.user_id = u.ID AND (m.meta_key LIKE %s OR m.meta_key IN ('first_name', 'last_name', 'linker_customer_role', 'linker_company_website', 'locale'))), 0) AS business_bytes
				 FROM {$wpdb->users} u WHERE
				 (EXISTS (SELECT 1 FROM {$wpdb->usermeta} c WHERE c.user_id = u.ID AND c.meta_key = %s AND c.meta_value LIKE %s)
				  OR EXISTS (SELECT 1 FROM {$wpdb->usermeta} r WHERE r.user_id = u.ID AND r.meta_key = %s))
				 AND NOT EXISTS (SELECT 1 FROM {$wpdb->usermeta} s WHERE s.user_id = u.ID AND s.meta_key = %s AND s.meta_value IN (%s, %s))
				 ORDER BY u.ID LIMIT %d",
				$wpdb->esc_like( 'billing_' ) . '%',
				$wpdb->get_blog_prefix() . 'capabilities',
				'%' . $wpdb->esc_like( '"customer";b:1' ) . '%',
				self::META,
				Approval::STATUS_META,
				Approval::APPROVED,
				Approval::REJECTED,
				self::MAX_PENDING + 1
			),
			ARRAY_A
		);
		// phpcs:enable
		if ( '' !== $wpdb->last_error || ! is_array( $rows ) ) {
			throw new \RuntimeException( 'registration_pending_read_failed' );
		}
		$result = array();
		foreach ( $rows as $row ) {
			$result[ (int) $row['ID'] ] = (int) $row['business_bytes'];
		}
		return $result;
	}

	/**
	 * No timer, email result, login or model result releases an account slot.
	 *
	 * @return array<string,mixed>|WP_Error Current aggregate only.
	 */
	public static function summary(): array|WP_Error {
		return self::edit(
			static function ( array &$state ): array {
				$pending = self::pending_users();
				return array(
					'pending_users'  => count( $pending ),
					'interrupted'    => count( $state ),
					'capacity'       => self::MAX_PENDING,
					'business_bytes' => array_sum( $pending ),
					'reserved_bytes' => array_sum( array_column( $state, 'bytes' ) ),
					'byte_capacity'  => self::MAX_BYTES,
				);
			}
		);
	}

	/**
	 * Serialize registration reservations using a connection-owned lock and CAS.
	 * The callback changes only this bounded registry, never external services.
	 *
	 * @param callable(array<string,mixed>&):(array<string,mixed>|WP_Error) $work Slot operation.
	 * @return array<string,mixed>|WP_Error Durable result.
	 */
	private static function edit( callable $work ): array|WP_Error {
		$result = self::unavailable();
		Lock::run(
			self::MUTEX,
			static function () use ( $work, &$result ): void {
				global $wpdb;
				try {
					$raw   = self::read();
					$state = null === $raw ? array() : maybe_unserialize( $raw );
					if ( ! is_array( $state ) || count( $state ) > self::MAX_PENDING ) {
						return;
					}
					$result = $work( $state );
					if ( is_wp_error( $result ) ) {
						return;
					}
					$encoded = maybe_serialize( $state );
					if ( $raw === $encoded ) {
						return;
					}
					// phpcs:disable WordPress.DB.DirectDatabaseQuery -- A lock-owned cache-free native option CAS cannot use update_option's positive/negative caches.
					$written = null === $raw
						? $wpdb->query( $wpdb->prepare( "INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) SELECT %s, %s, 'off' WHERE IS_USED_LOCK(%s) = CONNECTION_ID()", self::OPTION, $encoded, self::lock_name() ) )
						: $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value = %s, autoload = 'off' WHERE option_name = %s AND BINARY option_value = BINARY %s AND IS_USED_LOCK(%s) = CONNECTION_ID()", $encoded, self::OPTION, $raw, self::lock_name() ) );
					// phpcs:enable
					if ( 1 !== $written || self::read() !== $encoded ) {
						throw new \RuntimeException( 'registration_capacity_write_failed' );
					}
				} catch ( \Throwable $error ) {
					$result = self::unavailable();
				} finally {
					wp_cache_delete( self::OPTION, 'options' );
					wp_cache_delete( 'notoptions', 'options' );
					wp_cache_delete( 'alloptions', 'options' );
				}
			}
		);
		return $result;
	}

	/**
	 * Native option and lock ownership are read together, without object caches.
	 *
	 * @throws \RuntimeException Storage or ownership failure.
	 */
	private static function read(): ?string {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- The owned mutex and snapshot must be read on the actual writer connection.
		$row = $wpdb->get_row( $wpdb->prepare( "SELECT (SELECT option_value FROM {$wpdb->options} WHERE option_name = %s) AS value, IS_USED_LOCK(%s) = CONNECTION_ID() AS owned", self::OPTION, self::lock_name() ), ARRAY_A );
		if ( ! is_array( $row ) || '1' !== (string) ( $row['owned'] ?? '' ) || '' !== $wpdb->last_error || ( null !== $row['value'] && ! is_string( $row['value'] ) ) ) {
			throw new \RuntimeException( 'registration_capacity_read_failed' );
		}
		return $row['value'];
	}

	/** Existing database/prefix mutex namespace. */
	private static function lock_name(): string {
		global $wpdb;
		$database = isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) ? $wpdb->dbname : ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' );
		return 'linker-assessment-' . md5( $database . '/' . $wpdb->prefix . '/' . self::MUTEX );
	}

	/** Honest pre-create refusal; no claim that an account has been made. */
	private static function unavailable(): WP_Error {
		return new WP_Error( 'linker_registration_capacity', __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
	}
}
