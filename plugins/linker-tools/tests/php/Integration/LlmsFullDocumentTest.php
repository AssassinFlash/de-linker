<?php
/**
 * The full equipment reference reflects current Woo publication and sales scope.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Commerce\Products\EngineeringReference;
use Linker\Tools\LlmsTxt;
use PHPUnit\Framework\TestCase;

/**
 * Exercise the public reference against native products.
 *
 * @covers \Linker\Tools\LlmsTxt
 */
final class LlmsFullDocumentTest extends TestCase {
	/** Only the published sales product has a row and a public permalink. */
	public function test_full_document_uses_current_sales_products(): void {
		$fixtures = array();
		try {
			foreach ( array( 'Public test inverter', 'Draft test inverter', 'Reference test cable' ) as $name ) {
				$product = new \WC_Product_Simple();
				$product->set_name( $name );
				$product->set_status( 'Draft test inverter' === $name ? 'draft' : 'publish' );
				$product->save();
				$fixtures[] = $product;
				pll_set_post_language( $product->get_id(), 'en' );
			}
			update_post_meta( $fixtures[2]->get_id(), EngineeringReference::ROLE_META_KEY, EngineeringReference::CABLE );
			$text = LlmsTxt::full_document( untrailingslashit( (string) get_option( 'home' ) ) );
			self::assertStringContainsString( '| Public test inverter |', $text );
			self::assertStringContainsString( (string) get_permalink( $fixtures[0]->get_id() ), $text );
			self::assertStringNotContainsString( 'Draft test inverter', $text );
			self::assertStringNotContainsString( 'Reference test cable', $text );
			self::assertStringNotContainsString( 'not_released', $text );
			self::assertStringContainsString( '## Verified Inverter & Battery Compatibility', $text );
			self::assertStringContainsString( '## Meter, Backup & Parallel Controller Rules', $text );
		} finally {
			foreach ( $fixtures as $product ) {
				$product->delete( true );
			}
		}
	}
}
