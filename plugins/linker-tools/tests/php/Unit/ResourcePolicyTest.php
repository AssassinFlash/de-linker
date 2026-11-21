<?php
/**
 * Native routes that create a recoverable result.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Protection\ResourcePolicy;
use PHPUnit\Framework\TestCase;

/**
 * Private writes and native reads.
 *
 * @covers \Linker\Tools\Protection\ResourcePolicy
 */
final class ResourcePolicyTest extends TestCase {
	/** Page reads and selecting an existing conversation have no write receipt. */
	public function test_only_result_producing_actions_enter_the_write_path(): void {
		$this->assertSame( '', ResourcePolicy::action( '/linker-ai/v1/genie/draft', 'POST' ) );
		$this->assertSame( 'genie', ResourcePolicy::action( '/linker-ai/v1/genie/turn', 'POST' ) );
		$this->assertSame( 'solution_save', ResourcePolicy::action( '/linker-ai/v1/genie/solution', 'POST' ) );
		$this->assertSame( '', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'GET' ) );
		$this->assertSame( '', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'POST', true ) );
		$this->assertSame( 'conversation_create', ResourcePolicy::action( '/linker-ai/v1/genie/conversations', 'POST' ) );
	}
}
