<?php
/**
 * Real hosted bytes and normal evidence capture for product presentation tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use WP_Mock;

/** A specific current product fixture; no global approval or bypass is installed. */
trait CurrentFaqProduct {
	use ManagedDocumentFixture;

	/**
	 * Current product fields including only this test's generated bindings.
	 *
	 * @var array<string,mixed>
	 */
	private array $current_faq_meta = array();

	/**
	 * Supply the actual authority dependencies of the shortcode's chosen product.
	 *
	 * @param int                     $id Published product.
	 * @param array<int|string,mixed> $answers Explicit source FAQ rows.
	 */
	private function current_faq_product( int $id, array $answers ): void {
		$url                    = 'https://de-linker.com/wp-content/uploads/2026/manual.pdf';
		$this->current_faq_meta = array(
			Faqs::META_KEY                      => $answers,
			EngineeringData::DOCUMENTS_META_KEY => array(
				array(
					'url'  => $url,
					'type' => 'manual',
				),
			),
			'_linker_documents_managed'         => '1',
		);
		WP_Mock::userFunction( 'home_url' )->andReturn( 'https://de-linker.com' )->byDefault();
		$this->managed_documents( array( '2026/manual.pdf' ) );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'has_filter' )->andReturn( false )->byDefault();
		WP_Mock::userFunction( 'get_posts' )->andReturn( array( $id ) )->byDefault();
		WP_Mock::userFunction( 'get_post_type' )->with( $id )->andReturn( 'product' )->byDefault();
		WP_Mock::userFunction( 'get_post_status' )->with( $id )->andReturn( 'publish' )->byDefault();
		WP_Mock::userFunction( 'get_post' )->with( $id )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'           => $id,
					'post_title'   => 'Prepared FAQ fixture',
					'post_content' => '',
					'post_excerpt' => '',
					'post_name'    => 'prepared-faq',
				)
			)
		)->byDefault();
		WP_Mock::userFunction( 'get_object_taxonomies' )->andReturn( array() )->byDefault();
		WP_Mock::userFunction( 'pll_get_post_language' )->andReturn( 'en' )->byDefault();
		WP_Mock::userFunction( 'attachment_url_to_postid' )->andReturn( 0 )->byDefault();
		WP_Mock::userFunction( 'get_option' )->andReturn( array() )->byDefault();
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value, int $flags = 0 ): string => (string) json_encode( $value, $flags ) )->byDefault();
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			function ( int $product_id, string $key = '' ) use ( $id ): mixed {
				if ( $id !== $product_id ) {
					return array();
				}
				return '' === $key ? $this->current_faq_meta : ( $this->current_faq_meta[ $key ] ?? '' );
			}
		)->byDefault();
		WP_Mock::userFunction( 'update_post_meta' )->andReturnUsing(
			function ( int $product_id, string $key, mixed $value ) use ( $id ): bool {
				if ( $id !== $product_id ) {
					throw new \LogicException( 'The FAQ fixture owns only its chosen product.' );
				}
				$this->current_faq_meta[ $key ] = $value;
				return true;
			}
		)->byDefault();
		EvidenceBindings::capture_faqs( $id, true );
	}
}
