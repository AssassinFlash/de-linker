<?php
/**
 * Native product-taxonomy template assignment consumers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\ArchiveAssignments;
use Linker\Commerce\Presentation\Templates;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/**
 * Native metadata consumers, including the real Templates producer.
 *
 * @covers \Linker\Commerce\Presentation\ArchiveAssignments
 */
final class ArchiveAssignmentsTest extends TestCase {

	/**
	 * Native metadata rows, preserving every value.
	 *
	 * @var array<int, array<string, list<mixed>>>
	 */
	private array $meta = array();

	/**
	 * Existing published templates.
	 *
	 * @var array<int, WP_Post>
	 */
	private array $posts = array();

	/**
	 * Native language of each template.
	 *
	 * @var array<int, string|false>
	 */
	private array $languages = array();

	/**
	 * Assignment writes attempted by the producer.
	 *
	 * @var list<array{int, string}>
	 */
	private array $writes = array();

	/**
	 * Refuse native writes in the failure consumer.
	 *
	 * @var bool
	 */
	private bool $refuse_write = false;

	/**
	 * Refuse a specific later write to exercise partial batch recovery.
	 *
	 * @var int
	 */
	private int $refuse_at = 0;

	/**
	 * Native call returns success but readback has a different value.
	 *
	 * @var bool
	 */
	private bool $wrong_write = false;

	/**
	 * A native rollback add is refused after a partial write.
	 *
	 * @var bool
	 */
	private bool $refuse_restore = false;

	/**
	 * An updated-post-meta hook fails after the second persisted key.
	 *
	 * @var \Throwable|null
	 */
	private ?\Throwable $write_throwable = null;

	/**
	 * An added-post-meta hook fails during local restoration.
	 *
	 * @var \Throwable|null
	 */
	private ?\Throwable $restore_throwable = null;

