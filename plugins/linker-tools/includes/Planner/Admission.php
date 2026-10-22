<?php
/**
 * Planner write quotas through the existing native admission journal.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use WP_Error;

/** Native quota identity never decides the project principal. */
final class Admission {

	/**
	 * Admit a native write once and preserve uncertain dispatch receipts.
	 *
	 * @param Principal           $principal Independently verified owner.
	 * @param string              $path Allowlisted server path.
	 * @param array<string,mixed> $command Valid JSON object, without coercion.
	 * @param string              $body Original bounded request bytes.
	 * @param Transport           $transport Private transport.
	 * @return array{status:int,type:string,body:string}|WP_Error Private reply or admission refusal.
	 */
	public function send( Principal $principal, string $path, array $command, string $body, Transport $transport ): array|WP_Error {
		$policy = $this->policy( $path );
		if ( null === $policy ) {
			return $transport->call( $principal, $path, $body );
		}
		// The engine's immutable command receipt outlives the native journal's
		// one-day resource receipt. Recover it before reserving another unit.
		$previous = $transport->call( $principal, 'operations/replay/' . $path, $body );
		if ( is_wp_error( $previous ) || $previous['status'] >= 400 ) {
			return $previous;
		}
		$known = json_decode( $previous['body'] );
		if ( ! $known instanceof \stdClass || 1 !== ( $known->schema_version ?? null ) || ! in_array( $known->status ?? null, array( 'absent', 'replayed' ), true ) || ! str_starts_with( $previous['type'], 'application/json' ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		if ( 'replayed' === $known->status ) {
			if ( ! ( $known->result ?? null ) instanceof \stdClass ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			$acknowledged = $this->acknowledge( $principal, $path, $command, $body );
			if ( is_wp_error( $acknowledged ) ) {
				return $acknowledged;
			}
			$payload = wp_json_encode( $known->result, JSON_PRESERVE_ZERO_FRACTION );
			return is_string( $payload ) ? array(
				'status' => 200,
				'type'   => 'application/json',
				'body'   => $payload,
			) : Failure::make( 'invalid_reply', 502 );
		}
		if ( ! class_exists( Ledger::class ) || ! class_exists( Identity::class ) || ! is_string( $command['key'] ?? null ) || ! wp_is_uuid( $command['key'], 4 ) ) {
			return Failure::make( 'admission', 400 );
		}
		$quota = Identity::current();
		if ( is_wp_error( $quota ) ) {
			return $quota;
		}
		list( $name, $guest, $account, $window, $site ) = $policy;
		$signed = '' !== $quota->account;
		$limits = array( new Allowance( $name, $quota->browser, $signed ? $account : $guest, $window ), new Allowance( $name . '_site', 'site', $site, $window ) );
		$carry  = array();
		if ( $signed ) {
			$target   = new Allowance( $name, $quota->account, $account, $window );
			$limits[] = $target;
			$carry[]  = array(
				'source' => new Allowance( $name, $quota->browser, $guest, $window ),
				'target' => $target,
			);
		}
		$id          = $command['key'];
		$fingerprint = $this->fingerprint( $principal, $path, $body );
		$ledger      = new Ledger();
		// This lease covers only bounded RPC dispatch, not queued numerical work.
		$receipt = $ledger->reserve( $id, $fingerprint, $limits, 30, $carry, 'planner_write', $quota->binding(), $quota->owners() );
		if ( is_wp_error( $receipt ) ) {
			return $receipt;
		}
		$status = $receipt['status'] ?? '';
		if ( 'reserved' === $status ) {
			$dispatched = $ledger->dispatch( $id, $fingerprint );
			if ( is_wp_error( $dispatched ) ) {
				return $dispatched;
			}
		} elseif ( ! in_array( $status, array( 'dispatched', 'unresolved', 'completed' ), true ) ) {
			return Failure::make( 'operation_expired', 409 );
		}
		// An uncertain/repeated request reuses the same private command key.
		// The native journal does not infer that an upstream timeout did no work.
		$reply = $transport->call( $principal, $path, $body );
		if ( ! is_wp_error( $reply ) ) {
			$completed = $ledger->complete( $id, $fingerprint );
			if ( is_wp_error( $completed ) ) {
				return Failure::make( 'receipt_persistence', 503 );
			}
		}
		return $reply;
	}

	/**
	 * Close a still-present uncertain receipt after the engine confirms it.
	 * Missing/expired native receipts require no new reservation.
	 *
	 * @param Principal           $principal Verified owner.
	 * @param string              $path Server-selected command.
	 * @param array<string,mixed> $command Parsed command.
	 * @param string              $body Exact retry bytes.
	 * @return true|WP_Error Native acknowledgement or explicit journal failure.
	 */
	private function acknowledge( Principal $principal, string $path, array $command, string $body ): bool|WP_Error {
		$id = $command['key'] ?? null;
		if ( ! class_exists( Ledger::class ) || ! is_string( $id ) || ! wp_is_uuid( $id, 4 ) || false === get_option( Ledger::OPTION ) ) {
			return true;
		}
		$ledger      = new Ledger();
		$fingerprint = $this->fingerprint( $principal, $path, $body );
		$receipt     = $ledger->lookup( $id, $fingerprint );
		if ( is_wp_error( $receipt ) ) {
			return 'linker_admission_unknown_receipt' === $receipt->get_error_code() ? true : Failure::make( 'receipt_persistence', 503 );
		}
		if ( in_array( $receipt['status'] ?? '', array( 'dispatched', 'unresolved' ), true ) && is_wp_error( $ledger->complete( $id, $fingerprint ) ) ) {
			return Failure::make( 'receipt_persistence', 503 );
		}
		return true;
	}

	/**
	 * Scope native quota receipts to the owner and exact public command bytes.
	 *
	 * @param Principal $principal Verified owner.
	 * @param string    $path Server-selected command.
	 * @param string    $body Exact input bytes.
	 */
	private function fingerprint( Principal $principal, string $path, string $body ): string {
		return wp_hash( 'linker-planner-admission:v1|' . $principal->kind . '|' . $principal->subject . '|' . $path . '|' . hash( 'sha256', $body ), 'nonce', 'sha256' );
	}

	/**
	 * Explicit initial development admission policy, 548 native gateway spec.
	 * Fixed time buckets are UTC; none is a physical or country rule.
	 *
	 * @param string $path Allowlisted private command.
	 * @return array{string,int,int,int,int}|null Name, guest, account, window, site ceiling.
	 */
	private function policy( string $path ): ?array {
		return match ( $path ) {
			'projects/create' => array( 'planner_projects', 10, 100, DAY_IN_SECONDS, 500 ),
			'projects/revise', 'battery/scenario' => array( 'planner_edits', 240, 1200, HOUR_IN_SECONDS, 5000 ),
			'profiles/csv' => array( 'planner_uploads', 20, 100, DAY_IN_SECONDS, 500 ),
			'runs/energy' => array( 'planner_calculations', 30, 120, HOUR_IN_SECONDS, 500 ),
			default => null,
		};
	}
}
