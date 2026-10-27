<?php
/**
 * Shared current-publication and complete-item validation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Products\Publication;
use WP_Error;

/**
 * Woo owns publication; the engine owns the calculated result. Browser lines,
 * a fingerprint alone, and an old saved snapshot cannot authorize a new write.
 */
final class DesignProof {
	/**
	 * Current publication reads can be replaced by local fixtures.
	 *
	 * @param callable(array<string,mixed>):array<string,mixed>|null $validate Current authority read.
	 */
	public function __construct( private mixed $validate = null ) {}

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
		$dependencies = self::dependencies( $result );
		if ( null === $dependencies ) {
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
	 * Whether a stored result can reach fresh validation; never a permission grant.
	 *
	 * @param array<string, mixed> $result Historical result.
	 */
	public static function can_revalidate( array $result ): bool {
		return null !== self::dependencies( $result ) && array() !== self::items( $result );
	}

	/**
	 * The same local prerequisites for both the action and its account guidance.
	 *
	 * @param array<string, mixed> $result Historical result.
	 * @return array<string, mixed>|null
	 */
	private static function dependencies( array $result ): ?array {
		$dependencies = $result['publication'] ?? null;
		if ( ! is_array( $dependencies ) || ! is_array( $dependencies['products'] ?? null ) || array() === $dependencies['products'] || ! is_string( $dependencies['compatibility_revision'] ?? null ) || '' === $dependencies['compatibility_revision'] ) {
			return null;
		}
		return 'genie' === ( $result['kind'] ?? '' ) || self::has_engineering_proof( $dependencies ) ? $dependencies : null;
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
			// Engine BOM quantities are floats (including measured installer parts).
			// Woo pieces must be exactly integral and fit PHP's native integer range.
			if ( is_float( $quantity ) && is_finite( $quantity ) && floor( $quantity ) === $quantity && $quantity >= 1 && $quantity < PHP_INT_MAX ) {
				$quantity = (int) $quantity;
			}
			if ( ! is_int( $id ) || $id < 1 || ! is_int( $quantity ) || $quantity < 1 ) {
				return array();
			}
			if ( $quantity > PHP_INT_MAX - ( $totals[ $id ] ?? 0 ) ) {
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
