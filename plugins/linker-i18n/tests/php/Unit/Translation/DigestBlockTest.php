<?php
/**
 * The digest keeps an explicit empty translation status.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Plugin;
use Linker\I18n\Translation\DigestBlock;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Empty content is visible, while registration preserves earlier digest blocks.
 *
 * @covers \Linker\I18n\Translation\DigestBlock
 */
final class DigestBlockTest extends TestCase {

	/**
	 * The optional commerce boundary is loaded only for this consumer test.
	 */
	public function test_empty_block_is_registered_without_replacing_existing_blocks(): void {
		require_once dirname( __DIR__, 5 ) . '/linker-commerce/includes/Digest/Block.php';
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_terms', array( 'return' => array() ) );
		$existing = new \stdClass();
		$blocks   = ( new Plugin( '/plugin/linker-i18n.php' ) )->digest_blocks( array( $existing ) );
		$this->assertSame( $existing, $blocks[0] );
		$this->assertCount( 2, $blocks );
		$this->assertInstanceOf( DigestBlock::class, $blocks[1] );
		$this->assertSame( 'german_translation_exceptions', $blocks[1]->id() );
		$this->assertSame( 'German translation exceptions (0)', $blocks[1]->title() );
		$this->assertSame( array(), $blocks[1]->entries() );
		$this->assertSame( 'No German translation exceptions.', $blocks[1]->empty_text() );
	}
}
