<?php
/**
 * Owner-scoped staged project brief records for Installer desktop handoff.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/**
 * Plain customer text is staged under the verified native principal before
 * navigating to the Solution Configurator. No sizing numbers are inferred.
 */
final class ProjectBriefSource {

	public const OPTION_PREFIX = 'linker_planner_briefs_';
	/** Matches PlanningBrief.project_note in brief.py and brief.schema.json. */
	public const MAX_TEXT_LENGTH = 4096;
	/** Per-principal resource bound for staged project briefs. */
	public const MAX_RECORDS = 32;
	/** Bounded CAS retry budget under concurrent same-principal updates. */
	private const MAX_ATTEMPTS = 4;

	/**
	 * Stage or update a customer project note and verify an exact readback.
	 *
	 * @param Principal           $principal Verified native principal.
	 * @param array<string,mixed> $command   Bounded stage request.
	 * @return array<string,mixed>|WP_Error Authoritative readback or explicit refusal.
	 */
	public function stage( Principal $principal, array $command ): array|WP_Error {
		if ( 1 !== ( $command['schema_version'] ?? null ) || ! is_string( $command['text'] ?? null ) || ! is_string( $command['source_path'] ?? null ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$allowed = array( 'brief_id', 'expected_revision', 'schema_version', 'source_path', 'tab', 'text' );
		if ( array() !== array_diff( array_keys( $command ), $allowed ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$text        = $command['text'];
		$source_path = $command['source_path'];
		if ( '' === trim( $text ) || mb_strlen( $text, 'UTF-8' ) > self::MAX_TEXT_LENGTH || ! self::valid_path( $source_path ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$requested_id      = $command['brief_id'] ?? null;
		$expected_revision = $command['expected_revision'] ?? null;
		if ( null !== $requested_id && ( ! is_string( $requested_id ) || ! self::valid_id( $requested_id ) ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		if ( null !== $expected_revision && ( ! is_string( $expected_revision ) || ! self::valid_revision( $expected_revision ) ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$brief_id = is_string( $requested_id ) ? $requested_id : bin2hex( random_bytes( 16 ) );
		$revision = self::revision( $brief_id, $source_path, $text );
		$option   = self::option_name( $principal );
		$now      = time();
		for ( $attempt = 0; $attempt < self::MAX_ATTEMPTS; ++$attempt ) {
			$snapshot = $this->read_raw( $option );
			if ( is_wp_error( $snapshot ) ) {
				return $snapshot;
			}
			$records = $this->decode_records( $snapshot );
			if ( null === $records ) {
				return Failure::make( 'project_brief_unavailable', 503 );
			}
			$existing = $records[ $brief_id ] ?? null;
			if ( is_array( $existing ) ) {
				if ( $existing['text'] === $text && $existing['source_path'] === $source_path && $existing['revision'] === $revision ) {
					return self::public_record( $existing );
				}
				if ( null !== $expected_revision && ! hash_equals( $existing['revision'], $expected_revision ) ) {
					return Failure::make( 'project_brief_conflict', 409 );
				}
			} elseif ( null !== $expected_revision ) {
				return Failure::make( 'project_brief_conflict', 409 );
			}
			$record               = array(
				'schema_version' => 1,
				'brief_id'       => $brief_id,
				'revision'       => $revision,
				'text'           => $text,
				'source_path'    => $source_path,
				'updated_at'     => $now,
			);
			$records[ $brief_id ] = $record;
			$records              = self::trim_records( $records, $brief_id );
			if ( ! $this->write_cas( $option, $snapshot, $records ) ) {
				continue;
			}
			$verified = $this->read_record( $option, $brief_id );
			if ( is_array( $verified ) && $verified['revision'] === $revision && $verified['text'] === $text && $verified['source_path'] === $source_path ) {
				return self::public_record( $verified );
			}
		}
		return Failure::make( 'project_brief_persistence', 503 );
	}

	/**
	 * Read a staged project brief owned by the current native principal.
	 *
	 * @param Principal           $principal Verified native principal.
	 * @param array<string,mixed> $command   Bounded read request.
	 * @return array<string,mixed>|WP_Error Staged brief or explicit refusal.
	 */
	public function read( Principal $principal, array $command ): array|WP_Error {
		$keys = array_keys( $command );
		sort( $keys );
		if ( array( 'brief_id', 'schema_version' ) !== $keys || 1 !== $command['schema_version'] || ! is_string( $command['brief_id'] ) || ! self::valid_id( $command['brief_id'] ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$option   = self::option_name( $principal );
		$snapshot = $this->read_raw( $option );
		if ( is_wp_error( $snapshot ) ) {
			return $snapshot;
		}
		$records = $this->decode_records( $snapshot );
		if ( null === $records ) {
			return Failure::make( 'project_brief_unavailable', 503 );
		}
		$record = $records[ $command['brief_id'] ] ?? null;
		return is_array( $record ) ? self::public_record( $record ) : Failure::make( 'project_brief_unavailable', 404 );
	}

	/**
	 * Transfer a verified guest's staged briefs to the authenticated account,
	 * removing only records whose user-owned readback succeeded.
	 *
	 * @param string $guest_subject Verified guest subject (`wp:<blog>:guest:<sha256>`).
	 * @param int    $user_id       Verified account ID.
	 * @return bool True when all guest staged briefs are transferred and cleared.
	 */
	public function claim( string $guest_subject, int $user_id ): bool {
		if ( ! TransitionTicket::subject( $guest_subject ) || $user_id < 1 ) {
			return false;
		}
		$guest_option = self::option_name( new Principal( 'guest', $guest_subject ) );
		$guest_raw    = $this->read_raw( $guest_option );
		if ( is_wp_error( $guest_raw ) ) {
			return false;
		}
		if ( null === $guest_raw ) {
			return true;
		}
		$guest_records = $this->decode_records( $guest_raw );
		if ( null === $guest_records ) {
			return false;
		}
		if ( array() === $guest_records ) {
			return true;
		}
		$user_principal = new Principal( 'user', NativeIdentity::user_subject( $user_id ) );
		$user_option    = self::option_name( $user_principal );
		$claimed_ids    = array();
		foreach ( $guest_records as $id => $record ) {
			$existing = $this->read_record( $user_option, $id );
			if ( is_array( $existing ) ) {
				$claimed_ids[ $id ] = true;
				continue;
			}
			$staged = $this->stage(
				$user_principal,
				array(
					'schema_version' => 1,
					'brief_id'       => $record['brief_id'],
					'text'           => $record['text'],
					'source_path'    => $record['source_path'],
				)
			);
			if ( ! is_wp_error( $staged ) && ( $staged['brief_id'] ?? '' ) === $id && ( $staged['text'] ?? '' ) === $record['text'] ) {
				$claimed_ids[ $id ] = true;
			}
		}
		for ( $attempt = 0; $attempt < self::MAX_ATTEMPTS; ++$attempt ) {
			$current_raw = $this->read_raw( $guest_option );
			if ( is_wp_error( $current_raw ) ) {
				return false;
			}
			if ( null === $current_raw ) {
				return count( $claimed_ids ) === count( $guest_records );
			}
			$current_records = $this->decode_records( $current_raw );
			if ( null === $current_records ) {
				return false;
			}
			foreach ( array_keys( $claimed_ids ) as $id ) {
				if ( isset( $current_records[ $id ] ) && $current_records[ $id ]['revision'] === $guest_records[ $id ]['revision'] ) {
					unset( $current_records[ $id ] );
				}
			}
			if ( $this->write_cas( $guest_option, $current_raw, $current_records ) ) {
				return array() === $current_records && count( $claimed_ids ) === count( $guest_records );
			}
		}
		return false;
	}

	/**
	 * Deterministic revision hash for a staged brief record.
	 *
	 * @param string $brief_id    Opaque 32-hex brief ID.
	 * @param string $source_path Validated same-origin path.
	 * @param string $text        Customer plain text.
	 */
	public static function revision( string $brief_id, string $source_path, string $text ): string {
		return hash( 'sha256', $brief_id . "\n" . $source_path . "\n" . $text );
	}

	/**
	 * Option name for one verified principal.
	 *
	 * @param Principal $principal Verified native principal.
	 */
	public static function option_name( Principal $principal ): string {
		return self::OPTION_PREFIX . hash( 'sha256', $principal->kind . '|' . $principal->subject );
	}

	/**
	 * Check the 32-hex brief ID format.
	 *
	 * @param string $id Candidate ID.
	 */
	public static function valid_id( string $id ): bool {
		return 1 === preg_match( '/\A[a-f0-9]{32}\z/', $id );
	}

	/**
	 * Check the 64-hex revision format.
	 *
	 * @param string $revision Candidate revision.
	 */
	public static function valid_revision( string $revision ): bool {
		return 1 === preg_match( '/\A[a-f0-9]{64}\z/', $revision );
	}

	/**
	 * Require an internal same-origin pathname.
	 *
	 * @param string $path Candidate path.
	 */
	public static function valid_path( string $path ): bool {
		return '' !== $path
			&& strlen( $path ) <= 256
			&& str_starts_with( $path, '/' )
			&& ! str_starts_with( $path, '//' )
			&& ! str_contains( $path, "\r" )
			&& ! str_contains( $path, "\n" )
			&& ! str_contains( $path, '?' )
			&& ! str_contains( $path, '#' );
	}

	/**
	 * Public wire representation of a staged record.
	 *
	 * @param array{schema_version:int,brief_id:string,revision:string,text:string,source_path:string,updated_at:int} $record Stored record.
	 * @return array{schema_version:int,brief_id:string,revision:string,text:string,source_path:string}
	 */
	private static function public_record( array $record ): array {
		return array(
			'schema_version' => 1,
			'brief_id'       => $record['brief_id'],
			'revision'       => $record['revision'],
			'text'           => $record['text'],
			'source_path'    => $record['source_path'],
		);
	}

	/**
	 * Bound the per-principal map to MAX_RECORDS while retaining the active ID.
	 *
	 * @param array<string,array{schema_version:int,brief_id:string,revision:string,text:string,source_path:string,updated_at:int}> $records Records map.
	 * @param string                                                                                                                $keep_id Newly written ID.
	 * @return array<string,array{schema_version:int,brief_id:string,revision:string,text:string,source_path:string,updated_at:int}>
	 */
	private static function trim_records( array $records, string $keep_id ): array {
		if ( count( $records ) <= self::MAX_RECORDS ) {
			return $records;
		}
		uasort(
			$records,
			static fn ( array $a, array $b ): int => $a['updated_at'] <=> $b['updated_at']
		);
		$excess = count( $records ) - self::MAX_RECORDS;
		foreach ( array_keys( $records ) as $id ) {
			if ( $excess < 1 ) {
				break;
			}
			if ( $id !== $keep_id ) {
				unset( $records[ $id ] );
				--$excess;
			}
		}
		return $records;
	}

	/**
	 * Read and verify one record after a write.
	 *
	 * @param string $option   Option name.
	 * @param string $brief_id Target ID.
	 * @return array{schema_version:int,brief_id:string,revision:string,text:string,source_path:string,updated_at:int}|null
	 */
	private function read_record( string $option, string $brief_id ): ?array {
		$raw = $this->read_raw( $option );
		if ( is_wp_error( $raw ) ) {
			return null;
		}
		$records = $this->decode_records( $raw );
		return is_array( $records ) && isset( $records[ $brief_id ] ) ? $records[ $brief_id ] : null;
	}

	/**
	 * Read the option directly past the object cache when $wpdb is available.
	 *
	 * @param string $option Option name.
	 * @return string|null|WP_Error Raw JSON string, null when absent, or DB error.
	 */
	private function read_raw( string $option ): string|null|WP_Error {
		global $wpdb;
		if ( isset( $wpdb ) && is_object( $wpdb ) && isset( $wpdb->options ) && method_exists( $wpdb, 'get_var' ) && method_exists( $wpdb, 'prepare' ) ) {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Authoritative readback bypasses the options cache for CAS.
			$value = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s LIMIT 1", $option ) );
			if ( isset( $wpdb->last_error ) && '' !== (string) $wpdb->last_error ) {
				return Failure::make( 'project_brief_unavailable', 503 );
			}
			return is_string( $value ) ? $value : null;
		}
		$value = get_option( $option, null );
		return is_string( $value ) ? $value : null;
	}

	/**
	 * Atomic byte-exact compare-and-set of the option JSON.
	 *
	 * @param string                                                                                                                $option   Option name.
	 * @param string|null                                                                                                           $expected Previous raw JSON or null when absent.
	 * @param array<string,array{schema_version:int,brief_id:string,revision:string,text:string,source_path:string,updated_at:int}> $records  Updated map.
	 */
	private function write_cas( string $option, ?string $expected, array $records ): bool {
		$encoded = wp_json_encode(
			array(
				'schema_version' => 1,
				'records'        => (object) $records,
			),
			JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
		);
		if ( ! is_string( $encoded ) ) {
			return false;
		}
		if ( $expected === $encoded ) {
			return true;
		}
		global $wpdb;
		if ( isset( $wpdb ) && is_object( $wpdb ) && isset( $wpdb->options ) && method_exists( $wpdb, 'query' ) && method_exists( $wpdb, 'prepare' ) ) {
			// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Byte-exact atomic compare-and-set is not possible via update_option().
			if ( null === $expected ) {
				$written = $wpdb->query( $wpdb->prepare( "INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, 'off')", $option, $encoded ) );
			} else {
				$written = $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value = %s, autoload = 'off' WHERE option_name = %s AND BINARY option_value = BINARY %s", $encoded, $option, $expected ) );
			}
			// phpcs:enable
			wp_cache_delete( $option, 'options' );
			wp_cache_delete( 'notoptions', 'options' );
			wp_cache_delete( 'alloptions', 'options' );
			return 1 === $written;
		}
		$current = get_option( $option, null );
		if ( null === $expected ) {
			return null === $current && add_option( $option, $encoded, '', false );
		}
		return is_string( $current ) && hash_equals( $expected, $current ) && update_option( $option, $encoded, false );
	}

	/**
	 * Validate stored JSON map structure.
	 *
	 * @param string|null $raw Raw option string.
	 * @return array<string,array{schema_version:int,brief_id:string,revision:string,text:string,source_path:string,updated_at:int}>|null
	 */
	private function decode_records( ?string $raw ): ?array {
		if ( null === $raw || '' === $raw ) {
			return array();
		}
		$decoded = json_decode( $raw, true, 16 );
		if ( ! is_array( $decoded ) || 1 !== ( $decoded['schema_version'] ?? null ) || ! is_array( $decoded['records'] ?? null ) ) {
			return null;
		}
		$records = array();
		foreach ( $decoded['records'] as $id => $item ) {
			if (
				! is_string( $id )
				|| ! self::valid_id( $id )
				|| ! is_array( $item )
				|| 1 !== ( $item['schema_version'] ?? null )
				|| ( $item['brief_id'] ?? null ) !== $id
				|| ! is_string( $item['revision'] ?? null )
				|| ! self::valid_revision( $item['revision'] )
				|| ! is_string( $item['text'] ?? null )
				|| '' === trim( $item['text'] )
				|| mb_strlen( $item['text'], 'UTF-8' ) > self::MAX_TEXT_LENGTH
				|| ! is_string( $item['source_path'] ?? null )
				|| ! self::valid_path( $item['source_path'] )
				|| ! is_int( $item['updated_at'] ?? null )
			) {
				return null;
			}
			if ( ! hash_equals( $item['revision'], self::revision( $id, $item['source_path'], $item['text'] ) ) ) {
				return null;
			}
			$records[ $id ] = array(
				'schema_version' => 1,
				'brief_id'       => $id,
				'revision'       => $item['revision'],
				'text'           => $item['text'],
				'source_path'    => $item['source_path'],
				'updated_at'     => $item['updated_at'],
			);
		}
		return $records;
	}
}
