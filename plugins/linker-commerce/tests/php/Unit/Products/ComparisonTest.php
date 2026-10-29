<?php
/**
 * Tests for the comparison assembly.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Comparison;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Tests for Comparison: the one assembly Genie's ability and the comparison
 * page both read.
 *
 * @covers \Linker\Commerce\Products\Comparison
 */
final class ComparisonTest extends TestCase {

	/**
	 * Fixture products: category term, application, phase, and the figures and
	 * technical table the readings take.
	 *
	 * @var array<int, array<string, mixed>>
	 */
	private const PRODUCTS = array(
		6530 => array(
			'name'     => 'GoodWe GW60K-STS-G10',
			'category' => 'accessories',
			'figures'  => array(),
			'specs'    => array(),
		),
		4107 => array(
			'name'     => 'Inverter 4107',
			'category' => 'inverters',
			'phase'    => 'three-phase',
			'figures'  => array(
				'ac_output_kw_nominal' => array(
					'value' => '10',
					'unit'  => 'kW',
				),
			),
			'specs'    => array(
				array(
					'title'     => '',
					'spec_rows' => array(
						array(
							'spec_label'        => 'Rated AC power',
							'spec_value'        => '10.0',
							'spec_unit'         => 'kW',
							'spec_is_highlight' => true,
						),
					),
				),
			),
		),
		1832 => array(
			'name'     => 'Battery 1832',
			'category' => 'home-storage',
			'figures'  => array(
				'system_nominal_energy_kwh' => array(
					'value' => '5.12',
					'unit'  => 'kWh',
				),
			),
			'specs'    => array(
				array(
					'title'     => '',
					'spec_rows' => array(
						array(
							'spec_label' => 'Ingress protection',
							'spec_value' => 'IP66',
							'spec_unit'  => '',
						),
					),
				),
			),
		),
	);

	/**
	 * Tables to read instead of the small defaults.
	 *
	 * @var array<int, array<mixed>>
	 */
	private array $spec_tables = array();

	/**
	 * Translation and escaping return their argument.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_cache_supports', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_cache_flush_runtime', array( 'return' => true ) );
		// English products: each answers for itself (CommerceState::is_rfq_only asks the language layer).
		$this->english_products(
			array(
				4107 => 4107,
				1832 => 1832,
				6530 => 6530,
			)
		);
		$this->plain_text();
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => 0,
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction( 'get_ancestors', array( 'return' => array() ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_the_post_thumbnail_url', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => static fn ( int $id ): string => self::PRODUCTS[ $id ]['name'] ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => static fn ( int $id ): string => 'https://de-linker.test/product/' . $id . '/' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => static fn ( int $id ): string => isset( self::PRODUCTS[ $id ] ) ? 'product' : '' ) );
		WP_Mock::userFunction( 'get_post_status', array( 'return' => 'publish' ) );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => static function ( int $id, string $taxonomy ) {
					$product = self::PRODUCTS[ $id ];
					if ( 'product_cat' === $taxonomy ) {
						return array(
							(object) array(
								'term_id' => 10,
								'slug'    => $product['category'],
								'name'    => $product['category'],
							),
						);
					}
					$slugs = array();
					foreach ( (array) ( $product[ substr( $taxonomy, 3 ) ] ?? array() ) as $slug ) {
						$slugs[] = $slug;
					}
					return array() === $slugs ? false : array(
						(object) array(
							'term_id' => 20,
							'slug'    => $slugs[0],
							'name'    => $slugs[0],
						),
					);
				},
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => function ( int $id, string $key ) {
					$product = self::PRODUCTS[ $id ];
					return match ( $key ) {
						'_tv_b2b_figures'    => (string) json_encode( $product['figures'] ),
						'_tv_legacy_acf_json' => (string) json_encode( array( 'spec_groups' => $this->spec_tables[ $id ] ?? $product['specs'] ) ),
						'_linker_de_acf_json' => isset( $this->spec_tables[ $id ] ) ? (string) json_encode( array( 'spec_groups' => $this->spec_tables[ $id ] ) ) : '',
						default              => '',
					};
				},
			)
		);
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => static function ( int $id ) {
					if ( ! isset( self::PRODUCTS[ $id ] ) ) {
						return false;
					}
					$product = Mockery::mock( WC_Product::class );
					$product->allows( 'get_id' )->andReturn( $id );
					$product->allows( 'get_parent_id' )->andReturn( 0 );
					$product->allows( 'get_sku' )->andReturn( 'SKU-' . $id );
					$product->allows( 'get_price_html' )->andReturn( '<span>€ 100</span>' );
					$product->allows( 'is_in_stock' )->andReturn( true );
					return $product;
				},
			)
		);
	}

	/**
	 * The columns keep the order they were asked for, and an ID that is not a
	 * published product drops out.
	 */
	public function test_columns_keep_the_order_and_drop_unknown_ids(): void {
		$comparison = ( $this->comparison() )->of( array( 1832, 999, 4107 ) );

		$this->assertSame( array( 1832, 4107 ), array_column( $comparison['products'], 'product_id' ) );
		$this->assertSame( 'SKU-1832', $comparison['products'][0]['sku'] );
		$this->assertSame( 'Battery 1832', $comparison['products'][0]['title'] );
	}

