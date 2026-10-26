<?php
/**
 * Catalogue summaries and one PDP render have different document-read scopes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Exercise the real family grid, its model payload and its picker together.
 *
 * @covers \Linker\Commerce\Presentation\ProductShortcodes
 * @covers \Linker\Commerce\Storefront\ProductView
 */
final class ProductRenderScopeTest extends TestCase {

	/**
	 * Native state changes between shortcode reads.
	 *
	 * @var array<int,string>
	 */
	private array $statuses = array();

	/**
	 * Native engineering roles.
	 *
	 * @var array<int,string>
	 */
	private array $roles = array();

	/**
	 * The two real fixture families.
	 *
	 * @var array<int,\WC_Product>
	 */
	private array $products = array();

	/**
	 * Current native product loop identity.
	 *
	 * @var int
	 */
	private int $current = 11;

	/** Two families with three and two models, all rendered by the native grid. */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$groups = array( array( 11, 12, 13 ), array( 21, 22 ) );
		$legacy = array();
		foreach ( $groups as $ids ) {
			foreach ( $ids as $id ) {
				$this->statuses[ $id ] = 'publish';
				$legacy[ $id ]         = array( 'family_variants' => array_map( static fn ( int $member ): array => array( 'id' => $member ), $ids ) );
				$product               = Mockery::mock( \WC_Product::class );
				$product->allows( 'get_id' )->andReturn( $id );
				$product->allows( 'get_parent_id' )->andReturn( 0 );
				$product->allows( 'get_name' )->andReturn( 'Fixture model ' . $id );
				$product->allows( 'get_sku' )->andReturn( 'FIXTURE-' . $id );
				$product->allows( 'get_permalink' )->andReturn( 'http://linker.test/product/model-' . $id . '/' );
				$product->allows( 'get_image_id' )->andReturn( 0 );
				$product->allows( 'get_gallery_image_ids' )->andReturn( array() );
				$product->allows( 'get_short_description' )->andReturn( '' );
				$product->allows( 'get_description' )->andReturn( '' );
				$product->allows( 'get_attributes' )->andReturn( array() );
				$product->allows( 'is_in_stock' )->andReturn( true );
				$product->allows( 'is_purchasable' )->andReturn( true );
				$product->allows( 'get_price' )->andReturn( '100' );
				$this->products[ $id ] = $product;
			}
		}
		$this->english_products( array_combine( array_keys( $this->products ), array_keys( $this->products ) ) );
		WP_Mock::userFunction( 'wc_get_product' )->andReturnUsing( fn ( int $id ) => $this->products[ $id ] ?? false );
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing( fn ( int $id ): string => $this->statuses[ $id ] ?? 'draft' );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			fn ( int $id, string $key ): string => match ( $key ) {
				'_tv_legacy_acf_json' => (string) json_encode( $legacy[ $id ] ?? array() ),
				EngineeringReference::ROLE_META_KEY => $this->roles[ $id ] ?? '',
				default => '',
			}
		);
		WP_Mock::userFunction( 'get_the_terms' )->andReturn( false );
		WP_Mock::userFunction( 'wp_get_post_terms' )->andReturn( array() );
		WP_Mock::userFunction( 'has_term' )->andReturn( false );
		WP_Mock::userFunction( 'has_filter' )->andReturn( false );
		WP_Mock::userFunction( 'get_queried_object' )->andReturn( null );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( '' );
		WP_Mock::userFunction( 'pll_get_post_language' )->andReturn( 'en' );
		WP_Mock::userFunction( 'pll_get_post' )->andReturnUsing(
			static function ( int $id, string $lang = '' ): int {
				if ( 'en' === $lang ) {
					return $id;
				}
				return 0;
			}
		);
		WP_Mock::userFunction( 'is_user_logged_in' )->andReturn( false );
		WP_Mock::userFunction( 'get_option' )->andReturn( 'no' );
		WP_Mock::userFunction( 'sanitize_key' )->andReturnUsing( static fn ( string $value ): string => $value );
		WP_Mock::userFunction( 'get_posts' )->andReturn( array_keys( $this->products ) );
		WP_Mock::userFunction( 'get_post_time' )->andReturn( 0 );
		WP_Mock::userFunction( 'wc_get_product_visibility_term_ids' )->andReturn( array() );
		WP_Mock::userFunction( 'wc_get_page_permalink' )->andReturn( 'http://linker.test/my-account/' );
		WP_Mock::userFunction( 'wc_get_checkout_url' )->andReturn( 'http://linker.test/proforma-request/' );
		WP_Mock::userFunction( 'add_query_arg' )->andReturnUsing( static fn ( mixed $first, mixed $second = null, mixed $third = null ): string => (string) ( is_array( $first ) ? $second : $third ) );
		WP_Mock::userFunction( 'wp_unslash' )->andReturnUsing( static fn ( mixed $value ): mixed => $value );
		WP_Mock::userFunction( 'sanitize_text_field' )->andReturnUsing( static fn ( string $value ): string => $value );
		WP_Mock::userFunction( 'get_query_var' )->andReturn( 1 );
		WP_Mock::userFunction( 'get_the_ID' )->andReturnUsing( fn (): int => $this->current );
		WP_Mock::userFunction( 'get_post' )->andReturnUsing( static fn ( int $id ): \WP_Post => new \WP_Post( (object) array( 'ID' => $id ) ) );
		WP_Mock::userFunction( 'setup_postdata' )->andReturnUsing(
			function ( \WP_Post $post ): bool {
				$this->current = $post->ID;
				return true;
			}
		);
		WP_Mock::userFunction( 'wp_reset_postdata' );
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing( static fn ( int $id ): string => 'http://linker.test/product/model-' . $id . '/' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value ): string => (string) json_encode( $value ) );
		WP_Mock::userFunction( 'wp_strip_all_tags' )->andReturnUsing( static fn ( string $value ): string => strip_tags( $value ) );
		WP_Mock::userFunction( 'get_the_title' )->andReturn( 'Fixture' );
		WP_Mock::userFunction( 'get_term_link' )->andReturn( '' );
		WP_Mock::userFunction( 'wp_get_attachment_image_url' )->andReturn( '' );
		$_GET = array();
	}

	/** The old full-fields path calls this expensive boundary twelve times. */
	public function test_complete_multi_family_grid_never_reads_technical_documents(): void {
		$reads = 0;
		$view  = new ProductView(
			new CommerceState(),
			static function () use ( &$reads ): array {
				++$reads;
				return array();
			}
		);
		WP_Mock::userFunction( 'wp_upload_dir' )->andReturnUsing(
			static function (): never {
				throw new \LogicException( 'Catalogue summaries must not resolve or hash a PDF.' );
			}
		);
		$html = ( new ProductShortcodes( new ProductFilters(), $view ) )->products_families();
		$this->assertSame( 2, substr_count( $html, 'data-linker-family-card' ) );
		$this->assertSame( 2, substr_count( $html, 'data-linker-products>' ) );
		$this->assertSame( 5, substr_count( $html, 'data-linker-select-product=' ) );
		preg_match_all( '#<script type="application/json" data-linker-products>(.*?)</script>#s', $html, $matches );
		$payloads = array_map( static fn ( string $json ): array => json_decode( $json, true ), $matches[1] );
		$this->assertCount( 3, $payloads[0] );
		$this->assertCount( 2, $payloads[1] );
		foreach ( array_merge( ...$payloads ) as $member ) {
			$this->assertSame( 'FIXTURE-' . $member['id'], $member['sku'] );
			$this->assertSame( 'http://linker.test/product/model-' . $member['id'] . '/', $member['url'] );
			$this->assertSame( 'Fixture model ' . $member['id'], $member['name'] );
			$this->assertArrayHasKey( 'image', $member );
			$this->assertArrayHasKey( 'selection', $member );
			$this->assertArrayHasKey( 'priceHtml', $member );
			$this->assertArrayHasKey( 'availability', $member );
			$this->assertArrayHasKey( 'factsHtml', $member );
		}
		foreach ( array_keys( $this->products ) as $id ) {
			$this->assertStringContainsString( 'FIXTURE-' . $id, $html );
		}
		$this->assertSame( 0, $reads, 'Lead cards, model JSON and model pickers must all avoid the PDF reader.' );
	}

	/** Multiple PDP shortcodes share only their explicit presentation assembly. */
	public function test_one_product_render_assembles_document_fields_once(): void {
		$reads      = 0;
		$view       = new ProductView(
			new CommerceState(),
			static function () use ( &$reads ): array {
				++$reads;
				return array();
			}
		);
		$shortcodes = new ProductShortcodes( new ProductFilters(), $view );
		$shortcodes->pdp_brand();
		$this->assertStringContainsString( 'FIXTURE-11', $shortcodes->pdp_sku() );
		$shortcodes->pdp_downloads();
		$this->assertSame( 1, $reads );
		// A separate render opens its own assembly, even with the same view object.
		( new ProductShortcodes( new ProductFilters(), $view ) )->pdp_brand();
		$this->assertSame( 2, $reads );
	}

	/** A presentation snapshot never grants access after native withdrawal. */
	public function test_same_render_does_not_release_cached_fields_after_withdrawal(): void {
		$view       = new ProductView( new CommerceState(), static fn (): array => array() );
		$shortcodes = new ProductShortcodes( new ProductFilters(), $view );
		$this->assertStringContainsString( 'FIXTURE-11', $shortcodes->pdp_sku() );
		$this->statuses[11] = 'draft';
		$this->assertSame( '', $shortcodes->pdp_sku() );
		$this->statuses[11] = 'publish';
		$this->roles[11]    = EngineeringReference::PV_MODULE;
		$this->assertSame( '', $shortcodes->pdp_sku() );
	}
}
