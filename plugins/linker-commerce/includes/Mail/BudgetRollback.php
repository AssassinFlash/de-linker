<?php
/** Recoverable migration before an old-code mail rollback.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Mail;

use WP_Error;

/** The sending fence persists separately from any worker process. */
final class BudgetRollback {
	/** Pause only sending; customer submissions and durable jobs remain available. */
	public function pause(): bool {
		return null !== ( new OptionBudgetLedger() )->transact(
			static function ( array $state ): array {
				$state['paused'] = true;
				return array(
					'state' => $state,
					'slot'  => 0,
				);
			}
		);
	}

	/**
	 * Append unprojected real attempts, or reconcile old-code sends before resuming.
	 *
	 * @param bool $resume Reconcile the preserved legacy prefix and resume new code.
	 * @return array<string, int|string|bool>|WP_Error Safe operational receipt.
	 * @phpstan-impure
	 * @throws \RuntimeException Internally caught validation failures roll back both writes.
	 */
	public function transfer( bool $resume = false ): array|WP_Error {
		global $wpdb;
		$database = defined( 'DB_NAME' ) ? (string) constant( 'DB_NAME' ) : '';
		$name     = 'linker-mail-budget-' . md5( $database . '/' . $wpdb->prefix );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- One transaction atomically projects both options under the production reservation mutex.
		if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $name ) ) ) {
			return new WP_Error( 'mail_budget_busy', 'A mail budget operation is in progress.' );
		}
		$started = false;
		try {
			// Never commit or roll back an enclosing WooCommerce transaction.
			if ( ! BudgetTransaction::begin() ) {
				return new WP_Error( 'mail_budget_transaction_active', 'Run the budget migration outside another transaction.' );
			}
			$started = true;
			$raw     = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s FOR UPDATE", OptionBudgetLedger::OPTION ) );
			$state   = is_string( $raw ) ? json_decode( $raw, true ) : null;
			if ( ! is_array( $state ) || true !== ( $state['paused'] ?? false ) || ! is_array( $state['entries'] ?? null ) ) {
				throw new \RuntimeException( 'pause_required' );
			}
			$legacy_raw = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s FOR UPDATE", Throttle::OPTION ) );
			$legacy     = is_string( $legacy_raw ) ? maybe_unserialize( $legacy_raw ) : array();
			if ( ! is_array( $legacy ) || '' !== $wpdb->last_error ) {
				throw new \RuntimeException( 'legacy_unreadable' );
			}
			$before   = count( $legacy );
			$appended = 0;
			$imported = 0;
			$known    = is_array( $state['rollback_legacy'] ?? null ) ? $state['rollback_legacy'] : $legacy;
			$counts   = array();
			foreach ( $known as $stamp ) {
				$key            = (string) wp_json_encode( $stamp );
				$counts[ $key ] = ( $counts[ $key ] ?? 0 ) + 1;
			}
			foreach ( $legacy as $stamp ) {
				$key = (string) wp_json_encode( $stamp );
				if ( ( $counts[ $key ] ?? 0 ) > 0 ) {
					--$counts[ $key ];
				} elseif ( is_int( $stamp ) ) {
					foreach ( array( Throttle::PHP, Throttle::SMTP ) as $transport ) {
						$state['entries'][] = array(
							'time'      => $stamp,
							'transport' => $transport,
							'origin'    => 'legacy',
						);
					}
					++$imported;
				}
			}
			foreach ( $known as $stamp ) {
				if ( ( $counts[ (string) wp_json_encode( $stamp ) ] ?? 0 ) > 0 && ( ! is_int( $stamp ) || $stamp > time() - DAY_IN_SECONDS ) ) {
					throw new \RuntimeException( 'recent_legacy_history_changed' );
				}
			}
			if ( $resume ) {
				$state['paused'] = false;
			} else {
				$projected = is_array( $state['projected'] ?? null ) ? $state['projected'] : array();
				foreach ( $state['entries'] as $entry ) {
					if ( 'attempt' === ( $entry['origin'] ?? '' ) && is_int( $entry['id'] ?? null ) && is_int( $entry['time'] ?? null ) && ! in_array( $entry['id'], $projected, true ) ) {
						$legacy[]    = $entry['time'];
						$projected[] = $entry['id'];
						++$appended;
					}
				}
				$state['projected'] = $projected;
			}
			$state['rollback_legacy']       = $legacy;
			$state['rollback_prefix_count'] = count( $legacy );
			$state['rollback_prefix_hash']  = hash( 'sha256', (string) wp_json_encode( $legacy ) );
			$encoded                        = wp_json_encode( $state );
			$legacy_encoded                 = maybe_serialize( $legacy );
			if ( false === $encoded || false === $wpdb->query( $wpdb->prepare( "INSERT INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, 'off') ON DUPLICATE KEY UPDATE option_value = VALUES(option_value)", Throttle::OPTION, $legacy_encoded ) ) || false === $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value = %s WHERE option_name = %s", $encoded, OptionBudgetLedger::OPTION ) ) ) {
				throw new \RuntimeException( 'budget_write_failed' );
			}
			if ( $legacy_encoded !== $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", Throttle::OPTION ) ) || $encoded !== $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", OptionBudgetLedger::OPTION ) ) ) {
				throw new \RuntimeException( 'budget_readback_failed' );
			}
			if ( false === $wpdb->query( 'COMMIT' ) ) {
				throw new \RuntimeException( 'budget_commit_failed' );
			}
			$started = false;
			foreach ( array( Throttle::OPTION, OptionBudgetLedger::OPTION, 'notoptions', 'alloptions' ) as $key ) {
				wp_cache_delete( $key, 'options' );
			}
			return array(
				'paused'        => ! $resume,
				'before'        => $before,
				'after'         => count( $legacy ),
				'appended'      => $appended,
				'imported'      => $imported,
				'legacy_sha256' => $state['rollback_prefix_hash'],
			);
		} catch ( \Throwable $error ) {
			return new WP_Error( 'mail_budget_transfer_failed', 'The budget migration did not complete. Keep the current code and verify that sending is paused before retrying.' );
		} finally {
			if ( $started ) {
				$wpdb->query( 'ROLLBACK' );
			}
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
		}
		// phpcs:enable
	}
}
