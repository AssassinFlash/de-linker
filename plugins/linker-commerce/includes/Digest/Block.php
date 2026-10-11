<?php
/**
 * One block of the daily digest.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

/**
 * A section of the daily digest email (docs/specs/74-daily-digest.md). The
 * plugin ships the three blocks it can build itself; the approval ticket
 * registers the pending-accounts block through the
 * linker_commerce_digest_blocks filter, with the admin links of its entries.
 */
interface Block {

	/**
	 * Stable identifier of the block.
	 */
	public function id(): string;

	/**
	 * Heading of the block, in the language the email is rendered in.
	 */
	public function title(): string;

	/**
	 * The open items, oldest first.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 *         An empty url or link_text means the entry carries no link; an
	 *         empty detail means it carries nothing but its label.
	 */
	public function entries(): array;

	/**
	 * The sentence a block with no open items shows.
	 */
	public function empty_text(): string;
}
