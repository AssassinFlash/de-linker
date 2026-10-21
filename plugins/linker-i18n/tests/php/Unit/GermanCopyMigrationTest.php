<?php
/**
 * Tests for the reviewed German copy migration.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\GermanCopyMigration;
use Linker\I18n\Languages;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;

/**
 * The migration previews before writing, writes once and restores its
 * originals (ticket #264: German data changes are repeatable code, never
 * hand edits).
 *
 * @covers \Linker\I18n\GermanCopyMigration
 */
final class GermanCopyMigrationTest extends TestCase {

	/**
	 * The one reviewed entry these tests run.
	 *
	 * @var list<array{type:string,source:string,set:array<string,string>}>
	 */
	private const MANIFEST = array(
		array(
			'type'   => 'page',
			'source' => 'products',
			'set'    => array( 'meta:_seopress_titles_desc' => 'Neu' ),
		),
	);

	/**
	 * The simulated site: English source, German twin, meta values.
	 *
	 * @var array{meta: array<int, array<string, string>>, posts: array<int, WP_Post>}
	 */
	private array $site = array(
		'meta'  => array(),
		'posts' => array(),
	);

	/**
	 * Seeds one English page and its German twin.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( 'esc_html' );
		$source     = PolylangDouble::post(
			1034,
			array(
				'post_type'   => 'page',
				'post_name'   => 'products',
				'post_title'  => 'Products',
				'post_status' => 'publish',
			)
		);
		$twin       = PolylangDouble::post(
			6853,
			array(
				'post_type'    => 'page',
				'post_name'    => 'produkte',
				'post_title'   => 'Produkte',
				'post_content' => '',
				'post_excerpt' => '',
				'post_status'  => 'publish',
			)
		);
		$this->site = array(
			'meta'  => array(
				6853 => array( '_seopress_titles_desc' => 'Alt' ),
			),
			'posts' => array(
				1034 => $source,
				6853 => $twin,
			),
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => fn( array $args ): array => 'page' === ( $args['post_type'] ?? '' ) && in_array( 'products', (array) ( $args['post_name__in'] ?? array() ), true ) ? array( $this->site['posts'][1034] ) : array(),
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => fn( int $id ) => $this->site['posts'][ $id ] ?? null,
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static fn( int $id, string $lang ): int => 1034 === $id && 'de' === $lang ? 6853 : 0,
			)
		);
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => static fn( int $id ): string => 1034 === $id ? 'en' : 'de' ) );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => fn( int $id, string $key ): string => $this->site['meta'][ $id ][ $key ] ?? '',
			)
		);
		WP_Mock::userFunction(
			'metadata_exists',
			array(
				'return' => fn( string $type, int $id, string $key ): bool => isset( $this->site['meta'][ $id ][ $key ] ),
			)
		);
		WP_Mock::userFunction( 'delete_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => function ( int $id, string $key, $value ): bool {
					$this->site['meta'][ $id ][ $key ] = stripslashes( (string) $value );
					return true;
				},
			)
		);
		// Native post writes remove one slash layer. The flat post fields in
		// this fixture must receive the same slashed input as WordPress.
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static fn( mixed $value ): mixed => is_array( $value )
					? array_map( static fn( mixed $field ): mixed => is_string( $field ) ? addslashes( $field ) : $field, $value )
					: ( is_string( $value ) ? addslashes( $value ) : $value ),
			)
		);
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
	}

	/**
	 * The preview names the object, the field and both values without writing.
	 */
	public function test_the_plan_previews_the_german_change(): void {
		$rows = ( new GermanCopyMigration( new Languages(), self::MANIFEST ) )->plan();

		$this->assertCount( 1, $rows );
		$this->assertSame( 6853, $rows[0]['id'] );
		$this->assertSame( array( 'meta:_seopress_titles_desc' => 'Alt' ), $rows[0]['before'] );
		$this->assertSame( array( 'meta:_seopress_titles_desc' => 'Neu' ), $rows[0]['after'] );
		$this->assertSame( array( '_seopress_titles_desc' => true ), $rows[0]['existed'] );
	}

	/**
	 * A second run after the write has nothing to do — the migration is
	 * idempotent and never rewrites the same value twice.
	 */
	public function test_the_plan_is_empty_after_the_value_is_in_place(): void {
		$this->site['meta'][6853]['_seopress_titles_desc'] = 'Neu';

		$this->assertSame( array(), ( new GermanCopyMigration( new Languages(), self::MANIFEST ) )->plan() );
	}

