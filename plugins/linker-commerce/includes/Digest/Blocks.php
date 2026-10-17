<?php
/**
 * The blocks of a daily digest.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Health\InternalMail;

/**
 * Assembles the digest's blocks: the four this plugin builds, in the order of
 * docs/specs/74-daily-digest.md, then whatever other tickets registered — the
 * approval ticket puts the pending accounts first, so the owner's daily
 * approvals lead the email.
 */
final class Blocks {

	/**
	 * Sets up the assembly.
	 *
	 * @param JobStore $jobs The mail queue, for the failed-emails block.
	 */
	public function __construct( private readonly JobStore $jobs ) {}

	/**
	 * The blocks of today's digest, in order.
	 *
	 * @return list<Block>
	 */
	public function all(): array {
		$blocks = array(
			new InquiriesAwaitingProforma(),
			new ProformasAwaitingReply(),
			new FailedEmails( $this->jobs ),
			new InternalMail(),
		);
		/**
		 * The approval ticket adds the pending-accounts block here, unshifted
		 * onto what it receives (docs/specs/74-daily-digest.md, the block
		 * interface's plug point; introduced with the digest itself). What
		 * comes back is taken on trust only after the checks below.
		 *
		 * @since 0.2.0
		 */
		$filtered = apply_filters( 'linker_commerce_digest_blocks', $blocks );
		if ( ! is_array( $filtered ) ) {
			return $blocks;
		}
		return array_values(
			array_filter(
				$filtered,
				static fn ( $block ): bool => $block instanceof Block
			)
		);
	}
}
