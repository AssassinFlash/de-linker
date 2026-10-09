<?php
/**
 * Tests for the segment aligner.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Translation\Aligner;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Aligner.
 *
 * @covers \Linker\I18n\Translation\Aligner
 */
final class AlignerTest extends TestCase {

	/**
	 * Old and new sequences with the edit between them.
	 *
	 * @return array<string, array{string, string, list<array{string, int, int, int, int}>}>
	 */
	public function provide_edits(): array {
		return array(
			'one replaced'      => array( 'abcd', 'abxd', array( array( 'equal', 0, 2, 0, 2 ), array( 'replace', 2, 3, 2, 3 ), array( 'equal', 3, 4, 3, 4 ) ) ),
			'one added'         => array( 'abcd', 'abcde', array( array( 'equal', 0, 4, 0, 4 ), array( 'insert', 4, 4, 4, 5 ) ) ),
			'first removed'     => array( 'abcd', 'bcd', array( array( 'delete', 0, 1, 0, 0 ), array( 'equal', 1, 4, 0, 3 ) ) ),
			'all new'           => array( '', 'ab', array( array( 'insert', 0, 0, 0, 2 ) ) ),
			'all gone'          => array( 'ab', '', array( array( 'delete', 0, 2, 0, 0 ) ) ),
			'nothing in common' => array( 'abc', 'xyz', array( array( 'replace', 0, 3, 0, 3 ) ) ),
			'unchanged'         => array( 'abc', 'abc', array( array( 'equal', 0, 3, 0, 3 ) ) ),
		);
	}

	/**
	 * The runs describe the edit, longest common part kept.
	 *
	 * @dataProvider provide_edits
	 *
	 * @param string                                  $old      Old sequence, one letter per fingerprint.
	 * @param string                                  $current  New sequence.
	 * @param list<array{string, int, int, int, int}> $expected Runs.
	 */
	public function test_runs( string $old, string $current, array $expected ): void {
		$split = static fn( string $letters ): array => '' === $letters ? array() : str_split( $letters );

		$this->assertSame( $expected, ( new Aligner() )->runs( $split( $old ), $split( $current ) ) );
	}
}
