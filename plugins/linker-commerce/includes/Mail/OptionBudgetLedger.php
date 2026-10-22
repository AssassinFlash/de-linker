<?php
/**
 * Connection-serialized transport budgets.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * Direct SQL avoids cross-worker option-cache races.
 */
final class OptionBudgetLedger implements BudgetLedger {

	public const OPTION = 'linker_commerce_mail_transport_sends';

	/**
	 * Run one cache-free atomic operation.
	 *
	 * @param callable $work Mutation.
	 * @param bool     $write Whether to commit a change, or only inspect a fresh snapshot.
	 * @phpstan-param callable(array<string, mixed>): array{state: array<string, mixed>, slot: int} $work
	 */
	public function transact( callable $work, bool $write = true ): ?int {
		global $wpdb;
		$database = isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) ? $wpdb->dbname : ( defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '' );
		$name     = 'linker-mail-budget-' . md5( $database . '/' . $wpdb->prefix );
     // phpcs:disable WordPress.DB.DirectDatabaseQuery -- Atomic budget reservation needs a connection mutex and cache-free reads.
		if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $name ) ) ) {
			return null;
		}
		$started = false;
		try {
			if ( $write ) {
				if ( ! BudgetTransaction::begin() ) {
					return null;
				}
				$started = true;
			}
			$raw = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", self::OPTION ) );
			if ( $this->failed() ) {
				return null;
			}
			$state = is_string( $raw ) ? json_decode( $raw, true ) : null;
			if ( null !== $raw && ! is_array( $state ) ) {
				return null;
			}
			if ( null !== $raw && ( ! isset( $state['entries'] ) || ! is_array( $state['entries'] ) ) ) {
				return null;
			}
			if ( null === $raw ) {
				$legacy  = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", Throttle::OPTION ) );
				$times   = is_string( $legacy ) ? maybe_unserialize( $legacy ) : array();
				$entries = array();
				foreach ( is_array( $times ) ? $times : array() as $stamp ) {
					if ( is_int( $stamp ) ) {
						foreach ( array( Throttle::PHP, Throttle::SMTP ) as $transport ) {
							$entries[] = array(
								'time'      => $stamp,
								'transport' => $transport,
								'origin'    => 'legacy',
							);
						}
					}
				}
				$state = array(
					'entries' => $entries,
					'next_id' => 1,
				);
			}
			if ( $this->failed() ) {
				return null;
			}
			if ( isset( $state['next_id'] ) && ( ! is_int( $state['next_id'] ) || $state['next_id'] < 1 ) ) {
				return null;
			}
			if ( isset( $state['paused'] ) && ! is_bool( $state['paused'] ) ) {
				return null;
			}
			if ( isset( $state['entries'] ) ) {
				foreach ( $state['entries'] as $entry ) {
					if ( ! is_array( $entry ) || ! is_int( $entry['time'] ?? null ) || ! in_array( $entry['transport'] ?? '', array( Throttle::PHP, Throttle::SMTP ), true ) || ( 'attempt' === ( $entry['origin'] ?? '' ) && ( ! is_int( $entry['id'] ?? null ) || $entry['id'] < 1 || $entry['id'] >= ( $state['next_id'] ?? 1 ) ) ) ) {
						return null;
					}
				}
			}
			$normalized = isset( $state['entries'] ) ? array( 'entries' => $state['entries'] ) : array( 'legacy' => $state['legacy'] );
			foreach ( array( 'paused', 'next_id', 'projected', 'rollback_prefix_count', 'rollback_prefix_hash', 'rollback_legacy' ) as $key ) {
				if ( isset( $state[ $key ] ) ) {
					$normalized[ $key ] = $state[ $key ];
				}
			}
			$state  = $normalized;
			$result = $work( $state );
			if ( ! $write ) {
				return $result['slot'];
			}
			$written = $wpdb->query( $wpdb->prepare( "INSERT INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, 'off') ON DUPLICATE KEY UPDATE option_value = VALUES(option_value), autoload = 'off'", self::OPTION, wp_json_encode( $result['state'] ) ) );
			if ( false === $written ) {
				return null;
			}
			if ( false === $wpdb->query( 'COMMIT' ) ) {
				return null;
			}
			$started = false;
			wp_cache_delete( self::OPTION, 'options' );
			wp_cache_delete( 'notoptions', 'options' );
			return $result['slot'];
		} catch ( \Throwable $error ) {
			return null;
		} finally {
			if ( $started ) {
				$wpdb->query( 'ROLLBACK' );
			}
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
		}
     // phpcs:enable
	}
	/**
	 * Read mutable database connection state after each query.
	 *
	 * @phpstan-impure
	 */
	private function failed(): bool {
		global $wpdb;
		return '' !== $wpdb->last_error;
	}
}