	/**
	 * An inverter and a battery: both families of dimension rows, and never a
	 * single mixed "power" row.
	 */
	public function test_the_rows_carry_both_families_and_never_a_mixed_power_row(): void {
		$comparison = ( $this->comparison() )->of( array( 4107, 1832 ) );
		$fields     = array_column( $comparison['rows'], 'field' );

		$this->assertSame(
			array( 'application', 'phase', 'ac_power_kw', 'pv_input_kw', 'usable_kwh', 'nominal_kwh', 'kwh_range' ),
			$fields
		);
		$power = $comparison['rows'][2];
		$this->assertSame( 'Rated AC power (kW)', $power['label'] );
		$this->assertSame( 10.0, $power['values'][4107] );
		$this->assertSame( 'unknown', $power['values'][1832], 'a battery does not state inverter output' );
	}

	/**
	 * The dimension labels follow the request language, and the page's rows
	 * are the same set the ability documents.
	 */
	public function test_the_labels_follow_the_language(): void {
		$german = ( $this->comparison() )->of( array( 4107 ), 'de' );

		$this->assertSame( 'Anwendung', $german['rows'][0]['label'] );
		$this->assertSame( 'Bemessungsleistung AC (kW)', $german['rows'][2]['label'] );
	}

	/**
	 * The technical rows are the union of the selected products' own tables:
	 * a non-conflicting label stays readable, with values under their products.
	 */
	public function test_the_technical_rows_are_the_union_of_the_tables(): void {
		$comparison = ( $this->comparison() )->of( array( 4107, 1832 ) );
		$specs      = array_column( $comparison['specs'], null, 'label' );

		$this->assertSame( array( 'Rated AC power', 'Ingress protection' ), array_keys( $specs ) );
		$this->assertSame( '10.0 kW', $specs['Rated AC power']['values'][4107] );
		$this->assertSame( '', $specs['Rated AC power']['values'][1832] );
		$this->assertSame( 'IP66', $specs['Ingress protection']['values'][1832] );
	}

