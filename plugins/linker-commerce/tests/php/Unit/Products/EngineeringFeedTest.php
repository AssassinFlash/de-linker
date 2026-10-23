<?php
/**
 * Tests for building the engineering feed.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\EngineeringFeed;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for EngineeringFeed: the item's shape, the citation rule (a value
 * without a citation of a hosted document is not in the feed), the ?since=
 * filter and the envelope's data versions.
 *
 * @covers \Linker\Commerce\Products\EngineeringFeed
 */
final class EngineeringFeedTest extends TestCase {
	use \Linker\Commerce\Tests\Support\ManagedDocumentFixture;

	/** Release generated upload files after every unit case. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/**
	 * A product with every reading mocked: categories, the three name
	 * taxonomies, the selection-fact taxonomies, figures and documents.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'pll_get_post_language' )->andReturn( 'en' )->byDefault();
		$this->managed_documents( array( '2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf' ) );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true )->byDefault();
		WP_Mock::userFunction( 'get_object_taxonomies' )->andReturn( array() )->byDefault();
		WP_Mock::userFunction( 'get_post' )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'           => 4107,
					'post_title'   => 'H2-10K-T3',
					'post_content' => '',
					'post_excerpt' => '',
					'post_name'    => 'h2',
				)
			)
		)->byDefault();
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			static function ( int $id, string $key = '' ) {
				return '' === $key ? array() : '';
			}
		)->byDefault();
		WP_Mock::userFunction( 'attachment_url_to_postid' )->andReturn( 0 )->byDefault();
		WP_Mock::userFunction( 'get_option' )->andReturn( array() )->byDefault();
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( $value, int $flags = 0 ): string => (string) json_encode( $value, $flags ) )->byDefault();
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
		// Another test class may already have mocked has_filter (WP_Mock defines
		// a mocked function for the rest of the run), which puts the language
		// layer's twin-swap branch of SelectionFacts on the path; the swap has
		// no listener here.
		// Production's home, unless a test says this is an instance. Pull load
		// rewrites citations onto the instance origin; the default keeps the
		// production rule on the path the other tests walk.
		WP_Mock::userFunction( 'home_url' )->andReturn( 'https://de-linker.com' )->byDefault();
		WP_Mock::userFunction(
			'has_filter',
			array(
				'return' => false,
				'times'  => '0+',
			)
		);
	}

	/**
	 * The item names the product by its model, brand and series, carries the
	 * selection facts of #7 and the documents the migration wrote, and holds
	 * only the figure entries with a citation of a hosted document.
	 */
	public function test_the_item_carries_names_facts_cited_figures_and_documents(): void {
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- standing in for wp_json_encode, which WordPress is not here to provide.
				'return' => static fn( $data ): string => (string) json_encode( $data ),
			)
		);
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
		// The five #7 facts the feed schema requires (feed.schema.json); the
		// mocked figures state ac_output_kw_nominal 10 kW, the rest is unknown.
		$this->assertSame( 'unknown', $item['ac_power_kw'], 'uncited source values cannot become authorized engineering facts' );
		$this->assertSame( 'unknown', $item['pv_input_kw'] );
		$this->assertSame( 'unknown', $item['usable_kwh'] );
		$this->assertSame( 'unknown', $item['nominal_kwh'] );
		$this->assertNull( $item['kwh_range'] );
		$this->assertArrayNotHasKey( 'modified_gmt', $item, 'the product carries no modified_gmt (feed.schema.json)' );
		$this->assertSame(
			array( 'mppt_voltage_range_v' ),
			array_keys( get_object_vars( $item['figures'] ) ),
			'the uncited entry and the entry citing another site stay out of the feed'
		);
		$this->assertSame(
			array(
				'url'   => 'https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf',
				'title' => 'SAJ H2-10-30K-T2-T3 Datasheet (EN, BEU)',
				'type'  => 'datasheet',
				'lang'  => 'en',
			),
			array_intersect_key( $item['documents'][0], array_flip( array( 'url', 'title', 'type', 'lang' ) ) )
		);
		// The figures serialize as an object, also when the set is empty ({} never []).
		$this->assertSame( '{"mppt_voltage_range_v":{"value":"180~900","unit":"V","citation":{"url":"https:\/\/de-linker.com\/wp-content\/uploads\/2026\/09\/H2-10-30K-T2T3-datasheet-EN-BEU.pdf","page":2}}}', (string) wp_json_encode( $item['figures'] ) );
	}

	/**
	 * Pull load rewrites every live address to this instance. A citation of
	 * that rewritten address is still a document we host: the figure stays,
	 * and the feed names it on de-linker.com — the only host the engine's
	 * schema accepts. Another site, and another port of this machine, stay out.
	 */
	public function test_a_citation_rewritten_to_this_instance_stays_and_is_named_on_the_canonical_host(): void {
		WP_Mock::userFunction(
			'home_url',
			array(
				'return' => 'http://127.0.0.1:9240',
				'times'  => '0+',
			)
		);
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- standing in for wp_json_encode, which WordPress is not here to provide.
				'return' => static fn( $data ): string => (string) json_encode( $data ),
			)
		);
		$this->mock_query();
		$local     = 'http://127.0.0.1:9240/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf';
		$canonical = 'https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf';
		$this->mock_meta(
			4107,
			array(
				'mppt_voltage_range_v' => array(
					'value'    => '180~900',
					'unit'     => 'V',
					'citation' => array(
						'url'  => $local,
						'page' => 2,
					),
				),
				'comms'                => array(
					'value'    => 'Wi-Fi',
					'citation' => array(
						'url'  => 'https://www.example.com/some.pdf',
						'page' => 3,
					),
				),
				'other_port'           => array(
					'value'    => '1',
					'citation' => array(
						'url'  => 'http://127.0.0.1:1/wp-content/uploads/evil.pdf',
						'page' => 1,
					),
				),
			),
			$local
		);

		$item = EngineeringFeed::item( 4107 );

		$this->assertNotNull( $item );
		$this->assertSame(
			array( 'mppt_voltage_range_v' ),
			array_keys( get_object_vars( $item['figures'] ) ),
			'the instance citation stays; another site and another port stay out'
		);
		$figures = get_object_vars( $item['figures'] );
		$this->assertSame( $canonical, $figures['mppt_voltage_range_v']['citation']['url'] );
		$this->assertSame( 2, $figures['mppt_voltage_range_v']['citation']['page'] );
		$this->assertSame( '180~900', $figures['mppt_voltage_range_v']['value'] );
		$this->assertSame( $canonical, $item['documents'][0]['url'] );
	}

	/**
	 * On production the hosted-citation rule stays the closed host list.
	 * An instance address is not a document we host there.
	 */
	public function test_an_instance_address_is_not_hosted_when_this_site_is_production(): void {
		WP_Mock::userFunction(
			'home_url',
			array(
				'return' => 'https://de-linker.com',
				'times'  => '0+',
			)
		);
		$this->mock_query();
		$this->mock_meta(
			4107,
			array(
				'mppt_voltage_range_v' => array(
					'value'    => '180~900',
					'unit'     => 'V',
					'citation' => array(
						'url'  => 'http://127.0.0.1:9240/wp-content/uploads/2026/09/H2.pdf',
						'page' => 2,
					),
				),
			)
		);

		$item = EngineeringFeed::item( 4107 );

		$this->assertNotNull( $item );
		$this->assertSame( array(), get_object_vars( $item['figures'] ) );
		$this->assertSame(
			'https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf',
			$item['documents'][0]['url'],
			'a production document URL is not rewritten'
		);
	}

	/**
	 * A product without cited figures carries figures as an empty JSON
	 * object, never an empty list (feed.schema.json; the PHP empty-array
	 * trap).
	 */
	public function test_figures_without_a_cited_entry_serialize_as_an_empty_object(): void {
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- standing in for wp_json_encode, which WordPress is not here to provide.
				'return' => static fn( $data ): string => (string) json_encode( $data ),
			)
		);
		$this->mock_query();
		$this->mock_meta(
			4107,
			array(
				'comms' => array( 'value' => 'Wi-Fi' ),
			)
		);

		$item = EngineeringFeed::item( 4107 );

		$this->assertNotNull( $item );
		$this->assertSame( array(), get_object_vars( $item['figures'] ) );
		$this->assertSame( '{}', (string) wp_json_encode( $item['figures'] ) );
	}

	/**
	 * The envelope carries the versions of the data files, the contract itself
	 * and the overlay.
	 */
	public function test_the_envelope_carries_the_schema_version_the_compatibility_contract_and_the_overlay(): void {
		$this->mock_cache_warming();
		$this->mock_query();
		$this->mock_meta( 4107, array() );

		$feed = EngineeringFeed::feed();

		$this->assertSame( 1, $feed['schema_version'] );
		$this->assertSame( EngineeringData::compatibility_version(), $feed['compatibility_version'] );
		$this->assertSame( 64, strlen( $feed['compatibility_version'] ), 'the version the data file states' );
		$this->assertArrayHasKey( 'compatibility', $feed );
		$contract = $feed['compatibility'];
		$this->assertIsArray( $contract );
		$this->assertSame( EngineeringData::json( EngineeringData::COMPATIBILITY_FILE ), $contract );
		$this->assertSame( $feed['compatibility_version'], $contract['version'] ?? null, 'the contract the feed carries states the version it reports' );
		$this->assertNotEmpty( $contract['pairs'] ?? array() );
		$this->assertIsArray( $feed['overlay'] );
		$this->assertSame( 'mat_trina_solar_tsm_460neg9r_28', $feed['overlay'][0]['id'] );
		$this->assertSame( 'pv_module', $feed['overlay'][0]['kind'] );
		$this->assertArrayNotHasKey( 'series', $feed['overlay'][0] );
		$this->assertSame( 'en', $feed['overlay'][0]['documents'][0]['lang'] );
		$this->assertNotEmpty( $feed['generated_at'] );
	}

	/**
	 * With `since` only the products modified after it are asked for: the
	 * query carries the modified-after condition on the GMT column.
	 */
	public function test_since_narrows_the_product_query_to_the_modified(): void {
		$this->mock_cache_warming();
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
		$this->mock_cache_warming();
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
	 * The feed warms the post meta and product term caches in one bulk call
	 * each before reading the products: no per-item meta or term queries.
	 */
	public function test_the_feed_warms_the_meta_and_term_caches_for_its_products(): void {
		$this->mock_meta( 4107, array() );
		$this->mock_query();
		$warmed_meta  = null;
		$warmed_terms = null;
		WP_Mock::userFunction(
			'update_postmeta_cache',
			array(
				'args'   => array( WP_Mock\Functions::type( 'array' ) ),
				'times'  => 1,
				'return' => static function ( array $ids ) use ( &$warmed_meta ): array {
					$warmed_meta = $ids;

					return array();
				},
			)
		);
		WP_Mock::userFunction(
			'update_object_term_cache',
			array(
				'args'   => array( WP_Mock\Functions::type( 'array' ), 'product' ),
				'times'  => 1,
				'return' => static function ( array $ids, string $object_type ) use ( &$warmed_terms ): array {
					$warmed_terms = array( $ids, $object_type );

					return array();
				},
			)
		);

		EngineeringFeed::feed();

		$this->assertSame( array( 4107 ), $warmed_meta, 'one bulk meta cache load with every product ID' );
		$this->assertSame(
			array( array( 4107 ), 'product' ),
			$warmed_terms,
			'one bulk term cache load with every product ID, for the product taxonomies'
		);
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
	 * Mocks the two cache warmings the feed issues for its product IDs.
	 */
	private function mock_cache_warming(): void {
		WP_Mock::userFunction(
			'update_postmeta_cache',
			array(
				'args'   => array( WP_Mock\Functions::type( 'array' ) ),
				'return' => static fn(): array => array(),
			)
		);
		WP_Mock::userFunction(
			'update_object_term_cache',
			array(
				'args'   => array( WP_Mock\Functions::type( 'array' ), 'product' ),
				'return' => static fn(): array => array(),
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
	 * @param int                                 $id           Product ID.
	 * @param array<string, array<string, mixed>> $figures      Figure entries.
	 * @param string                              $document_url Document URL the migration wrote.
	 */
	private function mock_meta( int $id, array $figures, string $document_url = 'https://de-linker.com/wp-content/uploads/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf' ): void {
		$bindings = array();
		foreach ( $figures as $key => $entry ) {
			if ( is_string( $entry['citation']['url'] ?? null ) ) {
				$bindings[ $key ] = array(
					'figure_revision' => \Linker\Commerce\Products\Publication::revision( $entry ),
					'document_id'     => \Linker\Commerce\Products\Publication\DocumentFiles::id( $document_url ),
					'blob_sha256'     => hash_file( 'sha256', $this->publication_uploads . '/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf' ),
				);
			}
		}
		WP_Mock::userFunction( 'get_post_meta' )->with( $id, \Linker\Commerce\Products\Publication\EvidenceBindings::META_KEY, true )->andReturn( $bindings );

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
							'url'   => $document_url,
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
