<?php
/**
 * Tests for the LiveCanvas dynamic templates.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\Templates;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;
use WP_Post;

/**
 * Tests for Templates.
 *
 * @covers \Linker\Commerce\Presentation\Templates
 */
final class TemplatesTest extends TestCase {

	/**
	 * Every Woo page the presentation layer owns has an exported HTML file and a LiveCanvas meta key.
	 */
	public function test_catalog_covers_the_woo_pages_and_the_tool_pages(): void {
		$catalog = Templates::catalog();

		$this->assertSame(
			array(
				'is_shop_page',
				'is_cart_page',
				'is_checkout_page',
				'is_account_page',
				'is_single_product',
				'is_archive_for_post_type_product',
				'linker-compare',
				'linker-compare-de',
				'linker-faq',
				'linker-faq-de',
				'linker-advisor',
				'linker-advisor-de',
			),
			array_keys( $catalog )
		);
		foreach ( $catalog as $path ) {
			$this->assertFileExists( $path );
			$html = (string) file_get_contents( $path );
			$this->assertNotSame( '', trim( $html ) );
		}
		$single = (string) file_get_contents( $catalog['is_single_product'] );
		$this->assertStringContainsString( 'class="pdp-layout"', $single );
		$this->assertStringContainsString( '[linker_pdp_gallery_pair]', $single );
		$this->assertStringContainsString( '[linker_pdp_tools]', $single );
		$this->assertStringContainsString( '[lc_if condition="linker_commerce_pdp_has_pairings"]', $single );
		$this->assertStringNotContainsString( '[linker_pdp_buy]', $single );
		$this->assertStringContainsString( '[linker_catalog_families]', (string) file_get_contents( $catalog['is_shop_page'] ) );
		$this->assertStringContainsString( 'id="tv-storefront-pdp"', (string) file_get_contents( $catalog['is_single_product'] ) );
		$this->assertStringContainsString( 'id="tv-woo-b2b-catalog"', (string) file_get_contents( $catalog['is_shop_page'] ) );
		$this->assertStringContainsString( '[woocommerce_cart]', (string) file_get_contents( $catalog['is_cart_page'] ) );
		$this->assertStringContainsString( '[linker_checkout]', (string) file_get_contents( $catalog['is_checkout_page'] ) );
		$this->assertStringContainsString( '[woocommerce_my_account]', (string) file_get_contents( $catalog['is_account_page'] ) );
		$this->assertStringContainsString( '[linker_compare_table]', (string) file_get_contents( $catalog['linker-compare'] ) );
		$this->assertStringContainsString( '[linker_compare_table]', (string) file_get_contents( $catalog['linker-compare-de'] ) );
			$this->assertStringContainsString( '[linker_document_register]', (string) file_get_contents( $catalog['linker-faq'] ) );
			$this->assertStringContainsString( '[linker_document_register]', (string) file_get_contents( $catalog['linker-faq-de'] ) );
			$this->assertStringContainsString( '[linker_genie_workspace]', (string) file_get_contents( $catalog['linker-advisor'] ) );
			$this->assertStringContainsString( '[linker_genie_workspace]', (string) file_get_contents( $catalog['linker-advisor-de'] ) );
	}

