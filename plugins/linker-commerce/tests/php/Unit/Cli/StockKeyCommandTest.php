<?php
/**
 * Tests for the push key command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Cli;

use Linker\Commerce\Cli\StockKeyCommand;
use Linker\Commerce\Stock\PushKey;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_CLI\ExitException;
use WP_Mock;

/**
 * Tests for StockKeyCommand. The WP_CLI double (tests/php/Doubles/wordpress.php)
 * prints every log/warning/success line, so the expectations read the output.
 *
 * @covers \Linker\Commerce\Cli\StockKeyCommand
 */
final class StockKeyCommandTest extends TestCase {

	/**
	 * Only an administrator touches the key.
	 */
	public function test_refuses_non_administrators(): void {
		WP_Mock::userFunction( 'current_user_can', array( 'return' => false ) );

		$this->expectException( ExitException::class );
		( new StockKeyCommand() )( array(), array() );
	}

	/**
	 * Without options a key is generated, only its hash is stored, and the
	 * key itself is printed exactly once.
	 */
	public function test_generate_prints_the_key_once_and_stores_the_hash(): void {
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		$stored = '';
		WP_Mock::userFunction(
			'update_option',
			array(
				'times'  => 1,
				'args'   => array(
					PushKey::OPTION,
					Mockery::on(
						static function ( $value ) use ( &$stored ): bool {
							$stored = (string) $value;
							return is_string( $value ) && (bool) preg_match( '/^[0-9a-f]{64}$/', $value );
						}
					),
					false,
				),
				'return' => true,
			)
		);

		ob_start();
		( new StockKeyCommand() )( array(), array() );
		$output = (string) ob_get_clean();

		$this->assertSame( 1, preg_match( '/wp-cli log: ([0-9a-f]{64})\n/', $output, $key_line ), 'The key itself is the one log line.' );
		$this->assertSame( 1, (int) preg_match_all( '/[0-9a-f]{64}/', $output ), 'The key appears exactly once.' );
		$this->assertStringContainsString( PushKey::HEADER, $output );
		$this->assertSame( hash( 'sha256', (string) ( $key_line[1] ?? '' ) ), $stored );
	}

	/**
	 * --set stores the given key's hash; the key itself is not echoed.
	 */
	public function test_set_stores_the_given_key(): void {
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction(
			'update_option',
			array(
				'times'  => 1,
				'args'   => array( PushKey::OPTION, hash( 'sha256', 'my-erp-key' ), false ),
				'return' => true,
			)
		);

		ob_start();
		( new StockKeyCommand() )( array(), array( 'set' => 'my-erp-key' ) );
		$output = (string) ob_get_clean();

		$this->assertStringNotContainsString( 'my-erp-key', $output );
		$this->assertStringContainsString( 'Push key stored', $output );
	}

	/**
	 * An empty --set is refused.
	 */
	public function test_set_refuses_an_empty_key(): void {
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );

		$this->expectException( ExitException::class );
		( new StockKeyCommand() )( array(), array( 'set' => '' ) );
	}

	/**
	 * --clear removes the key: the endpoint rejects everything again.
	 */
	public function test_clear_removes_the_key(): void {
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction(
			'delete_option',
			array(
				'times'  => 1,
				'args'   => array( PushKey::OPTION ),
				'return' => true,
			)
		);

		ob_start();
		( new StockKeyCommand() )( array(), array( 'clear' => true ) );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'Push key removed', $output );
		$this->assertConditionsMet();
	}
}
