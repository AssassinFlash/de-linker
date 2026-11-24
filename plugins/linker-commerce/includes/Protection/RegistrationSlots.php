<?php
/**
 * Persistent public-account slots across native user creation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Settings\Options;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Registration\Approval;
use WP_Error;
use Linker\Commerce\Mail\ConnectionFence;

/**
 * Native users own account data; interrupted creation keeps its reserved slot.
 */
final class RegistrationSlots {


	public const OPTION = 'linker_public_registration_slots';
	public const META   = '_linker_public_registration_operation';
	// Operating allocation, not a customer-traffic measurement: specification 569.
	private const AUDIT_HISTORY = 128;
	public const MAX_BYTES      = 8388608;
	private const MUTEX         = 'registration-capacity';

	/**
	 * Native schema bounds core columns; all prospective Woo business meta is exact.
	 *
	 * @param  array<string,string> $values Validated native fields.
	 * @param  string               $email  Native validated address.
	 * @param  string               $locale Native customer locale.
	 * @return array<string,string> Complete native public business metadata.
	 */
	public static function profile_fields( array $values, string $email, string $locale ): array {
		$customer = new \WC_Customer();
		foreach ( array( 'billing_company', 'billing_first_name', 'billing_last_name', 'billing_country' ) as $field ) {
			$setter = 'set_' . $field;
			$customer->$setter( $values[ $field ] ?? '' );
		}
		$customer->set_billing_email( $email );
		$meta = array(
			'first_name'                                => $values['billing_first_name'] ?? '',
			'last_name'                                 => $values['billing_last_name'] ?? '',
			'locale'                                    => $locale,
			\Linker\Commerce\Registration\CustomerRole::META => $values[ \Linker\Commerce\Registration\CustomerRole::META ] ?? '',
			\Linker\Commerce\Registration\Website::META => \Linker\Commerce\Registration\Website::normalize( $values[ \Linker\Commerce\Registration\Website::META ] ?? '' ),
			\Linker\Commerce\Registration\VatProfile::VAT_META => \Linker\Commerce\Registration\VatNumber::normalize( $values[ \Linker\Commerce\Registration\VatProfile::VAT_META ] ?? '' ),
		);
		foreach ( $customer->get_billing() as $field => $value ) {
			$meta[ 'billing_' . $field ] = $value;
		}
		return $meta;
	}

	/**
	 * A creator holds its own connection mutex until bind or known rollback.
	 *
	 * @param string $key Server-owned placeholder HMAC.
	 */
	public static function hold( string $key ): bool {
		return ConnectionFence::run( static fn () => self::hold_owned( $key ) );
	}

	/** Original native creator mutex under its first-statement fence.
	 *
	 * @param string $key Server placeholder HMAC.
	 */
	private static function hold_owned( string $key ): bool {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- A staff orphan disposition must never race a still-running native creator.
		return '1' === (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', self::operation_lock( $key ) ) );
	}

	/**
	 * Release this connection's creator lock, never another worker's lock.
	 *
	 * @param string $key Server-owned placeholder.
	 */
	public static function release( string $key ): void {
		ConnectionFence::run( static fn () => self::release_owned( $key ) );
	}

	/** Release only on a live original native connection.
	 *
	 * @param string $key Server placeholder HMAC.
	 * @throws \RuntimeException The original mutex release cannot be confirmed.
	 */
	private static function release_owned( string $key ): void {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- MySQL enforces connection ownership.
		if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', self::operation_lock( $key ) ) ) ) {
			throw new \RuntimeException( 'registration_creator_release_unknown' );
		}
	}

	/**
	 * Staff's explicit orphan disposition; no age-based refund or native account deletion.
	 *
	 * @param string $key    Interrupted server placeholder.
	 * @param string $reason Staff's explicit evidence/reason.
	 */
	public static function resolve_interrupted( string $key, string $reason ): bool {
		try {
			return ConnectionFence::run( static fn () => self::resolve_owned( $key, $reason ) );
		} catch ( \Throwable $error ) {
			return false;
		}
	}