	/**
	 * Apply keeps the first original and writes through the native meta API;
	 * Verify then passes.
	 */
	public function test_apply_writes_once_and_verify_passes(): void {
		WP_Mock::userFunction( 'get_option', array( 'return' => null ) );
		WP_Mock::userFunction( 'update_option', array( 'return' => true ) );

		$migration = new GermanCopyMigration( new Languages(), self::MANIFEST );
		$this->assertSame( 1, $migration->apply() );
		$this->assertSame( 'Neu', $this->site['meta'][6853]['_seopress_titles_desc'] );
		$migration->verify();
		$this->assertSame( 0, $migration->apply() );
	}

	/** Legal icon escapes and regexes survive apply, repeat and rollback. */
	public function test_post_content_retains_backslashes_through_apply_and_rollback(): void {
		$before                                  = '<script>var icon="\u003csvg>";var space=/\s+/g;</script>';
		$after                                   = '<p>Grüße an Partner.</p>' . $before;
		$this->site['posts'][6853]->post_content = $before;
		$backup                                  = null;
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static function () use ( &$backup ) {
					return $backup;
				},
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => static function ( string $key, array $value ) use ( &$backup ): bool {
					$backup = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => function ( array $data ): int {
					$id = (int) $data['ID'];
					$this->site['posts'][ $id ]->post_content = stripslashes( (string) $data['post_content'] );
					return $id;
				},
			)
		);
		$manifest  = array(
			array(
				'type'   => 'page',
				'source' => 'products',
				'set'    => array( 'post_content' => $after ),
			),
		);
		$migration = new GermanCopyMigration( new Languages(), $manifest );
		$this->assertSame( 1, $migration->apply() );
		$this->assertSame( $after, $this->site['posts'][6853]->post_content );
		$migration->verify();
		$this->assertSame( 0, $migration->apply() );
		$this->assertSame( 1, $migration->rollback() );
		$this->assertSame( $before, $this->site['posts'][6853]->post_content );
	}

	/**
	 * Rollback restores the original through the same native API.
	 */
	public function test_rollback_restores_the_original(): void {
		$row    = array(
			'id'      => 6853,
			'type'    => 'page',
			'source'  => 1034,
			'before'  => array( 'meta:_seopress_titles_desc' => 'Alt' ),
			'after'   => array( 'meta:_seopress_titles_desc' => 'Neu' ),
			'existed' => array( '_seopress_titles_desc' => true ),
		);
		$backup = array(
			'version' => 1,
			'objects' => array( 'page:6853' => $row ),
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn( string $key, $fallback = false ) => GermanCopyMigration::BACKUP === $key ? $backup : $fallback,
			)
		);
		$this->site['meta'][6853]['_seopress_titles_desc'] = 'Neu';

		$this->assertSame( 1, ( new GermanCopyMigration( new Languages(), self::MANIFEST ) )->rollback() );
		$this->assertSame( 'Alt', $this->site['meta'][6853]['_seopress_titles_desc'] );
	}

	/**
	 * A replacement already applied is a no-op; a value that carries neither
	 * side is a drifted manifest and fails.
	 */
	public function test_a_replacement_is_idempotent_and_a_drifted_one_fails(): void {
		$manifest = array(
			array(
				'type'    => 'page',
				'source'  => 'products',
				'replace' => array(
					'meta:_seopress_titles_desc' => array(
						array(
							'old' => 'Alt',
							'new' => 'Neu',
						),
					),
				),
			),
		);
		$this->site['meta'][6853]['_seopress_titles_desc'] = 'Neu';
		$this->assertSame( array(), ( new GermanCopyMigration( new Languages(), $manifest ) )->plan() );

		$this->site['meta'][6853]['_seopress_titles_desc'] = 'Anders';
		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'Reviewed text not found' );
		( new GermanCopyMigration( new Languages(), $manifest ) )->plan();
	}

	/**
	 * A missing English source fails loudly before any write.
	 */
	public function test_a_missing_source_is_refused(): void {
		$manifest = array(
			array(
				'type'   => 'page',
				'source' => 'missing',
				'set'    => array( 'meta:_seopress_titles_desc' => 'Neu' ),
			),
		);

		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'Missing reviewed English source' );

		( new GermanCopyMigration( new Languages(), $manifest ) )->plan();
	}
}
