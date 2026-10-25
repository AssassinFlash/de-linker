<?php
/**
 * Current category supply follows Woo changes without a brand registry or PDFs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\SupplyBrands;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * A native-shaped category/attribute fixture with separate persisted/runtime data.
 *
 * @covers \Linker\Commerce\Presentation\SupplyBrands
 */
final class SupplyBrandsTest extends TestCase {

	/**
	 * Category parent edges; the commercial child is not hardcoded by the reader.
	 *
	 * @var array<string,string>
	 */
	private array $parents = array(
		'battery-systems' => 'commercial-storage',
		'meters'          => 'accessories',
	);

	/**
	 * Persisted Woo records, changed independently of a render's runtime cache.
	 *
	 * @var array<int,array{status:string,category:string,brand:string,hidden?:bool,outofstock?:bool,reference?:bool}>
	 */
	private array $source = array();

	/**
	 * Native runtime copies.
	 *
	 * @var array<int,array{status:string,category:string,brand:string,hidden?:bool,outofstock?:bool,reference?:bool}>
	 */
	private array $runtime = array();

	/**
	 * Fresh authority assembly count.
	 *
	 * @var int
	 */
	private int $refreshes = 0;

	/**
	 * Native Woo stock visibility setting.
	 *
	 * @var string
	 */
	private string $hide_stock = 'no';

	/**
	 * Request-local product_cat_children option, in WordPress's parent => children shape.
	 *
	 * @var array<string,list<string>>
	 */
	private array $runtime_children = array();

	/**
	 * Request-local stock option.
	 *
	 * @var string
	 */
	private string $runtime_hide_stock = 'no';

	/**
	 * Persisted native term taxonomy IDs; the Woo helper can retain older IDs statically.
	 *
	 * @var array<string,int>
	 */
	private array $visibility = array(
		'exclude-from-catalog' => 101,
		'outofstock'           => 102,
	);

