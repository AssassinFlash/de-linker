<?php
/**
 * Engine proof metadata and fail-closed legacy receipt coverage.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Protection\EnginePublication;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_REST_Response;

/**
 * A result receipt carries evidence, never publication authority.
 *
 * @covers \Linker\Tools\Protection\EnginePublication
 */
final class EnginePublicationTest extends TestCase {
	/** No browser result or old PDF receipt grants current publication. */
	public function test_a_success_without_proof_is_refused(): void {
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction( '__', array( 'return_arg' => 0 ) );
		foreach ( array( array( 'selected' => array() ), '%PDF-old' ) as $data ) {
			$result = EnginePublication::reply( new WP_REST_Response( $data, 200 ) );
			$this->assertInstanceOf( WP_Error::class, $result );
			$this->assertSame( 409, $result->get_error_data()['status'] );
		}
	}

	/** Binary data keeps proof without putting a large dependency set in headers. */
	public function test_binary_proof_is_request_local_metadata(): void {
		$reply        = new WP_REST_Response( '%PDF-confirmed', 200 );
		$dependencies = array(
			'products'               => array(),
			'documents'              => array(),
			'compatibility_revision' => str_repeat( 'a', 64 ),
		);
		EnginePublication::remember( $reply, $dependencies );
		$this->assertSame( $dependencies, EnginePublication::dependencies( $reply ) );
		$this->assertSame( array(), $reply->get_headers() );
		$this->assertSame( array(), EnginePublication::dependencies( new WP_REST_Response( '%PDF-other', 200 ) ) );
	}

	/**
	 * A cache provider that cannot refresh current Woo data is unavailable.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_unreadable_current_authority_is_a_service_failure(): void {
		require_once dirname( __DIR__, 4 ) . '/linker-commerce/includes/Products/Publication.php';
		require_once dirname( __DIR__, 4 ) . '/linker-commerce/includes/Account/DesignProof.php';
		WP_Mock::userFunction(
			'wp_cache_supports',
			array(
				'args'   => array( 'flush_runtime' ),
				'times'  => 1,
				'return' => false,
			)
		);
		WP_Mock::userFunction( '__', array( 'return_arg' => 0 ) );
		$result = EnginePublication::validate(
			array(
				'engineering_contract' => 2,
				'reference_inputs'     => array(),
				'products'             => array(),
				'documents'            => array(),
			)
		);
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_publication_unavailable', $result->get_error_code() );
		$this->assertSame( 503, $result->get_error_data()['status'] );
	}
}