	/** Builds real assignment keys, with no request/matcher or content substitute. */
	public function setUp(): void {
		parent::setUp();
		$this->meta      = array();
		$this->posts     = array(
			231  => self::post( 231 ),
			6905 => self::post( 6905 ),
		);
		$this->languages = array(
			231  => 'en',
			6905 => 'de',
		);
		$this->writes    = array();
		$taxonomies      = array();
		foreach ( array( 'product_brand', 'product_cat', 'product_tag', 'pa_battery-voltage', 'pa_brand', 'pa_installation-type', 'pa_monitoring-communication', 'pa_phase', 'pa_power-range', 'pa_product-family', 'pa_series' ) as $name ) {
			$taxonomies[ $name ] = (object) array(
				'name'               => $name,
				'public'             => true,
				'publicly_queryable' => true,
				'object_type'        => array( 'product' ),
			);
		}
		$taxonomies['private']  = (object) array(
			'name'               => 'private',
			'public'             => false,
			'publicly_queryable' => true,
			'object_type'        => array( 'product' ),
		);
		$taxonomies['internal'] = (object) array(
			'name'               => 'internal',
			'public'             => true,
			'publicly_queryable' => false,
			'object_type'        => array( 'product' ),
		);
		$taxonomies['category'] = (object) array(
			'name'               => 'category',
			'public'             => true,
			'publicly_queryable' => true,
			'object_type'        => array( 'post' ),
		);
		WP_Mock::userFunction(
			'get_object_taxonomies',
			array(
				'args'   => array( 'product', 'objects' ),
				'return' => $taxonomies,
			)
		);
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => fn( int $id ) => $this->languages[ $id ] ?? false ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => fn(): array => array_values( $this->posts ) ) )->byDefault();
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => function ( int $id, string $key, bool $single = false ) {
					$values = $this->meta[ $id ][ $key ] ?? array();
					return $single ? ( $values[0] ?? '' ) : $values;
				},
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => function ( int $id, string $key, $value ): bool {
					$this->writes[] = array( $id, $key );
					if ( $this->refuse_write || count( $this->writes ) === $this->refuse_at ) {
						return false;
					}
					$this->meta[ $id ][ $key ] = array( $this->wrong_write ? 'unexpected persisted value' : $value );
					if ( 2 === count( $this->writes ) && null !== $this->write_throwable ) {
						throw $this->write_throwable;
					}
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'delete_post_meta',
			array(
				'return' => function ( int $id, string $key ): bool {
					unset( $this->meta[ $id ][ $key ] );
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'add_post_meta',
			array(
				'return' => function ( int $id, string $key, $value ) {
					if ( $this->refuse_restore ) {
						return false;
					}
					$this->meta[ $id ][ $key ][] = is_string( $value ) ? stripslashes( $value ) : $value;
					if ( null !== $this->restore_throwable ) {
						throw $this->restore_throwable;
					}
					return 1;
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( $value ) => is_string( $value ) ? addslashes( $value ) : $value ) );
	}

	/**
	 * Creates an existing LC template without copying or inventing a layout.
	 *
	 * @param int $id Existing template ID.
	 */
	private static function post( int $id ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'          => $id,
				'post_type'   => Templates::POST_TYPE,
				'post_status' => 'publish',
			)
		);
	}

	/** The actual Templates producer must install metadata even with unchanged HTML. */
	public function test_templates_sync_installs_on_the_existing_pair_without_new_templates(): void {
		$paths    = Templates::paths();
		$by_meta  = array();
		$page_map = ( new \ReflectionClass( Templates::class ) )->getConstant( 'PAGES' );
		foreach ( $paths as $key => $path ) {
			if ( str_ends_with( $key, '__de' ) ) {
				continue;
			}
			$id                 = 'is_archive_for_post_type_product' === $key ? 231 : 1000 + count( $by_meta );
			$post               = self::post( $id );
			$post->post_content = (string) file_get_contents( $path );
			$post->post_title   = $page_map[ $key ][1] ?? 'Template';
			$this->posts[ $id ] = $post;
			$by_meta[ $key ]    = $post;
		}
		$this->posts[6905]->post_content = (string) file_get_contents( $paths['is_archive_for_post_type_product__de'] );
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			function ( array $args ) use ( $by_meta ): array {
				if ( in_array( $args['post_type'], array( 'page', 'lc_partial' ), true ) ) {
						return array();
				}
				$key = $args['name'] ?? $args['meta_key'] ?? null;
				return null === $key ? array_values( $this->posts ) : ( isset( $by_meta[ $key ] ) ? array( $by_meta[ $key ] ) : array() );
			}
		);
		WP_Mock::userFunction( 'get_post', array( 'return' => fn( int $id ): WP_Post => $this->posts[ $id ] ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn( int $id ): int => 231 === $id ? 6905 : 0 ) );
		WP_Mock::userFunction( 'wp_insert_post', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_update_post', array( 'times' => 0 ) );
		( new Templates() )->sync();
		$this->assertCount( 22, $this->writes );
		$this->assertSame( array( '1' ), $this->meta[6905]['is_archive_for_tax_product_cat'] );
		$this->assertSame( array( '1' ), $this->meta[231]['is_archive_for_tax_pa_series'] );
	}

	/** Only public/queryable product registrations participate; a second sync is inert. */
	public function test_discovery_sync_and_drift_are_idempotent(): void {
		$assignments = new ArchiveAssignments();
		$targets     = array(
			'en' => 231,
			'de' => 6905,
		);
		$this->assertCount( 11, $assignments->keys() );
		$this->assertCount( 22, $assignments->drift( $targets ) );
		$this->assertSame( 22, $assignments->sync( $targets ) );
		$this->assertSame( array(), $assignments->drift( $targets ) );
		$this->assertSame( 0, $assignments->sync( $targets ) );
		$this->assertCount( 22, $this->writes );
	}

	/** LC matches meta existence, so even a competing value of zero is explicit ownership. */
	public function test_same_language_generic_owner_refuses_the_entire_batch(): void {
		$this->posts[900]     = self::post( 900 );
		$this->languages[900] = 'de';
		$this->meta[900]      = array( 'is_archive_for_tax_pa_series' => array( '0' ) );
		$before               = $this->meta;
		try {
			( new ArchiveAssignments() )->sync(
				array(
					'en' => 231,
					'de' => 6905,
				)
			);
			$this->fail( 'Another published generic owner must refuse the batch.' );
		} catch ( \RuntimeException $error ) {
			$this->assertStringContainsString( 'is_archive_for_tax_pa_series', $error->getMessage() );
			$this->assertStringContainsString( '900', $error->getMessage() );
		}
		$this->assertSame( array(), $this->writes );
		$this->assertSame( $before, $this->meta );
	}

	/** Per-term and other-language assignments are not stolen or normalized. */
	public function test_other_language_and_per_term_assignments_remain_intact(): void {
		$this->posts[900]     = self::post( 900 );
		$this->languages[900] = 'de';
		$this->meta[900]      = array(
			'is_archive_for_tax_product_brand'  => array( '1' ),
			'is_archive_for_tax_pa_series__saj' => array( '1' ),
		);
		$before               = $this->meta[900];
		$this->assertSame( 11, ( new ArchiveAssignments() )->sync( array( 'en' => 231 ) ) );
		$this->assertSame( $before, $this->meta[900] );
	}

	/** A refused native metadata write cannot be counted successful. */
	public function test_refused_write_restores_the_batch_and_reports_failure(): void {
		$this->refuse_write = true;
		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'assignment' );
		try {
			( new ArchiveAssignments() )->sync( array( 'en' => 231 ) );
		} finally {
			$this->assertEmpty( $this->meta[231] ?? array() );
		}
	}

	/** A later native refusal restores the already-written earlier key. */
	public function test_partial_batch_failure_restores_prior_values(): void {
		$this->meta[231] = array( 'is_archive_for_tax_pa_battery-voltage' => array( '0', '' ) );
		$before          = $this->meta[231];
		$this->refuse_at = 2;
		try {
			( new ArchiveAssignments() )->sync( array( 'en' => 231 ) );
			$this->fail( 'A partially written batch must not pass.' );
		} catch ( \RuntimeException $error ) {
			$this->assertStringContainsString( 'failed readback', $error->getMessage() );
		}
		$this->assertSame( $before, $this->meta[231] );
		$this->assertCount( 2, $this->writes );
	}

	/** A successful API response without matching stored bytes still refuses. */
	public function test_write_success_does_not_replace_actual_readback(): void {
		$this->wrong_write = true;
		try {
			( new ArchiveAssignments() )->sync( array( 'en' => 231 ) );
			$this->fail( 'Incorrect persisted metadata cannot be accepted.' );
		} catch ( \RuntimeException $error ) {
			$this->assertStringContainsString( 'failed readback', $error->getMessage() );
		}
		$this->assertEmpty( $this->meta[231] ?? array() );
	}

	/** Failure of the local rollback is explicit, rather than claiming restoration. */
	public function test_failed_local_rollback_is_reported_separately(): void {
		$this->meta[231]      = array( 'is_archive_for_tax_pa_battery-voltage' => array( '0' ) );
		$this->refuse_at      = 2;
		$this->refuse_restore = true;
		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'Local assignment rollback also failed' );
		( new ArchiveAssignments() )->sync( array( 'en' => 231 ) );
	}

	/**
	 * Both families of native write-after-persist failures.
	 *
	 * @return array<string, array{\Throwable}>
	 */
	public static function hook_throwables(): array {
		return array(
			'plain Exception' => array( new \Exception( 'native metadata hook Exception' ) ),
			'Error'           => array( new \Error( 'native metadata hook Error' ) ),
		);
	}

	/**
	 * Native hooks can throw after writing; recovery restores every original byte.
	 *
	 * @dataProvider hook_throwables
	 * @param \Throwable $failure Native hook failure.
	 */
	public function test_native_hook_throwable_restores_values_and_rethrows_the_same_error( \Throwable $failure ): void {
		$keys                  = ( new ArchiveAssignments() )->keys();
		$this->meta[231]       = array(
			$keys[0]                                  => array( '', '0', "literal\\n and quote's" ),
			'is_archive_for_tax_product_brand__chint' => array( '1' ),
			'unrelated'                               => array( 'keep' ),
		);
		$before                = $this->meta[231];
		$this->write_throwable = $failure;
		try {
			( new ArchiveAssignments() )->sync( array( 'en' => 231 ) );
			$this->fail( 'A native write hook failure cannot pass.' );
		} catch ( \Throwable $caught ) {
			$this->assertSame( $this->write_throwable, $caught );
		}
		ksort( $before );
		ksort( $this->meta[231] );
		$this->assertSame( $before, $this->meta[231] );
		$this->assertArrayNotHasKey( $keys[1], $this->meta[231] );
		$this->assertCount( 2, $this->writes, 'both keys persisted before the hook threw' );
	}

	/**
	 * A restoration hook failure retains both causes instead of masking the write.
	 *
	 * @dataProvider hook_throwables
	 * @param \Throwable $failure Restoration hook failure.
	 */
	public function test_restore_throwable_reports_both_errors_and_retains_original_cause( \Throwable $failure ): void {
		$key                     = ( new ArchiveAssignments() )->keys()[0];
		$this->meta[231]         = array( $key => array( '', '0', "literal\\n and quote's" ) );
		$this->write_throwable   = new \Exception( 'original persisted write hook failure' );
		$this->restore_throwable = $failure;
		try {
			( new ArchiveAssignments() )->sync( array( 'en' => 231 ) );
			$this->fail( 'A failed local recovery cannot pass.' );
		} catch ( \Throwable $caught ) {
			$this->assertInstanceOf( \RuntimeException::class, $caught );
			$this->assertStringContainsString( 'original persisted write hook failure', $caught->getMessage() );
			$this->assertStringContainsString( 'Local assignment rollback also failed: ' . $failure->getMessage(), $caught->getMessage() );
			$this->assertSame( $this->write_throwable, $caught->getPrevious() );
		}
	}

	/** Unknown language cannot authorize taking an existing generic owner. */
	public function test_unclassified_owner_is_visible_in_drift_and_refused(): void {
		$this->posts[900] = self::post( 900 );
		$this->meta[900]  = array( 'is_archive_for_tax_product_tag' => array( '' ) );
		$assignments      = new ArchiveAssignments();
		$rows             = $assignments->drift( array( 'en' => 231 ) );
		$this->assertStringContainsString( 'language unknown', $rows[0]['detail'] );
		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( '900' );
		$assignments->sync( array( 'en' => 231 ) );
	}

	/** One primed published-template query contains no taxonomy meta joins. */
	public function test_owner_scan_uses_one_native_published_template_query(): void {
		WP_Mock::userFunction(
			'get_posts',
			array(
				'args'   => array(
					array(
						'post_type'              => Templates::POST_TYPE,
						'post_status'            => 'publish',
						'posts_per_page'         => -1,
						'lang'                   => '',
						'orderby'                => 'ID',
						'order'                  => 'ASC',
						'update_post_meta_cache' => true,
					),
				),
				'times'  => 1,
				'return' => array_values( $this->posts ),
			)
		);
		( new ArchiveAssignments() )->preflight(
			array(
				'en' => 231,
				'de' => 6905,
			)
		);
		$this->assertSame( array(), $this->writes );
	}

	/** Snapshot/restore retains absence, empty strings, all values and literal slash bytes. */
	public function test_exact_metadata_rollback_touches_only_owned_ids_and_keys(): void {
		$this->meta[231] = array(
			'is_archive_for_tax_product_brand'        => array( '', '0', "literal\\n and quote's" ),
			'is_archive_for_tax_product_brand__chint' => array( '1' ),
			'unrelated'                               => array( 'keep' ),
		);
		$assignments     = new ArchiveAssignments();
		$before          = $this->meta[231];
		$snapshot        = $assignments->snapshot( array( 'en' => 231 ) );
		$this->assertSame( array(), $snapshot[231]['is_archive_for_tax_pa_series'] );
		$assignments->sync( array( 'en' => 231 ) );
		$assignments->restore( $snapshot );
		ksort( $before );
		ksort( $this->meta[231] );
		$this->assertSame( $before, $this->meta[231] );
		$this->assertArrayNotHasKey( 6905, $snapshot );
	}
}
