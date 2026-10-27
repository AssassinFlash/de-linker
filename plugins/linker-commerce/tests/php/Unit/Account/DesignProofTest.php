<?php
/**
 * Confirmed designs need a trusted result and a complete current scope.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;

/**
 * Complete current scopes and trusted engine receipts.
 *
 * @covers \Linker\Commerce\Account\DesignProof
 */
final class DesignProofTest extends TestCase {
	/** No network: the owning service and source are explicit fixture transports. */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://engine.test' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
	}

	/** A withdrawn candidate invalidates the result even if it was not selected. */
	public function test_current_check_receives_the_complete_candidate_scope(): void {
		$result = self::result();
		$seen   = array();
		$proof  = new DesignProof(
			static function ( array $dependencies ) use ( &$seen ): array {
				$seen = $dependencies;
				return array( 'valid' => false );
			}
		);
		$this->assertFalse( $proof->is_current( $result ) );
		$this->assertSame( array( 10, 20 ), array_column( $seen['products'], 'product_id' ) );
	}

	/** An unreadable authority stops the action without claiming product withdrawal. */
	public function test_authority_unavailability_preserves_a_verification_error(): void {
		$proof = new DesignProof(
			static function (): array {
				throw new \RuntimeException( 'Current authority unavailable.' );
			}
		);
		$error = $proof->current_error( self::result() );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 'linker_solution_verification', $error->get_error_code() );
		$this->assertSame( array( 'status' => 503 ), $error->get_error_data() );
		$this->assertFalse( $proof->is_current( self::result() ) );
	}

	/** Missing or empty publication evidence cannot become a current write. */
	public function test_missing_scope_is_refused_even_if_the_external_validator_returns_true(): void {
		$proof = new DesignProof( static fn (): array => array( 'valid' => true ) );
		$this->assertFalse( $proof->is_current( array() ) );
		$this->assertFalse(
			$proof->is_current(
				array(
					'publication' => array(
						'products'               => array(),
						'documents'              => array(),
						'compatibility_revision' => 'x',
					),
				)
			)
		);
	}

	/** Old snapshots cannot omit the current reference-input contract. */
	public function test_engineering_receipt_requires_complete_reference_links(): void {
		$result = self::result();
		$proof  = new DesignProof( static fn (): array => array( 'valid' => true ) );
		$this->assertTrue( $proof->is_current( $result ) );
		unset( $result['publication']['engineering_contract'] );
		$this->assertFalse( $proof->is_current( $result ) );
		$result                                    = self::result();
		$result['publication']['reference_inputs'] = array(
			array(
				'reference_input_id' => 'reference-module',
				'product_id'         => 20,
				'product_revision'   => str_repeat( 'c', 64 ),
				'reference_revision' => str_repeat( 'c', 64 ),
			),
		);
		$this->assertFalse( $proof->is_current( $result ), 'The reference needs its current document.' );
		$result['publication']['documents'][] = array(
			'document_id'       => 'doc-reference',
			'document_revision' => str_repeat( 'e', 64 ),
			'product_id'        => 20,
		);
		$this->assertTrue( $proof->is_current( $result ) );
		$result['publication']['reference_inputs'][0]['reference_revision'] = str_repeat( 'f', 64 );
		$this->assertFalse( $proof->is_current( $result ) );
	}

	/** An ordinary signed Genie list has its independent non-engineering contract. */
	public function test_genie_list_keeps_its_independent_contract(): void {
		$result = self::result();
		unset( $result['publication']['engineering_contract'], $result['publication']['reference_inputs'] );
		$result['kind'] = 'genie';
		$this->assertTrue( ( new DesignProof( static fn (): array => array( 'valid' => true ) ) )->is_current( $result ) );
	}

	/** The native engine BOM serializes whole piece counts as JSON 1.0. */
	public function test_native_engine_float_piece_counts_keep_a_verified_complete_bom(): void {
		$result                                     = self::result();
		$result['selected']['lines'][0]['quantity'] = 1.0;
		$result['selected']['lines'][]              = array(
			'product'  => array( 'id' => 10 ),
			'quantity' => 2.0,
		);
		$this->assertSame(
			array(
				array(
					'product_id' => 10,
					'quantity'   => 3,
				),
			),
			DesignProof::items( $result )
		);
	}

	/** Piece counts cannot become fractional, coerced, non-finite or overflowed. */
	public function test_invalid_piece_counts_and_overflow_reject_the_entire_bom(): void {
		foreach ( array( 1.5, 0.0, -1.0, '1', true, INF, NAN, (float) PHP_INT_MAX ) as $quantity ) {
			$result                                     = self::result();
			$result['selected']['lines'][0]['quantity'] = $quantity;
			$this->assertSame( array(), DesignProof::items( $result ) );
		}
		$result                                     = self::result();
		$result['selected']['lines'][0]['quantity'] = PHP_INT_MAX;
		$result['selected']['lines'][]              = array(
			'product'  => array( 'id' => 10 ),
			'quantity' => 1,
		);
		$this->assertSame( array(), DesignProof::items( $result ) );
	}

	/**
	 * A selected product and a second candidate are separate dependencies.
	 *
	 * @return array<string,mixed>
	 */
	private static function result(): array {
		return array(
			'selection_fingerprint' => str_repeat( 'a', 64 ),
			'publication'           => array(
				'engineering_contract'   => 2,
				'reference_inputs'       => array(),
				'products'               => array(
					array(
						'product_id'       => 10,
						'product_revision' => str_repeat( 'b', 64 ),
					),
					array(
						'product_id'       => 20,
						'product_revision' => str_repeat( 'c', 64 ),
					),
				),
				'documents'              => array(),
				'compatibility_revision' => str_repeat( 'd', 64 ),
			),
			'selected'              => array(
				'lines' => array(
					array(
						'product'  => array( 'id' => 10 ),
						'quantity' => 1,
					),
				),
			),
		);
	}
}
