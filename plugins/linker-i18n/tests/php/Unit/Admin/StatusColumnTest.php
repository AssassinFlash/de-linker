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
use Linker\I18n\Tests\Unit\PolylangDouble;
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
		$this->assertSame( 'Translation pending', $column->label( true, State::NEEDS_REVIEW ) );
		$this->assertSame( 'Translation failed', $column->label( true, State::FAILED ) );
		$this->assertSame( 'Translation failed', $column->label( false, State::FAILED ) );
		$this->assertSame( 'German out of date: structure differs', $column->label( true, State::STRUCTURE_MISMATCH ) );
	}

	/**
	 * A German row exposes a nonce-scoped action only to an editor of the source.
	 */
	public function test_german_row_action_checks_source_permission(): void {
		PolylangDouble::mock(
			array(
				5 => 'en',
				6 => 'de',
			),
			array( 5 => 6 )
		);
		WP_Mock::userFunction( 'current_user_can', array( 'return' => static fn( string $capability, int $id ): bool => 6 === $id ) );
		$post = PolylangDouble::post( 6, array( 'post_type' => 'product' ) );
		$this->assertSame( array(), $this->column()->row_actions( array(), $post ) );
	}

	/**
	 * The nonce is checked before translation, even for an otherwise invalid ID.
	 */
	public function test_retranslate_checks_the_object_nonce_first(): void {
		$_GET['post'] = '5';
		WP_Mock::userFunction( 'absint', array( 'return' => 5 ) );
		WP_Mock::userFunction(
			'check_admin_referer',
			array(
				'args'   => array( StatusColumn::ACTION . '_5' ),
				'times'  => 1,
				'return' => static function (): void {
					throw new \RuntimeException( 'nonce rejected' );
				},
			)
		);
		WP_Mock::userFunction( 'as_enqueue_async_action', array( 'times' => 0 ) );
		try {
			$this->expectExceptionMessage( 'nonce rejected' );
			$this->column()->retranslate();
		} finally {
			unset( $_GET['post'] );
		}
	}

	/**
	 * A valid nonce cannot give an unauthorized user permission to translate.
	 */
	public function test_retranslate_rejects_missing_edit_permission(): void {
		$_GET['post'] = '5';
		PolylangDouble::mock( array( 5 => 'en' ) );
		WP_Mock::userFunction( 'absint', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'check_admin_referer', array( 'return' => true ) );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => false ) );
		WP_Mock::passthruFunction( 'esc_html__' );
		WP_Mock::userFunction(
			'wp_die',
			array(
				'return' => static function (): void {
					throw new \RuntimeException( 'permission rejected' );
				},
			)
		);
		WP_Mock::userFunction( 'as_enqueue_async_action', array( 'times' => 0 ) );
		try {
			$this->expectExceptionMessage( 'permission rejected' );
			$this->column()->retranslate();
		} finally {
			unset( $_GET['post'] );
		}
	}
}
