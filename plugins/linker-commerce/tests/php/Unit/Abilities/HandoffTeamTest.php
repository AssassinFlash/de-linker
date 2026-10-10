<?php
/**
 * Tests for linker/handoff-team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\HandoffTeam;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for HandoffTeam.
 *
 * @covers \Linker\Commerce\Abilities\HandoffTeam
 */
final class HandoffTeamTest extends TestCase {

	/**
	 * Email sanitizing as WordPress does it for the values used here.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => trim( $email ) ) );
		$this->options( array() );
	}

	/**
	 * The sentence names sales@de-linker.com (AGENTS.md §2) in both languages.
	 */
	public function test_default_mailbox_sentence(): void {
		$result = ( new HandoffTeam() )->execute( array( 'summary' => 'Need a delivery date.' ) );

		$this->assertSame( 'Our team will answer that at sales@de-linker.com.', $result['sentence_en'] );
		$this->assertSame( 'Unser Team beantwortet das unter sales@de-linker.com.', $result['sentence_de'] );
		$this->assertStringStartsWith( 'mailto:sales@de-linker.com?body=', $result['mailto'] );
		$this->assertStringContainsString( rawurlencode( 'Need a delivery date.' ), $result['mailto'] );
		$this->assertTrue( ( new HandoffTeam() )->can_execute() );
		$schema = ( new HandoffTeam() )->args()['output_schema'];
		$this->assertSame( array( 'sentence_en', 'sentence_de', 'mailto' ), $schema['required'] );
	}
}
