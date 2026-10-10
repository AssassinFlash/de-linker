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
	public function test_catalog_covers_the_woo_pages(): void {
		$catalog = Templates::catalog();

		$this->assertSame(
			array( 'is_shop_page', 'is_cart_page', 'is_checkout_page', 'is_account_page', 'is_single_product', 'is_archive_for_post_type_product' ),
			array_keys( $catalog )
		);
		foreach ( $catalog as $path ) {
			$this->assertFileExists( $path );
			$html = (string) file_get_contents( $path );
			$this->assertNotSame( '', trim( $html ) );
		}
		$this->assertStringContainsString( '[linker_price]', (string) file_get_contents( $catalog['is_single_product'] ) );
		$this->assertStringContainsString( '[woocommerce_cart]', (string) file_get_contents( $catalog['is_cart_page'] ) );
		$this->assertStringContainsString( '[linker_checkout]', (string) file_get_contents( $catalog['is_checkout_page'] ) );
		$this->assertStringContainsString( '[woocommerce_my_account]', (string) file_get_contents( $catalog['is_account_page'] ) );
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
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$existing ): array {
					$key = (string) ( $args['meta_key'] ?? '' );
					return isset( $existing[ $key ] ) ? array( $existing[ $key ] ) : array();
				},
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function () use ( &$created ): int {
					++$created;
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
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );

		$templates = new Templates();
		$first     = $templates->sync();
		$second    = $templates->sync();

		$this->assertSame( 6, $created );
		$this->assertSame( 6, $first['created'] );
		$this->assertSame( 0, $first['updated'] );
		$this->assertSame( 0, $second['created'] );
		$this->assertSame( 6, $second['updated'] );
		$this->assertSame( 6, $updated );
	}

	/**
	 * A published LiveCanvas template post.
	 *
	 * @param int    $id      Post id.
	 * @param string $content Body.
	 */
	private static function post( int $id, string $content = '' ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'           => $id,
				'post_type'    => 'lc_dynamic_template',
				'post_status'  => 'publish',
				'post_content' => $content,
				'post_title'   => 'Template',
			)
		);
	}
}
