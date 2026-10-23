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

	/** Configure native query/term behavior; no product or document assembler. */
	public function setUp(): void {
		parent::setUp();
		$this->source  = array(
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
		$this->runtime = $this->source;
		WP_Mock::userFunction( 'shortcode_atts' )->andReturnUsing( static fn ( array $defaults, array $atts ): array => array_merge( $defaults, $atts ) );
		WP_Mock::userFunction( 'sanitize_title' )->andReturnUsing( static fn ( string $slug ): string => trim( $slug ) );
		WP_Mock::userFunction( 'esc_html' )->andReturnUsing( static fn ( string $text ): string => htmlspecialchars( $text, ENT_QUOTES ) );
		WP_Mock::userFunction( 'wc_get_product_visibility_term_ids' )->andReturn(
			array(
				'exclude-from-catalog' => 101,
				'outofstock'           => 102,
			)
		);
		WP_Mock::userFunction( 'get_option' )->with( 'woocommerce_hide_out_of_stock_items' )->andReturnUsing( fn (): string => $this->hide_stock );
		WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			function (): bool {
				$this->runtime = $this->source;
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
		$ids    = array();
		foreach ( $this->source as $id => $product ) {
			$category = $product['category'];
			while ( ! in_array( $category, $scope['terms'], true ) && isset( $this->parents[ $category ] ) ) {
				$category = $this->parents[ $category ];
			}
			if ( 'publish' !== $product['status'] || ! in_array( $category, $scope['terms'], true ) || ( in_array( 101, $hidden, true ) && ! empty( $product['hidden'] ) ) || ( in_array( 102, $hidden, true ) && ! empty( $product['outofstock'] ) ) ) {
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
			$this->assertSame( '' === $lang ? 'All-in-one systems and battery systems from Pylontech and SAJ' : 'All-in-One-Systeme und Batteriesysteme von Pylontech und SAJ', $out[2] );
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

	/** The presentation module owns one native shortcode registration. */
	public function test_registers_native_shortcode_callback(): void {
		$reader = new SupplyBrands();
		WP_Mock::userFunction( 'add_shortcode' )->once()->with( 'linker_supply_brands', array( $reader, 'render' ) );
		$reader->register();
		$this->assertConditionsMet();
	}
}
