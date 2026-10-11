<?php
/**
 * The accounts waiting for the team's approval.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Digest\Block;
use WP_User;

/**
 * The first block of the daily digest (docs/specs/74-daily-digest.md, the
 * block interface): the customer accounts whose state is not approved, oldest
 * first, each with the way to its admin profile. The set is the approval
 * ticket's (docs/specs/11-commerce.md, the status contract): every account
 * whose role is customer and whose state is not approved waits — read through
 * Approval::status(), the one authority, never off the meta. The digest's
 * assembly reaches this block through the linker_commerce_digest_blocks filter
 * (Registration\Module), which puts it in front of the digest's own blocks.
 */
final class PendingApprovals implements Block {

	/**
	 * Stable identifier of the block.
	 */
	public const ID = 'pending_accounts';

	/**
	 * Sets up the block.
	 *
	 * @param Approval $approval The account approval rule.
	 */
	public function __construct( private readonly Approval $approval = new Approval() ) {}

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
		return __( 'Accounts waiting for approval', 'linker-commerce' );
	}

	/**
	 * The customers without approval, oldest first.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$entries = array();
		foreach ( get_users(
			array(
				'role'    => 'customer',
				'orderby' => 'registered',
				'order'   => 'ASC',
			)
		) as $customer ) {
			if ( ! $customer instanceof WP_User || Approval::APPROVED === $this->approval->status( $customer->ID ) ) {
				continue;
			}
			$entries[] = $this->entry( $customer );
		}
		return $entries;
	}

	/**
	 * The sentence a block with no open items shows.
	 */
	public function empty_text(): string {
		return __( 'No account is waiting for approval.', 'linker-commerce' );
	}

	/**
	 * One account as the digest lists it: the company, when it registered and
	 * the way to its profile in the admin. The date is written as an
	 * unambiguous day, not through the site's date format option: the digest
	 * speaks the site's language, and that option need not be that language's
	 * format (docs/specs/74-daily-digest.md, the mail's own rule).
	 *
	 * @param WP_User $customer The account.
	 * @return array{label: string, url: string, link_text: string, detail: string}
	 */
	private function entry( WP_User $customer ): array {
		$company = (string) get_user_meta( $customer->ID, 'billing_company', true );
		return array(
			'label'     => '' !== $company ? $company : $customer->display_name,
			'url'       => (string) admin_url( 'user-edit.php?user_id=' . $customer->ID ),
			'link_text' => __( 'Open the customer', 'linker-commerce' ),
			'detail'    => sprintf(
				/* translators: %s: the day and time the account registered. */
				__( 'Registered on %s', 'linker-commerce' ),
				(string) mysql2date( 'Y-m-d H:i', $customer->user_registered )
			),
		);
	}
}
