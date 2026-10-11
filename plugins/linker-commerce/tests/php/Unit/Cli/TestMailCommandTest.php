<?php
/**
 * Tests for the test-mail command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Cli;

use Linker\Commerce\Cli\TestMailCommand;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Tests\TestCase;
use WP_CLI\ExitException;
use WP_Mock;

/**
 * Tests for TestMailCommand: the switch is set, reported and removed, and the
 * output names what mail does next. The WP_CLI double prints every
 * log/warning/success line, so the expectations read the output.
 *
 * @covers \Linker\Commerce\Cli\TestMailCommand
 */
final class TestMailCommandTest extends TestCase {

	/**
	 * Options by name.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/**
	 * An in-memory option store behind the command.
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
	 * `on` sets the switch to the owner's default, `on --to=…` to a given
	 * address, and `off` removes it again.
	 */
	public function test_on_reports_and_off_removes(): void {
		$command = new TestMailCommand( new TestMode() );

		ob_start();
		$command->on( array(), array() );
		$this->assertStringContainsString( 'Test mode is on: every email goes to chester@de-linker.com.', (string) ob_get_clean() );
		$this->assertSame( TestMode::DEFAULT_TO, $this->options[ TestMode::OPTION ] );

		ob_start();
		$command->on( array(), array( 'to' => 'tester@example.test' ) );
		$this->assertStringContainsString( 'tester@example.test', (string) ob_get_clean() );
		$this->assertSame( 'tester@example.test', $this->options[ TestMode::OPTION ] );

		ob_start();
		$command->off( array(), array() );
		$this->assertStringContainsString( 'Test mode is off', (string) ob_get_clean() );
		$this->assertArrayNotHasKey( TestMode::OPTION, $this->options );
	}

	/**
	 * An address WordPress refuses fails the command instead of pretending the
	 * switch is on.
	 */
	public function test_a_non_address_fails(): void {
		$command = new TestMailCommand( new TestMode() );
		$this->expectException( ExitException::class );
		$command->on( array(), array( 'to' => 'not an address' ) );
	}

	/**
	 * `status` names both states.
	 */
	public function test_status(): void {
		$command = new TestMailCommand( new TestMode() );

		ob_start();
		$command->status( array(), array() );
		$this->assertStringContainsString( 'Test mode is off: emails go to their recipients.', (string) ob_get_clean() );

		$this->options[ TestMode::OPTION ] = TestMode::DEFAULT_TO;
		ob_start();
		$command->status( array(), array() );
		$this->assertStringContainsString( 'Test mode is on: every email goes to chester@de-linker.com.', (string) ob_get_clean() );
	}
}
