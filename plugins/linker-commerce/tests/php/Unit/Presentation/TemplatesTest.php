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
				'linker-configurator',
				'linker-configurator-de',
				// The German export of a page type is a source of its own: the
				// product page's German twin is rendered from it.
				'is_single_product__de',
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
			// The configurator's page is the application's mount point, in both
			// languages: the page must never fall back to markup it held before.
			$this->assertStringContainsString( '[linker_configurator]', (string) file_get_contents( $catalog['linker-configurator'] ) );
			$this->assertStringContainsString( '[linker_configurator]', (string) file_get_contents( $catalog['linker-configurator-de'] ) );
			// The German product page's own export: its words are German, so it
			// is not the English file (a shared file would print "Products").
			$german = (string) file_get_contents( $catalog['is_single_product__de'] );
			$this->assertStringContainsString( 'id="tv-storefront-pdp"', $german );
			$this->assertStringContainsString( '>Produkte</a>', $german );
			$this->assertStringContainsString( '[linker_pdp_gallery_pair]', $german );
			$this->assertStringNotContainsString( '>Products</a>', $german );
	}

	/**
	 * A missing template is created with its meta key — its content slashed
	 * like every write — and an insert WordPress refuses stops the run.
	 */
	public function test_sync_inserts_slashed_and_raises_on_a_refused_insert(): void {
		$slashed = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
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
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$existing ): array {
					if ( in_array( $args['post_type'], array( 'page', 'lc_partial' ), true ) ) {
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

			$this->assertSame( 14, $created, 'the six Woo templates and the eight tool-page templates' );
			$this->assertSame( 14, $first['created'] );
		$this->assertSame( 0, $first['updated'] );
		$this->assertSame( 0, $second['created'] );
			$this->assertSame( 14, $second['updated'] );
			$this->assertSame( 14, $updated );
			// Every insert and every update slashes its content — both write paths.
			$this->assertSame( 28, $slashes );
	}

	/**
	 * Templates whose post content already matches the file are left alone:
	 * counted unchanged, never written.
	 */
	public function test_sync_counts_unchanged_templates_and_writes_nothing(): void {
		$catalog = Templates::catalog();
		$keys    = array_keys( $catalog );
		$titles  = array(
			'linker-compare'         => 'Compare products',
			'linker-compare-de'      => 'Produkte vergleichen',
			'linker-faq'             => 'FAQ & documents',
			'linker-faq-de'          => 'FAQ & Dokumente',
			'linker-advisor'         => 'Genie',
			'linker-advisor-de'      => 'Genie',
			'linker-configurator'    => 'Solution Configurator',
			'linker-configurator-de' => 'Lösungskonfigurator',
		);
		$updated = 0;
		$inserts = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $catalog, $keys, $titles ): array {
					if ( in_array( $args['post_type'], array( 'page', 'lc_partial' ), true ) ) {
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
			$this->assertSame( 14, $report['unchanged'] );
		$this->assertSame( 0, $inserts + $updated );
	}

	/**
	 * The product page's German export is written into the German twin of the
	 * English template — the post LiveCanvas renders on /de/produkt/<slug>/
	 * once the assignment is looked up in the request's language. Measured
	 * 2026-10-13 on the review instance before this: /product/<slug>/ rendered
	 * the export through template 234 while /de/produkt/<slug>/ rendered the
	 * legacy template the snapshot carried through its German twin.
	 */
	public function test_the_german_product_export_is_written_into_the_templates_german_twin(): void {
		$catalog = Templates::catalog();
		$writes  = array();
		$this->mock_templates( 234, 6913, $writes );

		$report = ( new Templates() )->sync();

		$this->assertArrayHasKey( 6913, $writes, 'the German twin carries the German export' );
		$this->assertSame( (string) file_get_contents( $catalog['is_single_product__de'] ), $writes[6913]['post_content'] );
		$this->assertNotSame( (string) file_get_contents( $catalog['is_single_product'] ), $writes[6913]['post_content'] );
		$this->assertSame( 1, $report['de_twins_updated'] );
		$this->assertSame( array(), $report['de_twins_missing'] );
	}

	/**
	 * A German twin that already holds the export is left alone: sync is
	 * idempotent, and a second run writes nothing.
	 */
	public function test_a_current_german_twin_is_not_written_again(): void {
		$catalog = Templates::catalog();
		$writes  = array();
		$this->mock_templates( 234, 6913, $writes, (string) file_get_contents( $catalog['is_single_product__de'] ) );

		$report = ( new Templates() )->sync();

		$this->assertSame( array(), $writes );
		$this->assertSame( 0, $report['de_twins_updated'] );
		$this->assertSame( array(), $report['de_twins_missing'] );
	}

	/**
	 * A page type whose anchor has no German twin is reported, and no template
	 * is invented for it: the twin is a translation decision this class does
	 * not own, and present() prints the list.
	 */
	public function test_a_page_type_without_a_german_twin_is_reported_and_not_invented(): void {
		$writes = array();
		$this->mock_templates( 234, 0, $writes );

		$report = ( new Templates() )->sync();

		$this->assertSame( array(), $writes );
		$this->assertSame( 0, $report['de_twins_updated'] );
		$this->assertSame( array( 'is_single_product' ), $report['de_twins_missing'] );
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
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
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

			$this->assertCount( 14, $assigned, 'the six Woo templates and the eight tool-page templates' );
			$this->assertSame( array_fill( 0, 14, 'en' ), array_values( $assigned ) );
	}

	/**
	 * Polylang without configured languages has no source language to name:
	 * the templates stay languageless and a later `wp linker-i18n setup
	 * --assign` covers them.
	 */
	public function test_sync_skips_the_language_when_no_language_is_configured(): void {
		$assigned = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
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
			$this->assertSame( 14, $report['created'] );
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
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
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
	 * A missing or empty header export stops sync() before any write: the
	 * Woo templates and the header partials keep what they had.
	 */
	public function test_sync_refuses_a_missing_header_before_writing_templates(): void {
		$dir     = sys_get_temp_dir() . '/linker-commerce-missing-header-' . getmypid();
		$partial = $dir . '/partials';
		mkdir( $partial . '/de', 0777, true );
		$english = $partial . '/header.html';
		$german  = $partial . '/de/header.html';
		file_put_contents( $english, '<header>english</header>' );
		file_put_contents( $german, '<header>deutsch</header>' );

		$templates_written = 0;
		$partials_written  = 0;
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function () use ( &$templates_written ): int {
					++$templates_written;
					return 1;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$templates_written, &$partials_written ): int {
					if ( isset( $data['post_title'] ) ) {
						++$templates_written;
					} else {
						++$partials_written;
					}
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );

		$templates = new Templates();
		try {
			try {
				$templates->sync( array( $english, $dir . '/partials/missing-header.html' ) );
				$this->fail( 'A missing header source should stop sync() before any write' );
			} catch ( \RuntimeException $e ) {
				$this->assertStringContainsString( 'missing or empty', $e->getMessage() );
				$this->assertStringContainsString( 'missing-header.html', $e->getMessage() );
			}
			$this->assertSame( 0, $templates_written, 'templates must not be written when a header source is missing' );
			$this->assertSame( 0, $partials_written, 'partials must not be written when a header source is missing' );

			$templates_written = 0;
			file_put_contents( $german, "   \n" );
			try {
				$templates->sync( array( $english, $german ) );
				$this->fail( 'An empty header source should stop sync() before any write' );
			} catch ( \RuntimeException $e ) {
				$this->assertStringContainsString( 'missing or empty', $e->getMessage() );
				$this->assertStringContainsString( 'de/header.html', $e->getMessage() );
			}
			$this->assertSame( 0, $templates_written );
			$this->assertSame( 0, $partials_written );
		} finally {
			foreach ( array( $english, $german ) as $path ) {
				if ( file_exists( $path ) ) {
					unlink( $path );
				}
			}
			rmdir( $partial . '/de' );
			rmdir( $partial );
			rmdir( $dir );
		}
	}

		/**
		 * The installed English header and its Polylang twin are written from
		 * the two exports. The twin's slug is kopfzeile, the live German slug,
		 * not header. The German export is already localized, so a repeat
		 * present keeps the German addresses.
		 */
	public function test_sync_writes_the_localized_header_partials(): void {
		$files   = Templates::header_partials();
		$written = array();
		$twins   = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ): array {
					if ( 'lc_partial' === ( $args['post_type'] ?? '' ) && 'header' === ( $args['name'] ?? '' ) ) {
						return array( self::header_partial( 17, '2026-10-01 09:00:00', 'stale header', 'header' ) );
					}
					return array();
				},
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static function ( int $id, string $language ) use ( &$twins ): int {
					$twins[] = array( $id, $language );
					return 17 === $id && 'de' === $language ? 6919 : 0;
				},
			)
		);
		WP_Mock::userFunction( 'get_post', array( 'return' => static fn( int $id ): WP_Post => self::header_partial( $id, 'stale', 'stale header', 6919 === $id ? 'kopfzeile' : 'header' ) ) );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$written ): int {
					$written[ (int) $data['ID'] ] = (string) $data['post_content'];
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );

		( new Templates() )->sync();

		$this->assertSame( array( array( 17, 'de' ) ), $twins );
		$this->assertSame( (string) file_get_contents( $files[0] ), $written[17] );
		$this->assertSame( (string) file_get_contents( $files[1] ), $written[6919] );
		$this->assertStringContainsString( 'href="/de/loesung/heimspeicher/"', $written[6919] );
		$this->assertStringNotContainsString( 'href="/solution/', $written[6919] );
		$this->assertSame( 35, substr_count( $written[17], '<rect x=' ) );
	}

		/**
		 * The German partial is not the same slug. A date-ordered same-slug
		 * lookup would return the newer kopfzeile row if it were queried as
		 * header; the write still follows pll_get_post from the English anchor.
		 */
	public function test_header_twin_is_resolved_from_the_english_partial_not_the_slug(): void {
		$files   = Templates::header_partials();
		$english = (string) file_get_contents( $files[0] );
		$german  = (string) file_get_contents( $files[1] );
		$written = array();
		$queried = array();
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$queried ): array {
					if ( 'lc_partial' !== ( $args['post_type'] ?? '' ) ) {
						return array();
					}
					$queried[] = $args;
					// A same-slug query is the failure under test: the newer
					// German row would come back, and its slug is not header.
					if ( array( 'header' ) === ( $args['post_name__in'] ?? null ) ) {
						return array( self::header_partial( 6919, '2026-10-12 09:00:00', 'stale', 'kopfzeile' ) );
					}
					if ( 'header' === ( $args['name'] ?? '' ) ) {
						return array( self::header_partial( 17, '2026-10-01 09:00:00', 'stale', 'header' ) );
					}
					return array();
				},
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static fn( int $id, string $language ): int => 17 === $id && 'de' === $language ? 6919 : 0,
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static fn( int $id ): WP_Post => self::header_partial( $id, 'stale', 'stale', 6919 === $id ? 'kopfzeile' : 'header' ),
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$written ): int {
					$written[ (int) $data['ID'] ] = (string) $data['post_content'];
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );

		( new Templates() )->sync();

		$this->assertSame( array(), array_values( array_filter( $queried, static fn( array $args ): bool => isset( $args['post_name__in'] ) ) ) );
		$this->assertSame( $english, $written[17] );
		$this->assertSame( $german, $written[6919] );
		$this->assertNotSame( $written[17], $written[6919] );
	}

		/**
		 * An English header whose German twin cannot be resolved stops the
		 * sync. Neither language is written, and the run does not report the
		 * skipped language as a success.
		 */
	public function test_a_missing_german_header_twin_refuses_before_any_partial_write(): void {
		$written = 0;
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ): array {
					if ( 'lc_partial' === ( $args['post_type'] ?? '' ) && 'header' === ( $args['name'] ?? '' ) ) {
						return array( self::header_partial( 17, '2026-10-01 09:00:00', 'stale', 'header' ) );
					}
					return array();
				},
			)
		);
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function () use ( &$written ): int {
					++$written;
					return 1;
				},
			)
		);
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );

		try {
			( new Templates() )->sync();
			$this->fail( 'A missing German header twin should stop sync()' );
		} catch ( \RuntimeException $e ) {
			$this->assertStringContainsString( 'German header partial could not be resolved', $e->getMessage() );
			$this->assertStringContainsString( '17', $e->getMessage() );
		}
		$this->assertSame( 0, $written, 'neither language is written when the twin is missing' );
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
	 * A published header partial. post_date is the trap: the German twin is newer.
	 *
	 * @param int    $id      Post id.
	 * @param string $date    post_date, MySQL datetime.
	 * @param string $content Body.
	 * @param string $slug    post_name. Live German header is kopfzeile, not header.
	 */
	private static function header_partial( int $id, string $date, string $content = 'stale header', string $slug = 'header' ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'           => $id,
				'post_type'    => 'lc_partial',
				'post_status'  => 'publish',
				'post_name'    => $slug,
				'post_date'    => $date,
				'post_content' => $content,
				'post_title'   => 'kopfzeile' === $slug ? 'Kopfzeile' : 'Header',
			)
		);
	}

	/**
	 * A site whose product page type already has an English template — the
	 * anchor in the German-twin logic — with the German twin (or 0 for a site
	 * that has none). Records every post write in $writes.
	 *
	 * The site has no header partial and no tool page: those paths are covered
	 * by their own tests, and an empty answer keeps this one's writes to the
	 * twin the test is about.
	 *
	 * @param int                              $anchor          English template post id.
	 * @param int                              $twin            Its German twin, 0 when the site has none.
	 * @param array<int, array<string, mixed>> $writes Post writes, by id, filled in by the mock.
	 * @param string                           $twin_content    The twin's current body.
	 */
	private function mock_templates( int $anchor, int $twin, array &$writes, string $twin_content = 'stale legacy template' ): void {
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		// phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.FoundAfterLastUsed -- pll_get_post's $language, mirrored for the call shape.
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn( int $id, string $lang ): int => $id === $anchor ? $twin : 0 ) );
		WP_Mock::userFunction( 'pll_default_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'pll_get_post_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_set_post_language', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $anchor ): array {
					if ( in_array( $args['post_type'], array( 'page', 'lc_partial' ), true ) ) {
						return array();
					}
					if ( 'is_single_product' === (string) ( $args['meta_key'] ?? '' ) ) {
						return array( self::post( $anchor, 'stale export', 'Single product' ) );
					}
					return array();
				},
			)
		);
		$english = (string) file_get_contents( Templates::catalog()['is_single_product'] );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static function ( int $id ) use ( $anchor, $twin, $twin_content, $english ): WP_Post {
					if ( $id === $twin ) {
						return self::post( $id, $twin_content, 'Vorlage für einzelnes Produkt' );
					}
					// The English anchor already holds its export: the only post
					// this sync has left to write is the German twin.
					return self::post( $id, $id === $anchor ? $english : 'stale export' );
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function (): int {
					static $id = 700;
					return ++$id;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$writes ): int {
					$writes[ (int) $data['ID'] ] = $data;
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn( string $value ): string => $value ) );
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
