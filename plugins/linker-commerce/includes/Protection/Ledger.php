<?php
/**
 * Atomic multi-dimensional admission, dispatch and recovery receipts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** One non-autoloaded native option commits the journal under a connection lock. */
final class Ledger {
	public const OPTION = 'linker_public_admission_ledger';
	public const POLICY = 'public-admission-519-v1';
	// Initial operational bounds, docs/specs/519-public-admission.md.
	private const RECEIPT_SECONDS   = DAY_IN_SECONDS;
	private const MAX_RECEIPTS      = 10000;
	private const MAX_DIMENSIONS    = 16;
	private const MAX_JOURNAL_BYTES = 8388608;
	private const LOCK_WAIT         = 1;
	private const MAX_LEASE         = 300;
	private const MAX_EVENTS        = 256;

	/**
	 * The clock can be fixed in real database fixtures.
	 *
	 * @param (callable():int)|null $clock Server clock.
	 */
	public function __construct( private mixed $clock = null ) {}

	/**
	 * Reserve all dimensions or none, preserving a replay's original outcome.
	 *
	 * @phpstan-impure
	 *
	 * @param string                                            $id UUID of this logical operation.
	 * @param string                                            $fingerprint HMAC of its subject, action and canonical input.
	 * @param Allowance[]                                       $allowances Server-selected dimensions.
	 * @param int                                               $lease Seconds before unused/in-flight recovery.
	 * @param list<array{source: Allowance, target: Allowance}> $carry Anonymous spend to import on login.
	 * @param string                                            $purpose Server-owned operation kind.
	 * @param string                                            $binding Optional private current-subject reference.
	 * @param string[]                                          $owners Additional private account associations, without another quota.
	 * @return array<string,mixed>|WP_Error Durable receipt or explicit refusal.
	 */
	public function reserve( string $id, string $fingerprint, array $allowances, int $lease, array $carry = array(), string $purpose = 'operation', string $binding = '', array $owners = array() ): array|WP_Error {
		$id = strtolower( $id );
		if ( ! wp_is_uuid( $id, 4 ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $fingerprint ) || array() === $allowances || count( $allowances ) > self::MAX_DIMENSIONS || count( $carry ) > self::MAX_DIMENSIONS || $lease < 1 || $lease > self::MAX_LEASE || 1 !== preg_match( '/\A[a-z0-9_]{1,40}\z/', $purpose ) || ( '' !== $binding && 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $binding ) ) ) {
			return self::error( 'input' );
		}
		if ( count( $owners ) > self::MAX_DIMENSIONS || count( array_filter( $owners, static fn ( string $owner ): bool => 1 === preg_match( '/\A[a-f0-9]{64}\z/', $owner ) ) ) !== count( $owners ) ) {
			return self::error( 'input' );
		}
		return $this->edit(
			static function ( array &$state, int $now ) use ( $id, $fingerprint, $allowances, $lease, $carry, $purpose, $binding, $owners ): array|WP_Error {
				if ( isset( $state['receipts'][ $id ] ) ) {
					$existing = $state['receipts'][ $id ];
					$same     = hash_equals( (string) $existing['fingerprint'], $fingerprint ) && $existing['purpose'] === $purpose && $existing['binding'] === $binding;
					self::event( $state, $now, $purpose, $same ? 'replay' : 'payload_changed' );
					return $same ? self::remaining( $existing, $state, $allowances, $now ) : self::error( 'payload_changed' );
				}
				if ( count( $state['receipts'] ) >= self::MAX_RECEIPTS ) {
					return self::error( 'capacity' );
				}
				$candidate = $state;
				foreach ( $carry as $link ) {
					if ( $link['source']->window <= 0 || $link['source']->window !== $link['target']->window || $link['source']->key( $now ) === $link['target']->key( $now ) || ! in_array( $link['target']->key( $now ), array_map( static fn ( Allowance $allowance ): string => $allowance->key( $now ), $allowances ), true ) ) {
						return self::error( 'input' );
					}
					$source = $link['source']->key( $now );
					$target = $link['target']->key( $now );
					$old    = $candidate['buckets'][ $source ] ?? array( 'used' => 0 );
					// The first account claims this anonymous history. A different
					// account on a shared browser never imports another user's spend.
					if ( isset( $old['claimed_to'] ) && $old['claimed_to'] !== $target ) {
						continue;
					}
					$held = 0;
					foreach ( $candidate['receipts'] as $receipt ) {
						if ( 'reserved' === $receipt['status'] ) {
							$held += (int) ( $receipt['debits'][ $source ]['units'] ?? 0 );
						}
					}
					$spent = max( 0, (int) $old['used'] - $held );
					$delta = max( 0, $spent - (int) ( $old['claimed_units'] ?? 0 ) );
					if ( $delta > 0 ) {
						$bucket                          = $candidate['buckets'][ $target ] ?? array(
							'used'  => 0,
							'end'   => $link['target']->ends( $now ),
							'owner' => $link['target']->owner(),
						);
						$bucket['used']                 += $delta;
						$candidate['buckets'][ $target ] = $bucket;
						$old['claimed_to']               = $target;
						$old['claimed_units']            = $spent;
						$candidate['buckets'][ $source ] = $old;
						foreach ( $candidate['receipts'] as $receipt_id => $receipt ) {
							if ( isset( $receipt['debits'][ $source ] ) && in_array( $receipt['status'], array( 'dispatched', 'completed', 'unresolved' ), true ) ) {
								$candidate['receipts'][ $receipt_id ]['owners'] = array_values( array_unique( array_merge( $receipt['owners'], array( $link['target']->owner() ) ) ) );
							}
						}
					}
				}
				$debits = array();
				foreach ( $allowances as $allowance ) {
					$key = $allowance->key( $now );
					if ( isset( $debits[ $key ] ) ) {
						return self::error( 'input' );
					}
					$bucket = $candidate['buckets'][ $key ] ?? array(
						'used'  => 0,
						'end'   => $allowance->ends( $now ),
						'owner' => $allowance->owner(),
					);
					if ( (int) $bucket['used'] + $allowance->units > $allowance->capacity ) {
						self::event( $state, $now, $purpose, 'quota', $allowance->name );
						return self::error(
							'quota',
							array(
								'dimension'   => $allowance->name,
								'retry_after' => self::retry( $state, $allowance, $now ),
							)
						);
					}
					$bucket['used']              += $allowance->units;
					$bucket['name']               = $allowance->name;
					$bucket['capacity']           = $allowance->capacity;
					$candidate['buckets'][ $key ] = $bucket;
					$debits[ $key ]               = array(
						'units'  => $allowance->units,
						'flight' => 0 === $allowance->window,
					);
				}
				$receipt                      = array(
					'status'      => 'reserved',
					'purpose'     => $purpose,
					'binding'     => $binding,
					'created_at'  => $now,
					'fingerprint' => $fingerprint,
					'lease_until' => $now + $lease,
					'retry_until' => $now + self::RECEIPT_SECONDS,
					'debits'      => $debits,
					'outcome'     => 0,
					'owners'      => array_values( array_unique( array_merge( $owners, array_map( static fn ( Allowance $allowance ): string => $allowance->owner(), $allowances ) ) ) ),
				);
				$candidate['receipts'][ $id ] = $receipt;
				$state                        = $candidate;
				self::event( $state, $now, $purpose, 'admitted' );
				return self::remaining( $receipt, $state, $allowances, $now );
			}
		);
	}

	/**
	 * Recover a previously admitted operation without reserving or dispatching it.
	 *
	 * @phpstan-impure
	 * @param string $id Stable operation UUID.
	 * @param string $fingerprint Same subject/action/input reference.
	 * @param bool   $retry Count an actual native-operation retry, not a staff read.
	 * @return array<string,mixed>|WP_Error Existing receipt or explicit unknown.
	 */
	public function lookup( string $id, string $fingerprint, bool $retry = false ): array|WP_Error {
		$id = strtolower( $id );
		return $this->edit(
			static function ( array &$state, int $now ) use ( $id, $fingerprint, $retry ): array|WP_Error {
				$receipt = $state['receipts'][ $id ] ?? null;
				if ( $retry && is_array( $receipt ) && hash_equals( (string) $receipt['fingerprint'], $fingerprint ) ) {
					self::event( $state, $now, $receipt['purpose'], 'replay' );
				}
				return is_array( $receipt ) && hash_equals( (string) $receipt['fingerprint'], $fingerprint ) ? $receipt : self::error( 'unknown_receipt' );
			}
		);
	}

	/**
	 * Check the native verification receipt before expensive reversible parsing.
	 * Dispatch still repeats this check inside its atomic transition (#521).
	 *
	 * @param array{id:string,binding:string,action:string,single:bool} $proof Signed proof reference.
	 * @param string                                                    $operation Reserved operation UUID.
	 * @return array<string,mixed>|WP_Error Safe validity, no provider work.
	 */
	public function verified( array $proof, string $operation ): array|WP_Error {
		return $this->edit(
			static function ( array &$state, int $now ) use ( $proof, $operation ): array|WP_Error {
				$receipt = $state['receipts'][ $operation ] ?? null;
				if ( ! is_array( $receipt ) || 'reserved' !== $receipt['status'] || $proof['action'] !== $receipt['purpose'] || $proof['binding'] !== $receipt['binding'] ) {
					return self::error( 'proof' );
				}
				return self::proof_error( $state, $proof, $operation, $now ) ?? array( 'valid' => true );
			}
		);
	}

	/**
	 * One predicate at pre-parse and atomic dispatch; neither trusts the MAC alone.
	 *
	 * @param array<string,mixed>                                       $state Private journal.
	 * @param array{id:string,binding:string,action:string,single:bool} $proof Checked reference.
	 * @param string                                                    $operation Current logical operation.
	 * @param int                                                       $now Server clock.
	 */
	private static function proof_error( array $state, array $proof, string $operation, int $now ): ?WP_Error {
		$parent  = $state['receipts'][ $proof['id'] ] ?? null;
		$purpose = 'verification_' . $proof['action'];
		if ( ! is_array( $parent ) || $purpose !== $parent['purpose'] || $proof['binding'] !== $parent['binding'] || 'completed' !== $parent['status'] || 1 !== $parent['outcome'] || $parent['created_at'] + Proof::LIFETIME <= $now ) {
			return self::error( 'proof' );
		}
		if ( $proof['single'] && isset( $parent['consumed_by'] ) && $parent['consumed_by'] !== $operation ) {
			return self::error( 'proof_reused' );
		}
		return null;
	}

	/**
	 * Mark the irreversible boundary before any upstream/business side effect.
	 *
	 * @phpstan-impure
	 * Only the winner dispatches; a replay cannot dispatch a second time.
	 *
	 * @param string                                                            $id UUID.
	 * @param string                                                            $fingerprint Bound input fingerprint.
	 * @param array{id:string,binding:string,action:string,single:bool}|array{} $proof Validated signed proof reference; empty for trusted background work.
	 * @return array<string,mixed>|WP_Error Updated receipt.
	 */
	public function dispatch( string $id, string $fingerprint, array $proof = array() ): array|WP_Error {
		return $this->transition( $id, $fingerprint, 'dispatch', 0, $proof );
	}

	/**
	 * A durable native result ID can be recovered without repeating the operation.
	 *
	 * @phpstan-impure
	 *
	 * @param string $id UUID.
	 * @param string $fingerprint Bound input fingerprint.
	 * @param int    $outcome Native record ID, or zero for a resource-only completion.
	 * @return array<string,mixed>|WP_Error Updated receipt.
	 */
	public function complete( string $id, string $fingerprint, int $outcome = 0 ): array|WP_Error {
		return $this->transition( $id, $fingerprint, 'complete', max( 0, $outcome ) );
	}

	/**
	 * Refund only a reservation that never crossed the dispatch boundary.
	 *
	 * @phpstan-impure
	 *
	 * @param string $id UUID.
	 * @param string $fingerprint Bound input fingerprint.
	 * @return array<string,mixed>|WP_Error Updated receipt.
	 */
	public function cancel( string $id, string $fingerprint ): array|WP_Error {
		return $this->transition( $id, $fingerprint, 'cancel', 0 );
	}

	/**
	 * Recovery and aggregate staff health share admission's authoritative read.
	 *
	 * @phpstan-impure
	 * @return array<string,mixed>|WP_Error Counts only; never private receipt data.
	 */
	public function summary(): array|WP_Error {
		return $this->edit(
			static function ( array &$state ): array {
				$counts = array();
				foreach ( $state['receipts'] as $receipt ) {
					$purpose = $receipt['purpose'];
					$status  = $receipt['status'];
					if ( str_starts_with( $purpose, 'verification_' ) && 'completed' === $status ) {
						$verification = Verification::from_code( $receipt['outcome'] );
						$status      .= '/' . $verification->status . '/' . $verification->reason;
					}
					$counts[ $purpose ][ $status ] = ( $counts[ $purpose ][ $status ] ?? 0 ) + 1;
				}
				$windows = array();
				foreach ( $state['buckets'] as $key => $bucket ) {
					if ( ! isset( $bucket['name'], $bucket['capacity'] ) ) {
						continue;
					}
					$name  = $bucket['name'];
					$left  = max( 0, $bucket['capacity'] - $bucket['used'] );
					$reset = $bucket['end'];
					if ( 0 === $reset ) {
						foreach ( $state['receipts'] as $receipt ) {
							if ( isset( $receipt['debits'][ $key ] ) && in_array( $receipt['status'], array( 'reserved', 'dispatched' ), true ) ) {
								$reset = max( $reset, $receipt['lease_until'] );
							}
						}
					}
					$window = $windows[ $name ] ?? array(
						'buckets'           => 0,
						'minimum_remaining' => $left,
						'reset_at'          => $reset,
					);
					++$window['buckets'];
					$window['minimum_remaining'] = min( $window['minimum_remaining'], $left );
					$window['reset_at']          = max( $window['reset_at'], $reset );
					$windows[ $name ]            = $window;
				}
				return array(
					'counts'   => $counts,
					'receipts' => count( $state['receipts'] ),
					'buckets'  => count( $state['buckets'] ),
					'windows'  => $windows,
					'events'   => array_values( $state['events'] ?? array() ),
					'policy'   => self::POLICY,
				);
			}
		);
	}

	/**
	 * Current safe diagnostics never contain the bucket key or subject.
	 *
	 * @param array<string,mixed> $receipt Durable result.
	 * @param array<string,mixed> $state Current journal.
	 * @param Allowance[]         $limits Current server policy.
	 * @param int                 $now Server time.
	 * @return array<string,mixed>
	 */
	private static function remaining( array $receipt, array $state, array $limits, int $now ): array {
		$receipt['allowances'] = array();
		foreach ( $limits as $limit ) {
			$bucket                  = $state['buckets'][ $limit->key( $now ) ] ?? array( 'used' => 0 );
			$receipt['allowances'][] = array(
				'dimension' => $limit->name,
				'remaining' => max( 0, $limit->capacity - $bucket['used'] ),
				'reset_at'  => $limit->ends( $now ),
			);
		}
		return $receipt;
	}

	/**
	 * Fixed-window reset or actual earliest sufficient lease recovery.
	 *
	 * @param array<string,mixed> $state Journal.
	 * @param Allowance           $limit Exhausted dimension.
	 * @param int                 $now Server time.
	 */
	private static function retry( array $state, Allowance $limit, int $now ): int {
		if ( $limit->window > 0 ) {
			return max( 1, $limit->ends( $now ) - $now );
		}
		$key      = $limit->key( $now );
		$free     = $limit->capacity - ( $state['buckets'][ $key ]['used'] ?? 0 );
		$releases = array();
		foreach ( $state['receipts'] as $receipt ) {
			if ( in_array( $receipt['status'], array( 'reserved', 'dispatched' ), true ) && isset( $receipt['debits'][ $key ] ) ) {
				$releases[ $receipt['lease_until'] ] = ( $releases[ $receipt['lease_until'] ] ?? 0 ) + $receipt['debits'][ $key ]['units'];
			}
		}
		ksort( $releases );
		foreach ( $releases as $at => $units ) {
			$free += $units;
			if ( $free >= $limit->units ) {
				return max( 1, $at - $now );
			}
		}
		return self::MAX_LEASE;
	}

	/**
	 * Bounded UTC-day aggregate reasons, without identity or request references.
	 *
	 * @param array<string,mixed> $state Journal.
	 * @param int                 $now Server time.
	 * @param string              $purpose Server-owned operation.
	 * @param string              $reason Stable reason code.
	 * @param string              $dimension Optional server-owned dimension.
	 */
	private static function event( array &$state, int $now, string $purpose, string $reason, string $dimension = '' ): void {
		$end               = ( intdiv( $now, DAY_IN_SECONDS ) + 1 ) * DAY_IN_SECONDS;
		$key               = hash( 'sha256', self::POLICY . '|' . $purpose . '|' . $reason . '|' . $dimension . '|' . $end );
		$state['events'] ??= array();
		if ( ! isset( $state['events'][ $key ] ) && count( $state['events'] ) >= self::MAX_EVENTS ) {
			return; // Diagnostics cannot make an otherwise admissible request fail.
		}
		$event = $state['events'][ $key ] ?? array(
			'purpose'   => $purpose,
			'reason'    => $reason,
			'dimension' => $dimension,
			'count'     => 0,
			'reset_at'  => $end,
			'policy'    => self::POLICY,
		);
		++$event['count'];
		$state['events'][ $key ] = $event;
	}

	/**
	 * Native privacy callbacks know only verified account/recipient owner hashes.
	 * Site/shared counters stay aggregated; erased receipts cannot be repopulated.
	 *
	 * @phpstan-impure
	 * @param string[] $owners Resolved private subject hashes.
	 * @param bool     $erase Remove linked payload after taking its export snapshot.
	 * @return array<string,mixed>|WP_Error Scoped export and removal count.
	 */
	public function privacy( array $owners, bool $erase ): array|WP_Error {
		return $this->edit(
			static function ( array &$state ) use ( $owners, $erase ): array {
				$keys = array();
				foreach ( $state['buckets'] as $key => $bucket ) {
					if ( in_array( $bucket['owner'], $owners, true ) ) {
						$keys[] = $key;
					}
				}
				// Anonymous spending imported into this account is linked evidence too.
				foreach ( $state['buckets'] as $key => $bucket ) {
					if ( in_array( $bucket['claimed_to'] ?? '', $keys, true ) ) {
						$keys[] = $key;
					}
				}
				$data = array();
				foreach ( $state['receipts'] as $id => $receipt ) {
					if ( array_intersect( $owners, $receipt['owners'] ) || array_intersect( $keys, array_keys( $receipt['debits'] ) ) ) {
						$data[] = array(
							'id'              => $id,
							'status'          => $receipt['status'],
							'purpose'         => $receipt['purpose'],
							'input_reference' => $receipt['fingerprint'],
							'outcome'         => $receipt['outcome'],
							'retry_until'     => $receipt['retry_until'],
						);
						if ( $erase ) {
							foreach ( $state['receipts'] as $parent_id => $parent ) {
								if ( ( $parent['consumed_by'] ?? '' ) === $id ) {
									// Retain single-use without retaining the erased record link.
									$state['receipts'][ $parent_id ]['consumed_by'] = 'erased';
								}
							}
							if ( in_array( $receipt['status'], array( 'reserved', 'dispatched' ), true ) ) {
								self::release( $state, $receipt, 'reserved' === $receipt['status'] );
							}
							// Keep only an opaque replay tombstone until its original expiry.
							$state['receipts'][ $id ] = array(
								'status'      => 'erased',
								'purpose'     => 'erased',
								'binding'     => '',
								'created_at'  => 0,
								'fingerprint' => '',
								'lease_until' => 0,
								'retry_until' => $receipt['retry_until'],
								'debits'      => array(),
								'outcome'     => 0,
								'owners'      => array(),
							);
						}
					}
				}
				$buckets = array();
				foreach ( $keys as $key ) {
					if ( isset( $state['buckets'][ $key ] ) ) {
						$buckets[ $key ] = array(
							'used'       => $state['buckets'][ $key ]['used'],
							'window_end' => $state['buckets'][ $key ]['end'],
						);
					}
				}
				if ( $erase ) {
					foreach ( $keys as $key ) {
						unset( $state['buckets'][ $key ] );
					}
				}
				return array(
					'data'    => $data,
					'buckets' => $buckets,
					'removed' => $erase ? count( $data ) + count( $buckets ) : 0,
				);
			}
		);
	}

	/**
	 * Serialized compare-and-transition, with no provider or business I/O.
	 *
	 * @param string                                                            $id UUID.
	 * @param string                                                            $fingerprint Bound input.
	 * @param string                                                            $operation Transition.
	 * @param int                                                               $outcome Native result.
	 * @param array{id:string,binding:string,action:string,single:bool}|array{} $proof Checked proof reference.
	 * @return array<string,mixed>|WP_Error Current state.
	 */
	private function transition( string $id, string $fingerprint, string $operation, int $outcome, array $proof = array() ): array|WP_Error {
		$id = strtolower( $id );
		if ( ! wp_is_uuid( $id, 4 ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $fingerprint ) ) {
			return self::error( 'input' );
		}
		return $this->edit(
			static function ( array &$state, int $now ) use ( $id, $fingerprint, $operation, $outcome, $proof ): array|WP_Error {
				$receipt = $state['receipts'][ $id ] ?? null;
				if ( ! is_array( $receipt ) || ! hash_equals( (string) $receipt['fingerprint'], $fingerprint ) ) {
					return self::error( 'unknown_receipt' );
				}
				$status = (string) $receipt['status'];
				if ( 'dispatch' === $operation && 'reserved' === $status ) {
					if ( array() !== $proof ) {
						$invalid = self::proof_error( $state, $proof, $id, $now );
						if ( null !== $invalid ) {
							return $invalid;
						}
						if ( $proof['single'] ) {
							$state['receipts'][ $proof['id'] ]['consumed_by'] = $id;
						}
					}
					$receipt['status'] = 'dispatched';
				} elseif ( 'cancel' === $operation && 'reserved' === $status ) {
					self::release( $state, $receipt, true );
					$receipt['status'] = 'cancelled';
				} elseif ( 'complete' === $operation && in_array( $status, array( 'dispatched', 'unresolved' ), true ) ) {
					if ( 'dispatched' === $status ) {
						self::release( $state, $receipt, false );
					}
					$receipt['status']  = 'completed';
					$receipt['outcome'] = $outcome;
				} elseif ( 'complete' !== $operation || 'completed' !== $status || $receipt['outcome'] !== $outcome ) {
					return self::error( 'already_' . $status );
				}
				$state['receipts'][ $id ] = $receipt;
				return $receipt;
			}
		);
	}

	/**
	 * Release leases exactly once; dispatched spending is never refunded.
	 *
	 * @param array<string,mixed> $state Journal.
	 * @param array<string,mixed> $receipt Receipt.
	 * @param bool                $refund Include fixed-window spending only before dispatch.
	 */
	private static function release( array &$state, array $receipt, bool $refund ): void {
		foreach ( $receipt['debits'] as $key => $debit ) {
			if ( isset( $state['buckets'][ $key ] ) && ( $refund || $debit['flight'] ) ) {
				$state['buckets'][ $key ]['used'] = max( 0, (int) $state['buckets'][ $key ]['used'] - (int) $debit['units'] );
			}
		}
	}

	/**
	 * Recovery runs under the same lock and in the same atomic commit.
	 *
	 * @param array<string,mixed> $state Journal.
	 * @param int                 $now Server clock.
	 */
	private static function recover( array &$state, int $now ): void {
		foreach ( $state['events'] ?? array() as $key => $event ) {
			if ( $event['reset_at'] <= $now ) {
				unset( $state['events'][ $key ] );
			}
		}
		foreach ( $state['receipts'] as $id => $receipt ) {
			if ( in_array( $receipt['status'], array( 'reserved', 'dispatched' ), true ) && $receipt['lease_until'] <= $now ) {
				self::release( $state, $receipt, 'reserved' === $receipt['status'] );
				$state['receipts'][ $id ]['status'] = 'reserved' === $receipt['status'] ? 'expired' : 'unresolved';
			}
			if ( $receipt['retry_until'] <= $now ) {
				unset( $state['receipts'][ $id ] );
			}
		}
		foreach ( $state['buckets'] as $key => $bucket ) {
			if ( ( $bucket['end'] > 0 && $bucket['end'] <= $now ) || ( 0 === $bucket['end'] && 0 === $bucket['used'] ) ) {
				unset( $state['buckets'][ $key ] );
			}
		}
	}

	/**
	 * Native options avoid a new table; one journal prevents partial multi-key spend.
	 * No object cache sits between the authoritative read/compare/write/readback.
	 *
	 * @param callable(array<string,mixed>&,int):(array<string,mixed>|WP_Error) $work State mutation.
	 * @return array<string,mixed>|WP_Error Result, unavailable on any storage failure.
	 */
	private function edit( callable $work ): array|WP_Error {
		global $wpdb;
		$name = 'linker-admission-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Connection mutex and atomic journal readback have no WordPress options API equivalent.
		$taken = $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, %d)', $name, self::LOCK_WAIT ) );
		if ( '1' !== (string) $taken ) {
			return self::error( 'busy' );
		}
		try {
			$wpdb->query( $wpdb->prepare( "INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, 'off')", self::OPTION, '{"version":1,"buckets":{},"receipts":{}}' ) );
			$raw   = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", self::OPTION ) );
			$state = self::decode( $raw );
			$now   = is_callable( $this->clock ) ? (int) ( $this->clock )() : time();
			self::recover( $state, $now );
			$result  = $work( $state, $now );
			$encoded = wp_json_encode( $state );
			if ( ! is_string( $encoded ) || strlen( $encoded ) > self::MAX_JOURNAL_BYTES ) {
				return self::error( 'storage' );
			}
			// wpdb may reconnect and retry after losing its connection-owned lock.
			// The write itself checks ownership and the exact original snapshot.
			$updated = $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value = %s, autoload = 'off' WHERE option_name = %s AND BINARY option_value = BINARY %s AND IS_USED_LOCK(%s) = CONNECTION_ID()", $encoded, self::OPTION, $raw, $name ) );
			if ( false === $updated || ( $raw !== $encoded && 1 !== $updated ) ) {
				return self::error( 'storage' );
			}
			$readback = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s AND IS_USED_LOCK(%s) = CONNECTION_ID()", self::OPTION, $name ) );
			if ( $readback !== $encoded ) {
				return self::error( 'storage' );
			}
			return $result;
		} catch ( \Throwable $error ) {
			return self::error( 'storage' );
		} finally {
			wp_cache_delete( self::OPTION, 'options' );
			wp_cache_delete( 'notoptions', 'options' );
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
		}
		// phpcs:enable
	}

	/**
	 * Corrupt or unknown journal versions fail closed, never reset allowance.
	 *
	 * @param mixed $raw Database JSON.
	 * @return array<string,mixed> Checked journal.
	 * @throws \RuntimeException Invalid state requires explicit repair.
	 */
	private static function decode( mixed $raw ): array {
		$state = is_string( $raw ) && strlen( $raw ) <= self::MAX_JOURNAL_BYTES ? json_decode( $raw, true ) : null;
		if ( ! is_array( $state ) || 1 !== ( $state['version'] ?? null ) || ! is_array( $state['buckets'] ?? null ) || ! is_array( $state['receipts'] ?? null ) ) {
			throw new \RuntimeException( 'ledger_invalid' );
		}
		foreach ( $state['buckets'] as $bucket ) {
			if ( ! is_array( $bucket ) || ! is_int( $bucket['used'] ?? null ) || $bucket['used'] < 0 || ! is_int( $bucket['end'] ?? null ) || $bucket['end'] < 0 || ! is_string( $bucket['owner'] ?? null ) ) {
				throw new \RuntimeException( 'ledger_invalid_bucket' );
			}
			if ( ( isset( $bucket['name'] ) || isset( $bucket['capacity'] ) ) && ( ! is_string( $bucket['name'] ?? null ) || ! is_int( $bucket['capacity'] ?? null ) || $bucket['capacity'] < 1 ) ) {
				throw new \RuntimeException( 'ledger_invalid_policy' );
			}
		}
		if ( isset( $state['events'] ) && ( ! is_array( $state['events'] ) || count( $state['events'] ) > self::MAX_EVENTS ) ) {
			throw new \RuntimeException( 'ledger_invalid_events' );
		}
		foreach ( $state['events'] ?? array() as $event ) {
			if ( ! is_array( $event ) || ! is_string( $event['purpose'] ?? null ) || ! is_string( $event['reason'] ?? null ) || ! is_string( $event['dimension'] ?? null ) || ! is_string( $event['policy'] ?? null ) || ! is_int( $event['count'] ?? null ) || $event['count'] < 1 || ! is_int( $event['reset_at'] ?? null ) || $event['reset_at'] < 0 ) {
				throw new \RuntimeException( 'ledger_invalid_event' );
			}
		}
		foreach ( $state['receipts'] as $receipt ) {
			if ( ! is_array( $receipt ) || ! is_string( $receipt['purpose'] ?? null ) || ! is_string( $receipt['binding'] ?? null ) || ! is_string( $receipt['fingerprint'] ?? null ) || ! in_array( $receipt['status'] ?? '', array( 'reserved', 'dispatched', 'unresolved', 'completed', 'cancelled', 'expired', 'erased' ), true ) || ! is_int( $receipt['created_at'] ?? null ) || ! is_int( $receipt['lease_until'] ?? null ) || ! is_int( $receipt['retry_until'] ?? null ) || ! is_array( $receipt['debits'] ?? null ) || ! is_int( $receipt['outcome'] ?? null ) || ! is_array( $receipt['owners'] ?? null ) || count( array_filter( $receipt['owners'], 'is_string' ) ) !== count( $receipt['owners'] ) ) {
				throw new \RuntimeException( 'ledger_invalid_receipt' );
			}
			foreach ( $receipt['debits'] as $debit ) {
				if ( ! is_array( $debit ) || ! is_int( $debit['units'] ?? null ) || $debit['units'] <= 0 || ! is_bool( $debit['flight'] ?? null ) ) {
					throw new \RuntimeException( 'ledger_invalid_debit' );
				}
			}
		}
		return $state;
	}

	/**
	 * Callers localize fixed codes; no raw input or DB/provider error is exposed.
	 *
	 * @param string              $reason Fixed reason.
	 * @param array<string,mixed> $data Safe retry/dimension data.
	 */
	private static function error( string $reason, array $data = array() ): WP_Error {
		return new WP_Error( 'linker_admission_' . $reason, 'Public admission could not complete.', $data );
	}
}