	/**
	 * A live product has two different rated powers in different source groups.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_live_rated_powers_keep_their_source_context_in_both_languages(): void {
		$german = false;
		WP_Mock::userFunction(
			'linker_i18n_is_de',
			array(
				'return' => static function () use ( &$german ): bool {
					return $german;
				},
			)
		);
		$products = json_decode( (string) file_get_contents( dirname( __DIR__, 5 ) . '/linker-i18n/tests/fixtures/live/products.json' ), true, 512, JSON_THROW_ON_ERROR );
		$product  = array_values( array_filter( $products, static fn( array $item ): bool => 6530 === $item['id'] ) )[0];
		$cases    = array(
			'en' => array(
				'meta' => '_tv_legacy_acf_json',
				'rows' => array(
					array(
						'label'  => 'Rated power (Grid, back-up and smart port)',
						'values' => array( 6530 => '60 kW' ),
					),
					array(
						'label'  => 'Rated power (Inverter side)',
						'values' => array( 6530 => '30 kW (Printed for this Model on both the EMEA datasheet and the ESA 5–30 kW manual.)' ),
					),
				),
			),
			'de' => array(
				'meta' => '_linker_de_acf_json',
				'rows' => array(
					array(
						'label'  => 'Nennleistung (Netz, Notstrom und Smart Port)',
						'values' => array( 6530 => '60 kW' ),
					),
					array(
						'label'  => 'Nennleistung (Wechselrichterseite)',
						'values' => array( 6530 => '30 kW (Im EMEA-Datenblatt und im ESA-Handbuch 5–30 kW gleichlautend für dieses Modell.)' ),
					),
				),
			),
		);
		foreach ( $cases as $language => $case ) {
			$german                  = 'de' === $language;
			$source                  = json_decode( $product['meta'][ $case['meta'] ], true, 512, JSON_THROW_ON_ERROR );
			$this->spec_tables[6530] = $source['spec_groups'];
			$comparison              = $this->comparison()->of( array( 6530 ), $language );
			$labels                  = 'de' === $language ? 'Nennleistung' : 'Rated power';
			$power_rows              = array_values( array_filter( $comparison['specs'], static fn( array $row ): bool => str_starts_with( $row['label'], $labels ) ) );
			$this->assertSame( $case['rows'], $power_rows, $language );
		}
	}

	/** Context and product identity decide alignment, including repeated rows. */
	public function test_technical_rows_align_only_unambiguous_matching_groups(): void {
		$this->spec_tables[4107] = array(
			array(
				'spec_group_title' => 'Grid',
				'spec_rows'        => array(
					self::spec_row( 'Rated power', '60', 'kW' ),
					self::spec_row( 'Frequency', '50', 'Hz' ),
					self::spec_row( 'Voltage', '100', 'V', 'first' ),
					self::spec_row( 'Voltage', '200', 'V', 'second' ),
				),
			),
			array(
				'spec_group_title' => 'Inverter side',
				'spec_rows'        => array( self::spec_row( 'Rated power', '30', 'kW', 'source' ) ),
			),
		);
		$this->spec_tables[1832] = array(
			array(
				'spec_group_title' => 'Grid',
				'spec_rows'        => array(
					self::spec_row( 'Rated power', '50', 'kW' ),
					self::spec_row( 'Frequency', '60', 'Hz' ),
					self::spec_row( 'Voltage', '12', 'V' ),
				),
			),
			array(
				'spec_group_title' => 'Battery',
				'spec_rows'        => array( self::spec_row( 'Rated power', '7', 'kW' ) ),
			),
			array(
				'spec_group_title' => 'Inverter side',
				'spec_rows'        => array( self::spec_row( 'Rated power', '25', 'kW' ) ),
			),
			array(
				'spec_group_title' => '',
				'spec_rows'        => array( self::spec_row( 'Rated power', '42', 'kW' ) ),
			),
		);

		$specs = $this->comparison()->of( array( 4107, 1832 ) )['specs'];
		$this->assertSame(
			array( 'Rated power (Grid)', 'Frequency', 'Voltage (Grid)', 'Voltage (Grid)', 'Rated power (Inverter side)', 'Voltage (Grid)', 'Rated power (Battery)', 'Rated power' ),
			array_column( $specs, 'label' )
		);
		$this->assertSame(
			array(
				array( '60 kW', '50 kW' ),
				array( '50 Hz', '60 Hz' ),
				array( '100 V (first)', '' ),
				array( '200 V (second)', '' ),
				array( '30 kW (source)', '25 kW' ),
				array( '', '12 V' ),
				array( '', '7 kW' ),
				array( '', '42 kW' ),
			),
			array_map( static fn( array $spec ): array => array_values( $spec['values'] ), $specs )
		);
		foreach ( $specs as $spec ) {
			$this->assertSame( array( 4107, 1832 ), array_keys( $spec['values'] ) );
		}
	}

	/**
	 * One source-format technical row.
	 *
	 * @param string $label Specification label.
	 * @param string $value Specification value.
	 * @param string $unit  Unit.
	 * @param string $note  Source note.
	 * @return array<string, string>
	 */
	private static function spec_row( string $label, string $value, string $unit, string $note = '' ): array {
		return array(
			'spec_label' => $label,
			'spec_value' => $value,
			'spec_unit'  => $unit,
			'spec_note'  => $note,
		);
	}

