<?php
/**
 * Transport-specific, atomic rolling budgets.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * Allocations and evidence are documented in docs/specs/545-mail-capacity/SPEC.md.
 */
final class Throttle {

	/**
	 * Untouched legacy history, conservatively imported into both pools once.
	 */
	public const OPTION       = 'linker_commerce_mail_sends';
	public const PER_MINUTE   = 8;
	public const PER_DAY      = 80;
	public const SMTP_PER_DAY = 400;
	public const PHP_RESERVE  = 16;
	public const SMTP_RESERVE = 40;
	public const PHP          = 'php';
	public const SMTP         = 'smtp';

	/**
	 * Create the atomic budget boundary.
	 *
	 * @param BudgetLedger $ledger Atomic storage.
	 * @param InternalSmtp $smtp   Transport configuration only, no connection.
	 */
	public function __construct( private readonly BudgetLedger $ledger = new OptionBudgetLedger(), private readonly InternalSmtp $smtp = new InternalSmtp() ) {
	}

	/**
	 * Read the next slot in one transport.
	 *
	 * @param int    $now       Unix time.
	 * @param string $transport SMTP or PHP.
	 * @param bool   $critical  Trusted producer priority.
	 */
	public function next_slot( int $now, string $transport = self::PHP, bool $critical = false ): int {
		return $this->slot( $now, $transport, $critical, false );
	}

	/**
	 * Read the original message transport and priority slot.
	 *
	 * @param int     $now      Unix time.
	 * @param Message $message  Original queued message.
	 * @param bool    $critical Staff-authorized job promotion.
	 */
	public function next_message_slot( int $now, Message $message, bool $critical = false ): int {
		return $this->next_slot( $now, $this->transport( $message ), $critical || $message->critical );
	}

	/**
	 * Select a configured transport without connecting.
	 *
	 * @param Message $message Original queued message.
	 */
	public function transport( Message $message ): string {
		return $message->is_internal() && $this->smtp->available() ? self::SMTP : self::PHP;
	}

	/**
	 * Atomically charge only when a slot is available.
	 *
	 * @param int    $now       Unix time.
	 * @param string $transport Actual attempt channel.
	 * @param bool   $critical  Trusted producer priority.
	 */
	public function reserve( int $now, string $transport = self::PHP, bool $critical = false ): int {
		return $this->slot( $now, $transport, $critical, true );
	}

	/**
	 * Legacy callers must obey the same atomic boundary.
	 *
	 * @param int $now Unix time.
	 */
	public function record( int $now ): void {
		$this->reserve( $now );
	}

	/**
	 * Find or reserve one slot under the storage mutex.
	 *
	 * @param int    $now       Unix time.
	 * @param string $transport Actual attempt channel.
	 * @param bool   $critical  Trusted producer priority.
	 * @param bool   $reserve   Whether to charge the slot.
	 */
	private function slot( int $now, string $transport, bool $critical, bool $reserve ): int {
		if ( ! in_array( $transport, array( self::PHP, self::SMTP ), true ) ) {
			return $now + DAY_IN_SECONDS;
		}
		$result = $this->ledger->transact(
			static function ( array $state ) use ( $now, $transport, $critical, $reserve ): array {
				$entries = $state['entries'] ?? array();
				if ( ! isset( $state['entries'] ) ) {
					foreach ( is_array( $state['legacy'] ?? null ) ? $state['legacy'] : array() as $time ) {
						if ( is_int( $time ) ) {
							$entries[] = array(
								'time'      => $time,
								'transport' => self::PHP,
								'origin'    => 'legacy',
							);
							$entries[] = array(
								'time'      => $time,
								'transport' => self::SMTP,
								'origin'    => 'legacy',
							);
						}
					}
				}
				$all_entries = $entries;
				$entries     = array_values( array_filter( is_array( $entries ) ? $entries : array(), static fn ( $entry ): bool => is_array( $entry ) && is_int( $entry['time'] ?? null ) && $entry['time'] > $now - DAY_IN_SECONDS && in_array( $entry['transport'] ?? '', array( self::PHP, self::SMTP ), true ) ) );
				$times       = array_column( array_filter( $entries, static fn ( array $entry ): bool => $entry['transport'] === $transport ), 'time' );
				sort( $times );
				$minute = array_values( array_filter( $times, static fn ( int $time ): bool => $time > $now - MINUTE_IN_SECONDS ) );
				$limit  = self::SMTP === $transport ? self::SMTP_PER_DAY : self::PER_DAY;
				$limit -= $critical ? 0 : ( self::SMTP === $transport ? self::SMTP_RESERVE : self::PHP_RESERVE );
				$slot   = true === ( $state['paused'] ?? false ) ? $now + MINUTE_IN_SECONDS : $now;
				if ( count( $minute ) >= self::PER_MINUTE ) {
					$slot = max( $slot, $minute[ count( $minute ) - self::PER_MINUTE ] + MINUTE_IN_SECONDS );
				}
				if ( count( $times ) >= $limit ) {
						$slot = max( $slot, $times[ count( $times ) - $limit ] + DAY_IN_SECONDS );
				}
				if ( $reserve && $slot === $now ) {
					$entries[] = array(
						'time'      => $now,
						'transport' => $transport,
						'origin'    => 'attempt',
						'id'        => $state['next_id'] ?? 1,
					);
				}
				return array(
					'state' => array_merge(
						$state,
						array(
							'entries' => $reserve ? $entries : $all_entries,
							'next_id' => ( $state['next_id'] ?? 1 ) + ( $reserve && $slot === $now ? 1 : 0 ),
						)
					),
					'slot'  => $slot,
				);
			},
			$reserve
		);
		return $result ?? $now + 1;
	}
}
