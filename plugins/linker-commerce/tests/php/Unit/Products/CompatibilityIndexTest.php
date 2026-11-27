<?php
/**
 * Public product compatibility and certificate evidence.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Tests\Support\MocksLiveProducts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/** @covers \Linker\Commerce\Products\CompatibilityIndex */
final class CompatibilityIndexTest extends TestCase {
	use MocksLiveProducts;

	/** Published releases include the required control unit and exclude the one-module battery. */
	public function test_equipment_links_share_the_current_declarations(): void {
		$this->mock_live_products( array( 4107, 1832, 2067, 2092, 3556, 6519 ) );
		WP_Mock::userFunction( '__' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'wc_format_localized_decimal' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'wp_list_pluck' )->andReturnUsing( 'array_column' );
		$manifest = $this->publication_data()->manifest();
		foreach ( $manifest['products'] as &$row ) {
			$row['locale_product_ids'] = array( 'en' => $row['product_id'] );
		}
		unset( $row );
		$h2 = array_column( CompatibilityIndex::for_product( 4107, $manifest )['compatible'], null, 'product_id' );
		$this->assertArrayNotHasKey( 1832, $h2 );
		$this->assertSame( 'released_with_accessory', $h2[2067]['verdict'] );
		$this->assertContains( 2092, array_column( $h2[2067]['accessories'], 'product_id' ) );
		$this->assertContains( 4107, array_column( CompatibilityIndex::for_product( 2092, $manifest )['accessory_for'], 'product_id' ) );
		$this->assertContains( 6519, array_column( CompatibilityIndex::for_product( 3556, $manifest )['compatible'], 'product_id' ) );
		$this->assertSame( array(), CompatibilityIndex::for_product( 99999, $manifest )['compatible'] );
	}


	/** A document's publication role determines whether its title describes a certificate. */
	public function test_only_certificates_supply_grid_standards(): void {
		$row = array(
			'title' => 'ET certificate: VDE-AR-N 4105 and EN 50549-1',
			'url'   => 'https://example.org/et.pdf',
			'type'  => 'certificate',
		);
		$this->assertSame( array( 'EN 50549', 'VDE-AR-N 4105' ), CompatibilityIndex::document_standards( $row ) );
		$row['type'] = 'manual';
		$this->assertSame( array(), CompatibilityIndex::document_standards( $row ) );
	}
}