	/** Configure native query/term behavior; no product or document assembler. */
	public function setUp(): void {
		parent::setUp();
		$this->source = array(
			11 => array(
				'status'   => 'publish',
				'category' => 'home-storage',
				'brand'    => 'GoodWe',
			),
			12 => array(
				'status'   => 'publish',
				'category' => 'home-storage',
				'brand'    => 'GoodWe',
			),
			21 => array(
				'status'   => 'publish',
				'category' => 'battery-systems',
				'brand'    => 'Pylontech',
			),
			31 => array(
				'status'   => 'publish',
				'category' => 'commercial-storage',
				'brand'    => 'SAJ',
			),
			41 => array(
				'status'   => 'draft',
				'category' => 'home-storage',
				'brand'    => 'EcoFlow',
			),
			42 => array(
				'status'   => 'publish',
				'category' => 'home-storage',
				'brand'    => 'EcoFlow',
			),
			51 => array(
				'status'    => 'publish',
				'category'  => 'home-storage',
				'brand'     => 'Reference',
				'reference' => true,
			),
			61 => array(
				'status'   => 'publish',
				'category' => 'meters',
				'brand'    => 'Chint',
			),
			71 => array(
				'status'   => 'publish',
				'category' => 'inverters',
				'brand'    => 'InverterOnly',
			),
			81 => array(
				'status'   => 'publish',
				'category' => 'home-storage',
				'brand'    => 'Hidden',
				'hidden'   => true,
			),
		);
		$this->refresh_runtime();
		WP_Mock::userFunction( 'shortcode_atts' )->andReturnUsing( static fn ( array $defaults, array $atts ): array => array_merge( $defaults, $atts ) );
		WP_Mock::userFunction( 'sanitize_title' )->andReturnUsing( static fn ( string $slug ): string => trim( $slug ) );
		WP_Mock::userFunction( 'esc_html' )->andReturnUsing( static fn ( string $text ): string => htmlspecialchars( $text, ENT_QUOTES ) );
		WP_Mock::userFunction( 'wc_get_product_visibility_term_ids' )->andReturn(
			array(
				'exclude-from-catalog' => 101,
				'outofstock'           => 102,
			)
		);
		WP_Mock::userFunction( 'get_option' )->with( 'woocommerce_hide_out_of_stock_items' )->andReturnUsing( fn (): string => $this->runtime_hide_stock );
		WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			function (): bool {
				$this->refresh_runtime();
				++$this->refreshes;
				return true;
			}
		);
		WP_Mock::userFunction( 'has_filter' )->andReturn( true );
		foreach ( array_keys( $this->source ) as $id ) {
			$this->filter_returns( 'linker_commerce_facts_product_id', 42 === $id ? 41 : $id, array( $id ) );
		}
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing( fn ( int $id ): string => $this->runtime[ $id ]['status'] );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing( fn ( int $id ): string => ! empty( $this->runtime[ $id ]['reference'] ) ? EngineeringReference::PV_MODULE : '' );
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing( $this->native_products( ... ) );
		WP_Mock::userFunction( 'get_terms' )->andReturnUsing(
			function ( array $args ): array {
				if ( 'product_cat' === $args['taxonomy'] ) {
					self::assertSame( '', $args['lang'], 'Category identity lookup is explicit across frontend languages.' );
					$ids = array(
						'home-storage'       => 100,
						'commercial-storage' => 200,
					);
					return array_values( array_intersect_key( $ids, array_flip( $args['slug'] ) ) );
				}
				self::assertSame( 'pa_brand', $args['taxonomy'] );
				self::assertNotEmpty( $args['object_ids'], 'An empty object list would expose unrelated native brands.' );
				$names = array_map( fn ( int $id ): string => $this->runtime[ $id ]['brand'], $args['object_ids'] );
				sort( $names );
				return $names;
			}
		);
		WP_Mock::userFunction( 'wp_upload_dir' )->andReturnUsing(
			static function (): never {
				throw new \LogicException( 'Navigation supply must not resolve/hash PDFs.' );
			}
		);
	}

	/** Refresh only local copies, as WordPress runtime cache flush does. */
	private function refresh_runtime(): void {
		$this->runtime            = $this->source;
		$this->runtime_hide_stock = $this->hide_stock;
		$this->runtime_children   = array();
		foreach ( $this->parents as $child => $parent ) {
			$this->runtime_children[ $parent ][] = $child;
		}
	}

	/**
	 * Expand the request-local hierarchy option, including recursive descendants.
	 *
	 * @param string $root Category slug.
	 * @return list<string>
	 */
	private function descendants( string $root ): array {
		$children = $this->runtime_children[ $root ] ?? array();
		foreach ( $children as $child ) {
			$children = array_merge( $children, $this->descendants( $child ) );
		}
		return $children;
	}

	/**
	 * Native category descendants and catalog visibility determine query candidates.
	 *
	 * @param array<string,mixed> $args Native query.
	 * @return int[]
	 */
	private function native_products( array $args ): array {
		self::assertSame( 'publish', $args['post_status'] );
		self::assertFalse( $args['cache_results'] );
		self::assertTrue( $args['linker_publication_internal'] );
		self::assertSame( '', $args['lang'] );
		$scope = $args['tax_query'][0];
		self::assertSame( 'product_cat', $scope['taxonomy'] );
		self::assertTrue( $scope['include_children'] );
		$hidden = $args['tax_query'][1]['terms'] ?? array();
		if ( 'name' === ( $args['tax_query'][1]['field'] ?? '' ) ) {
			$hidden = array_map( fn ( string $name ): int => $this->visibility[ $name ], $hidden );
		}
		self::assertSame( 'term_id', $scope['field'], 'Native taxonomy expansion must not repeat a language-scoped slug lookup.' );
		$roots      = array_map( static fn ( int $id ): string => 100 === $id ? 'home-storage' : 'commercial-storage', $scope['terms'] );
		$categories = $roots;
		foreach ( $roots as $root ) {
			$categories = array_merge( $categories, $this->descendants( $root ) );
		}
		$ids = array();
		foreach ( $this->source as $id => $product ) {
			if ( 'publish' !== $product['status'] || ! in_array( $product['category'], $categories, true ) || ( in_array( $this->visibility['exclude-from-catalog'], $hidden, true ) && ! empty( $product['hidden'] ) ) || ( in_array( $this->visibility['outofstock'], $hidden, true ) && ! empty( $product['outofstock'] ) ) ) {
				continue;
			}
			$ids[] = $id;
		}
		return $ids;
	}

	/** All ten real header fragments retain their sentence and category scope. */
	public function test_real_en_de_header_fragments_use_current_related_brands(): void {
		foreach ( array(
			''    => 'Energy storage from GoodWe, Pylontech and SAJ.',
			'de/' => 'Energiespeicher von GoodWe, Pylontech und SAJ.',
		) as $lang => $storage ) {
			$template = file_get_contents( dirname( __DIR__, 4 ) . '/content/livecanvas/partials/' . $lang . 'header.html' );
			preg_match_all( '/\[linker_supply_brands ([^\]]+)\]/', (string) $template, $fragments );
			$this->assertCount( 5, $fragments[1] );
			$out = array();
			foreach ( $fragments[1] as $fragment ) {
				preg_match_all( '/(\w+)="([^"]*)"/', $fragment, $attributes, PREG_SET_ORDER );
				$atts  = array_column( $attributes, 2, 1 );
				$out[] = ( new SupplyBrands() )->render( $atts );
			}
			$this->assertSame( $storage, $out[0] );
			$this->assertSame( '' === $lang ? 'Home batteries from GoodWe' : 'Heimspeicher-Batterien von GoodWe', $out[1] );
			$this->assertSame( $out[1], $out[3] );
			$this->assertSame( '' === $lang ? 'Commercial storage from Pylontech and SAJ' : 'Gewerbespeicher von Pylontech und SAJ', $out[2] );
			$this->assertSame( $out[2], $out[4] );
		}
		$this->assertSame( 10, $this->refreshes, 'Each independent fragment opens one fresh batch, regardless of product count.' );
	}

	/** A newly added descendant and brand appear without code/template maintenance. */
	public function test_new_descendant_brand_and_later_withdrawal_follow_native_woo(): void {
		$reader = new SupplyBrands();
		$atts   = array( 'categories' => 'commercial-storage' );
		$this->assertSame( 'Pylontech and SAJ', $reader->render( $atts ) );
		$this->parents['future-storage'] = 'battery-systems';
		$this->source[91]                = array(
			'status'   => 'publish',
			'category' => 'future-storage',
			'brand'    => 'New & Storage',
		);
		$this->filter_returns( 'linker_commerce_facts_product_id', 91, array( 91 ) );
		$this->assertSame( 'New &amp; Storage, Pylontech and SAJ', $reader->render( $atts ) );
		$this->source[91] = array_replace( $this->source[91], array( 'status' => 'draft' ) );
		$this->assertSame( 'Pylontech and SAJ', $reader->render( $atts ) );
		$this->assertSame( 3, $this->refreshes );
	}

	/** A still-published locale mirror never restores a withdrawn canonical. */
	public function test_source_withdrawal_and_reference_role_leave_no_old_claim(): void {
		$reader           = new SupplyBrands();
		$atts             = array(
			'categories' => 'home-storage',
			'prefix'     => 'Home batteries from ',
			'suffix'     => '.',
		);
		$this->source[41] = array_replace( $this->source[41], array( 'status' => 'publish' ) );
		$this->assertSame( 'Home batteries from EcoFlow and GoodWe.', $reader->render( $atts ) );
		$this->source[41] = array_replace( $this->source[41], array( 'status' => 'draft' ) );
		$this->source[11] = array_replace( $this->source[11], array( 'status' => 'draft' ) );
		$this->source[12] = array_replace( $this->source[12], array( 'status' => 'draft' ) );
		$this->assertSame( '', $reader->render( $atts ), 'Only the hidden product, reference and withdrawn source mirror remain.' );
		$this->assertSame( 2, $this->refreshes );
	}

	/** Woo's configured stock hiding applies, without treating stock as publication. */
	public function test_stock_visibility_and_empty_or_missing_brands(): void {
		$reader           = new SupplyBrands();
		$this->source[31] = array_replace( $this->source[31], array( 'outofstock' => true ) );
		$atts             = array(
			'categories' => 'commercial-storage',
			'prefix'     => 'Energy storage from ',
			'suffix'     => '.',
		);
		$this->assertSame( 'Energy storage from Pylontech and SAJ.', $reader->render( $atts ) );
		$this->hide_stock = 'yes';
		$this->assertSame( 'Energy storage from Pylontech.', $reader->render( $atts ) );
		$this->source[21] = array_replace( $this->source[21], array( 'brand' => '' ) );
		$this->assertSame( '', $reader->render( $atts ) );
		$this->assertSame( '', $reader->render( array( 'categories' => 'missing' ) ) );
		$this->assertSame( '', $reader->render() );
	}

	/** A reparented child cannot survive the next fragment's stale hierarchy option. */
	public function test_reparented_category_is_removed_before_candidate_selection(): void {
		$reader = new SupplyBrands();
		$atts   = array( 'categories' => 'commercial-storage' );
		$this->assertSame( 'Pylontech and SAJ', $reader->render( $atts ) );
		$this->parents['battery-systems'] = 'accessories';
		$this->assertSame( 'SAJ', $reader->render( $atts ) );
		$this->assertSame( 2, $this->refreshes );
	}

	/** Stock hiding must refresh before candidate SQL, with published statuses unchanged. */
	public function test_stock_option_change_is_applied_before_candidate_selection(): void {
		$reader           = new SupplyBrands();
		$atts             = array( 'categories' => 'commercial-storage' );
		$this->source[31] = array_replace( $this->source[31], array( 'outofstock' => true ) );
		$this->assertSame( 'Pylontech and SAJ', $reader->render( $atts ) );
		$this->hide_stock = 'yes';
		$this->assertSame( 'Pylontech', $reader->render( $atts ) );
		$this->assertSame( 2, $this->refreshes );
	}

	/** Woo's static visibility ID helper is not a fresh authority for recreated terms. */
	public function test_visibility_term_ids_do_not_remain_statically_cached(): void {
		$reader = new SupplyBrands();
		$atts   = array( 'categories' => 'home-storage' );
		$this->assertSame( 'GoodWe', $reader->render( $atts ) );
		$this->visibility['exclude-from-catalog'] = 201;
		$this->assertSame( 'GoodWe', $reader->render( $atts ) );
		$this->assertSame( 2, $this->refreshes );
	}

	/** The commercial sentence names its category even when only batteries remain. */
	public function test_commercial_template_does_not_promise_an_unavailable_product_type(): void {
		$this->source[31] = array_replace( $this->source[31], array( 'status' => 'draft' ) );
		foreach ( array(
			''    => 'Commercial storage from Pylontech',
			'de/' => 'Gewerbespeicher von Pylontech',
		) as $lang => $expected ) {
			$template = file_get_contents( dirname( __DIR__, 4 ) . '/content/livecanvas/partials/' . $lang . 'header.html' );
			preg_match_all( '/\[linker_supply_brands ([^\]]+)\]/', (string) $template, $fragments );
			foreach ( array( 2, 4 ) as $position ) {
				preg_match_all( '/(\w+)="([^"]*)"/', $fragments[1][ $position ], $attributes, PREG_SET_ORDER );
				$this->assertSame( $expected, ( new SupplyBrands() )->render( array_column( $attributes, 2, 1 ) ) );
			}
		}
	}

	/** The presentation module owns one native shortcode registration. */
	public function test_registers_native_shortcode_callback(): void {
		$reader = new SupplyBrands();
		WP_Mock::userFunction( 'add_shortcode' )->once()->with( 'linker_supply_brands', array( $reader, 'render' ) );
		$reader->register();
		$this->assertConditionsMet();
	}
}