	/** Native staff disposition under its first-statement fence.
	 *
	 * @param string $key Interrupted placeholder.
	 * @param string $reason Staff evidence.
	 */
	private static function resolve_owned( string $key, string $reason ): bool {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- A live creator, including this connection, must not be resolved by staff.
		$creator = $wpdb->get_var( $wpdb->prepare( 'SELECT IS_USED_LOCK(%s)', self::operation_lock( $key ) ) );
		if ( ! current_user_can( 'edit_users' ) || '' === trim( $reason ) || strlen( $reason ) > 2048 || null !== $creator || ! self::hold( $key ) ) {
			return false; }
		try {
			return \Linker\Commerce\Mail\NativeTransaction::run(
				static function () use ( $key, $reason ): bool {
					$result = self::edit(
						static function ( array &$state ) use ( $key, $reason ): array|WP_Error {
							global $wpdb;
          // phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- A committed account's association is authoritative, regardless of its role or label.
							$user = $wpdb->get_var( $wpdb->prepare( "SELECT user_id FROM {$wpdb->usermeta} WHERE meta_key = %s AND meta_value = %s LIMIT 1", self::META, $key ) );
							if ( '' !== $wpdb->last_error || null !== $user || ! isset( $state[ $key ] ) ) {
								return self::unavailable();
							}
							$audit   = self::audit();
							$audit[] = array(
								'key'    => $key,
								'at'     => time(),
								'by'     => get_current_user_id(),
								'reason' => $reason,
								'owner'  => $state[ $key ]['owner'] ?? '',
							);
							$audit   = array_slice( $audit, -self::AUDIT_HISTORY );
							update_option( 'linker_registration_dispositions', $audit, false );
							if ( self::audit() !== $audit ) {
								return self::unavailable();
							}
							unset( $state[ $key ] );
							return array();
						}
					);
					if ( ! is_array( $result ) ) {
						throw new \RuntimeException( 'registration_disposition_failed' ); }
					return true;
				}
			);
		} catch ( \Throwable $error ) {
			return false;
		} finally {
			foreach ( array( self::OPTION, 'linker_registration_dispositions', 'alloptions', 'notoptions' ) as $option ) {
				wp_cache_delete( $option, 'options' ); }
			self::release( $key );
		}
	}

	/**
	 * Staff-only aggregate screen's bounded interrupted registry, never credentials.
	 *
	 * @return array<string,mixed>|WP_Error Current interrupted placeholders.
	 */
	public static function interrupted(): array|WP_Error {
		return self::edit(
			static function ( array &$state ): array {
				return $state;
			}
		);
	}

	/**
	 * Native verified-email privacy callback receives only this recipient's bounded records.
	 *
	 * @param  string $owner Server recipient HMAC.
	 * @return array<string,mixed>|WP_Error Owned source/audit records.
	 */
	public static function owned_data( string $owner ): array|WP_Error {
		return self::edit(
			static function ( array &$state ) use ( $owner ): array {
				$audit = self::audit();
				return array(
					'interrupted'  => array_filter( $state, static fn ( array $entry ): bool => ( $entry['owner'] ?? '' ) === $owner ),
					'dispositions' => array_values( array_filter( $audit, static fn ( array $record ): bool => ( $record['owner'] ?? '' ) === $owner ) ),
				);
			}
		);
	}

	/**
	 * Verified privacy removes the owner association without refunding unknown work.
	 *
	 * @param string $owner Native recipient HMAC.
	 */
	public static function forget_owner( string $owner ): bool {
		try {
			return \Linker\Commerce\Mail\NativeTransaction::run(
				static function () use ( $owner ): bool {
					$result = self::edit(
						static function ( array &$state ) use ( $owner ): array|WP_Error {
							foreach ( $state as &$entry ) {
								if ( ( $entry['owner'] ?? '' ) === $owner ) {
									unset( $entry['owner'] );
								}
							}
							unset( $entry );
							$audit = self::audit();
							foreach ( $audit as &$record ) {
								if ( ( $record['owner'] ?? '' ) === $owner ) {
									unset( $record['owner'], $record['reason'] );
								}
							}
							unset( $record );
							update_option( 'linker_registration_dispositions', $audit, false );
							return self::audit() === $audit ? array() : self::unavailable();
						}
					);
					if ( is_wp_error( $result ) ) {
						throw new \RuntimeException( 'registration_audit_forget_failed' );
					}
					return true;
				}
			);
		} catch ( \Throwable $error ) {
			return false;
		}
	}

