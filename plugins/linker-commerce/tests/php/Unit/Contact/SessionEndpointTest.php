<?php
/**
 * A form session belongs to a same-origin browser interaction.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\SessionEndpoint;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Anonymous token response and cache headers.
 *
 * @covers \Linker\Commerce\Contact\SessionEndpoint
 */
final class SessionEndpointTest extends TestCase {
	/** Both the browser Origin and its Referer fallback must belong to this site. */
	public function test_requires_a_same_origin_request(): void {
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( 'parse_url' );
		$request = new \WP_REST_Request();
		foreach ( array( null, 'https://elsewhere.test/', 'http://linker.test:8000/' ) as $origin ) {
			if ( null !== $origin ) {
				$request->set_header( 'Origin', $origin );
				$request->set_header( 'Referer', 'http://linker.test/contact/' );
			}
			$error = ( new SessionEndpoint() )->issue( $request );
			$this->assertInstanceOf( \WP_Error::class, $error );
			$this->assertSame( 403, $error->get_error_data()['status'] );
		}
	}

	/** Only the private response carries the fields needed by the native handler. */
	public function test_issues_private_fields_on_same_site_interaction(): void {
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( 'parse_url' );
		WP_Mock::userFunction( 'wp_create_nonce' )->with( Form::NONCE_ACTION )->andReturn( 'contact-token' );
		WP_Mock::userFunction( 'wp_generate_uuid4' )->andReturn( '12345678-1234-4567-89ab-cdef01234567' );
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		try {
			foreach ( array(
				'Referer' => 'http://linker.test/de/kontakt/',
				'Origin'  => 'http://linker.test',
			) as $key => $url ) {
				$request = new \WP_REST_Request();
				$request->set_header( $key, $url );
				$result = ( new SessionEndpoint() )->issue( $request );
				$this->assertInstanceOf( \WP_REST_Response::class, $result );
				$this->assertSame( 200, $result->get_status() );
				$this->assertSame(
					array(
						'nonce'     => 'contact-token',
						'requestId' => '12345678-1234-4567-89ab-cdef01234567',
					),
					$result->get_data()
				);
				$this->assertSame( 'private, no-store, max-age=0', $result->get_headers()['Cache-Control'] );
				$this->assertSame( 'no-cache', $result->get_headers()['X-LiteSpeed-Cache-Control'] );
				$this->assertSame( 'Origin, Cookie', $result->get_headers()['Vary'] );
			}
		} finally {
			unset( $_COOKIE[ Identity::COOKIE ] );
		}
	}
}
