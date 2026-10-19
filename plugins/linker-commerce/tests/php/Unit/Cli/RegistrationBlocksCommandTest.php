<?php
/**
 * Tests for the blocked-registration counter command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Cli;

use Linker\Commerce\Cli\RegistrationBlocksCommand;
use Linker\Commerce\Registration\BlockedRegistrations;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The command is the observable face of a blocked registration (#225).
 *
 * @covers \Linker\Commerce\Cli\RegistrationBlocksCommand
 */
final class RegistrationBlocksCommandTest extends TestCase {

	/**
	 * The counts print by reason with their total; an empty counter says so.
	 */
	public function test_it_prints_the_counts(): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( BlockedRegistrations::OPTION, array() ),
				'return' => array(
					'counts' => array(
						'honeypot' => 2,
						'limit'    => 1,
					),
					'last'   => '2026-10-19 08:00:00',
				),
			)
		);
		ob_start();
		( new RegistrationBlocksCommand() )( array(), array() );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'honeypot: 2', $output );
		$this->assertStringContainsString( 'limit: 1', $output );
		$this->assertStringContainsString( 'total: 3', $output );
		$this->assertStringContainsString( '2026-10-19 08:00:00', $output );
	}

	/**
	 * Without a block the command says so instead of printing an empty table.
	 */
	public function test_it_reports_an_empty_counter(): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( BlockedRegistrations::OPTION, array() ),
				'return' => false,
			)
		);
		ob_start();
		( new RegistrationBlocksCommand() )( array(), array() );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'No blocked registrations.', $output );
	}

	/**
	 * --reset removes the stored counts.
	 */
	public function test_reset_clears_the_option(): void {
		WP_Mock::userFunction(
			'delete_option',
			array(
				'args'   => array( BlockedRegistrations::OPTION ),
				'return' => true,
			)
		);
		ob_start();
		( new RegistrationBlocksCommand() )( array(), array( 'reset' => true ) );
		$output = (string) ob_get_clean();

		$this->assertStringContainsString( 'cleared', $output );
		$this->assertConditionsMet();
	}
}
