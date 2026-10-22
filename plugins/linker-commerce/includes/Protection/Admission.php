<?php
/**
 * Public proof and budget admission used by native business/resource handlers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;

/** Callers validate fields, reserve, validate heavy inputs, dispatch, then do work. */
final class Admission {
	/**
	 * Private current mode; server consumers supply their sourced policy dimensions.
	 *
	 * @param Configuration $configuration Shared private configuration.
	 * @param Ledger|null   $ledger Shared native journal.
	 */
	public function __construct( private readonly Configuration $configuration, private readonly ?Ledger $ledger = null ) {}

	/**
	 * Preserve a completed retry before requiring a fresh challenge; do no work twice.
	 *
	 * @param string                                         $action Public action.
	 * @param string                                         $proof Verified proof from the browser.
	 * @param string                                         $id Logical business/turn UUID, separate from challenge UUID.
	 * @param array<string,mixed>                            $payload Validated semantic input, no transport fields.
	 * @param Allowance[]                                    $limits Server-selected dimensions.
	 * @param int                                            $lease Required in-flight lease.
	 * @param bool                                           $single A business proof admits one logical submission.
	 * @param list<array{source:Allowance,target:Allowance}> $carry Login carry policy.
	 * @param string[]                                       $owners Additional trusted privacy owner HMACs.
	 * @return array<string,mixed>|WP_Error Native permit or explicit refusal.
	 */
	public function reserve( string $action, string $proof, string $id, array $payload, array $limits, int $lease, bool $single = false, array $carry = array(), array $owners = array() ): array|WP_Error {
		if ( 'observe' === $this->configuration->mode ) {
			return Observation::reserve( $this->ledger ?? new Ledger(), $action, $id, $payload, $limits, $lease, $carry, $owners );
		}
		if ( 'off' === $this->configuration->mode ) {
			return array(
				'enforced' => false,
				'mode'     => $this->configuration->mode,
			);
		}
		$verification = Configuration::verification_required( $action );
		if ( 'enforce' !== $this->configuration->mode || ( $verification && ! $this->configuration->ready() ) || ! Actions::valid( $action ) || ! wp_is_uuid( $id, 4 ) ) {
			return self::failure( 'configuration', 503 );
		}
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return self::failure( 'cookie', 503 );
		}
		$fingerprint = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fingerprint ) ) {
			return self::failure( 'input', 400 );
		}
		$ledger = $this->ledger ?? new Ledger();
		$old    = $ledger->lookup( $id, $fingerprint, true );
		if ( ! is_wp_error( $old ) ) {
			if ( $old['purpose'] !== $action || $old['binding'] !== $identity->binding() ) {
				return self::failure( 'input', 409 );
			}
			return 'completed' === $old['status'] ? array(
				'enforced' => true,
				'reused'   => true,
				'receipt'  => $old,
				'id'       => strtolower( $id ),
			) : self::failure( 'pending', 409 );
		}
		if ( 'linker_admission_unknown_receipt' !== $old->get_error_code() ) {
			return self::failure( 'unavailable', 503 );
		}
		$checked = $verification ? ( new Proof() )->read( $proof, 'verified', $action, $identity ) : null;
		if ( $verification && null === $checked ) {
			return self::failure( 'proof', 400 );
		}
		$receipt = $ledger->reserve( $id, $fingerprint, $limits, $lease, $carry, $action, $identity->binding(), array_values( array_unique( array_merge( $identity->owners(), $owners ) ) ) );
		if ( is_wp_error( $receipt ) ) {
			return self::ledger_failure( $receipt );
		}
		return array(
			'enforced'    => true,
			'reused'      => false,
			'receipt'     => $receipt,
			'id'          => strtolower( $id ),
			'fingerprint' => $fingerprint,
			'proof'       => null === $checked ? array() : array(
				'id'      => $checked['id'],
				'binding' => $identity->binding(),
				'action'  => $action,
				'single'  => $single,
			),
		);
	}

	/**
	 * A real successful verification receipt is needed before attachment parsing.
	 *
	 * @param array<string,mixed> $permit Reserved server permit.
	 * @return array<string,mixed>|WP_Error Safe result; dispatch remains mandatory.
	 */
	public function validate( array $permit ): array|WP_Error {
		if ( empty( $permit['enforced'] ) || ! empty( $permit['reused'] ) || empty( $permit['proof'] ) ) {
			return $permit;
		}
		$result = ( $this->ledger ?? new Ledger() )->verified( $permit['proof'], $permit['id'] );
		return is_wp_error( $result ) ? self::ledger_failure( $result ) : $permit;
	}

	/**
	 * This is the last gate before a native write or upstream call.
	 *
	 * @param array<string,mixed> $permit Server permit, never client JSON.
	 * @return array<string,mixed>|WP_Error Dispatched receipt or explicit failure.
	 */
	public function dispatch( array $permit ): array|WP_Error {
		if ( 'observe' === ( $permit['mode'] ?? '' ) ) {
			return Observation::advance( $this->ledger ?? new Ledger(), $permit, 'dispatch' );
		}
		if ( empty( $permit['enforced'] ) ) {
			return $permit;
		}
		if ( ! empty( $permit['reused'] ) ) {
			return self::failure( 'already_completed', 409 );
		}
		$ledger = $this->ledger ?? new Ledger();
		$result = $ledger->dispatch( $permit['id'], $permit['fingerprint'], $permit['proof'] );
		if ( is_wp_error( $result ) ) {
			$ledger->cancel( $permit['id'], $permit['fingerprint'] );
		}
		return is_wp_error( $result ) ? self::ledger_failure( $result ) : $result;
	}

	/**
	 * A rejected heavy input gives back only its unused reservation.
	 *
	 * @param array<string,mixed> $permit Server permit.
	 * @return array<string,mixed>|WP_Error Current receipt.
	 */
	public function cancel( array $permit ): array|WP_Error {
		if ( 'observe' === ( $permit['mode'] ?? '' ) ) {
			return Observation::advance( $this->ledger ?? new Ledger(), $permit, 'cancel' );
		}
		if ( ! empty( $permit['reused'] ) ) {
			return self::failure( 'already_completed', 409 );
		}
		return empty( $permit['enforced'] ) ? $permit : ( $this->ledger ?? new Ledger() )->cancel( $permit['id'], $permit['fingerprint'] );
	}

	/**
	 * Save only the native result ID; its module still owns authorization/readback.
	 *
	 * @param array<string,mixed> $permit Server permit.
	 * @param int                 $outcome Native result ID or zero.
	 * @return array<string,mixed>|WP_Error Completed receipt.
	 */
	public function complete( array $permit, int $outcome = 0 ): array|WP_Error {
		if ( 'observe' === ( $permit['mode'] ?? '' ) ) {
			return Observation::advance( $this->ledger ?? new Ledger(), $permit, 'complete', $outcome );
		}
		if ( ! empty( $permit['reused'] ) ) {
			return $permit['receipt'];
		}
		return empty( $permit['enforced'] ) ? $permit : ( $this->ledger ?? new Ledger() )->complete( $permit['id'], $permit['fingerprint'], $outcome );
	}

	/**
	 * Internal storage diagnostics are not customer-facing error text.
	 *
	 * @param WP_Error $error Safe journal error.
	 */
	private static function ledger_failure( WP_Error $error ): WP_Error {
		$code    = $error->get_error_code();
		$reason  = is_string( $code ) ? str_replace( 'linker_admission_', '', $code ) : 'unavailable';
		$status  = 'quota' === $reason ? 429 : ( in_array( $reason, array( 'proof', 'proof_reused', 'payload_changed', 'input' ), true ) ? 409 : 503 );
		$failure = self::failure( $reason, $status );
		$data    = $error->get_error_data();
		if ( is_array( $data ) ) {
			$failure->add_data( array_merge( $data, array( 'status' => $status ) ) );
		}
		return $failure;
	}

	/**
	 * The form keeps its input on every refusal.
	 *
	 * @param string $reason Safe reason.
	 * @param int    $status HTTP status.
	 */
	private static function failure( string $reason, int $status ): WP_Error {
		return new WP_Error( 'linker_admission_' . $reason, in_array( $reason, array( 'pending', 'already_completed' ), true ) ? __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-commerce' ) : __( 'Your request could not be processed. Please try again.', 'linker-commerce' ), array( 'status' => $status ) );
	}
}
