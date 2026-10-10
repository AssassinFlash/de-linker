<?php
/**
 * Tests for linker/search-knowledge and the MariaDB index reader.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\KnowledgeIndex;
use Linker\Commerce\Abilities\SearchKnowledge;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Dense ranking is preferred; FULLTEXT is the fallback when there is no encoder.
 * A product scope that finds nothing falls back to the whole library.
 *
 * @covers \Linker\Commerce\Abilities\SearchKnowledge
 * @covers \Linker\Commerce\Abilities\KnowledgeIndex
 */
final class SearchKnowledgeTest extends TestCase {

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
	}

	/**
	 * OPTIONS exposes the hit schema with chunk_id, document URL and page.
	 */
	public function test_args_expose_chunk_schema(): void {
		$schema = ( new SearchKnowledge() )->args()['output_schema'];
		$hit    = $schema['properties']['hits']['items'];

		$this->assertSame( array( 'chunk_id', 'doc_url', 'title', 'page', 'section', 'text', 'score' ), $hit['required'] );
		$this->assertTrue( ( new SearchKnowledge() )->can_execute() );
	}

	/**
	 * Model codes stay one BOOLEAN MODE phrase.
	 */
	public function test_boolean_query_keeps_model_codes(): void {
		$db         = Mockery::mock( \wpdb::class );
		$db->prefix = 'wp_';
		$index      = new KnowledgeIndex( $db );

		$this->assertSame( '"gw10k-et" "10" "kw"', $index->boolean_query( 'GW10K-ET 10 kW' ) );
	}

	/**
	 * With a query vector the ranking is VEC_DISTANCE_COSINE, not MATCH.
	 */
	public function test_dense_ranking_is_used_when_a_vector_is_available(): void {
		$db   = $this->db();
		$seen = array();
			$db->allows( 'prepare' )->andReturnUsing(
				static function ( string $sql, ...$unused ) use ( &$seen ): string {
					unset( $unused );
					$seen[] = $sql;
					return 'prepared';
				}
			);
			$db->allows( 'get_col' )->andReturn( array( 1 ) );
			$db->allows( 'get_results' )->andReturn(
				array(
					array(
						'rowid'    => 1,
						'id'       => 'c1',
						'url'      => 'https://de-linker.com/a.pdf',
						'title'    => 'Manual',
						'title_en' => 'Manual',
						'page'     => 2,
						'section'  => '',
						'text'     => '10 kW',
					),
				)
			);
			$index = new KnowledgeIndex( $db, static fn(): array => array( 1.0, 0.0 ) );
		$result    = ( new SearchKnowledge( $index ) )->execute(
			array(
				'query' => 'rated AC power',
				'lang'  => 'en',
			)
		);

		$this->assertSame( 'c1', $result['hits'][0]['chunk_id'] );
		$this->assertSame( 2, $result['hits'][0]['page'] );
		$this->assertStringContainsString( 'VEC_DISTANCE_COSINE', $seen[0] );
		$this->assertStringNotContainsString( 'MATCH', $seen[0] );
	}

	/**
	 * Without an encoder the ranking is FULLTEXT.
	 */
	public function test_fulltext_is_the_fallback_without_an_encoder(): void {
		$db   = $this->db();
		$seen = array();
			$db->allows( 'prepare' )->andReturnUsing(
				static function ( string $sql, ...$unused ) use ( &$seen ): string {
					unset( $unused );
					$seen[] = $sql;
					return 'prepared';
				}
			);
		$db->allows( 'get_col' )->andReturn( array( 1 ) );
		$db->allows( 'get_results' )->andReturn(
			array(
				array(
					'rowid'    => 1,
					'id'       => 'c1',
					'url'      => 'https://de-linker.com/a.pdf',
					'title'    => 'Manual',
					'title_en' => 'Manual',
					'page'     => 2,
					'section'  => '',
					'text'     => '10 kW',
				),
			)
		);
		$index  = new KnowledgeIndex( $db, null );
		$result = ( new SearchKnowledge( $index ) )->execute(
			array(
				'query' => 'GW10K-ET',
				'lang'  => 'en',
			)
		);

		$this->assertSame( 'c1', $result['hits'][0]['chunk_id'] );
		$this->assertStringContainsString( 'MATCH', $seen[0] );
		$this->assertStringNotContainsString( 'VEC_DISTANCE', $seen[0] );
	}

	/**
	 * An empty product-scoped ranking retries the whole library.
	 */
	public function test_empty_product_scope_falls_back_to_the_library(): void {
		$db    = $this->db();
		$calls = 0;
		$db->allows( 'prepare' )->andReturn( 'prepared' );
		$db->allows( 'get_col' )->andReturnUsing(
			static function () use ( &$calls ): array {
				++$calls;
				return 1 === $calls ? array() : array( 4 );
			}
		);
		$db->allows( 'get_results' )->andReturn(
			array(
				array(
					'rowid'    => 4,
					'id'       => 'c4',
					'url'      => 'https://de-linker.com/b.pdf',
					'title'    => 'Other',
					'title_en' => 'Other',
					'page'     => 1,
					'section'  => '',
					'text'     => 'text',
				),
			)
		);
		$index  = new KnowledgeIndex( $db, null );
		$result = ( new SearchKnowledge( $index ) )->execute(
			array(
				'query'       => 'hybrid',
				'lang'        => 'en',
				'product_ids' => array( 4107 ),
			)
		);

		$this->assertSame( 2, $calls );
		$this->assertSame( 'c4', $result['hits'][0]['chunk_id'] );
	}

	/**
	 * A wpdb-shaped double: prefix plus the methods KnowledgeIndex calls.
	 *
	 * @return \wpdb&\Mockery\MockInterface
	 */
	private function db() {
		$db         = Mockery::mock( \wpdb::class );
		$db->prefix = 'wp_';

		return $db;
	}
}
