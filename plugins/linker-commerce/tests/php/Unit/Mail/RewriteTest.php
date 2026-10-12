<?php
/**
 * Tests for the test-mode rewrite of an outgoing message.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The seam is Outbox's delivery, which calls redirect() on the copy it sends
 * after the queue has stored the original message. While the switch is on that
 * copy names the tester address and nothing else; the message the caller keeps
 * is unchanged, and that is the routing data the queue asserts on.
 *
 * @covers \Linker\Commerce\Mail\TestMode
 */
final class RewriteTest extends TestCase {

	/**
	 * Options by name.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/**
	 * An in-memory option store and the WordPress address rule.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $name, $default_value = false ) => $this->options[ $name ] ?? $default_value ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => str_contains( $email, '@' ) ? trim( $email ) : '' ) );
		WP_Mock::userFunction(
			'is_email',
			array( 'return' => static fn ( string $email ): string|false => 1 === preg_match( '/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/', $email ) ? $email : false )
		);
	}

	/**
	 * While the switch is on, the copy that leaves names the tester address and
	 * drops Cc and Bcc. The message handed in is not rewritten.
	 *
	 * @dataProvider paths
	 *
	 * @param Message $message A message a path hands to the outbox.
	 */
	public function test_every_path_leaves_only_for_the_tester( Message $message ): void {
		$this->options[ TestMode::OPTION ] = 'tester@example.test';
		$original                          = $message->to_array();

		$delivery = ( new TestMode() )->redirect( $message );

		$this->assertSame( array( 'tester@example.test' ), $delivery->to );
		$this->assertSame( array(), $this->copies( $delivery->headers ), 'Cc and Bcc are dropped, not redirected.' );
		$this->assertSame( $original, $message->to_array(), 'The queued message keeps the recipients it came with.' );
	}

	/**
	 * The paths that left the instance: the old plugin's VAT review mail, the
	 * copies it queues for the three owner inboxes, a customer approval mail,
	 * and a team notification that already carries a blind copy.
	 *
	 * @return array<string, array{0: Message}>
	 */
	public function paths(): array {
		return array(
			'the old plugin VAT review mail'        => array(
				new Message(
					array( 'sales@de-linker.com' ),
					'Linker VAT check needs review: DE123456789',
					'A Linker partner VAT check needs review.',
					array(),
					array()
				),
			),
			'a copy the old plugin queues for an owner inbox' => array(
				new Message(
					array( '857558227@qq.com' ),
					'Linker VAT check needs review: DE123456789',
					'A Linker partner VAT check needs review.',
					array(),
					array()
				),
			),
			'the other owner copies'                => array(
				new Message(
					array( 'chester@de-linker.com', 'sales@sunriverinverter.com' ),
					'Linker VAT check needs review: DE123456789',
					'A Linker partner VAT check needs review.',
					array(),
					array()
				),
			),
			'a customer approval mail'              => array(
				new Message(
					array( 'buyer@example.test' ),
					'Your partner account is approved',
					'<p>Approved</p>',
					array( 'Content-Type: text/html; charset=UTF-8' ),
					array()
				),
			),
			'a team notification with a blind copy' => array(
				new Message(
					array( 'sales@de-linker.com' ),
					'New customer: Example GmbH',
					'<p>Registered</p>',
					array( 'Bcc: archive@example.test', 'Content-Type: text/html; charset=UTF-8' ),
					array()
				),
			),
		);
	}

	/**
	 * While the switch is off the same path keeps the recipients it was given.
	 */
	public function test_off_leaves_every_path_alone(): void {
		$message = new Message(
			array( 'sales@de-linker.com' ),
			'Linker VAT check needs review: DE123456789',
			'A Linker partner VAT check needs review.',
			array( 'Bcc: 857558227@qq.com' ),
			array()
		);

		$this->assertSame( $message, ( new TestMode() )->redirect( $message ) );
	}

	/**
	 * Subject, body, content type and attachments survive the rewrite.
	 */
	public function test_the_rewrite_keeps_the_message(): void {
		$this->options[ TestMode::OPTION ] = 'tester@example.test';

		$delivery = ( new TestMode() )->redirect(
			new Message(
				array( 'buyer@example.test' ),
				'Your partner account is approved',
				'<p>Approved</p>',
				array( 'Content-Type: text/html; charset=UTF-8', 'Bcc: archive@example.test' ),
				array( '/tmp/proforma.pdf' )
			)
		);

		$this->assertSame( 'Your partner account is approved', $delivery->subject );
		$this->assertSame( '<p>Approved</p>', $delivery->body );
		$this->assertSame( array( '/tmp/proforma.pdf' ), $delivery->attachments );
		$this->assertSame( array( 'Content-Type: text/html; charset=UTF-8' ), $delivery->headers );
	}

	/**
	 * Addresses named by Cc or Bcc headers.
	 *
	 * @param string[] $headers Header lines.
	 * @return list<string>
	 */
	private function copies( array $headers ): array {
		$found = array();
		foreach ( $headers as $header ) {
			$name = strtolower( ltrim( $header ) );
			if ( str_starts_with( $name, 'cc:' ) || str_starts_with( $name, 'bcc:' ) ) {
				$found[] = trim( substr( $header, (int) strpos( $header, ':' ) + 1 ) );
			}
		}
		return $found;
	}
}
