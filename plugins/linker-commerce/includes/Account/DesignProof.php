<?php
/**
 * Server-verified designs for new account and solution-draft writes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Products\Publication;
use WP_Error;

/**
 * Woo owns publication; the engine owns the calculated result. Browser lines,
 * a fingerprint alone, and an old saved snapshot cannot authorize a new write.
 */
final class DesignProof {
	/**
	 * External reads can be replaced by local fixtures; production uses Woo and Tools.
	 *
	 * @param callable(array<string,mixed>):array<string,mixed>|null        $validate Current authority read.
	 * @param callable(string,string):(array{0:int,1:string}|WP_Error)|null $fetch Trusted engine transport.
	 */
	public function __construct( private mixed $validate = null, private mixed $fetch = null ) {}

	/**
	 * Resolves a fingerprint to the engine's complete, currently valid result.
	 *
	 * @param string               $kind        Configurator kind.
	 * @param array<string, mixed> $input       Original design input.
	 * @param string               $fingerprint Result confirmed by the customer.
	 * @param int|null             $system_index Explicit commercial system choice.
	 * @return array<string, mixed>|WP_Error
	 */
	public function verify( string $kind, array $input, string $fingerprint, ?int $system_index = null ): array|WP_Error {
		if ( ! in_array( $kind, SolutionsRoute::KINDS, true ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $fingerprint ) || array() === $input ) {
			return self::unavailable();
		}
		$body = wp_json_encode(
			array(
				'kind'                  => $kind,
				'input'                 => $input,
				'selection_fingerprint' => $fingerprint,
			)
		);
		if ( ! is_string( $body ) ) {
			return self::unavailable();
		}
		$url = rtrim( (string) get_option( Monitor::ENGINE_URL_OPTION, '' ), '/' ) . '/selection/validate';
		/**
		 * Trusted Tools adapter applies resource protection and current publication
		 * checks in every mode. No direct-HTTP fallback can bypass that adapter.
		 *
		 * @since 0.2.0
		 */
		$reply = is_callable( $this->fetch ) ? ( $this->fetch )( $url, $body ) : apply_filters( 'linker_tools_engine_request', self::unavailable(), $url, $body ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Shared server-only Tools seam.
		if ( $reply instanceof WP_Error || ! is_array( $reply ) || count( $reply ) !== 2 ) {
			return self::verification_failed();
		}
		[ $status, $payload ] = $reply;
		if ( $status >= 500 || in_array( $status, array( 401, 403 ), true ) ) {
			return self::verification_failed();
		}
		$result = is_string( $payload ) ? json_decode( $payload, true ) : null;
		if ( $status < 200 || $status >= 300 || ! is_array( $result ) || ( $result['selection_fingerprint'] ?? '' ) !== $fingerprint ) {
			return self::unavailable();
		}
		if ( 'commercial' === $kind ) {
			if ( null === $system_index || $system_index < 0 || ! is_array( $result['systems'][ $system_index ] ?? null ) ) {
				return self::unavailable();
			}
			$result['selected_system_index'] = $system_index;
		}
		if ( array() === self::items( $result ) ) {
			return self::unavailable();
		}
		$error = $this->current_error( $result );
		if ( $error instanceof WP_Error ) {
			return $error;
		}
		return $result;
	}

	/**
	 * A final current-authority check, including all candidates and documents.
	 *
	 * @param array<string, mixed> $result Trusted engine result or stored snapshot.
	 * @phpstan-impure Reads current Woo state on every check, including after writes.
	 */
	public function is_current( array $result ): bool {
		return null === $this->current_error( $result );
	}

	/**
	 * Preserve the distinction between revoked dependencies and unavailable authority.
	 *
	 * @param array<string,mixed> $result Trusted result or historical snapshot.
	 * @phpstan-impure Reads the current authority on each invocation.
	 */
	public function current_error( array $result ): ?WP_Error {
		$dependencies = $result['publication'] ?? null;
		if ( ! is_array( $dependencies ) || ! is_array( $dependencies['products'] ?? null ) || array() === $dependencies['products'] || ! is_string( $dependencies['compatibility_revision'] ?? null ) || '' === $dependencies['compatibility_revision'] ) {
			return self::unavailable();
		}
		if ( 'genie' !== ( $result['kind'] ?? '' ) && ! self::has_engineering_proof( $dependencies ) ) {
			return self::unavailable();
		}
		try {
			$checked = is_callable( $this->validate ) ? ( $this->validate )( $dependencies ) : Publication::validate( $dependencies );
		} catch ( \RuntimeException $error ) {
			return self::verification_failed();
		}
		return true === ( $checked['valid'] ?? false ) ? null : self::unavailable();
	}

	/**
	 * Reject old engineering receipts that omitted non-sale reference evidence.
	 * Genie product lists have their own signed contract and do not call this gate.
	 *
	 * @param array<string,mixed> $dependencies Trusted engineering dependency scope.
	 */
	public static function has_engineering_proof( array $dependencies ): bool {
		$references = $dependencies['reference_inputs'] ?? null;
		if ( 2 !== ( $dependencies['engineering_contract'] ?? null ) || ! is_array( $references ) || ! array_is_list( $references ) || ! is_array( $dependencies['products'] ?? null ) || ! is_array( $dependencies['documents'] ?? null ) ) {
			return false;
		}
		$versions = array();
		foreach ( $dependencies['products'] as $product ) {
			if ( is_array( $product ) && is_int( $product['product_id'] ?? null ) && is_string( $product['product_revision'] ?? null ) ) {
				$versions[ $product['product_id'] ] = $product['product_revision'];
			}
		}
		foreach ( $references as $reference ) {
			if ( ! is_array( $reference ) || ! is_string( $reference['reference_input_id'] ?? null ) || '' === $reference['reference_input_id'] || ! is_int( $reference['product_id'] ?? null ) || $reference['product_id'] < 1 || ! is_string( $reference['product_revision'] ?? null ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $reference['product_revision'] ) || ( $reference['reference_revision'] ?? null ) !== $reference['product_revision'] ) {
				return false;
			}
			if ( ( $versions[ $reference['product_id'] ] ?? null ) !== $reference['product_revision'] ) {
				return false;
			}
			$has_document = false;
			foreach ( $dependencies['documents'] as $document ) {
				if ( is_array( $document ) && ( $document['product_id'] ?? null ) === $reference['product_id'] && is_string( $document['document_id'] ?? null ) && '' !== $document['document_id'] && is_string( $document['document_revision'] ?? null ) && '' !== $document['document_revision'] ) {
					$has_document = true;
					break;
				}
			}
			if ( ! $has_document ) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Complete purchasable BOM, from the trusted result rather than request lines.
	 * Overlay components without a Woo product are engineering inputs only.
	 *
	 * @param array<string, mixed> $result Engine result.
	 * @return list<array{product_id:int,quantity:int}>
	 */
	public static function items( array $result ): array {
		$selected = $result['selected'] ?? null;
		if ( null === $selected && is_int( $result['selected_system_index'] ?? null ) ) {
			$selected = $result['systems'][ $result['selected_system_index'] ] ?? null;
		}
		$lines = is_array( $selected ) ? ( $selected['lines'] ?? null ) : null;
		if ( ! is_array( $lines ) ) {
			return array();
		}
		$totals = array();
		foreach ( $lines as $line ) {
			if ( ! is_array( $line ) || ! is_array( $line['product'] ?? null ) ) {
				continue;
			}
			$id       = $line['product']['id'] ?? null;
			$quantity = $line['quantity'] ?? null;
			if ( ! is_int( $id ) || $id < 1 || ! is_int( $quantity ) || $quantity < 1 ) {
				return array();
			}
			$totals[ $id ] = ( $totals[ $id ] ?? 0 ) + $quantity;
		}
		ksort( $totals, SORT_NUMERIC );
		$items = array();
		foreach ( $totals as $id => $quantity ) {
			$items[] = array(
				'product_id' => $id,
				'quantity'   => $quantity,
			);
		}
		return $items;
	}

	/** Current write refused; the customer's historical snapshot remains readable. */
	public static function unavailable(): WP_Error {
		return new WP_Error(
			'linker_solution_changed',
			__( 'This solution needs a new calculation before it can be saved or added to your solution draft.', 'linker-commerce' ),
			array( 'status' => 409 )
		);
	}

	/** A verification outage is separate from a changed product or design. */
	public static function verification_failed(): WP_Error {
		return new WP_Error( 'linker_solution_verification', __( 'The solution could not be checked. Please try again.', 'linker-commerce' ), array( 'status' => 503 ) );
	}
}
