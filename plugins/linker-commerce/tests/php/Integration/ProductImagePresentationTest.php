<?php
/**
 * Public product photographs retain their verified model and their independent media owners.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use function Linker\Commerce\Migrate\T3\media_restore;

/**
 * Verify published model descriptions and gallery rollback against native media storage.
 *
 * @coversNothing
 */
final class ProductImagePresentationTest extends IntegrationTestCase {
	/** An unrelated draft may adopt the WebP in a featured image, gallery or content. */
	public function test_rollback_keeps_other_posts_adopted_images(): void {
		require_once dirname( __DIR__, 5 ) . '/tools/migrate/batch-t3-media.php';
		$upload = wp_upload_bits( 'linker-t3-test.webp', null, (string) file_get_contents( dirname( __DIR__, 3 ) . '/assets/linker-logo-wordmark.webp' ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Test-owned copy of the plugin's WebP fixture.
		$this->assertFalse( $upload['error'] );
		$image = wp_insert_attachment( array( 'post_mime_type' => 'image/webp' ), $upload['file'] );
		$this->later(
			static function () use ( $image ): void {
				wp_delete_attachment( $image, true );
			}
		);
		$article = wp_insert_post(
			array(
				'post_type'   => 'page',
				'post_title'  => 'Gallery rollback fixture',
				'post_status' => 'draft',
			)
		);
		$this->later(
			static function () use ( $article ): void {
				wp_delete_post( $article, true );
			}
		);
		update_post_meta( $image, '_linker_t3_png_source', $article );
		$snapshot = array(
			'products' => array(),
			'sources'  => array( $article => array( 'existing' => 0 ) ),
		);
		foreach ( array( '_thumbnail_id', '_product_image_gallery' ) as $key ) {
			update_post_meta( $article, $key, $image );
			media_restore( $snapshot );
			$this->assertSame( (string) $image, get_post_meta( $article, $key, true ) );
			$this->assertFileExists( $upload['file'] );
			delete_post_meta( $article, $key );
		}
		wp_update_post(
			array(
				'ID'           => $article,
				'post_content' => '<img src="' . esc_url( $upload['url'] ) . '">',
			)
		);
		media_restore( $snapshot );
		$this->assertFileExists( $upload['file'] );
		wp_delete_post( $article, true );
		media_restore( $snapshot );
		$this->assertNull( get_post( $image ) );
		$this->assertFileDoesNotExist( $upload['file'] );
	}

	/** The same bare model has its own published power and alternate view on both real product pages. */
	public function test_public_goodwe_product_photographs_describe_the_local_model(): void {
		$english = get_page_by_path( 'goodwe-gw50k-et-10', OBJECT, 'product' );
		if ( ! $english ) {
			$this->markTestSkipped( 'Requires the published GoodWe commercial product pair.' );
		}
		foreach ( array( 'en', 'de' ) as $language ) {
			$id       = pll_get_post( $english->ID, $language );
			$response = wp_remote_get( (string) get_permalink( $id ) );
			$this->assertSame( 200, wp_remote_retrieve_response_code( $response ) );
			$markup = wp_remote_retrieve_body( $response );
			$tags   = new \WP_HTML_Tag_Processor( $markup );
			$alts   = array();
			while ( $tags->next_tag() ) {
				if ( 'IMG' === $tags->get_tag() && $tags->has_class( 'pdp-gallery-main' ) ) {
					$alts['main'] = $tags->get_attribute( 'alt' );
				}
				if ( 'META' === $tags->get_tag() && 'og:image:alt' === $tags->get_attribute( 'property' ) ) {
					$alts['og'] = $tags->get_attribute( 'content' );
				}
				if ( 'BUTTON' === $tags->get_tag() && $tags->has_class( 'pdp-gallery-secondary' ) && $tags->next_tag( array( 'tag_name' => 'IMG' ) ) ) {
					$alts['secondary'] = $tags->get_attribute( 'alt' );
				}
			}
			$expected = 'GoodWe GW50K-ET-10 — 50 kW, ' . ( 'de' === $language ? 'dreiphasig, Wechselrichter' : 'three-phase, Inverters' );
			$this->assertSame( $expected, $alts['main'] ?? null );
			$this->assertSame( $expected, $alts['og'] ?? null );
			$this->assertSame( $expected . ( 'de' === $language ? ' — weitere Produktansicht' : ' — alternate product view' ), $alts['secondary'] ?? null );
		}
	}
}
