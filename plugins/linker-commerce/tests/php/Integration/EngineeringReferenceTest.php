<?php
/**
 * Real Woo adoption and immediate withdrawal of an engineering reference input.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\EngineeringFeed;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use Linker\Commerce\Products\Publication\ReferenceMigration;
use Linker\Commerce\Products\Publication\Visibility;
use Linker\Commerce\Products\SelectionFacts;
use WC_Cart;
use WC_Product;
use WP_REST_Request;

/**
 * Adopted engineering inputs remain ordinary current Woo dependencies.
 *
 * @coversNothing
 */
final class EngineeringReferenceTest extends IntegrationTestCase {
	/** Dry runs write nothing; first adoption uses existing Woo fields and evidence. */
	public function test_native_migration_is_hidden_non_purchasable_and_idempotent(): void {
		$input = $this->input();
		$plan  = ReferenceMigration::run( $input, true );
		$this->assertSame( 'would_create', $plan['action'] );
		$this->assertSame( 0, $plan['product_id'] );
		$this->assertSame( array(), $this->reference_ids( $plan['engineering_id'] ) );
		$result = ReferenceMigration::run( $input, false );
		$id     = $result['product_id'];
		$this->retain_fixture_product( $id );
		$this->assertSame( 'created', $result['action'] );
		$product = wc_get_product( $id );
		$this->assertInstanceOf( WC_Product::class, $product );
		$this->assertSame( 'publish', $product->get_status() );
		$this->assertSame( 'hidden', $product->get_catalog_visibility() );
		$this->assertTrue( $product->is_virtual() );
		$this->assertSame( '', $product->get_price( 'edit' ) );
		$this->assertSame( '', $product->get_sku() );
		$this->assertSame( array(), wp_get_object_terms( $id, 'product_cat', array( 'fields' => 'ids' ) ) );
		$default_category = (int) get_option( 'default_product_cat' );
		$product->set_category_ids( array( $default_category ) );
		$product->save();
		$this->assertSame( array(), wp_get_object_terms( $id, 'product_cat', array( 'fields' => 'ids' ) ), 'A subsequent native Woo save cannot restore a reference category.' );
		wp_set_object_terms( $id, array( $default_category ), 'product_cat' );
		$this->assertSame( array(), wp_get_object_terms( $id, 'product_cat', array( 'fields' => 'ids' ) ), 'Direct native term assignment also excludes engineering references.' );
		$ordinary = $this->product( '1' );
		wp_set_object_terms( $ordinary->get_id(), array(), 'product_cat' );
		$ordinary_categories = wp_get_object_terms( $ordinary->get_id(), 'product_cat', array( 'fields' => 'ids' ) );
		$this->assertIsArray( $ordinary_categories );
		$this->assertContains( $default_category, $ordinary_categories, 'Woo still restores the default category for an ordinary product.' );
		$this->assertFalse( $product->is_purchasable(), 'The real priority chain must refuse even unpriced-inquiry permission.' );
		$this->assertFalse( $product->is_visible() );
		$this->assertCount( 30, get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true ) );
		$this->assertCount( 30, get_post_meta( $id, EvidenceBindings::META_KEY, true ) );
		$this->assertCount( 2, Publication::document_rows( $id ) );
		$feed      = EngineeringFeed::feed();
		$reference = $this->reference( $feed, $id );
		$this->assertNotNull( $reference );
		$this->assertSame( $result['engineering_id'], $reference['id'] );
		$this->assertSame( 'Trina Solar', $reference['brand'] );
		$this->assertSame( 'TSM-460NEG9R.28', $reference['model'] );
		$this->assertSame( $reference['product_revision'], $reference['reference_revision'] );
		$this->assertCount( 30, get_object_vars( $reference['figures'] ) );
		$this->assertNotContains( $id, array_column( $feed['products'], 'id' ) );
		$this->assertTrue( Publication::validate( $this->dependencies( $reference ) )['valid'] );
		$cart = new WC_Cart();
		$cart->set_cart_contents(
			array(
				'stale-reference' => array(
					'product_id' => $id,
					'data'       => $product,
					'quantity'   => 1,
				),
			)
		);
		( new Visibility() )->prune( $cart );
		$this->assertSame( array(), $cart->get_cart_contents() );
		foreach ( array( '/wc/store/v1/products/' . $id, '/wc/store/v1/products' ) as $route ) {
			$request = new WP_REST_Request( 'GET', $route );
			$request->set_query_params( array( 'include' => array( $id ) ) );
			$response = rest_do_request( $request );
			if ( '/wc/store/v1/products' === $route ) {
				$this->assertSame( array(), $response->get_data() );
			} else {
				$this->assertSame( 404, $response->get_status() );
			}
		}
		foreach ( array( array( 'models' => array( 'TSM-460NEG9R.28' ) ), array( 'text' => 'Module TSM-460NEG9R.28' ) ) as $body ) {
			$request = new WP_REST_Request( 'POST', '/linker/v1/publication/identify' );
			$request->set_header( 'Content-Type', 'application/json' );
			$request->set_body( (string) wp_json_encode( $body ) );
			$identified = rest_do_request( $request )->get_data();
			$this->assertSame( 'unavailable', $identified['models'][0]['status'] );
			$this->assertArrayNotHasKey( 'product_id', $identified['models'][0] );
		}
		$figures                    = get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true );
		$figures['pmax_w']['value'] = '461';
		update_post_meta( $id, SelectionFacts::FIGURES_META_KEY, $figures );
		$this->assertSame( 'unchanged', ReferenceMigration::run( $input, false )['action'] );
		$this->assertSame( '461', get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true )['pmax_w']['value'] );
		$this->assertSame( array( $id ), $this->reference_ids( $result['engineering_id'] ) );
		$withdraw = ReferenceMigration::withdraw( $id, true );
		$this->assertSame( 'would_withdraw', $withdraw['action'] );
		$this->assertSame( 'publish', get_post_status( $id ) );
		ReferenceMigration::withdraw( $id, false );
		$this->assertSame( 'draft', get_post_status( $id ) );
		$this->assertNull( $this->reference( EngineeringFeed::feed(), $id ) );
		$this->assertFalse( Publication::validate( $this->dependencies( $reference ) )['valid'] );
		$this->assertSame( 'unchanged', ReferenceMigration::run( $input, false )['action'] );
		$this->assertSame( 'draft', get_post_status( $id ), 'An idempotent migration must never republish a withdrawn record.' );
	}

	/** Replaced bytes and revoked relations cannot be restored by the import file. */
	public function test_replacement_and_relation_removal_are_current_woo_authority(): void {
		$input  = $this->input();
		$result = ReferenceMigration::run( $input, false );
		$id     = $result['product_id'];
		$this->retain_fixture_product( $id );
		$before = $this->reference( EngineeringFeed::feed(), $id );
		$this->assertNotNull( $before );
		$bindings  = get_post_meta( $id, EvidenceBindings::META_KEY, true );
		$documents = Publication::document_rows( $id );
		$file      = \Linker\Commerce\Products\Publication\DocumentFiles::resolve( $documents[0]['url'] );
		$this->assertNotNull( $file );
		file_put_contents( $file['path'], "%PDF-1.4\nreplacement reference bytes\n%%EOF" );
		$this->assertSame( 'unchanged', ReferenceMigration::run( $input, false )['action'] );
		EvidenceBindings::capture( $id, true );
		$this->assertSame( $bindings, get_post_meta( $id, EvidenceBindings::META_KEY, true ) );
		$this->assertNull( $this->reference( EngineeringFeed::feed(), $id ), 'Missing bound required values omit the reference without poisoning other engine products.' );
		$this->assertFalse( Publication::validate( $this->dependencies( $before ) )['valid'] );
		$figures                    = get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true );
		$figures['pmax_w']['value'] = '461';
		update_post_meta( $id, SelectionFacts::FIGURES_META_KEY, $figures );
		$this->assertNull( $this->reference( EngineeringFeed::feed(), $id ), 'One corrected value cannot authorize the other required values.' );
		foreach ( $figures as &$figure ) {
			$figure['citation']['page'] = 3;
		}
		unset( $figure );
		update_post_meta( $id, SelectionFacts::FIGURES_META_KEY, $figures );
		$current = $this->reference( EngineeringFeed::feed(), $id );
		$this->assertNotNull( $current );
		$this->assertCount( 30, get_object_vars( $current['figures'] ) );
		$compatibility = Publication::manifest()['compatibility_revision'];
		update_post_meta( $id, EngineeringData::DOCUMENTS_META_KEY, array() );
		$this->assertSame( 'unchanged', ReferenceMigration::run( $input, false )['action'] );
		$this->assertNull( $this->reference( EngineeringFeed::feed(), $id ) );
		$this->assertFalse( Publication::validate( $this->dependencies( $current ) )['valid'] );
		$this->assertSame( $compatibility, Publication::manifest()['compatibility_revision'], 'Reference changes do not invalidate a scope which uses only the compatibility contract.' );
		$this->assertFileExists( $file['path'] );
	}

	/**
	 * Reuse the verified 30 facts and 2 document rows, with fixture-owned files.
	 *
	 * @return array<string,mixed>
	 */
	private function input(): array {
		$input = EngineeringData::json( EngineeringData::OVERLAY_FILE );
		$this->assertIsArray( $input );
		$tag       = self::tag();
		$directory = wp_upload_dir()['basedir'] . '/reference-tests-' . $tag;
		$this->assertTrue( wp_mkdir_p( $directory ) );
		$this->later(
			static function () use ( $directory ): void {
				rmdir( $directory );
			}
		);
		$urls = array();
		foreach ( $input['overlay'][0]['documents'] as $index => &$document ) {
			$path = $directory . '/module-' . $index . '.pdf';
			file_put_contents( $path, "%PDF-1.4\nreference fixture " . $index . "\n%%EOF" );
			$url                      = wp_upload_dir()['baseurl'] . '/reference-tests-' . $tag . '/module-' . $index . '.pdf';
			$urls[ $document['url'] ] = $url;
			$document['url']          = $url;
			$this->later(
				static function () use ( $path ): void {
					wp_delete_file( $path );
				}
			);
		}
		unset( $document );
		foreach ( $input['overlay'][0]['figures'] as &$figure ) {
			$figure['citation']['url'] = $urls[ $figure['citation']['url'] ];
		}
		unset( $figure );
		$input['overlay'][0]['id'] = 'mat_reference_fixture_' . $tag;
		return $input;
	}

	/**
	 * Identity lookup is only for this test's unique migration input.
	 *
	 * @param string $identity Engineering identity.
	 * @return list<int>
	 */
	private function reference_ids( string $identity ): array {
		return array_values(
			array_map(
				'intval',
				get_posts(
					array(
						'post_type'               => 'product',
						'post_status'             => 'any',
						'fields'                  => 'ids',
						'posts_per_page'          => -1,
						'meta_key'                => EngineeringReference::ID_META_KEY, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Fixture's unique migration identity.
					'meta_value'                  => $identity, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- Bounded fixture lookup.
					'suppress_filters'            => true,
					'lang'                        => '',
					'linker_publication_internal' => true,
					'cache_results'               => false,
					)
				)
			)
		);
	}

	/**
	 * Remove only the newly created fixture record on exit.
	 *
	 * @param int $id Fixture product identity.
	 */
	private function retain_fixture_product( int $id ): void {
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
	}

	/**
	 * Select only this fixture from the site's full current feed.
	 *
	 * @param array<string,mixed> $feed Actual feed.
	 * @param int                 $id Canonical product identity.
	 * @return array<string,mixed>|null
	 */
	private function reference( array $feed, int $id ): ?array {
		foreach ( $feed['overlay'] as $reference ) {
			if ( $id === $reference['canonical_product_id'] ) {
				return $reference;
			}
		}
		return null;
	}

	/**
	 * The reference uses the same normal current product/document dependency API.
	 *
	 * @param array<string,mixed> $reference Current overlay record.
	 * @return array<string,mixed>
	 */
	private function dependencies( array $reference ): array {
		$id = $reference['canonical_product_id'];
		return array(
			'products'  => array(
				array(
					'product_id'       => $id,
					'product_revision' => $reference['product_revision'],
				),
			),
			'documents' => array_map(
				static fn ( array $document ): array => array(
					'document_id'       => $document['document_id'],
					'document_revision' => $document['document_revision'],
					'product_id'        => $id,
				),
				$reference['documents']
			),
		);
	}
}
