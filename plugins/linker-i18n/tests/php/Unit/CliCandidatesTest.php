<?php
/**
 * Bulk translation fills gaps without re-translating existing German.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Cli\Command;
use Linker\I18n\Languages;
use Linker\I18n\Translation\State;
use ReflectionClass;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests the selection used by --missing, its --all alias, and --pending.
 *
 * @covers \Linker\I18n\Cli\Command
 */
final class CliCandidatesTest extends TestCase {

	/**
	 * Existing German in any non-pending state is excluded from a bulk backfill.
	 */
	public function test_bulk_candidates_are_only_missing_or_pending(): void {
		$statuses = array(
			1 => 'synced',
			2 => 'needs_review',
			3 => 'failed',
			4 => 'structure_mismatch',
			5 => 'pending',
			6 => '',
		);
		PolylangDouble::mock(
			array_fill_keys( array( 101, 102, 103, 104, 105 ), 'de' ),
			array(
				1 => 101,
				2 => 102,
				3 => 103,
				4 => 104,
				5 => 105,
			),
			array_fill_keys( array( 111, 112, 113, 114, 115 ), 'de' ),
			array(
				11 => 111,
				12 => 112,
				13 => 113,
				14 => 114,
				15 => 115,
			)
		);
		WP_Mock::userFunction( 'get_post_types', array( 'return' => array( 'page' ) ) );
		WP_Mock::userFunction( 'get_taxonomies', array( 'return' => array( 'category' ) ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array_map( static fn( int $id ) => PolylangDouble::post( $id ), array_keys( $statuses ) ) ) );
		WP_Mock::userFunction( 'get_terms', array( 'return' => array_map( static fn( int $id ) => PolylangDouble::term( $id + 10 ), array_keys( $statuses ) ) ) );
		WP_Mock::userFunction( 'get_metadata', array( 'return' => static fn( string $kind, int $id ): string => $statuses[ 'term' === $kind ? $id - 10 : $id ] ) );
		$class   = new ReflectionClass( Command::class );
		$command = $class->newInstanceWithoutConstructor();
		$class->getProperty( 'languages' )->setValue( $command, new Languages() );
		$class->getProperty( 'state' )->setValue( $command, new State() );
		$select = $class->getMethod( 'pending' );
		$this->assertSame( array( array( 'post', 5 ), array( 'term', 15 ) ), $select->invoke( $command ) );
		$this->assertSame( array( array( 'post', 5 ), array( 'post', 6 ), array( 'term', 15 ), array( 'term', 16 ) ), $select->invoke( $command, true ) );
	}
}
