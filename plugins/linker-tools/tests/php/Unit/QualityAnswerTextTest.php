<?php
/**
 * Tests for the last answer the admin's conversation view shows.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\QualityPage;
use WP_Mock\Tools\TestCase;

/**
 * The stored stream's text: what the team reads behind the contact mail's
 * "Read the whole conversation" (#243).
 *
 * @covers \Linker\Tools\Genie\QualityPage::answer_text
 */
final class QualityAnswerTextTest extends TestCase {

	/**
	 * Text and handoff blocks in order; cards and the contact card are not text.
	 */
	public function test_the_answer_text_is_its_text_blocks_in_order(): void {
		$stream = "event: meta\ndata: {\"turn_id\": 4}\n\n"
			. "event: block\ndata: {\"type\": \"text\", \"text\": \"Gern meldet sich jemand.\", \"refs\": []}\n\n"
			. "event: block\ndata: {\"type\": \"cards\", \"product_ids\": [4107]}\n\n"
			. "event: block\ndata: {\"type\": \"handoff\", \"summary\": \"Unser Team beantwortet das unter sales@de-linker.com.\"}\n\n"
			. "event: block\ndata: {\"type\": \"contact\", \"reason\": \"asked\"}\n\n"
			. "event: done\ndata: {\"ok\": true}\n\n";
		$this->assertSame(
			"Gern meldet sich jemand.\n\nUnser Team beantwortet das unter sales@de-linker.com.",
			QualityPage::answer_text( $stream )
		);
	}

	/**
	 * No stream, no answer.
	 */
	public function test_an_empty_stream_has_no_text(): void {
		$this->assertSame( '', QualityPage::answer_text( '' ) );
	}
}
