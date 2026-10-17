<?php
/**
 * Internal SMTP configuration at the server-file boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\InternalSmtp;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Only fake configuration is written; never open a machine's SMTP env file.
 *
 * @covers \Linker\Commerce\Mail\InternalSmtp
 */
final class InternalSmtpTest extends TestCase {

	/**
	 * A complete file must match the internal sender before authentication is ready.
	 */
	public function test_authentication_requires_a_complete_matching_configuration(): void {
		$this->options( array() );
		WP_Mock::passthruFunction( 'sanitize_email' );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		$file = tempnam( sys_get_temp_dir(), 'linker-smtp-test-' );
		$this->assertIsString( $file );
		try {
			$smtp = new InternalSmtp( $file );
			$this->assertFalse( $smtp->authenticated() );
			file_put_contents( $file, "LINKER_SMTP_HOST=smtp.example.test\nLINKER_SMTP_PORT=465\nLINKER_SMTP_USER=sales@sunriverinverter.com\nLINKER_SMTP_PASS='fake-password'\n" );
			$this->assertTrue( $smtp->authenticated() );
			file_put_contents( $file, "LINKER_SMTP_HOST=smtp.example.test\nLINKER_SMTP_PORT=465\nLINKER_SMTP_USER=sales@sunriverinverter.com\nLINKER_SMTP_PASS=''\n" );
			$this->assertFalse( $smtp->authenticated(), 'Quoted empty passwords are missing configuration.' );
			file_put_contents( $file, "LINKER_SMTP_HOST=smtp.example.test\nLINKER_SMTP_PORT=465\nLINKER_SMTP_USER=other@example.test\nLINKER_SMTP_PASS=fake-password\n" );
			$this->assertFalse( $smtp->authenticated() );
		} finally {
			unlink( $file );
		}
		$this->assertFalse( ( new InternalSmtp( $file ) )->authenticated(), 'An absent file selects visible fallback.' );
	}
}
