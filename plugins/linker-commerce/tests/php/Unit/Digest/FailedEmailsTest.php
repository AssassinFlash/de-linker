<?php
/**
 * Tests for the digest's failed-emails block.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\FailedEmails;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use stdClass;
use WP_Mock;

/**
 * Tests for FailedEmails: one entry per message whose retries ran out, with
 * subject, recipients and last error.
 *
 * @covers \Linker\Commerce\Digest\FailedEmails
 */
final class FailedEmailsTest extends TestCase {

	/**
	 * Translation returns its argument.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * The block lists what the queue holds as failed.
	 */
	public function test_entries_from_the_queue(): void {
		$post     = new stdClass();
		$post->ID = 7;
		$message  = json_encode(
			array(
				'to'      => array( 'sales@de-linker.com', 'ops@example.test' ),
				'subject' => 'Daily digest, October 11, 2026',
				'body'    => '<p>…</p>',
				'headers' => array(),
			)
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'   => JobStore::POST_TYPE,
						'post_status' => JobStore::FAILED_STATUS,
						'numberposts' => -1,
						'orderby'     => 'date',
						'order'       => 'ASC',
					),
				),
				'return' => array( $post ),
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn ( int $id, string $key ): string => '_linker_mail_message' === $key ? (string) $message : 'Could not instantiate mail function.',
			)
		);

		$block   = new FailedEmails( new JobStore() );
		$entries = $block->entries();

		$this->assertCount( 1, $entries );
		$this->assertSame( 'Daily digest, October 11, 2026', $entries[0]['label'] );
		$this->assertSame( '', $entries[0]['url'] );
		$this->assertSame( 'To: sales@de-linker.com, ops@example.test – Error: Could not instantiate mail function.', $entries[0]['detail'] );
		$this->assertSame( 'No email failed to send.', $block->empty_text() );
	}

	/**
	 * An empty queue is an empty block.
	 */
	public function test_no_failures_no_entries(): void {
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );

		$this->assertSame( array(), ( new FailedEmails( new JobStore() ) )->entries() );
	}
}