	/**
	 * A missing template is created with its meta key — its content slashed
	 * like every write — and an insert WordPress refuses stops the run.
	 */
	public function test_sync_inserts_slashed_and_raises_on_a_refused_insert(): void {
		$slashed = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static function ( string $value ) use ( &$slashed ): string {
					++$slashed;
					return $value;
				},
			)
		);
		$error = Mockery::mock( \WP_Error::class );
		$error->allows( 'get_error_message' )->andReturn( 'Invalid post type' );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => $error,
			)
		);

		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'wp_insert_post refused the is_shop_page template: Invalid post type' );
		try {
			( new Templates() )->sync();
		} finally {
			Mockery::close();
		}
		$this->assertSame( 1, $slashed );
	}

	/**
	 * A missing template is created with its meta key; a second run updates the same posts and does not create another.
	 */
	public function test_sync_is_idempotent(): void {
		/**
		 * Published templates already assigned, keyed by LiveCanvas meta.
		 *
		 * @var array<string, WP_Post>
		 */
		$existing = array();
		$created  = 0;
		$updated  = 0;
		$slashes  = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$existing ): array {
					if ( 'page' === $args['post_type'] ) {
						return array();
					}
					$key = (string) ( $args['name'] ?? $args['meta_key'] ?? '' );
					return isset( $existing[ $key ] ) ? array( $existing[ $key ] ) : array();
				},
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function ( array $data ) use ( &$created, &$existing ): int {
					++$created;
					if ( isset( $data['post_name'] ) ) {
						$existing[ (string) $data['post_name'] ] = self::post( 500 + $created, 'created', (string) ( $data['post_title'] ?? '' ) );
					}
					return 500 + $created;
				},
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => static function ( int $id, string $key ) use ( &$existing ): bool {
					$existing[ $key ] = self::post( $id, 'from-file' );
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static function ( int $id ): WP_Post {
					return self::post( $id, 'stale' );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function () use ( &$updated ): int {
					++$updated;
					return 1;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static function ( string $value ) use ( &$slashes ): string {
					++$slashes;
					return $value;
				},
			)
		);

		$templates = new Templates();
		$first     = $templates->sync();
		$second    = $templates->sync();

			$this->assertSame( 12, $created, 'the six Woo templates and the six tool-page templates' );
			$this->assertSame( 12, $first['created'] );
		$this->assertSame( 0, $first['updated'] );
		$this->assertSame( 0, $second['created'] );
			$this->assertSame( 12, $second['updated'] );
			$this->assertSame( 12, $updated );
			// Every insert and every update slashes its content — both write paths.
			$this->assertSame( 24, $slashes );
	}

	/**
	 * Templates whose post content already matches the file are left alone:
	 * counted unchanged, never written.
	 */
	public function test_sync_counts_unchanged_templates_and_writes_nothing(): void {
		$catalog = Templates::catalog();
		$keys    = array_keys( $catalog );
		$titles  = array(
			'linker-compare'    => 'Compare products',
			'linker-compare-de' => 'Produkte vergleichen',
			'linker-faq'        => 'FAQ & documents',
			'linker-faq-de'     => 'FAQ & Dokumente',
			'linker-advisor'    => 'Genie',
			'linker-advisor-de' => 'Genie',
		);
		$updated = 0;
		$inserts = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $catalog, $keys, $titles ): array {
					if ( 'page' === $args['post_type'] ) {
						return array();
					}
					$key = (string) ( $args['name'] ?? $args['meta_key'] ?? '' );
					$id  = 600 + array_search( $key, $keys, true );
					return array( self::post( $id, (string) file_get_contents( $catalog[ $key ] ), $titles[ $key ] ?? 'Template' ) );
				},
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static function ( int $id ) use ( $catalog, $keys, $titles ): WP_Post {
					$key = (string) $keys[ $id - 600 ];
					return self::post( $id, (string) file_get_contents( $catalog[ $key ] ), $titles[ $key ] ?? 'Template' );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 0,
				'return' => static function () use ( &$inserts ): int {
					++$inserts;
					return 1;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times'  => 0,
				'return' => static function () use ( &$updated ): int {
					++$updated;
					return 1;
				},
			)
		);

		$report = ( new Templates() )->sync();

		$this->assertSame( 0, $report['created'] );
		$this->assertSame( 0, $report['updated'] );
			$this->assertSame( 12, $report['unchanged'] );
		$this->assertSame( 0, $inserts + $updated );
	}

	/**
	 * A template created while Polylang runs gets the site's source language
	 * when it has none, and one that already carries a language keeps it (#11's
	 * LiveCanvas forensics: a languageless source is silently skipped when its
	 * German twin is paired).
	 */
	public function test_sync_assigns_the_source_language_to_languageless_templates(): void {
		$assigned = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static fn(): array => array(), // Nothing existing: sync creates all ten.
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function () {
					static $id = 700;
					return ++$id;
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_get_post_language',
			array(
				'return' => static fn(): bool => false, // The API answers false for a post without a language.
			)
		);
		WP_Mock::userFunction(
			'pll_set_post_language',
			array(
				'return' => static function ( int $id, string $slug ) use ( &$assigned ): bool {
					$assigned[ $id ] = $slug;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );

		( new Templates() )->sync();

			$this->assertCount( 12, $assigned, 'the six Woo templates and the six tool-page templates' );
			$this->assertSame( array_fill( 0, 12, 'en' ), array_values( $assigned ) );
	}

	/**
	 * Polylang without configured languages has no source language to name:
	 * the templates stay languageless and a later `wp linker-i18n setup
	 * --assign` covers them.
	 */
	public function test_sync_skips_the_language_when_no_language_is_configured(): void {
		$assigned = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static fn(): array => array(),
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function () {
					static $id = 800;
					return ++$id;
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) ); // Polylang's answer without languages.
		WP_Mock::userFunction(
			'pll_set_post_language',
			array(
				'return' => static function ( int $id, string $slug ) use ( &$assigned ): bool {
					$assigned[ $id ] = $slug;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );

		$report = ( new Templates() )->sync();

		$this->assertSame( array(), $assigned );
			$this->assertSame( 12, $report['created'] );
	}

	/**
	 * Each tool page carries the LiveCanvas per-post choice of its own
	 * language's template: the page's template loader reads the choice from
	 * the queried post, so the English page and the German page name
	 * different templates.
	 */
	public function test_tool_pages_get_their_template_choice(): void {
		$assigned = array();
		$pages    = array(
			array(
				'ID'        => 5385,
				'post_name' => 'compare-products',
				'post_type' => 'page',
			),
			array(
				'ID'        => 6608,
				'post_name' => 'compare-products',
				'post_type' => 'page',
			),
			array(
				'ID'        => 932,
				'post_name' => 'faq-download',
				'post_type' => 'page',
			),
			array(
				'ID'        => 6871,
				'post_name' => 'faq-download',
				'post_type' => 'page',
			),
			array(
				'ID'        => 4101,
				'post_name' => 'linker-advisor',
				'post_type' => 'page',
			),
			array(
				'ID'        => 4102,
				'post_name' => 'linker-berater',
				'post_type' => 'page',
			),
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $pages ): array {
					if ( 'page' !== $args['post_type'] ) {
						return array();
					}
					return array_values(
						array_filter(
							self::wp_posts( $pages ),
							static fn( WP_Post $post ): bool => $post->post_name === $args['name']
						)
					);
				},
			)
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		WP_Mock::userFunction(
			'wp_slash',
			array(
				'return' => static fn( $value ) => $value,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static fn(): int => 700,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'is_wp_error',
			array(
				'return' => false,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'times'  => '0+',
				'return' => static function ( int $id, string $key, $value ) use ( &$assigned ): bool {
					$assigned[ $id ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'pll_get_post_language',
			array(
				'return' => static fn ( int $id ): string => in_array( $id, array( 6608, 6871, 4102 ), true ) ? 'de' : 'en',
				'times'  => '0+',
			)
		);
		// sync() also gives every template it creates or updates the site's
		// source language (assign_source_language()).
		WP_Mock::userFunction(
			'pll_default_language',
			array(
				'return' => 'en',
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'pll_set_post_language',
			array(
				'return' => true,
				'times'  => '0+',
			)
		);

		( new Templates() )->sync();

		$this->assertSame( 'linker-compare', $assigned[5385] );
		$this->assertSame( 'linker-compare-de', $assigned[6608] );
			$this->assertSame( 'linker-faq', $assigned[932] );
			$this->assertSame( 'linker-faq-de', $assigned[6871] );
			$this->assertSame( 'linker-advisor', $assigned[4101] );
			$this->assertSame( 'linker-advisor-de', $assigned[4102] );
	}

	/**
	 * The page's rows as WP_Post objects.
	 *
	 * @param array<int, array<string, mixed>> $rows Rows.
	 * @return list<WP_Post>
	 */
	private static function wp_posts( array $rows ): array {
		$posts = array();
		foreach ( $rows as $row ) {
			$posts[] = new WP_Post(
				(object) array(
					'ID'           => (int) $row['ID'],
					'post_name'    => (string) $row['post_name'],
					'post_type'    => (string) $row['post_type'],
					'post_status'  => 'publish',
					'post_title'   => 'Page',
					'post_content' => '',
				)
			);
		}
		return $posts;
	}

	/**
	 * A published LiveCanvas template post.
	 *
	 * @param int    $id      Post id.
	 * @param string $content Body.
	 * @param string $title   Post title, the tool templates' own words.
	 */
	private static function post( int $id, string $content = '', string $title = 'Template' ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'           => $id,
				'post_type'    => 'lc_dynamic_template',
				'post_status'  => 'publish',
				'post_content' => $content,
				'post_title'   => $title,
			)
		);
	}
}