	/**
	 * The mutex name contains a server HMAC only, never an email or password.
	 *
	 * @param string $key Server placeholder.
	 */
	private static function operation_lock( string $key ): string {
		global $wpdb;
		return 'linker-reg-' . md5( ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' ) . '/' . $wpdb->prefix . '/' . $key );
	}

	/**
	 * Read current native unresolved accounts without loading private fields.
	 * Existing customers are counted without importing or changing their data.
	 *
	 * @return array{count:int,bytes:int} Full legacy/current aggregate without loading personal values.
	 * @throws \RuntimeException A failed query cannot mean zero pending accounts.
	 */
	private static function pending_users(): array {
		global $wpdb;
		// phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- Admission needs an authoritative bounded native account count, including pre-existing customers and public core registrations.
		$rows = $wpdb->get_row(
			$wpdb->prepare(
				"SELECT COUNT(*) AS total, COALESCE(SUM(profiles.business_bytes), 0) AS bytes FROM (SELECT u.ID, OCTET_LENGTH(u.user_login) + OCTET_LENGTH(u.user_nicename) + OCTET_LENGTH(u.user_email) + OCTET_LENGTH(u.user_url) + OCTET_LENGTH(u.display_name)
				 + COALESCE((SELECT SUM(OCTET_LENGTH(m.meta_key) + OCTET_LENGTH(m.meta_value)) FROM {$wpdb->usermeta} m WHERE m.user_id = u.ID AND (m.meta_key LIKE %s OR m.meta_key IN ('first_name', 'last_name', 'linker_customer_role', 'linker_company_website', 'locale'))), 0) AS business_bytes
				 FROM {$wpdb->users} u WHERE
				 (EXISTS (SELECT 1 FROM {$wpdb->usermeta} c WHERE c.user_id = u.ID AND c.meta_key = %s AND c.meta_value LIKE %s)
				  OR EXISTS (SELECT 1 FROM {$wpdb->usermeta} r WHERE r.user_id = u.ID AND r.meta_key = %s))
				 AND NOT (COALESCE((SELECT s.meta_value FROM {$wpdb->usermeta} s WHERE s.user_id = u.ID AND s.meta_key = %s ORDER BY s.umeta_id LIMIT 1), '') IN (%s, %s)
				 AND CAST(COALESCE((SELECT a.meta_value FROM {$wpdb->usermeta} a WHERE a.user_id = u.ID AND a.meta_key = 'linker_approval_changed_by' ORDER BY a.umeta_id LIMIT 1), '0') AS UNSIGNED) > 0
				 AND CAST(COALESCE((SELECT t.meta_value FROM {$wpdb->usermeta} t WHERE t.user_id = u.ID AND t.meta_key = 'linker_approval_changed_at' ORDER BY t.umeta_id LIMIT 1), '0') AS UNSIGNED) > 0)
				  ) profiles",
				$wpdb->esc_like( 'billing_' ) . '%',
				$wpdb->get_blog_prefix() . 'capabilities',
				'%' . $wpdb->esc_like( '"customer";b:1' ) . '%',
				self::META,
				Approval::STATUS_META,
				Approval::APPROVED,
				Approval::REJECTED
			),
			ARRAY_A
		);
		// phpcs:enable
		if ( '' !== $wpdb->last_error || ! is_array( $rows ) ) {
			throw new \RuntimeException( 'registration_pending_read_failed' );
		}
		return array(
			'count' => (int) $rows['total'],
			'bytes' => (int) $rows['bytes'],
		);
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
					'pending_users'  => $pending['count'],
					'interrupted'    => count( $state ),
					'business_bytes' => $pending['bytes'],
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
	 * @param  callable(array<string,mixed>&):(array<string,mixed>|WP_Error) $work Slot operation.
	 * @return array<string,mixed>|WP_Error Durable result.
	 */
	private static function edit( callable $work ): array|WP_Error {
		try {
			return ConnectionFence::run( static fn () => self::edit_owned( $work ) );
		} catch ( \Throwable $error ) {
			return self::unavailable();
		}
	}

	/** DB-only capacity edit; no provider or transport can enter this scope.
	 *
	 * @param callable(array<string,mixed>&):(array<string,mixed>|WP_Error) $work Exact registry edit.
	 * @return array<string,mixed>|WP_Error Native durable result.
	 */
	private static function edit_owned( callable $work ): array|WP_Error {
		$result = self::unavailable();
		Lock::run(
			self::MUTEX,
			static function () use ( $work, &$result ): void {
				global $wpdb;
				try {
					$raw   = self::read();
					$state = null === $raw ? array() : maybe_unserialize( $raw );
					if ( ! is_array( $state ) ) {
						return;
					}
					foreach ( $state as $key => $entry ) {
						if ( ! is_string( $key ) || ! preg_match( '/^[a-f0-9]{64}$/D', $key ) || ! is_array( $entry ) || ! is_int( $entry['at'] ?? null ) || ! is_int( $entry['bytes'] ?? null ) || $entry['bytes'] < 1 || $entry['bytes'] > self::MAX_BYTES ) {
								return;
						}
					}
					$result = $work( $state );
					if ( is_wp_error( $result ) ) {
						return;
					}
					$encoded = maybe_serialize( $state );
					if ( $raw === $encoded ) {
						return;
					}
             // phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- A lock-owned cache-free native option CAS cannot use update_option's positive/negative caches.
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
					wp_cache_delete( 'linker_registration_dispositions', 'options' );
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
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- The owned mutex and snapshot must be read on the actual writer connection.
		$row = $wpdb->get_row( $wpdb->prepare( "SELECT (SELECT option_value FROM {$wpdb->options} WHERE option_name = %s FOR UPDATE NOWAIT) AS value, IS_USED_LOCK(%s) = CONNECTION_ID() AS owned", self::OPTION, self::lock_name() ), ARRAY_A );
		if ( ! is_array( $row ) || '1' !== (string) ( $row['owned'] ?? '' ) || '' !== $wpdb->last_error || ( null !== $row['value'] && ! is_string( $row['value'] ) ) ) {
			throw new \RuntimeException( 'registration_capacity_read_failed' );
		}
		return $row['value'];
	}

	/**
	 * Read the bounded audit without option/negative caches on its owning connection.
	 *
	 * @return list<array<string,mixed>> Authoritative native staff decisions.
	 * @throws \RuntimeException A failed read or lost owner is not an empty audit.
	 */
	private static function audit(): array {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- Same registration mutex and original native row-read contract as the slot registry.
		$row = $wpdb->get_row( $wpdb->prepare( "SELECT (SELECT option_value FROM {$wpdb->options} WHERE option_name = %s FOR UPDATE NOWAIT) AS value, IS_USED_LOCK(%s) = CONNECTION_ID() AS owned", 'linker_registration_dispositions', self::lock_name() ), ARRAY_A );
		if ( ! is_array( $row ) || '1' !== (string) ( $row['owned'] ?? '' ) || '' !== $wpdb->last_error || ( null !== $row['value'] && ! is_string( $row['value'] ) ) ) {
			throw new \RuntimeException( 'registration_audit_read_failed' );
		}
		$audit = null === $row['value'] ? array() : maybe_unserialize( $row['value'] );
		if ( ! is_array( $audit ) || count( $audit ) > self::AUDIT_HISTORY || count( array_filter( $audit, 'is_array' ) ) !== count( $audit ) ) {
			throw new \RuntimeException( 'registration_audit_invalid' );
		}
		return array_values( $audit );
	}

	/**
	 * Existing database/prefix mutex namespace.
	 */
	private static function lock_name(): string {
		global $wpdb;
		$database = isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) ? $wpdb->dbname : ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' );
		return 'linker-assessment-' . md5( $database . '/' . $wpdb->prefix . '/' . self::MUTEX );
	}

	/**
	 * Honest pre-create refusal; no claim that an account has been made.
	 */
	private static function unavailable(): WP_Error {
		/* translators: %s: public team email address. */
		return new WP_Error( 'linker_registration_capacity', sprintf( __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email %s.', 'linker-commerce' ), ( new Options() )->team_mailbox() ) );
	}
}
