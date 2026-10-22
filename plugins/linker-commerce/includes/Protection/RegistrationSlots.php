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
use Linker\Commerce\Mail\Capacity;

/**
 * Native users own account data; interrupted creation keeps its reserved slot.
 */
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
	 * @param  string $operation Server-admitted registration UUID.
	 * @param  int    $bytes     Proven native business-profile envelope, excluding credentials.
	 * @param  string $recipient HMAC of the original verified recipient.
	 * @return array<string,mixed>|WP_Error Durable slot.
	 */
	public static function reserve( string $operation, int $bytes, string $recipient = '' ): array|WP_Error {
		if ( 1 > $bytes || self::MAX_BYTES < $bytes ) {
			return self::unavailable();
		}
		$key = hash_hmac( 'sha256', 'registration|' . $operation, wp_salt( 'auth' ) );
		return self::edit(
			static function ( array &$state ) use ( $key, $bytes, $recipient ): array|WP_Error {
				if ( isset( $state[ $key ] ) ) {
					return new WP_Error( 'linker_registration_pending', __( 'This request has already been processed. Please check the result before sending it again.', 'linker-commerce' ) );
				}
				$pending = self::pending_users();
				if ( $pending['count'] + count( $state ) >= self::MAX_PENDING || $pending['bytes'] + array_sum( array_column( $state, 'bytes' ) ) + $bytes > self::MAX_BYTES ) {
					return self::unavailable();
				}
				$state[ $key ] = array(
					'at'    => time(),
					'bytes' => $bytes,
					'owner' => $recipient,
				);
				return array( 'key' => $key );
			}
		);
	}

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
	 * Upper bound from native users schema and complete native billing metadata.
	 *
	 * @param array<string,string> $values Native business fields.
	 * @param string               $email  Native email.
	 * @param string               $locale Native locale.
	 */
	public static function profile_bytes( array $values, string $email, string $locale ): int {
		// wp-admin/includes/schema.php: UTF8MB4 maximum for the five counted
		// native columns, never the password/hash/session/activation key.
		$bytes = 4 * ( 60 + 50 + 100 + 100 + 250 );
		foreach ( self::profile_fields( $values, $email, $locale ) as $key => $value ) {
			$bytes += strlen( $key ) + strlen( (string) $value );
		}
		return $bytes;
	}

	/**
	 * Only a caller that proved native insertion never started/rolled back may cancel.
	 * Unknown crash placeholders are never refunded by age.
	 *
	 * @param string $key Server reservation key.
	 */
	public static function cancel_uncreated( string $key ): bool {
		$result = self::edit(
			static function ( array &$state ) use ( $key ): array|WP_Error {
				global $wpdb;
       // phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- Prove no native association before releasing a known uncreated slot.
				$id = $wpdb->get_var( $wpdb->prepare( "SELECT user_id FROM {$wpdb->usermeta} WHERE meta_key = %s AND meta_value = %s LIMIT 1", self::META, $key ) );
				if ( '' !== $wpdb->last_error || null !== $id || ! isset( $state[ $key ] ) ) {
					return self::unavailable();
				}
				unset( $state[ $key ] );
				return array();
			}
		);
		return is_array( $result );
	}

	/**
	 * A creator holds its own connection mutex until bind or known rollback.
	 *
	 * @param string $key Server-owned placeholder HMAC.
	 */
	public static function hold( string $key ): bool {
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
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- MySQL enforces connection ownership.
		$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', self::operation_lock( $key ) ) );
	}

	/**
	 * Staff's explicit orphan disposition; no age-based refund or native account deletion.
	 *
	 * @param string $key    Interrupted server placeholder.
	 * @param string $reason Staff's explicit evidence/reason.
	 */
	public static function resolve_interrupted( string $key, string $reason ): bool {
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
							$audit   = get_option( 'linker_registration_dispositions', array() );
							$audit   = is_array( $audit ) ? $audit : array();
							$audit[] = array(
								'key'    => $key,
								'at'     => time(),
								'by'     => get_current_user_id(),
								'reason' => $reason,
								'owner'  => $state[ $key ]['owner'] ?? '',
							);
							$audit   = array_slice( $audit, -self::MAX_PENDING );
							update_option( 'linker_registration_dispositions', $audit, false );
							if ( get_option( 'linker_registration_dispositions' ) !== $audit ) {
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
				$audit = get_option( 'linker_registration_dispositions', array() );
				return array(
					'interrupted'  => array_filter( $state, static fn ( array $entry ): bool => ( $entry['owner'] ?? '' ) === $owner ),
					'dispositions' => is_array( $audit ) ? array_values( array_filter( $audit, static fn ( array $record ): bool => ( $record['owner'] ?? '' ) === $owner ) ) : array(),
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
		$result = self::edit(
			static function ( array &$state ) use ( $owner ): array|WP_Error {
				foreach ( $state as &$entry ) {
					if ( ( $entry['owner'] ?? '' ) === $owner ) {
						unset( $entry['owner'] );
					}
				}
				unset( $entry );
				$audit = get_option( 'linker_registration_dispositions', array() );
				if ( ! is_array( $audit ) ) {
					return self::unavailable();
				}
				foreach ( $audit as &$record ) {
					if ( ( $record['owner'] ?? '' ) === $owner ) {
						unset( $record['owner'], $record['reason'] );
					}
				}
				unset( $record );
				update_option( 'linker_registration_dispositions', $audit, false );
				return get_option( 'linker_registration_dispositions' ) === $audit ? array() : self::unavailable();
			}
		);
		return is_array( $result );
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
	 * Begin one native pending business-profile write under the same global mutex.
	 *
	 * @param  int                  $id                 Native pending user.
	 * @param  array<string,string> $columns            Changed native public columns.
	 * @param  array<string,string> $meta               Changed business metadata.
	 * @param  bool                 $protect_extensions Hold a rollback-only scope if core extensions would otherwise write before WP_Error.
	 * @return array<string,mixed>|WP_Error Connection-owned native write scope.
	 */
	public static function begin_change( int $id, array $columns, array $meta, bool $protect_extensions = false ): array|WP_Error {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- New registration and pending profile growth share exactly one connection mutex.
		$locked = '1' === (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', self::lock_name() ) );
		if ( ! $locked && ! $protect_extensions ) {
			return self::unavailable();
		}
		try {
			$transaction = new \Linker\Commerce\Mail\NativeTransaction();
		} catch ( \Throwable $error ) {
			if ( $locked ) {
				$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', self::lock_name() ) ); }
			return self::unavailable();
		}
		$context = array(
			'id'          => $id,
			'locked'      => $locked,
			'transaction' => $transaction,
		);
		if ( ! $locked ) {
			return $context + array( 'rejected' => true );
		}
		$before = self::native_profile( $id );
		if ( is_wp_error( $before ) ) {
			self::end_change( $context, false );
			return $before;
		}
		$context['old_bytes'] = $before['bytes'];
		$result               = self::check_change( $context, $columns, $meta );
		if ( ! $result ) {
			self::end_change( $context, false );
			return self::unavailable();
		}
		return $context;
	}

	/**
	 * Exact current native profile plus changed values; only positive growth needs room.
	 *
	 * @param array<string,mixed>  $context Held native scope.
	 * @param array<string,string> $columns Changed public columns.
	 * @param array<string,string> $meta    Changed public metadata.
	 */
	public static function check_change( array $context, array $columns = array(), array $meta = array() ): bool {
		$result = self::edit(
			static function ( array &$state ) use ( $context, $columns, $meta ): array|WP_Error {
				$current = self::native_profile( $context['id'] );
				if ( is_wp_error( $current ) ) {
					return $current;
				}
				$proposed_columns = array_replace( $current['columns'], $columns );
				$bytes            = array_sum( array_map( 'strlen', $proposed_columns ) );
				$seen             = array();
				foreach ( $current['rows'] as $row ) {
					$key          = $row['meta_key'];
					$bytes       += strlen( $key ) + strlen( $meta[ $key ] ?? $row['meta_value'] );
					$seen[ $key ] = true;
				}
				foreach ( $meta as $key => $value ) {
					if ( ! isset( $seen[ $key ] ) ) {
						$bytes += strlen( $key ) + strlen( $value );
					}
				}
				$pending = self::pending_users();
				return $bytes <= $context['old_bytes'] || $pending['bytes'] - $current['bytes'] + $bytes + array_sum( array_column( $state, 'bytes' ) ) <= self::MAX_BYTES ? array() : self::unavailable();
			}
		);
		return is_array( $result );
	}

	/**
	 * Commit only after native writer readback; a failed scope rolls back itself only.
	 *
	 * @param array<string,mixed> $context Native owner/savepoint.
	 * @param bool                $commit  Whether the native writer reached its verified after hook.
	 */
	public static function end_change( array $context, bool $commit ): bool|WP_Error {
		global $wpdb;
		$confirmed = false;
		try {
			$okay = $commit && self::check_change( $context );
			if ( $okay ) {
				$context['transaction']->commit();
			} else {
				$context['transaction']->rollback(); }
			$confirmed = true;
			return $okay;
		} catch ( \Throwable $error ) {
			try {
				$context['transaction']->rollback(); } catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- No compensation on a lost original connection.
				/* Unknown original owner: no compensation. */ }
				return new WP_Error( 'linker_registration_profile_unknown', 'Native profile transaction could not be confirmed.' );
		} finally {
			if ( $confirmed && ! empty( $context['locked'] ) ) {
				// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- The confirmed original native owner releases its mutex.
				$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', self::lock_name() ) );
			}
			clean_user_cache( $context['id'] );
			wp_cache_delete( $context['id'], 'user_meta' );
		}
	}

	/**
	 * Read only native business columns/metadata; never hashes, passwords or tokens.
	 *
	 * @param  int $id Native user.
	 * @return array<string,mixed>|WP_Error Exact native logical bytes and values.
	 */
	public static function native_profile( int $id ): array|WP_Error {
		global $wpdb;
		// phpcs:disable WordPress.DB.DirectDatabaseQuery, WordPress.DB.PreparedSQL.NotPrepared -- Capacity must inspect this writer connection, not object-cache snapshots.
		$columns      = $wpdb->get_row( $wpdb->prepare( "SELECT user_login, user_nicename, user_email, user_url, display_name FROM {$wpdb->users} WHERE ID = %d", $id ), ARRAY_A );
		$column_error = $wpdb->last_error;
		if ( ! is_array( $columns ) ) {
			return self::unavailable();
		}
		$rows = $wpdb->get_results( $wpdb->prepare( "SELECT meta_key, meta_value FROM {$wpdb->usermeta} WHERE user_id = %d AND (meta_key LIKE %s OR meta_key IN ('first_name','last_name','linker_customer_role','linker_company_website','locale')) ORDER BY umeta_id", $id, $wpdb->esc_like( 'billing_' ) . '%' ), ARRAY_A );
		// phpcs:enable
		if ( ! is_array( $rows ) || '' !== implode( '', array( $column_error, $wpdb->last_error ) ) ) {
			return self::unavailable();
		}
		$meta  = array();
		$bytes = array_sum( array_map( 'strlen', $columns ) );
		foreach ( $rows as $row ) {
			$meta[ $row['meta_key'] ] = $row['meta_value'];
			$bytes                   += strlen( $row['meta_key'] ) + strlen( $row['meta_value'] );
		}
		return array(
			'columns' => $columns,
			'meta'    => $meta,
			'rows'    => $rows,
			'bytes'   => $bytes,
		);
	}

	/**
	 * Exchange a placeholder only after the native user and association exist.
	 * The native pending account then occupies capacity until staff disposition.
	 *
	 * @param  string $key     Server reservation key.
	 * @param  int    $user_id Created native user.
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
					'capacity'       => self::MAX_PENDING,
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
		return new WP_Error( 'linker_registration_capacity', __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
	}
}
