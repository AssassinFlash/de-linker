<?php
/**
 * Resource budgets for account and guest work.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;
use Linker\Tools\Protection\ResourcePolicy;
use PHPUnit\Framework\TestCase;

require_once dirname( __DIR__, 4 ) . '/linker-commerce/vendor/autoload.php';

/**
 * Native resource dimensions for signed-in and anonymous work.
 *
 * @covers \Linker\Tools\Protection\ResourcePolicy
 */
final class ResourcePolicyTest extends TestCase {
	/** Account activity uses provider and concurrent work capacity, independent of earlier finished turns. */
	public function test_account_turn_reserves_only_running_work(): void {
		$identity = new Identity( str_repeat( 'a', 64 ), str_repeat( 'b', 64 ) );
		$plan     = ResourcePolicy::plan( 'genie', $identity, 1 );
		$this->assertNotEmpty( $plan['limits'] );
		foreach ( $plan['limits'] as $limit ) {
			$this->assertSame( 0, $limit->window );
		}
		$this->assertContains( 'genie_site_busy', array_map( static fn ( Allowance $limit ): string => $limit->name, $plan['limits'] ) );
		foreach ( array( 'conversation_create', 'solution_save' ) as $action ) {
			$this->assertSame( array(), ResourcePolicy::plan( $action, $identity )['limits'] );
		}
	}

	/** Guest conversations and saved snapshots consume storage write capacity. */
	public function test_anonymous_persistent_writes_stay_bounded(): void {
		$guest = new Identity( str_repeat( 'a', 64 ), '' );
		foreach ( array( 'conversation_create', 'solution_save' ) as $action ) {
			$plan  = ResourcePolicy::plan( $action, $guest );
			$names = array_map( static fn ( Allowance $limit ): string => $limit->name, $plan['limits'] );
			$this->assertContains( 'tool_write_site_day', $names );
		}
	}
}
