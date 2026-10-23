<?php
/**
 * Current publication/evidence at the public product abilities.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\CheckCompatibility;
use Linker\Commerce\Abilities\CompareProducts;
use Linker\Commerce\Abilities\GetProduct;
use Linker\Commerce\Abilities\PublicationData;
use Linker\Commerce\Abilities\SearchProducts;
use Linker\Commerce\Tests\Support\MocksLiveProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Publication changes cannot leave facts in a public ability response.
 *
 * @covers \Linker\Commerce\Abilities\PublicationData
 */
final class ProductPublicationTest extends TestCase {
	use MocksLiveProducts;

	/** Use the existing captured product inputs and a permission-only fixture. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		$this->mock_live_products( array( 4107, 1832, 3556, 6519 ) );
	}

	/** Removing the association removes both figures and derived scalar facts. */
	public function test_removed_evidence_cannot_leak_through_scalar_facts(): void {
		$manifest              = $this->publication_data()->manifest();
		$manifest['documents'] = array();
		$data                  = new PublicationData( static fn(): array => $manifest );
		$result                = ( new GetProduct( $data ) )->execute( array( 'product_id' => 4107 ) );
		$this->assertSame( array(), $result['documents'] );
		$this->assertSame( array(), (array) $result['figures'] );
		$this->assertSame( 'unknown', $result['facts']['ac_power_kw'] );
		$this->assertSame( 3, $result['facts']['phase'] );
	}

	/** A source change after assembling facts invalidates the whole read. */
	public function test_inflight_withdrawal_releases_no_product_facts(): void {
		$manifest = $this->publication_data()->manifest();
		$calls    = 0;
		$data     = new PublicationData(
			static function () use ( $manifest, &$calls ): array {
				++$calls;
				if ( $calls > 1 ) {
					$manifest['products'] = array();
				}
				return $manifest;
			}
		);
		$result   = ( new GetProduct( $data ) )->execute( array( 'product_id' => 4107 ) );
		$this->assertSame( '', $result['title'] );
		$this->assertSame( array(), (array) $result['facts'] );
	}

	/** Withdrawal among any considered candidates discards the selection. */
	public function test_candidate_set_changes_before_release(): void {
		$manifest = $this->publication_data()->manifest();
		$calls    = 0;
		$data     = new PublicationData(
			static function () use ( $manifest, &$calls ): array {
				++$calls;
				if ( $calls > 1 ) {
					$manifest['products'] = array_values( array_filter( $manifest['products'], static fn( array $product ): bool => 3556 !== $product['product_id'] ) );
				}
				return $manifest;
			}
		);
		$result   = ( new SearchProducts( $data ) )->select( array( 4107, 3556 ), array(), 'en', 12 );
		$this->assertSame( array(), $result['qualified'] );
	}

	/** A compatibility file without current association grants no verdict. */
	public function test_withdrawn_document_invalidates_compatibility(): void {
		$manifest              = $this->publication_data()->manifest();
		$manifest['documents'] = array();
		$result                = ( new CheckCompatibility( new PublicationData( static fn(): array => $manifest ) ) )->execute(
			array(
				'inverter_id' => 3556,
				'battery_id'  => 6519,
			)
		);
		$this->assertSame(
			array(
				'verdict'    => 'unknown',
				'conditions' => array(),
				'documents'  => array(),
			),
			$result
		);
	}

	/** A partial comparison cannot silently replace the requested whole pair. */
	public function test_unavailable_member_refuses_entire_comparison(): void {
		$manifest             = $this->publication_data()->manifest();
		$manifest['products'] = array_values( array_filter( $manifest['products'], static fn( array $product ): bool => 3556 !== $product['product_id'] ) );
		$result               = ( new CompareProducts( null, new PublicationData( static fn(): array => $manifest ) ) )->execute( array( 'product_ids' => array( 4107, 3556 ) ) );
		$this->assertSame(
			array(
				'products' => array(),
				'rows'     => array(),
			),
			$result
		);
	}
}
