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
	// Bounded journal traversal per request; 548 native gateway resource policy.
	private const MAX_ATTEMPT_CHAIN = 32;

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
		if ( ! $known instanceof \stdClass || 1 !== ( $known->schema_version ?? null ) || ! in_array( $known->status ?? null, array( 'absent', 'replayed' ), true ) || ! is_string( $known->command_sha256 ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $known->command_sha256 ) || ! is_string( $known->command_scope ?? null ) || 1 !== preg_match( '/\A(?:create|(?:revise|evaluate|asset):[a-f0-9]{32})\z/', $known->command_scope ) || ! str_starts_with( $previous['type'], 'application/json' ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		if ( 'replayed' === $known->status ) {
			if ( ! ( $known->result ?? null ) instanceof \stdClass || ! JsonNumbers::supported( $known->result ) ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			$acknowledged = $this->acknowledge( $principal, $path, $command, $known->command_scope, $known->command_sha256 );
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
			return $this->refusal( $quota );
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
		$fingerprint = $this->fingerprint( $principal, $path, $known->command_scope, $known->command_sha256 );
		$id          = $this->operation_id( $principal, $command['key'], $quota->binding(), $fingerprint );
		if ( is_wp_error( $id ) ) {
			return $this->refusal( $id );
		}
		$ledger = new Ledger();
		// This lease covers only bounded RPC dispatch, not queued numerical work.
		$receipt = $ledger->reserve( $id, $fingerprint, $limits, 30, $carry, 'planner_write', $quota->binding(), $quota->owners() );
		if ( is_wp_error( $receipt ) ) {
			return $this->refusal( $receipt );
		}
		$status = $receipt['status'] ?? '';
		if ( 'reserved' === $status ) {
			$dispatched = $ledger->dispatch( $id, $fingerprint );
			if ( is_wp_error( $dispatched ) ) {
				return $this->refusal( $dispatched );
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
	 * @param string              $command_scope Private receipt's project-qualified scope.
	 * @param string              $command_hash Private engine's canonical intent.
	 * @return true|WP_Error Native acknowledgement or explicit journal failure.
	 */
	private function acknowledge( Principal $principal, string $path, array $command, string $command_scope, string $command_hash ): bool|WP_Error {
		$id = $command['key'] ?? null;
		if ( ! class_exists( Ledger::class ) || ! class_exists( Identity::class ) || ! is_string( $id ) || ! wp_is_uuid( $id, 4 ) || false === get_option( Ledger::OPTION ) ) {
			return true;
		}
		$quota = Identity::current();
		if ( is_wp_error( $quota ) ) {
			return true; // The permanent owned engine receipt is already confirmed.
		}
		$ledger      = new Ledger();
		$fingerprint = $this->fingerprint( $principal, $path, $command_scope, $command_hash );
		$id          = $this->operation_id( $principal, $id, $quota->binding(), $fingerprint, true );
		if ( is_wp_error( $id ) ) {
			// Exhausting unused local attempts is not a persistence failure and
			// cannot hide an already-confirmed permanent engine result.
			if ( 'linker_admission_capacity' === $id->get_error_code() ) {
				return true;
			}
			return Failure::make( 'receipt_persistence', 503 );
		}
		$receipt = $ledger->lookup( $id, $fingerprint );
		if ( is_wp_error( $receipt ) ) {
			// A permanent owned receipt can predate login or native salt rotation.
			// Its old, independently scoped quota fingerprint is not this actor's
			// entry to complete. No new reservation/charge or mutation is made.
			return 'linker_admission_unknown_receipt' === $receipt->get_error_code() ? true : Failure::make( 'receipt_persistence', 503 );
		}
		if ( in_array( $receipt['status'] ?? '', array( 'dispatched', 'unresolved' ), true ) && is_wp_error( $ledger->complete( $id, $fingerprint ) ) ) {
			return Failure::make( 'receipt_persistence', 503 );
		}
		return true;
	}

	/**
	 * Namespace the transport journal by its actual native principal/binding.
	 * The engine keeps the original business key and owns permanent replay.
	 * An earlier dispatched attempt under a different native context retains
	 * its charge; an absent engine receipt needs a new admitted attempt there.
	 * Reusing a raw UUID globally otherwise rejects legitimate login recovery.
	 * A still-present legacy receipt is retained only for this exact context.
	 *
	 * @param Principal $principal Verified native principal.
	 * @param string    $key Original client intent UUID.
	 * @param string    $binding Existing native quota context.
	 * @param string    $fingerprint This principal's canonical intent.
	 * @param bool      $confirmed The engine has already proved this exact result.
	 * @return string|WP_Error Existing or namespaced journal ID, or refusal.
	 */
	private function operation_id( Principal $principal, string $key, string $binding, string $fingerprint, bool $confirmed = false ): string|WP_Error {
		$ledger = new Ledger();
		$legacy = $ledger->lookup_context( $key, $fingerprint, 'planner_write', $binding );
		if ( ! is_wp_error( $legacy ) && ! in_array( $legacy['status'] ?? '', array( 'expired', 'cancelled' ), true ) ) {
			return $key;
		}
		if ( is_wp_error( $legacy ) && 'linker_admission_erased' === $legacy->get_error_code() ) {
			return $confirmed ? $key : $legacy;
		}
		// A confirmed permanent receipt remains recoverable even if an unrelated
		// old entry shares its key. It cannot settle that mismatched entry.
		if ( is_wp_error( $legacy ) && 'linker_admission_unknown_receipt' !== $legacy->get_error_code() && ! ( $confirmed && 'linker_admission_payload_changed' === $legacy->get_error_code() ) ) {
			return $legacy;
		}
		// Preserve exact key bytes, matching the engine's opaque Key contract.
		$seed = 'linker-planner-quota:v2|' . $principal->kind . '|' . $principal->subject . '|' . $binding . '|' . $key;
		$hash = wp_hash( $seed, 'auth', 'sha256' );
		for ( $attempt = 0; $attempt < self::MAX_ATTEMPT_CHAIN; ++$attempt ) {
			$id      = $this->uuid( $hash );
			$receipt = $ledger->lookup_context( $id, $fingerprint, 'planner_write', $binding );
			if ( is_wp_error( $receipt ) ) {
				return 'linker_admission_unknown_receipt' === $receipt->get_error_code() || ( $confirmed && in_array( $receipt->get_error_code(), array( 'linker_admission_payload_changed', 'linker_admission_erased' ), true ) ) ? $id : $receipt;
			}
			if ( ! in_array( $receipt['status'] ?? '', array( 'expired', 'cancelled' ), true ) ) {
				return $id;
			}
			// Only a proven unused, refunded attempt gets a stable successor.
			// Concurrent retries converge; dispatched/erased entries never reopen.
			$hash = wp_hash( $seed . '|after|' . $id, 'auth', 'sha256' );
		}
		return new WP_Error( 'linker_admission_capacity' );
	}

	/**
	 * Format an internal journal ID; never replace the public business key.
	 *
	 * @param string $hash Server HMAC of the current attempt context.
	 */
	private function uuid( string $hash ): string {
		// Ledger::reserve/transition accept a UUID4-shaped local identifier.
		// These format bits are protocol representation, not a new client key.
		return substr( $hash, 0, 8 ) . '-' . substr( $hash, 8, 4 ) . '-4' . substr( $hash, 13, 3 ) . '-' . dechex( ( hexdec( $hash[16] ) & 3 ) | 8 ) . substr( $hash, 17, 3 ) . '-' . substr( $hash, 20, 12 );
	}

	/**
	 * Scope native quota to the same canonical intent as its permanent receipt.
	 *
	 * @param Principal $principal Verified owner.
	 * @param string    $path Server-selected command.
	 * @param string    $command_scope Same private receipt's resource-qualified scope.
	 * @param string    $command_hash Private engine's validated canonical hash.
	 */
	private function fingerprint( Principal $principal, string $path, string $command_scope, string $command_hash ): string {
		return wp_hash( 'linker-planner-admission:v1|' . $principal->kind . '|' . $principal->subject . '|' . $path . '|' . $command_scope . '|' . $command_hash, 'nonce', 'sha256' );
	}

	/**
	 * The native journal is transport-neutral; its adapter supplies HTTP status.
	 *
	 * @param WP_Error $error Native admission outcome.
	 */
	private function refusal( WP_Error $error ): WP_Error {
		return match ( $error->get_error_code() ) {
			'linker_admission_quota' => Failure::make( 'rate_limit', 429 ),
			'linker_admission_payload_changed' => Failure::make( 'operation_changed', 409 ),
			'linker_admission_input' => Failure::make( 'admission', 400 ),
			default => Failure::make( 'admission_unavailable', 503 ),
		};
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
			'profiles/csv', 'geometry/import' => array( 'planner_uploads', 20, 100, DAY_IN_SECONDS, 500 ),
			'runs/energy', 'runs/pv', 'runs/weather', 'runs/equipment' => array( 'planner_calculations', 30, 120, HOUR_IN_SECONDS, 500 ),
			default => null,
		};
	}
}
