<?php
/**
 * Tests for building the engineering feed.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\EngineeringData;
use Linker\Commerce\Catalog\EngineeringFeed;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for EngineeringFeed: the item's shape, the citation rule (a value
 * without a citation of a hosted document is not in the feed), the ?since=
 * filter and the envelope's data versions.
 *
 * @covers \Linker\Commerce\Catalog\EngineeringFeed
 */
final class EngineeringFeedTest extends TestCase {

	/**
	 * A product with every reading mocked: categories, the three name
	 * taxonomies, the selection-fact taxonomies, figures and documents.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 4107 ),
				'return' => 'product',
			)
		);
		WP_Mock::userFunction(
			'get_post_status',
			array(
				'args'   => array( 4107 ),
				'return' => 'publish',
			)
		);
		$product = new \stdClass();
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'args'   => array( 4107 ),
				'return' => $product,
			)
		);
		WP_Mock::userFunction(
			'get_post_modified_time',
			array(
				'args'   => array( 'c', true, 4107 ),
				'return' => '2026-10-10T00:00:00+00:00',
			)
		);
		$this->mock_terms( 4107, 'product_cat', array( 12 => 'inverters' ) );
		$this->mock_terms( 4107, 'pa_application', array( 3 => 'home' ) );
		$this->mock_terms( 4107, 'pa_phase', array( 4 => 'three-phase' ) );
		$this->mock_terms( 4107, 'pa_model', array( 7 => 'H2-10K-T3' ) );
		$this->mock_terms( 4107, 'pa_brand', array( 8 => 'SAJ' ) );
		$this->mock_terms( 4107, 'pa_series', array( 9 => 'saj-h2' ) );
		WP_Mock::userFunction( 'get_ancestors' )->never();
	}

	/**
	 * The item names the product by its model, brand and series, carries the
	 * selection facts of #7 and the documents the migration wrote, and holds
	 * only the figure entries with a citation of a hosted document.
	 */
	public function test_the_item_carries_names_facts_cited_figures_and_documents(): void {
		$this->mock_query();
		$this->mock_meta(
			4107,
			array(
				'mppt_voltage_range_v' => array(
					'value'    => '180~900',
					'unit'     => 'V',
					'citation' => array(
						'url'  => 'https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf',
						'page' => 2,
					),
				),
				'ac_output_kw_nominal' => array(
					'value' => '10',
					'unit'  => 'kW',
				),
				'comms'                => array(
					'value'    => 'Wi-Fi',
					'citation' => array(
						'url'  => 'https://www.example.com/some.pdf',
						'page' => 3,
					),
				),
			)
		);

		$item = EngineeringFeed::item( 4107 );

		$this->assertNotNull( $item );
		$this->assertSame( 4107, $item['id'] );
		$this->assertSame( 'H2-10K-T3', $item['model'] );
		$this->assertSame( 'SAJ', $item['brand'] );
		$this->assertSame( 'saj-h2', $item['series'] );
		$this->assertSame( 'inverters', $item['device_class'] );
		$this->assertSame( 'home', $item['application'] );
		$this->assertSame( 3, $item['phase'] );
		$this->assertSame(
			array( 'mppt_voltage_range_v' ),
			array_keys( $item['figures'] ),
			'the uncited entry and the entry citing another site stay out of the feed'
		);
		$this->assertSame(
			array(
				'url'   => 'https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf',
				'title' => 'SAJ H2-10-30K-T2-T3 Datasheet (EN, BEU)',
				'type'  => 'datasheet',
				'lang'  => 'en',
			),
			$item['documents'][0]
		);
		$this->assertSame( '2026-10-10T00:00:00+00:00', $item['modified_gmt'] );
	}

	/**
	 * The envelope carries the versions of the data files and the overlay.
	 */
	public function test_the_envelope_carries_the_data_versions_and_the_overlay(): void {
		$this->mock_query();
		$this->mock_meta( 4107, array() );

		$feed = EngineeringFeed::feed();

		$this->assertSame( EngineeringData::version( EngineeringData::COMPATIBILITY_FILE ), $feed['compatibility_version'] );
		$this->assertSame( 64, strlen( $feed['compatibility_version'] ) );
		$this->assertIsArray( $feed['overlay'] );
		$this->assertSame( 'mat_trina_solar_tsm_460neg9r_28', $feed['overlay'][0]['id'] );
		$this->assertNotEmpty( $feed['generated_at'] );
	}

