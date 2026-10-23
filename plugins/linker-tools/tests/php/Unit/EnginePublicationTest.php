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

/** @covers \Linker\Tools\Protection\EnginePublication */
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
		$reply = new WP_REST_Response( '%PDF-confirmed', 200 );
		$dependencies = array( 'products' => array(), 'documents' => array(), 'compatibility_revision' => str_repeat( 'a', 64 ) );
		EnginePublication::remember( $reply, $dependencies );
		$this->assertSame( $dependencies, EnginePublication::dependencies( $reply ) );
		$this->assertSame( array(), $reply->get_headers() );
		$this->assertSame( array(), EnginePublication::dependencies( new WP_REST_Response( '%PDF-other', 200 ) ) );
	}
}
