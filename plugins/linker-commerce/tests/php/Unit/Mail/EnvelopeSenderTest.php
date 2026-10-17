<?php
/**
 * Envelope sender policy at the WordPress mailer boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\EnvelopeSender;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * The envelope policy at PHPMailer's public interface.
 *
 * @covers \Linker\Commerce\Mail\EnvelopeSender
 */
final class EnvelopeSenderTest extends TestCase {

	/**
	 * A reused PHPMailer gets the current envelope without changing From or Reply-To.
	 */
	public function test_delivery_changes_only_the_envelope(): void {
		$this->options( array( Options::ENVELOPE_SENDER => 'bounce@example.test' ) );
		WP_Mock::passthruFunction( 'sanitize_email' );
		WP_Mock::userFunction( 'is_email', array( 'return' => 'bounce@example.test' ) );
		$mailer = Mockery::mock( 'PHPMailer\PHPMailer\PHPMailer' );
		// phpcs:disable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- PHPMailer's native public fields.
		$mailer->From     = 'sales@de-linker.com';
		$mailer->FromName = 'Linker';
		$mailer->Sender   = 'previous@example.test';
		$mailer->shouldNotReceive( 'clearReplyTos' );
		$mailer->shouldNotReceive( 'addReplyTo' );

		( new EnvelopeSender( new Options() ) )->apply( $mailer );

		$this->assertSame( 'bounce@example.test', $mailer->Sender );
		$this->assertSame( 'sales@de-linker.com', $mailer->From );
		$this->assertSame( 'Linker', $mailer->FromName );
		// phpcs:enable
	}
}
