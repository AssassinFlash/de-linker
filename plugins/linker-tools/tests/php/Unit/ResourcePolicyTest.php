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
	/** The private Genie service admits model work; these routes retain the native operation identity. */
	public function test_owned_turns_and_account_saves_need_only_idempotency(): void {
		$account = new Identity( str_repeat( 'a', 64 ), str_repeat( 'b', 64 ) );
		$guest   = new Identity( str_repeat( 'c', 64 ), '' );
		foreach ( array( $account, $guest ) as $identity ) {
			$this->assertSame( array(), ResourcePolicy::plan( 'genie', $identity )['limits'] );
		}
		foreach ( array( 'conversation_create', 'solution_save' ) as $action ) {
			$this->assertSame( array(), ResourcePolicy::plan( $action, $account )['limits'] );
		}
		$this->assertEquals( ResourcePolicy::plan( 'conversation_create', $guest ), ResourcePolicy::plan( 'genie', $guest, true ) );
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
