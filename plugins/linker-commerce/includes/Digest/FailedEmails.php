<?php
/**
 * Emails whose retries ran out.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use Linker\Commerce\Mail\JobStore;

/**
 * Block of the queued emails every retry failed for (docs/specs/74-daily-digest.md:
 * no time window — a message stays listed as long as it sits in the queue as
 * failed, which is what the settings screen's notice counts too). The digest
 * is itself such a message when its own send failed, so a broken pipe reports
 * itself in the next day's digest.
 */
final class FailedEmails implements Block {

	/**
	 * Stable identifier of the block.
	 */
	public const ID = 'failed_emails';

	/**
	 * Sets up the block.
	 *
	 * @param JobStore $jobs The mail queue.
	 */
	public function __construct( private readonly JobStore $jobs ) {}

	/**
	 * Stable identifier of the block.
	 */
	public function id(): string {
		return self::ID;
	}

	/**
	 * Heading of the block.
	 */
	public function title(): string {
		return __( 'Emails that could not be delivered', 'linker-commerce' );
	}

	/**
	 * The failed messages, oldest first, with their recipients and last error.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$entries = array();
		foreach ( $this->jobs->failed() as $job ) {
			$entries[] = array(
				'label'     => $job['subject'],
				'url'       => '',
				'link_text' => '',
				'detail'    => sprintf(
					/* translators: 1: the recipients of the email, 2: the error of the last attempt. */
					__( 'To: %1$s – Error: %2$s', 'linker-commerce' ),
					implode( ', ', $job['to'] ),
					$job['error']
				),
			);
		}
		return $entries;
	}

	/**
	 * The sentence a block with no open items shows.
	 */
	public function empty_text(): string {
		return __( 'No email failed to send.', 'linker-commerce' );
	}
}
