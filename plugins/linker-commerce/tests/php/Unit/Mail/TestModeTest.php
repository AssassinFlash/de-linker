<?php
/**
 * Tests for the test-mode switch of outgoing mail.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for TestMode: the option behind the switch, and the message as it goes
 * to the mailer while the switch is on.
 *
 * @covers \Linker\Commerce\Mail\TestMode
 */
final class TestModeTest extends TestCase {

	/**
	 * Options by name.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/**
	 * An in-memory option store; addresses are taken as WordPress takes them.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $name, $default_value = false ) => $this->options[ $name ] ?? $default_value ) );
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => function ( string $name, $value ): bool {
					$this->options[ $name ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'delete_option',
			array(
				'return' => function ( string $name ): bool {
					unset( $this->options[ $name ] );
					return true;
				},
			)
		);
		// WordPress's own rule: what is not an address comes back empty.
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => str_contains( $email, '@' ) ? trim( $email ) : '' ) );
	}

	/**
	 * A message as the outbox hands it to the mailer.
	 */
	private function message(): \Linker\Commerce\Mail\Message {
		return new \Linker\Commerce\Mail\Message(
			array( 'buyer@example.test' ),
			'Your partner account is approved',
			'<p>Body</p>',
			array( 'From: Linker <sales@de-linker.com>', 'Bcc: archive@example.test', 'Content-Type: text/html; charset=UTF-8' ),
			array()
		);
	}

	/**
	 * The switch is off when the option is absent or empty, on when it holds an address.
	 */
	public function test_the_switch_reads_the_option(): void {
		$test_mode = new TestMode();
		$this->assertFalse( $test_mode->enabled() );
		$this->assertSame( '', $test_mode->address() );

		$this->options[ TestMode::OPTION ] = TestMode::DEFAULT_TO;
		$this->assertTrue( $test_mode->enabled() );
		$this->assertSame( TestMode::DEFAULT_TO, $test_mode->address() );

		$this->options[ TestMode::OPTION ] = '';
		$this->assertFalse( $test_mode->enabled() );
	}

	/**
	 * Turning it on takes the default address or a given one and reads the
	 * switch back; turning it off removes the option; a non-address is refused.
	 */
	public function test_turning_the_switch_on_and_off(): void {
		$test_mode = new TestMode();

		$this->assertTrue( $test_mode->enable() );
		$this->assertSame( TestMode::DEFAULT_TO, $test_mode->address() );
		$this->assertSame( 'chester@de-linker.com', TestMode::DEFAULT_TO, 'The owner ruled this default.' );

		$this->assertTrue( $test_mode->enable( 'tester@example.test' ) );
		$this->assertSame( 'tester@example.test', $test_mode->address() );

		$this->assertTrue( $test_mode->disable() );
		$this->assertArrayNotHasKey( TestMode::OPTION, $this->options, 'The option is removed, not emptied.' );
		$this->assertFalse( $test_mode->enabled() );
		$this->assertTrue( $test_mode->disable(), 'Turning an off switch off again is fine.' );

		$this->assertFalse( $test_mode->enable( 'not an address' ), 'A non-address is refused.' );
		$this->assertFalse( $test_mode->enabled() );
	}

	/**
	 * While test mode is off the message goes out as it is.
	 */
	public function test_off_passes_the_message_through(): void {
		$message = $this->message();
		$this->assertSame( $message, ( new TestMode() )->redirect( $message ) );
	}

	/**
	 * While test mode is on the message goes to the one address, with no
	 * visible or blind copy and everything else kept.
	 */
	public function test_on_redirects_to_the_one_address(): void {
		$this->options[ TestMode::OPTION ] = TestMode::DEFAULT_TO;
		$redirected                        = ( new TestMode() )->redirect( $this->message() );

		$this->assertSame( array( TestMode::DEFAULT_TO ), $redirected->to );
		$this->assertSame(
			array( 'From: Linker <sales@de-linker.com>', 'Content-Type: text/html; charset=UTF-8' ),
			$redirected->headers,
			'The copies are dropped; sender and content type stay.'
		);
		$this->assertSame( 'Your partner account is approved', $redirected->subject );
		$this->assertSame( '<p>Body</p>', $redirected->body );
	}
}
