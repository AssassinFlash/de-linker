<?php
/**
 * Genie quality in the team's daily digest.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\QualityDigestBlock;
use Linker\Tools\Genie\QualityStore;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for QualityDigestBlock.
 *
 * @covers \Linker\Tools\Genie\QualityDigestBlock
 */
final class QualityDigestBlockTest extends TestCase {

	/**
	 * The block shows the summary line and links to the quality page.
	 *
	 * @throws \LogicException When WP_Mock answers with another responder.
	 */
	public function test_entries_show_the_summary_and_the_page_link(): void {
		require_once dirname( __DIR__, 4 ) . '/linker-commerce/includes/Digest/Block.php';
		$line      = 'Genie quality check, last 24 hours: 12 answers judged, 1 flagged, 2 decided by the second judge, 0 could not be judged.';
		$responder = WP_Mock::onFilter( QualityStore::SUMMARY_FILTER )->withAnyArgs();
		if ( ! $responder instanceof WP_Mock\Filter_Responder ) {
			throw new \LogicException( 'WP_Mock::onFilter() answers with a Filter_Responder.' );
		}
		$responder->reply(
			array(
				'line' => $line,
				'url'  => 'https://example.test/wp-admin/admin.php?page=linker-genie-quality',
			)
		);
		WP_Mock::passthruFunction( '__' );

		$entries = ( new QualityDigestBlock() )->entries();

		$this->assertCount( 1, $entries );
		$this->assertSame( $line, $entries[0]['label'] );
		$this->assertSame(
			'https://example.test/wp-admin/admin.php?page=linker-genie-quality',
			$entries[0]['url']
		);
		$this->assertSame( 'Open', $entries[0]['link_text'] );
		$this->assertSame( '', $entries[0]['detail'] );
	}

	/**
	 * No verdict summary means no entry.
	 *
	 * @throws \LogicException When WP_Mock answers with another responder.
	 */
	public function test_entries_are_empty_without_a_summary(): void {
		require_once dirname( __DIR__, 4 ) . '/linker-commerce/includes/Digest/Block.php';
		$responder = WP_Mock::onFilter( QualityStore::SUMMARY_FILTER )->withAnyArgs();
		if ( ! $responder instanceof WP_Mock\Filter_Responder ) {
			throw new \LogicException( 'WP_Mock::onFilter() answers with a Filter_Responder.' );
		}
		$responder->reply( array() );

		$this->assertSame( array(), ( new QualityDigestBlock() )->entries() );
	}

	/**
	 * The block identifies itself and has its own heading.
	 */
	public function test_identity_and_title(): void {
		require_once dirname( __DIR__, 4 ) . '/linker-commerce/includes/Digest/Block.php';
		WP_Mock::passthruFunction( '__' );

		$block = new QualityDigestBlock();

		$this->assertSame( 'linker_genie_quality', $block->id() );
		$this->assertSame( 'Genie quality check', $block->title() );
		$this->assertSame( '', $block->empty_text() );
		$this->assertSame(
			QualityStore::SUMMARY_FILTER,
			'linker_tools_genie_quality_summary'
		);
	}
}
