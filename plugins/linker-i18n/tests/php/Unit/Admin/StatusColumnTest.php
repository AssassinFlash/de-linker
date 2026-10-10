<?php
/**
 * Tests for the German column of the admin lists.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Admin;

use Linker\I18n\Admin\StatusColumn;
use Linker\I18n\Jobs;
use Linker\I18n\Languages;
use Linker\I18n\Translation\State;
use ReflectionClass;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for StatusColumn.
 *
 * @covers \Linker\I18n\Admin\StatusColumn
 */
final class StatusColumnTest extends TestCase {

	/**
	 * The column, without a queue (the tested methods do not use it).
	 */
	private function column(): StatusColumn {
		WP_Mock::passthruFunction( '__' );
		$jobs = ( new ReflectionClass( Jobs::class ) )->newInstanceWithoutConstructor();
		return new StatusColumn( new Languages(), new State(), $jobs );
	}

	/**
	 * The column is added to the list.
	 */
	public function test_column_is_added(): void {
		$this->assertSame(
			array(
				'title'       => 'Title',
				'linker_i18n' => 'German',
			),
			$this->column()->columns( array( 'title' => 'Title' ) )
		);
	}

	/**
	 * Labels for each state of the German version.
	 */
	public function test_labels(): void {
		$column = $this->column();

		$this->assertSame( 'Missing', $column->label( false, '' ) );
		$this->assertSame( 'Missing, translation pending', $column->label( false, State::PENDING ) );
		$this->assertSame( 'Synced', $column->label( true, State::SYNCED ) );
		$this->assertSame( 'Translation pending', $column->label( true, State::PENDING ) );
		$this->assertSame( 'Needs review', $column->label( true, State::NEEDS_REVIEW ) );
	}
}