	/**
	 * With `since` only the products modified after it are asked for: the
	 * query carries the modified-after condition on the GMT column.
	 */
	public function test_since_narrows_the_product_query_to_the_modified(): void {
		$this->mock_meta( 4107, array() );
		$seen = null;
		$this->mock_query(
			static function ( array $args ) use ( &$seen ): array {
				$seen = $args;

				return array( 4107 );
			}
		);

		$feed = EngineeringFeed::feed( '2026-10-09T00:00:00+00:00' );

		$this->assertSame( array( 4107 ), array_column( $feed['products'], 'id' ) );
		$this->assertIsArray( $seen );
		$this->assertSame( 'post_modified_gmt', $seen['date_query'][0]['column'] );
		$this->assertSame( '2026-10-09 00:00:00', $seen['date_query'][0]['after'] );
		$this->assertFalse( $seen['date_query'][0]['inclusive'] );
	}

	/**
	 * Without `since` the query carries no date condition.
	 */
	public function test_without_since_the_query_has_no_date_condition(): void {
		$this->mock_meta( 4107, array() );
		$seen = null;
		$this->mock_query(
			static function ( array $args ) use ( &$seen ): array {
				$seen = $args;

				return array( 4107 );
			}
		);

		EngineeringFeed::feed();

		$this->assertIsArray( $seen );
		$this->assertArrayNotHasKey( 'date_query', $seen );
	}

	/**
	 * A post that is not a published product answers null.
	 */
	public function test_a_non_product_answers_null(): void {
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'args'   => array( 99 ),
				'return' => 'page',
			)
		);

		$this->assertNull( EngineeringFeed::item( 99 ) );
	}

	/**
	 * Mocks the product query; the capturing callable sees the query's args.
	 *
	 * @param callable|null $capture Receives the args, returns the product IDs.
	 */
	private function mock_query( ?callable $capture = null ): void {
		WP_Mock::userFunction(
			'get_posts',
			array(
				'args'   => array(
					WP_Mock\Functions::type( 'array' ),
				),
				'return' => $capture ?? static fn(): array => array( 4107 ),
			)
		);
	}

	/**
	 * Mocks the terms of a taxonomy for a product.
	 *
	 * @param int                $id       Product ID.
	 * @param string             $taxonomy Taxonomy.
	 * @param array<int, string> $slugs    Slug by term ID.
	 */
	private function mock_terms( int $id, string $taxonomy, array $slugs ): void {
		$names = array(
			'pa_model'  => 'H2-10K-T3',
			'pa_brand'  => 'SAJ',
			'pa_series' => 'saj-h2',
		);
		$terms = array();
		foreach ( $slugs as $term_id => $slug ) {
			$term          = new \stdClass();
			$term->term_id = $term_id;
			$term->slug    = $slug;
			$term->name    = $names[ $taxonomy ] ?? $slug;
			$terms[]       = $term;
		}
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'args'   => array( $id, $taxonomy ),
				'return' => $terms,
			)
		);
	}

	/**
	 * Mocks the two metas the feed reads: figures and documents.
	 *
	 * @param int                                 $id      Product ID.
	 * @param array<string, array<string, mixed>> $figures Figure entries.
	 */
	private function mock_meta( int $id, array $figures ): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( $id, '_tv_b2b_figures', true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => json_encode( $figures ),
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( $id, EngineeringData::DOCUMENTS_META_KEY, true ),
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WP's wrapper is not loaded in the unit tests.
				'return' => json_encode(
					array(
						array(
							'url'   => 'https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf',
							'title' => 'SAJ H2-10-30K-T2-T3 Datasheet (EN, BEU)',
							'type'  => 'datasheet',
							'lang'  => 'en',
						),
					)
				),
			)
		);
	}
}