	/**
	 * The address's selection: numbers only, duplicates and non-numbers out,
	 * in order and never more than a comparison holds.
	 */
	public function test_parse_ids_caps_and_cleans_the_address(): void {
		$this->assertSame(
			array(
				'ids'    => array( 4, 7 ),
				'capped' => false,
			),
			Comparison::parse_ids( '4, 7, 4' )
		);
		$this->assertSame(
			array(
				'ids'    => array( 1, 2, 3, 4 ),
				'capped' => true,
			),
			Comparison::parse_ids( '1,2,3,4,5' )
		);
		$this->assertSame(
			array(
				'ids'    => array(),
				'capped' => false,
			),
			Comparison::parse_ids( 'abc,-3,0,1e3' )
		);
	}

	/** A comparison page releases no partial result after an in-flight withdrawal. */
	public function test_withdrawal_before_release_refuses_the_complete_comparison(): void {
		$reads      = 0;
		$source     = new \Linker\Commerce\Abilities\PublicationData(
			static function () use ( &$reads ): array {
				++$reads;
				$products = array(
					array(
						'product_id'           => 4107,
						'product_revision'     => 'a',
						'published_locale_ids' => array( 4107 ),
					),
				);
				if ( 1 === $reads ) {
					$products[] = array(
						'product_id'           => 1832,
						'product_revision'     => 'b',
						'published_locale_ids' => array( 1832 ),
					);
				}
				return array(
					'source_revision'        => (string) $reads,
					'compatibility_revision' => 'rules',
					'products'               => $products,
					'documents'              => array(),
				);
			}
		);
		$comparison = new Comparison( facts_reader: static fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => \Linker\Commerce\Products\SelectionFacts::for_product( $id ), publication: $source );
		$this->assertSame(
			array(
				'products' => array(),
				'rows'     => array(),
				'specs'    => array(),
			),
			$comparison->of( array( 4107, 1832 ) )
		);
	}

	/** Replacing a cited document cannot relabel old comparison facts as current. */
	public function test_new_document_bytes_before_release_refuse_the_comparison(): void {
		$reads      = 0;
		$source     = new \Linker\Commerce\Abilities\PublicationData(
			static function () use ( &$reads ): array {
				++$reads;
				return array(
					'source_revision'        => (string) $reads,
					'compatibility_revision' => 'rules',
					'products'               => array(
						array(
							'product_id'           => 4107,
							'product_revision'     => 'a',
							'published_locale_ids' => array( 4107 ),
						),
					),
					'documents'              => array(
						array(
							'document_id'       => 'source',
							'document_revision' => 'bytes-' . $reads,
							'product_ids'       => array( 4107 ),
						),
					),
				);
			}
		);
		$comparison = new Comparison( facts_reader: static fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => \Linker\Commerce\Products\SelectionFacts::for_product( $id ), publication: $source );
		$this->assertSame(
			array(
				'products' => array(),
				'rows'     => array(),
				'specs'    => array(),
			),
			$comparison->of( array( 4107 ) )
		);
	}

	/** Presentation fixtures inject their stated facts and an explicit source set. */
	private function comparison(): \Linker\Commerce\Products\Comparison {
		$source = new \Linker\Commerce\Abilities\PublicationData(
			static function (): array {
				$products = array();
				foreach ( array_keys( self::PRODUCTS ) as $id ) {
					$products[] = array(
						'product_id'           => $id,
						'product_revision'     => (string) $id,
						'published_locale_ids' => array( $id ),
					);
				}
				return array(
					'source_revision'        => 'fixture',
					'compatibility_revision' => 'fixture',
					'products'               => $products,
					'documents'              => array(),
				);
			}
		);
		return new \Linker\Commerce\Products\Comparison( facts_reader: static fn( int $id ): \Linker\Commerce\Products\SelectionFactSet => \Linker\Commerce\Products\SelectionFacts::for_product( $id ), publication: $source );
	}
}
