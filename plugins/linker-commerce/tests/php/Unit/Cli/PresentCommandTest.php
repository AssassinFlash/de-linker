<?php
/**
 * Tests for the presentation installer command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Cli;

use Linker\Commerce\Cli\PresentCommand;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for PresentCommand.
 *
 * @covers \Linker\Commerce\Cli\PresentCommand
 */
final class PresentCommandTest extends TestCase {

	/**
	 * A non-administrator is refused before any write.
	 */
	public function test_refuses_a_non_administrator(): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => false,
			)
		);

		try {
			( new PresentCommand() )->__invoke( array(), array() );
			$this->fail( 'WP_CLI::error should stop the command' );
		} catch ( \WP_CLI\ExitException $e ) {
			$this->assertNotSame( '', $e->getMessage() );
		}
	}
}
