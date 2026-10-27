<?php
/**
 * Identity permission reads are current without loading technical document bytes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication\Controller;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Tests\Support\CurrentFaqProduct;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * A label status never needs a product's PDF or technical facts.
 *
 * @covers \Linker\Commerce\Products\Publication
 * @covers \Linker\Commerce\Products\Publication\Controller
 */
final class IdentityTest extends TestCase {
	use CurrentFaqProduct;

	/** A real PDF association makes accidental manifest loading observable. */
	public function setUp(): void {
		parent::setUp();
		$this->current_faq_product( 12, array() );
		WP_Mock::userFunction( 'nocache_headers' );
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing( static fn ( mixed $value ): bool => $value instanceof \WP_Error );
		WP_Mock::userFunction( 'wp_get_object_terms' )->andReturnUsing(
			static fn ( array $ids ): array => array_map(
				static fn ( int $id ): object => (object) array(
					'object_id' => $id,
					'name'      => 'MODEL-12',
				),
				$ids
			)
		)->byDefault();
	}

	/** Remove only the fixture's generated upload. */
	public function tearDown(): void {
		$this->remove_managed_documents();
		parent::tearDown();
	}

	/** This fails if identify traverses any associated PDF path or hashes bytes. */
	public function test_identity_avoids_document_io_and_refreshes_once(): void {
		WP_Mock::userFunction( 'wp_upload_dir' )->andReturnUsing(
			static function (): never {
				throw new \LogicException( 'Identify must not resolve or hash technical documents.' );
			}
		);
		$refreshes = 0;
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			static function () use ( &$refreshes ): bool {
				++$refreshes;
				return true;
			}
		);
		$ids = array( 12, 13 );
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			static function () use ( &$ids ): array {
				return $ids;
			}
		);
		WP_Mock::userFunction( 'get_post_type' )->with( 13 )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->with( 13 )->andReturn( 'draft' );
		$primes = array();
		WP_Mock::userFunction( '_prime_post_caches' )->andReturnUsing(
			static function ( array $product_ids, bool $terms, bool $meta ) use ( &$primes ): void {
				$primes[] = array( $product_ids, $terms, $meta );
			}
		);
		$term_reads = array();
		WP_Mock::userFunction( 'wp_get_object_terms' )->andReturnUsing(
			static function ( mixed $product_ids, string $taxonomy, array $args ) use ( &$term_reads ): array {
				$term_reads[] = array( $product_ids, $taxonomy, $args );
				if ( ! is_array( $product_ids ) ) {
					return array( 12 === $product_ids ? 'MODEL-12' : 'DRAFT-13' );
				}
				// Native relationship IDs, not term IDs or return order, own each label.
				return array(
					(object) array(
						'term_id'          => 12,
						'term_taxonomy_id' => 112,
						'object_id'        => 13,
						'name'             => 'DRAFT-13',
					),
					(object) array(
						'term_id'          => 13,
						'term_taxonomy_id' => 113,
						'object_id'        => 12,
						'name'             => 'MODEL-12',
					),
				);
			}
		);
		foreach ( array( array( 'models' => array( 'MODEL-12', 'UNKNOWN', 'DRAFT-13' ) ), array( 'text' => 'Use MODEL-12 alongside DRAFT-13 here.' ) ) as $body ) {
			$refreshes  = 0;
			$primes     = array();
			$term_reads = array();
			$response   = $this->identify( $body );
			$this->assertInstanceOf( \WP_REST_Response::class, $response );
			$data = $response->get_data();
			$this->assertSame( 'published', $data['models'][0]['status'] );
			$this->assertSame( 12, $data['models'][0]['product_id'] );
			$this->assertSame( 1, $refreshes );
			$this->assertSame(
				array(
					array(
						array( 12, 13 ),
						'pa_model',
						array(
							'fields' => 'all_with_object_id',
							'lang'   => '',
						),
					),
				),
				$term_reads
			);
			$this->assertSame( array( array( array( 12, 13 ), false, true ) ), $primes );
			$this->assertSame( 'no-store, private, max-age=0', $response->get_headers()['Cache-Control'] );
			$this->assertSame( array( 'model', 'status', 'product_id' ), array_keys( $data['models'][0] ) );
			if ( isset( $body['models'] ) ) {
				$this->assertSame(
					array(
						'model'  => 'UNKNOWN',
						'status' => 'unknown',
					),
					$data['models'][1]
				);
			}
			$this->assertSame(
				array(
					'model'  => isset( $body['models'] ) ? 'DRAFT-13' : 'draft-13',
					'status' => 'unavailable',
				),
				$data['models'][ isset( $body['models'] ) ? 2 : 1 ]
			);
		}
		$ids        = array();
		$primes     = array();
		$term_reads = array();
		$response   = $this->identify( array( 'text' => 'MODEL-12 DRAFT-13' ) );
		$this->assertInstanceOf( \WP_REST_Response::class, $response );
		$this->assertSame( array( 'models' => array() ), $response->get_data() );
		$this->assertSame( array(), $primes );
		$this->assertSame( array(), $term_reads );
	}

	/** Native status and role changes are read again on each call, without a TTL. */
	public function test_each_read_observes_native_withdrawal_and_reference_role(): void {
		$status = 'publish';
		WP_Mock::userFunction( 'get_post_status' )->with( 12 )->andReturnUsing(
			static function () use ( &$status ): string {
				return $status;
			}
		);
		$body     = array( 'models' => array( 'MODEL-12' ) );
		$response = $this->identify( $body );
		$this->assertInstanceOf( \WP_REST_Response::class, $response );
		$this->assertSame( 'published', $response->get_data()['models'][0]['status'] );
		$status   = 'draft';
		$response = $this->identify( $body );
		$this->assertInstanceOf( \WP_REST_Response::class, $response );
		$this->assertSame(
			array(
				array(
					'model'  => 'MODEL-12',
					'status' => 'unavailable',
				),
			),
			$response->get_data()['models']
		);
		$status = 'publish';
		$this->current_faq_meta[ EngineeringReference::ROLE_META_KEY ] = EngineeringReference::PV_MODULE;
		$response = $this->identify( $body );
		$this->assertInstanceOf( \WP_REST_Response::class, $response );
		$this->assertSame(
			array(
				array(
					'model'  => 'MODEL-12',
					'status' => 'unavailable',
				),
			),
			$response->get_data()['models']
		);
	}

	/**
	 * A published mirror cannot extend an unavailable source or draft locale.
	 *
	 * @throws \LogicException When the native identity filter mock is unavailable.
	 */
	public function test_identity_requires_both_locale_and_canonical_publication(): void {
		WP_Mock::userFunction( 'get_posts' )->andReturn( array( 13 ) );
		WP_Mock::userFunction( 'get_post_type' )->with( 13 )->andReturn( 'product' );
		WP_Mock::userFunction( 'has_filter' )->andReturn( true );
		foreach ( array(
			12 => 12,
			13 => 12,
		) as $locale => $source ) {
			$responder = WP_Mock::onFilter( 'linker_commerce_facts_product_id' )->with( $locale );
			if ( ! $responder instanceof \WP_Mock\Filter_Responder ) {
				throw new \LogicException( 'Expected the native canonical identity filter responder.' );
			}
			$responder->reply( $source );
		}
		$states = array(
			12 => 'draft',
			13 => 'publish',
		);
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing(
			static function ( int $id ) use ( &$states ): string {
				return $states[ $id ];
			}
		);
		foreach ( array( array( 'draft', 'publish', 'unavailable' ), array( 'publish', 'draft', 'unavailable' ), array( 'publish', 'publish', 'published' ) ) as [ $source, $locale, $expected ] ) {
			$states   = array(
				12 => $source,
				13 => $locale,
			);
			$response = $this->identify( array( 'models' => array( 'MODEL-12' ) ) );
			$this->assertInstanceOf( \WP_REST_Response::class, $response );
			$this->assertSame( $expected, $response->get_data()['models'][0]['status'] );
			if ( 'published' === $expected ) {
				$this->assertSame( 12, $response->get_data()['models'][0]['product_id'] );
			} else {
				$this->assertArrayNotHasKey( 'product_id', $response->get_data()['models'][0] );
			}
		}
	}

	/** Duplicate labels still prefer the currently published ordinary source. */
	public function test_duplicate_labels_preserve_the_published_preference(): void {
		WP_Mock::userFunction( 'get_post_type' )->with( 13 )->andReturn( 'product' );
		$status = 'draft';
		WP_Mock::userFunction( 'get_post_status' )->with( 13 )->andReturnUsing(
			static function () use ( &$status ): string {
				return $status;
			}
		);
		WP_Mock::userFunction( 'wp_get_object_terms' )->andReturn(
			array(
				(object) array(
					'object_id' => 13,
					'name'      => 'MODEL-12',
				),
				(object) array(
					'object_id' => 12,
					'name'      => 'MODEL-12',
				),
			)
		);
		$ids = array();
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			function ( array $query ) use ( &$ids ): array {
				$this->assertFalse( $query['cache_results'] );
				$this->assertSame( '', $query['lang'] );
				$this->assertTrue( $query['linker_publication_internal'] );
				return $ids;
			}
		);
		foreach ( array(
			array( array( 12, 13 ), 'draft', 12 ),
			array( array( 13, 12 ), 'draft', 12 ),
			array( array( 12, 13 ), 'publish', 13 ),
			array( array( 13, 12 ), 'publish', 12 ),
		) as [ $order, $status, $expected ] ) {
			$ids      = $order;
			$response = $this->identify( array( 'models' => array( 'MODEL-12' ) ) );
			$this->assertInstanceOf( \WP_REST_Response::class, $response );
			$this->assertSame(
				array(
					'model'      => 'MODEL-12',
					'status'     => 'published',
					'product_id' => $expected,
				),
				$response->get_data()['models'][0]
			);
		}
	}

	/** A native taxonomy failure cannot be misreported as an unknown label. */
	public function test_unreadable_native_identity_is_explicitly_unavailable(): void {
		WP_Mock::userFunction( 'wp_get_object_terms' )->andReturn( new \WP_Error( 'native_unavailable', 'Internal source error.' ) );
		$response = $this->identify( array( 'models' => array( 'UNKNOWN' ) ) );
		$this->assertInstanceOf( \WP_Error::class, $response );
		$this->assertSame( 'publication_unavailable', $response->get_error_code() );
		$this->assertSame( array( 'status' => 503 ), $response->get_error_data() );
	}

	/**
	 * Exercise the public contract, not an internal projection directly.
	 *
	 * @param array<string,mixed> $body Caller input.
	 * @return \WP_REST_Response|\WP_Error
	 */
	private function identify( array $body ): \WP_REST_Response|\WP_Error {
		$request = Mockery::mock( \WP_REST_Request::class );
		$request->shouldReceive( 'get_json_params' )->andReturn( $body );
		return ( new Controller() )->dispatch( 'identify', $request );
	}
}
