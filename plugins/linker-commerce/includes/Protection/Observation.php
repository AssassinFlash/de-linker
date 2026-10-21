<?php
/**
 * Non-blocking admission observations use the same atomic budget mechanics.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Shadow receipts never authorize or prevent the original native operation. */
final class Observation {
	/**
	 * Reserve only the shadow accounting; an error remains advisory.
	 *
	 * @param Ledger                                         $ledger Shared journal.
	 * @param string                                         $action Server-owned public action.
	 * @param string                                         $id Native logical operation UUID.
	 * @param array<string,mixed>                            $payload Canonical semantic input.
	 * @param Allowance[]                                    $limits Server policy.
	 * @param int                                            $lease In-flight recovery.
	 * @param list<array{source:Allowance,target:Allowance}> $carry Login associations.
	 * @return array<string,mixed> Non-blocking permit and safe advisory diagnostic.
	 */
	public static function reserve( Ledger $ledger, string $action, string $id, array $payload, array $limits, int $lease, array $carry ): array {
		$permit   = array(
			'mode'     => 'observe',
			'enforced' => false,
		);
		$identity = Identity::current();
		if ( is_wp_error( $identity ) || ! Actions::valid( $action ) || ! wp_is_uuid( $id, 4 ) ) {
			return $permit + array( 'advisory' => array( 'reason' => 'unavailable' ) );
		}
		$fingerprint = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fingerprint ) ) {
			return $permit + array( 'advisory' => array( 'reason' => 'input' ) );
		}
		$result = $ledger->reserve( $id, $fingerprint, $limits, $lease, $carry, 'observe_' . $action, $identity->binding(), $identity->owners() );
		if ( is_wp_error( $result ) ) {
			return $permit + array( 'advisory' => self::failure( $result ) );
		}
		return $permit + array(
			'shadow'   => array(
				'id'          => strtolower( $id ),
				'fingerprint' => $fingerprint,
			),
			'advisory' => array(
				'reason'     => $result['status'],
				'allowances' => $result['allowances'],
			),
		);
	}

	/**
	 * Preserve observed spending/recovery without changing the native flow.
	 *
	 * @param Ledger              $ledger Shared journal.
	 * @param array<string,mixed> $permit Original trusted observation.
	 * @param string              $operation dispatch, complete or cancel.
	 * @param int                 $outcome Native result reference.
	 * @return array<string,mixed> Always non-blocking.
	 */
	public static function advance( Ledger $ledger, array $permit, string $operation, int $outcome = 0 ): array {
		if ( ! isset( $permit['shadow'] ) ) {
			return $permit;
		}
		$id          = $permit['shadow']['id'];
		$fingerprint = $permit['shadow']['fingerprint'];
		$result      = match ( $operation ) {
			'dispatch' => $ledger->dispatch( $id, $fingerprint ),
			'complete' => $ledger->complete( $id, $fingerprint, $outcome ),
			default => $ledger->cancel( $id, $fingerprint ),
		};
		$permit['advisory'] = is_wp_error( $result ) ? self::failure( $result ) : array( 'reason' => $result['status'] );
		return $permit;
	}

	/**
	 * Fixed error keys and safe quota timing contain no customer content.
	 *
	 * @param WP_Error $error Journal outcome.
	 * @return array<string,mixed>
	 */
	private static function failure( WP_Error $error ): array {
		return array(
			'reason' => $error->get_error_code(),
			'quota'  => $error->get_error_data(),
		);
	}
}
