<?php
/**
 * Published guide selection and reference markup.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\GuideEquipmentMesh;
use Linker\Commerce\Storefront\PageSchema;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/** Validate guide discovery in both languages.
 *
 * @covers \Linker\Commerce\Storefront\GuideEquipmentMesh
 */
final class GuideEquipmentMeshTest extends TestCase {
	/** Resolve each language edition of all eleven journal entries. */
	public function test_bilingual_technical_guides_reference_local_pages(): void {
		$entries = GuideEquipmentMesh::entries();
		self::assertCount( 11, $entries );
		$schema = new PageSchema();
		$this->plain_text();
		WP_Mock::userFunction( 'wc_get_product_id_by_sku' )->andReturn( 0 );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'get_terms' )->andReturn( array() );
		$matrix = new WP_Post( (object) array( 'ID' => 100 ) );
		WP_Mock::userFunction( 'get_page_by_path' )->with( 'inverter-battery-compatibility' )->andReturn( $matrix );
		WP_Mock::userFunction( 'pll_get_post' )->andReturnUsing( static fn( $id, $lang ) => 'en' === $lang ? $id : $id + 100 );
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing( static fn( $id ) => 'https://linker.test/' . $id . '/' );
		$this->mock_journal( $entries );
		$count = 0;
		foreach ( array( 'en', 'de' ) as $lang ) {
			WP_Mock::userFunction( 'pll_current_language' )->andReturn( $lang )->byDefault();
			foreach ( array_keys( $entries ) as $i => $slug ) {
				$post = new WP_Post(
					(object) array(
						'ID'        => $i + 1,
						'post_name' => 'en' === $lang ? $slug : 'de-' . $slug,
					)
				);
				WP_Mock::userFunction( 'get_queried_object' )->andReturn( $post )->byDefault();
				$node = $schema->article_schema( array( '@type' => 'BlogPosting' ) );
				if ( 'ecoflow-goodwe-saj-pylontech-europe-storage-2026' === $slug ) {
					self::assertSame( 'BlogPosting', $node['@type'] );
					continue;
				}
				++$count;
				self::assertSame( array( 'BlogPosting', 'TechArticle' ), $node['@type'] );
				self::assertSame( 'Expert', $node['proficiencyLevel'] );
				self::assertSame( 'WebPage', $node['mentions'][0]['@type'] );
				self::assertSame( 'https://linker.test/' . ( 'en' === $lang ? 100 : 200 ) . '/', $node['mentions'][0]['url'] );
			}
		}
		self::assertSame( 20, $count );
	}

	/**
	 * English source slugs for the mock translation pairs.
	 *
	 * @param array<string,mixed> $entries Canonical guide roster.
	 */
	private function mock_journal( array $entries ): void {
		$slugs = array_keys( $entries );
		WP_Mock::userFunction( 'get_post_field' )->andReturnUsing( static fn( $field, $id ) => $slugs[ $id - 1 ] );
		foreach ( $entries as $entry ) {
			self::assertGreaterThanOrEqual( 3, count( $entry['skus'] ) );
			self::assertLessThanOrEqual( 6, count( $entry['skus'] ) );
			self::assertStringNotContainsString( 'ECOFLOW', implode( ' ', $entry['skus'] ) );
		}
	}

	/** Only a visible, opt-in list without a matching SEOPress FAQ becomes structured data. */
	public function test_visible_and_deduplicated_faq(): void {
		$page = new PageSchema();
		$post = new WP_Post(
			(object) array(
				'ID'           => 10,
				'post_content' => '<p>No questions.</p>',
			)
		);
		WP_Mock::userFunction( 'has_block' )->andReturn( false );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( array() )->byDefault();
		self::assertSame( array(), $page->guide_faq( $post ) );
		$post->post_content = '<section class="lk-faq-list"><h3>Which model?</h3><p>Model A</p><div hidden><h3>Hidden?</h3><p>Hidden</p></div></section>';
		$faq                = $page->guide_faq( $post );
		self::assertSame( 'FAQPage', $faq['@type'] );
		self::assertCount( 1, $faq['mainEntity'] );
		self::assertSame( 'Which model?', $faq['mainEntity'][0]['name'] );
		self::assertSame( 'Model A', $faq['mainEntity'][0]['acceptedAnswer']['text'] );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( array( array( '_seopress_pro_rich_snippets_type' => 'faq' ) ) );
		self::assertSame( array(), $page->guide_faq( $post ) );
	}
}
