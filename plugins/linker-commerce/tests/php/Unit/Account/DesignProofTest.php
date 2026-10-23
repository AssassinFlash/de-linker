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
			},
			static fn (): array => array( 200, (string) json_encode( $result ) )
		);
		$this->assertInstanceOf( WP_Error::class, $proof->verify( 'residential', array( 'plz' => '39179' ), str_repeat( 'a', 64 ) ) );
		$this->assertSame( array( 10, 20 ), array_column( $seen['products'], 'product_id' ) );
	}

	/** A different result cannot be saved using a client's copied fingerprint. */
	public function test_the_trusted_result_must_match_the_confirmed_fingerprint(): void {
		$proof = new DesignProof( static fn (): array => array( 'valid' => true ), static fn (): array => array( 200, (string) json_encode( self::result() ) ) );
		$this->assertInstanceOf( WP_Error::class, $proof->verify( 'residential', array( 'plz' => '39179' ), str_repeat( 'b', 64 ) ) );
	}

	/** An unreadable authority stops the action without claiming product withdrawal. */
	public function test_authority_unavailability_preserves_a_verification_error(): void {
		$proof = new DesignProof(
			static function (): array {
				throw new \RuntimeException( 'Current authority unavailable.' );
			},
			static fn (): array => array( 200, (string) json_encode( self::result() ) )
		);
		$error = $proof->verify( 'residential', array( 'plz' => '39179' ), str_repeat( 'a', 64 ) );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 'linker_solution_verification', $error->get_error_code() );
		$this->assertSame( array( 'status' => 503 ), $error->get_error_data() );
		$this->assertFalse( $proof->is_current( self::result() ) );
	}

	/** Commercial calls identify the customer's explicit card, never the first one. */
	public function test_commercial_selection_requires_an_explicit_valid_index(): void {
		$result = self::result();
		unset( $result['selected'] );
		$result['systems'] = array(
			array(
				'lines' => array(
					array(
						'product'  => array( 'id' => 10 ),
						'quantity' => 2,
					),
				),
			),
			array(
				'lines' => array(
					array(
						'product'  => array( 'id' => 20 ),
						'quantity' => 3,
					),
				),
			),
		);
		$proof             = new DesignProof( static fn (): array => array( 'valid' => true ), static fn (): array => array( 200, (string) json_encode( $result ) ) );
		$this->assertInstanceOf( WP_Error::class, $proof->verify( 'commercial', array( 'plz' => '39179' ), str_repeat( 'a', 64 ) ) );
		$this->assertInstanceOf( WP_Error::class, $proof->verify( 'commercial', array( 'plz' => '39179' ), str_repeat( 'a', 64 ), 2 ) );
		$verified = $proof->verify( 'commercial', array( 'plz' => '39179' ), str_repeat( 'a', 64 ), 1 );
		$this->assertIsArray( $verified );
		$this->assertSame(
			array(
				array(
					'product_id' => 20,
					'quantity'   => 3,
				),
			),
			DesignProof::items( $verified )
		);
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

	/**
	 * A selected product and a second candidate are separate dependencies.
	 *
	 * @return array<string,mixed>
	 */
	private static function result(): array {
		return array(
			'selection_fingerprint' => str_repeat( 'a', 64 ),
			'publication'           => array(
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
