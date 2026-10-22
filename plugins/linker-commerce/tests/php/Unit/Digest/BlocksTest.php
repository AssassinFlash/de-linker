<?php
/**
 * Tests for the digest's block assembly.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\Block;
use Linker\Commerce\Digest\Blocks;
use Linker\Commerce\Digest\FailedEmails;
use Linker\Commerce\Digest\InquiriesAwaitingProforma;
use Linker\Commerce\Digest\ProformasAwaitingReply;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Tests\TestCase;

/**
 * Tests for Blocks: the four built-in blocks, in order, and the filter the
 * approval ticket adds its block through.
 *
 * @covers \Linker\Commerce\Digest\Blocks
 */
final class BlocksTest extends TestCase {

	/**
	 * The built-in blocks come in the spec's order: inquiries, proformas,
	 * failed emails. Without a registered filter the list passes through.
	 */
	public function test_built_in_blocks_in_order(): void {
		$this->filter_returns( 'linker_commerce_digest_blocks', null );

		$blocks = ( new Blocks( new JobStore() ) )->all();

		$this->assertSame(
			array( InquiriesAwaitingProforma::ID, ProformasAwaitingReply::ID, FailedEmails::ID, 'internal_mail', 'pending_inquiry_reviews' ),
			array_map( static fn ( Block $block ): string => $block->id(), $blocks )
		);
	}

	/**
	 * The filter replaces the list: whatever its callback returns (the
	 * approval ticket's callback unshifts its block onto what it receives)
	 * is the digest's blocks; anything that is not a block comes back out
	 * again.
	 */
	public function test_filter_replaces_and_keeps_blocks_only(): void {
		$pending = new class() implements Block {
			/**
			 * Stable identifier of the block.
			 */
			public function id(): string {
				return 'pending_accounts';
			}

			/**
			 * Heading of the block.
			 */
			public function title(): string {
				return 'Pending accounts';
			}

			/**
			 * The open items.
			 */
			public function entries(): array {
				return array();
			}

			/**
			 * The sentence a block with no open items shows.
			 */
			public function empty_text(): string {
				return '';
			}
		};
		$this->filter_returns( 'linker_commerce_digest_blocks', array( $pending, 'not a block' ) );

		$all = ( new Blocks( new JobStore() ) )->all();

		$this->assertCount( 1, $all );
		$this->assertSame( 'pending_accounts', $all[0]->id() );
	}

	/**
	 * A filter that returns nonsense leaves the built-in blocks standing.
	 */
	public function test_a_broken_filter_keeps_the_built_ins(): void {
		$this->filter_returns( 'linker_commerce_digest_blocks', 'nonsense' );

		$this->assertCount( 5, ( new Blocks( new JobStore() ) )->all() );
	}
}
